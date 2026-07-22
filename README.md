# claude-bingo

A 5×5 bingo board of LLM verbal tics, scored against your own Claude Code
transcripts.

```
         B               I               N               G               O
  ┌───────────────┬───────────────┬───────────────┬───────────────┬───────────────┐
  │   I hear you  │   Good catch  │ battle-tested │  load-bearing │  worth naming │
  │       ×2      │       ×9      │       —       │      ×71      │       ×3      │
  ├───────────────┼───────────────┼───────────────┼───────────────┼───────────────┤
  │    Happy to   │   Let me be   │   Hope this   │   Excellent!  │     Let me    │
  │       ×4      │     direct    │     helps     │       —       │      ×74      │
  │               │       ×2      │       —       │               │               │
  └───────────────┴───────────────┴───────────────┴───────────────┴───────────────┘

  BINGO! row 1, diagonal ↘
  18/25 squares · 201 utterances · 1,534 transcripts

  ── worst offenders ────────────────────────────────────────
     74  Let me
         …before changing anything. Let me check what the config actual…
     71  load-bearing
         …that assumption is doing a lot of load-bearing work here.
```

Everything runs locally. It reads `~/.claude/projects/**/*.jsonl` and prints to
your terminal. There are no network calls and no dependencies beyond the Python
standard library.

## Install

**As a Claude Code plugin** — then just ask Claude to play bingo:

```
/plugin marketplace add lavallee/claude-bingo
/plugin install claude-bingo@claude-bingo
```

**As a CLI:**

```bash
uvx claude-bingo board     # no install
pipx install claude-bingo  # or keep it around
```

**From source:**

```bash
git clone https://github.com/lavallee/claude-bingo
cd claude-bingo
python3 -m claude_bingo board
```

Requires Python 3.11+ (for `tomllib`).

## Use

```bash
claude-bingo board              # generate a fresh board
claude-bingo board --size 3     # smaller, for a quick round
claude-bingo board --seed 12345 # reproduce a specific board
claude-bingo score              # score it against the last 7 days
claude-bingo score --days 30    # ...or however far back you dare look
claude-bingo score --no-quotes  # skip the receipts
claude-bingo phrases            # list the phrase bank
```

The board is saved to `$XDG_DATA_HOME/claude-bingo/board.json` (default
`~/.local/share/claude-bingo/board.json`), so `score` picks up whatever you last
generated.

A given `--seed` reproduces a given board only for a given phrase bank — add
phrases and the same seed deals a different hand.

## The phrase bank

65 phrases across 9 categories, in
[`claude_bingo/phrases.toml`](claude_bingo/phrases.toml). Each entry is a board
label and the regex that hunts for it:

```toml
[linkedin-brain]
"delve" = "\\bdelv(?:e|es|ing)\\b"
"tapestry" = "\\btapestry\\b"
```

Patterns are matched case-insensitively and in multiline mode, so `^` anchors to
the start of any line.

Add your own without touching the package in
`~/.config/claude-bingo/phrases.toml` — same format. A label that collides with
a bundled one overrides its pattern.

## Contributing

PRs to the phrase bank are the point of this repo. Add to an existing category
or start a new one. Two things make a good entry:

- **The label reads at a glance.** It lands in a 13-column cell.
- **The regex is specific enough to mean something.** `\bjust\b` will match
  everything and tell you nothing; `you'?re absolutely right` earns its square.

Run `claude-bingo phrases` to check yours loaded, and `claude-bingo score` to
see whether it actually catches anything.

## License

MIT
