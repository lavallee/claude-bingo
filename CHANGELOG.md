# Changelog

## 0.2.1

- `score` no longer counts claude-bingo's own output. A rendered board
  self-matches 15 of its 24 squares, so every round you played inflated the
  next one. Blocks carrying a board border are skipped.

## 0.2.0

- Codex support: ships `.codex-plugin/plugin.json` and a Codex catalog at
  `.agents/plugins/marketplace.json`, so `codex plugin marketplace add
  lavallee/claude-bingo` works the same way the Claude Code one does.
  `claude-bingo` is also listed in both catalogs of `lyra-forge/marketplace`.
- One launcher for every path: `scripts/claude-bingo` at the plugin root,
  replacing the per-harness `PYTHONPATH` incantations in the skill.
- A readable error instead of `ModuleNotFoundError: tomllib` on Python older
  than 3.11, naming a newer interpreter if one is on PATH.
- Board rows are sized to their tallest cell, so a fresh board no longer
  renders with two blank lines in every row.
- Long labels keep their count when the cell has to truncate them.
- Tests cover the packaging surface that a checkout can't: version lockstep
  across four manifests, HTTPS-only plugin sources, and the skill's launcher
  path.

## 0.1.0

- First release: `board`, `score`, `phrases`, a 65-phrase bank, and a Claude
  Code plugin.
