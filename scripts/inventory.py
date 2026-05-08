#!/usr/bin/env python3
"""
loom inventory — zero-AI engagement status checker.

Usage:
    python3 scripts/inventory.py                    # list all engagements
    python3 scripts/inventory.py <slug>             # detail for one engagement
    python3 scripts/inventory.py --root /some/path  # override root

Reads LOOM_ENGAGEMENTS_ROOT (default: ~/engagements).
No AI, no network — purely local file inspection.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

STAGE_OUTPUTS = [
    ("ideation",            "demo/{slug}-ideation.md"),
    ("discovery-parser",    "demo/{slug}-discovery.json"),
    ("diagnostic-analyzer", "demo/{slug}-current-state.json"),
    ("opportunity-review",  "opportunity/{slug}-opportunity-summary.md"),
    ("platform-audit",      "demo/{slug}-platform-audit.json"),
    ("script-template",     "demo/{slug}-demo-script.md"),
    ("agent-design",        "demo/{slug}-agent-builder-spec.md"),
    ("vulcan-generate",     "data/{slug}-vulcan-queries.json"),
    ("data-modeler",        "data/{slug}-data-model.json"),
    ("fleet-integrations",  "deploy/{slug}-integrations-manifest.json"),
    ("ml-designer",         "data/{slug}-ml-config.json"),
    ("validator",           "deploy/{slug}-demo-checklist.md"),
    ("cloud-provision",     ".env"),
    ("deploy",              "deploy/bootstrap.py"),
]

STATUS_ICONS = {
    "complete": "✅",
    "skipped":  "⏭ ",
    "pending":  "🔲",
    "unknown":  "❓",
}


def get_root() -> Path:
    raw = os.environ.get("LOOM_ENGAGEMENTS_ROOT", "").strip()
    return Path(raw).expanduser() if raw else Path.home() / "engagements"


def list_engagements(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        [p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def read_state(eng_dir: Path, slug: str) -> dict | None:
    state_file = eng_dir / f"{slug}-pipeline-state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except json.JSONDecodeError:
            return None
    return None


def infer_state_from_files(eng_dir: Path, slug: str) -> dict:
    """Fall back to file scan when no pipeline-state.json exists."""
    stages = {}
    for stage, template in STAGE_OUTPUTS:
        filename = template.replace("{slug}", slug)
        output_path = eng_dir / filename
        if output_path.exists():
            mtime = datetime.fromtimestamp(output_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            stages[stage] = {"status": "complete", "output": filename, "mtime": mtime}
        else:
            stages[stage] = {"status": "pending", "output": filename}
    return {"slug": slug, "engagement_dir": str(eng_dir), "stages": stages, "source": "file-scan"}


def print_summary(eng_dir: Path, slug: str, verbose: bool = False):
    state = read_state(eng_dir, slug)
    source = "pipeline-state"
    if state is None:
        state = infer_state_from_files(eng_dir, slug)
        source = "file-scan"

    stages = state.get("stages", {})
    complete = sum(1 for s in stages.values() if s.get("status") == "complete")
    total = len(STAGE_OUTPUTS)
    last_updated = state.get("last_updated", "—")

    print(f"\n{'━' * 55}")
    print(f"  {slug}")
    print(f"  {eng_dir}")
    print(f"  {complete}/{total} stages complete  |  source: {source}  |  updated: {last_updated}")
    print(f"{'━' * 55}")

    if verbose:
        for stage, template in STAGE_OUTPUTS:
            info = stages.get(stage, {"status": "unknown"})
            icon = STATUS_ICONS.get(info.get("status", "unknown"), "❓")
            filename = template.replace("{slug}", slug)
            mtime = info.get("mtime", "")
            suffix = f"  ({mtime})" if mtime else ""
            print(f"  {icon}  {stage:<24}  {filename}{suffix}")

    # Show .env presence and cluster hint
    env_file = eng_dir / ".env"
    if env_file.exists():
        es_url = ""
        try:
            for line in env_file.read_text().splitlines():
                if line.startswith("ES_URL=") or line.startswith("ELASTICSEARCH_URL="):
                    es_url = line.split("=", 1)[1].strip().strip('"')
                    break
        except Exception:
            pass
        print(f"\n  🔑  .env present" + (f"  →  {es_url}" if es_url else ""))
    else:
        print(f"\n  ⬜  .env absent (no cluster provisioned)")

    print()


def main():
    parser = argparse.ArgumentParser(description="loom engagement inventory")
    parser.add_argument("slug", nargs="?", help="Engagement slug to inspect (omit for all)")
    parser.add_argument("--root", help="Override LOOM_ENGAGEMENTS_ROOT")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show all stages")
    args = parser.parse_args()

    root = Path(args.root).expanduser() if args.root else get_root()

    if not root.exists():
        print(f"❌  Engagements root not found: {root}", file=sys.stderr)
        print(f"    Set LOOM_ENGAGEMENTS_ROOT or create ~/engagements", file=sys.stderr)
        sys.exit(1)

    print(f"\nDEMOBUILDER INVENTORY")
    print(f"Root: {root}")

    if args.slug:
        eng_dir = root / args.slug
        if not eng_dir.exists():
            print(f"❌  Engagement not found: {eng_dir}", file=sys.stderr)
            sys.exit(1)
        print_summary(eng_dir, args.slug, verbose=True)
    else:
        engagements = list_engagements(root)
        if not engagements:
            print(f"\n  (no engagements found under {root})")
        for eng_dir in engagements:
            print_summary(eng_dir, eng_dir.name, verbose=args.verbose)


if __name__ == "__main__":
    main()
