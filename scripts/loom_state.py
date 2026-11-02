#!/usr/bin/env python3
"""loom_state — SA-first control plane CLI. See `python3 scripts/loom_state.py --help`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loomstate.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
