#!/usr/bin/env python3
"""claude-bingo — a board of LLM-isms, scored against your own transcripts.

    claude-bingo board                 generate a fresh 5x5 board
    claude-bingo score                 score it against the last 7 days of logs
    claude-bingo score --days 30       ...or however far back you dare look
    claude-bingo phrases               list the phrase bank

Everything runs locally. Transcripts are read, never sent anywhere.
"""

import argparse
import json
import os
import random
import re
import sys
import textwrap
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import phrases

LOG_ROOT = Path.home() / ".claude" / "projects"

CELL_W = 15
FREE = "FREE SPACE"

# ANSI, kept minimal so it degrades to noise-free plain text when piped.
RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
GREEN, YELLOW, RED, CYAN, MAGENTA = (
    "\033[32m", "\033[33m", "\033[31m", "\033[36m", "\033[35m",
)

_BANK = None


def bank():
    """Phrase bank, loaded once per process (workers re-import this module)."""
    global _BANK
    if _BANK is None:
        _BANK = phrases.load()
    return _BANK


def board_path():
    base = os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / "claude-bingo" / "board.json"


def color(s, c):
    return s if not sys.stdout.isatty() else f"{c}{s}{RESET}"


# ---------------------------------------------------------------- board gen

def make_board(size, seed):
    labels = bank()["labels"]
    needed = size * size - (1 if size % 2 else 0)
    if needed > len(labels):
        sys.exit(f"only {len(labels)} phrases in the bank; {size}x{size} needs "
                 f"{needed}")
    rng = random.Random(seed)
    picks = rng.sample(labels, needed)
    if size % 2:
        picks.insert(size * size // 2, FREE)
    return {
        "seed": seed,
        "size": size,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cells": picks,
    }


# ---------------------------------------------------------------- scanning

def recent_logs(days):
    cutoff = time.time() - days * 86400
    for path in LOG_ROOT.rglob("*.jsonl"):
        try:
            if path.stat().st_mtime >= cutoff:
                yield path
        except OSError:
            continue


def _scan_file(args):
    """Worker: return {label: (count, first_example)} for one transcript."""
    path, cutoff_iso, wanted = args
    by_label = bank()["by_label"]
    pats = [(label, by_label[label]) for label in wanted if label in by_label]
    hits = {}
    try:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                if '"assistant"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("type") != "assistant":
                    continue
                if (rec.get("timestamp") or "") < cutoff_iso:
                    continue
                content = rec.get("message", {}).get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "text":
                        continue
                    text = block.get("text") or ""
                    for label, pat in pats:
                        found = pat.findall(text)
                        if not found:
                            continue
                        count, example = hits.get(label, (0, None))
                        hits[label] = (
                            count + len(found),
                            example or _snippet(text, pat),
                        )
    except OSError:
        pass
    return hits


def _snippet(text, pat, width=64):
    m = pat.search(text)
    if not m:
        return None
    start = max(0, m.start() - width // 3)
    end = min(len(text), m.end() + width // 2)
    frag = " ".join(text[start:end].split())
    return ("…" if start else "") + frag + ("…" if end < len(text) else "")


def scan(days, wanted, jobs):
    if not LOG_ROOT.exists():
        sys.exit(f"no transcripts found — {LOG_ROOT} doesn't exist.\n"
                 "claude-bingo scores your local Claude Code logs; you need "
                 "some history first.")
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    files = list(recent_logs(days))
    if not files:
        sys.exit(f"no transcripts touched in the last {days} days under {LOG_ROOT}")

    totals = {}
    work = [(f, cutoff_iso, wanted) for f in files]
    done = 0
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for hits in pool.map(_scan_file, work, chunksize=8):
            done += 1
            if sys.stderr.isatty() and done % 50 == 0:
                pct = 100 * done // len(files)
                print(f"\r  scanning… {done}/{len(files)} ({pct}%)",
                      end="", file=sys.stderr)
            for label, (count, example) in hits.items():
                prev_count, prev_example = totals.get(label, (0, None))
                totals[label] = (prev_count + count, prev_example or example)
    if sys.stderr.isatty():
        print("\r" + " " * 40 + "\r", end="", file=sys.stderr)
    return totals, len(files)


# ---------------------------------------------------------------- rendering

def wrap_cell(label, count=None):
    lines = textwrap.wrap(label, CELL_W - 2) or [""]
    if count is not None:
        lines.append(f"×{count}" if count else "—")
    lines = lines[:4]
    return lines + [""] * (4 - len(lines))


def render(board, totals=None):
    size = board["size"]
    cells = board["cells"]
    marked = set()
    if totals is not None:
        for i, label in enumerate(cells):
            if label == FREE or totals.get(label, (0, None))[0]:
                marked.add(i)

    header = "BINGO"[:size] if size <= 5 else "".join(
        chr(65 + i) for i in range(size))
    top = "┌" + "┬".join("─" * CELL_W for _ in range(size)) + "┐"
    mid = "├" + "┼".join("─" * CELL_W for _ in range(size)) + "┤"
    bot = "└" + "┴".join("─" * CELL_W for _ in range(size)) + "┘"

    out = []
    out.append("  " + "".join(
        color(ch.center(CELL_W + 1), BOLD + MAGENTA) for ch in header))
    out.append("  " + top)
    for r in range(size):
        if r:
            out.append("  " + mid)
        rows = []
        for c in range(size):
            i = r * size + c
            label = cells[i]
            count = None if totals is None else totals.get(label, (0, None))[0]
            if label == FREE:
                rows.append((["", "FREE", "SPACE", ""], True))
            else:
                rows.append((wrap_cell(label, count), i in marked))
        for line_no in range(4):
            parts = []
            for lines, is_marked in rows:
                text = lines[line_no].center(CELL_W)
                if is_marked:
                    text = color(text, GREEN + BOLD)
                elif totals is not None:
                    text = color(text, DIM)
                parts.append(text)
            out.append("  │" + "│".join(parts) + "│")
    out.append("  " + bot)
    return "\n".join(out)


def find_bingos(board, marked):
    size = board["size"]
    lines = []
    for r in range(size):
        lines.append(("row %d" % (r + 1), [r * size + c for c in range(size)]))
    for c in range(size):
        name = "BINGO"[c] if size <= 5 else chr(65 + c)
        lines.append(("col %s" % name, [r * size + c for r in range(size)]))
    lines.append(("diagonal ↘", [i * size + i for i in range(size)]))
    lines.append(("diagonal ↙", [i * size + (size - 1 - i) for i in range(size)]))
    return [name for name, idx in lines if all(i in marked for i in idx)]


# ---------------------------------------------------------------- commands

def cmd_board(args):
    seed = args.seed if args.seed is not None else random.randrange(1 << 30)
    board = make_board(args.size, seed)
    path = board_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(board, indent=2) + "\n")
    print()
    print(render(board))
    print()
    print(color(f"  board #{seed}", DIM) + color(f"  →  {path}", DIM))
    print(color("  score it:  claude-bingo score", DIM))
    print()


def cmd_score(args):
    path = board_path()
    if not path.exists():
        sys.exit("no board yet — run:  claude-bingo board")
    board = json.loads(path.read_text())
    wanted = [c for c in board["cells"] if c != FREE]

    print(color(f"\n  scanning {LOG_ROOT} — last {args.days} days…", DIM),
          file=sys.stderr)
    totals, n_files = scan(args.days, wanted, args.jobs)

    print()
    print(render(board, totals))
    print()

    marked = {i for i, label in enumerate(board["cells"])
              if label == FREE or totals.get(label, (0, None))[0]}
    bingos = find_bingos(board, marked)
    squares = len(marked)
    total_hits = sum(c for c, _ in totals.values())

    verdict = (color("BLACKOUT — every square. Seek help.", RED + BOLD)
               if squares == len(board["cells"])
               else color("BINGO! " + ", ".join(bingos), GREEN + BOLD)
               if bingos else color("no bingo — suspiciously well-behaved", YELLOW))
    print(f"  {verdict}")
    print(color(f"  {squares}/{len(board['cells'])} squares · {total_hits:,} "
                f"utterances · {n_files:,} transcripts", DIM))
    print()

    ranked = sorted(totals.items(), key=lambda kv: -kv[1][0])[:args.top]
    if ranked:
        print(color("  ── worst offenders " + "─" * 40, DIM))
        for label, (count, example) in ranked:
            if not count:
                continue
            print(f"  {color(str(count).rjust(5), CYAN + BOLD)}  "
                  f"{color(label, BOLD)}")
            if example and args.quotes:
                for line in textwrap.wrap(example, 68):
                    print(color(f"         {line}", DIM))
        print()


def cmd_phrases(args):
    b = bank()
    by_category = {}
    for label in b["labels"]:
        by_category.setdefault(b["categories"][label], []).append(label)

    if args.category:
        wanted = {c.lower() for c in args.category}
        by_category = {k: v for k, v in by_category.items() if k.lower() in wanted}
        if not by_category:
            sys.exit("no such category. try:  claude-bingo phrases")

    print()
    for category, labels in by_category.items():
        print(f"  {color(category, BOLD + MAGENTA)}")
        for label in labels:
            print(f"    {label}")
        print()
    print(color(f"  {len(b['labels'])} phrases · bundled: {phrases.BUNDLED}", DIM))
    print(color(f"  add your own:  {phrases.USER_PHRASES}", DIM))
    print()


def main():
    p = argparse.ArgumentParser(
        prog="claude-bingo",
        description="Bingo for LLM-isms, scored against your Claude transcripts. "
                    "Reads local logs only; nothing is uploaded.")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("board", help="generate a fresh board")
    b.add_argument("--size", type=int, default=5, help="board dimension (default 5)")
    b.add_argument("--seed", type=int,
                   help="reproduce a specific board (only stable for a given "
                        "phrase bank)")
    b.set_defaults(func=cmd_board)

    s = sub.add_parser("score", help="score the board against your logs")
    s.add_argument("--days", type=int, default=7, help="how far back (default 7)")
    s.add_argument("--top", type=int, default=12, help="offenders to list")
    s.add_argument("--jobs", type=int, default=min(8, (os.cpu_count() or 4)))
    s.add_argument("--no-quotes", dest="quotes", action="store_false",
                   help="skip the receipts")
    s.set_defaults(func=cmd_score)

    ph = sub.add_parser("phrases", help="list the phrase bank")
    ph.add_argument("--category", action="append",
                    help="limit to a category (repeatable)")
    ph.set_defaults(func=cmd_phrases)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
