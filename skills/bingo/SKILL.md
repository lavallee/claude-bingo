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

The tool is pure standard library, so it runs from the plugin with no install
step. Everything goes through one launcher: this plugin's root-level
`scripts/claude-bingo`. In Claude Code that path is
`${CLAUDE_PLUGIN_ROOT}/scripts/claude-bingo`; in Codex, resolve it against the
plugin directory this skill was loaded from.

Below, `claude-bingo` stands for `python3 <that launcher>`.

```bash
claude-bingo board                    # a fresh board, saved for scoring
claude-bingo board --size 3           # smaller, for a quick round
claude-bingo board --seed 12345       # reproduce a specific board

claude-bingo score                    # score the saved board, last 7 days
claude-bingo score --days 30          # ...or however far back they dare look
claude-bingo score --no-quotes        # skip the receipts
claude-bingo score --top 5            # shorter offenders list

claude-bingo phrases                  # the whole bank
claude-bingo phrases --category linkedin-brain
```

So a real invocation in Claude Code looks like:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/claude-bingo" board
```

If it reports that it needs Python 3.11 or newer, it will also print the exact
command to retry with. Don't try to work around it by other means.

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

The bundled bank is TOML at `claude_bingo/phrases.toml` inside the plugin. Users
can add their own without touching the plugin, in
`~/.config/claude-bingo/phrases.toml`:

```toml
[my-category]
"the label on the board" = "the regex that hunts for it"
```

Patterns are matched case-insensitively and in multiline mode, so `^` anchors to
the start of any line. A label that collides with a bundled one overrides its
pattern. `claude-bingo phrases` prints both paths — use it to confirm a new
entry loaded.

## Privacy

Everything is local. The tool reads transcript files and prints to the terminal;
it makes no network calls. If a user asks what it touches, the honest answer is
`~/.claude/projects/**/*.jsonl`, read-only.
