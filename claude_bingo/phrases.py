"""Loads the phrase bank from TOML.

The bundled bank lives next to this module. Users can add their own in
$XDG_CONFIG_HOME/claude-bingo/phrases.toml (same format); entries there are
merged in, and a duplicate label overrides the bundled pattern.
"""

import os
import re
import sys
import tomllib
from pathlib import Path

BUNDLED = Path(__file__).parent / "phrases.toml"


def _config_dir():
    base = os.environ.get("XDG_CONFIG_HOME")
    return Path(base) if base else Path.home() / ".config"


USER_PHRASES = _config_dir() / "claude-bingo" / "phrases.toml"


def _load_file(path):
    """Return [(category, label, compiled_pattern)] from one TOML file."""
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as e:
        sys.exit(f"{path}: malformed TOML — {e}")
    except OSError as e:
        sys.exit(f"{path}: {e.strerror}")

    out = []
    for category, entries in data.items():
        if not isinstance(entries, dict):
            sys.exit(f"{path}: [{category}] must be a table of label = \"regex\"")
        for label, pattern in entries.items():
            if not isinstance(pattern, str):
                sys.exit(f"{path}: [{category}] {label!r} must be a string regex")
            try:
                compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            except re.error as e:
                sys.exit(f"{path}: [{category}] {label!r} has a bad regex — {e}")
            out.append((category, label, compiled))
    return out


def load():
    entries = _load_file(BUNDLED)
    if USER_PHRASES.exists():
        entries += _load_file(USER_PHRASES)

    # Later entries win, but keep first-seen ordering so boards stay stable.
    by_label, order = {}, []
    for category, label, pattern in entries:
        if label not in by_label:
            order.append(label)
        by_label[label] = (category, pattern)

    return {
        "labels": order,
        "by_label": {label: by_label[label][1] for label in order},
        "categories": {label: by_label[label][0] for label in order},
    }
