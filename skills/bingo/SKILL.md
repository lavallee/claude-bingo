---
name: bingo
description: Play LLM-ism bingo — generate a board of Claude's verbal tics ("delve", "You're absolutely right", "load-bearing") and score it against the user's own local Claude Code transcripts. Use when the user asks to play bingo, wants to see which LLM-isms or verbal tics they've been subjected to, asks how often Claude says a given phrase, or wants their transcripts analysed for slop.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/*)
---

# Claude Bingo

A 5×5 board of LLM verbal tics, scored against the user's local Claude Code
transcripts under `~/.claude/projects`.

This is a game. Keep the tone light, and don't get defensive about the results —
the phrases on the board are things *you* say, and the user finding that funny is
the entire point.

## Running it

The tool is pure stdlib, so it runs straight from the plugin directory with no
install step:

```bash
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m claude_bingo board
```

Generate a fresh board:

```bash
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m claude_bingo board
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m claude_bingo board --size 3
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m claude_bingo board --seed 12345
```

Score the saved board against recent history:

```bash
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m claude_bingo score
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m claude_bingo score --days 30
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m claude_bingo score --no-quotes
```

Inspect the phrase bank:

```bash
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m claude_bingo phrases
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m claude_bingo phrases --category linkedin-brain
```

## How to respond

- The output is already formatted for a terminal — box-drawing board, colour,
  a ranked "worst offenders" list with real quotes. **Show it as-is** in a code
  block. Don't re-render the board as a markdown table or re-summarise every
  cell; that throws away the thing the user asked for.
- Add a short reaction after the output, not before it.
- If there's no board yet, `score` will say so. Run `board` first, then score.
- `score` walks every transcript in the window, so a wide `--days` on a heavy
  user takes a few seconds. That's expected.

## Adding phrases

The bank is TOML at `${CLAUDE_PLUGIN_ROOT}/claude_bingo/phrases.toml`. Users can
add their own without touching the plugin, in
`~/.config/claude-bingo/phrases.toml`:

```toml
[my-category]
"the label on the board" = "the regex that hunts for it"
```

Patterns are matched case-insensitively and in multiline mode. A label that
collides with a bundled one overrides its pattern.

## Privacy

Everything is local. The tool reads transcript files and prints to the terminal;
it makes no network calls. If a user asks what it touches, the honest answer is
`~/.claude/projects/**/*.jsonl`, read-only.
