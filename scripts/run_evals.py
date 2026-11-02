#!/usr/bin/env python3
"""
run_evals.py — loom eval runner

Iterates every skills/*/evals/evals.json, validates the schema, and reports
a summary of evals available per skill. Does not execute LLM calls — use the
--check flag to validate structure, or integrate with an LLM eval harness for
assertion testing.

Usage:
  python3 scripts/run_evals.py                  # schema validation + inventory
  python3 scripts/run_evals.py --skill weave-script   # limit to one skill
  python3 scripts/run_evals.py --verbose         # show assertion lists

Also validates artifact fixtures (tests/fixtures/, skills/*/evals/fixtures/) against
schemas/ by filename suffix (e.g. *-discovery.json → discovery.schema.json).

Exit codes:
  0 — all evals parse cleanly
  1 — one or more evals.json files or artifact fixtures failed schema validation
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

REQUIRED_EVAL_KEYS = {"id", "prompt", "expected_output"}
REQUIRED_ROOT_KEYS = {"skill_name", "evals"}

FIXTURE_GLOBS = ("tests/fixtures/**/*.json", "skills/*/evals/fixtures/**/*.json")
SCHEMA_BY_SUFFIX = {
    "discovery.json": "discovery",
    "opportunity-profile.json": "opportunity-profile",
    "platform-audit.json": "platform-audit",
    "capability-map.json": "capability-map",
    "gap-responses.json": "gap-responses",
    "pipeline-state.json": "pipeline-state",
}


def validate_fixtures() -> tuple[int, list[str]]:
    """Validate artifact fixtures against schemas/ by filename suffix."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from loomstate.schema import validate_file  # noqa: PLC0415

    checked, errors = 0, []
    for pattern in FIXTURE_GLOBS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            schema = next((s for suf, s in SCHEMA_BY_SUFFIX.items() if path.name.endswith(suf)), None)
            if not schema:
                continue
            checked += 1
            errors += [f"{path.relative_to(REPO_ROOT)}: {e}" for e in validate_file(path, schema)]
    return checked, errors


def validate_evals_file(path: Path) -> list[str]:
    """Return a list of validation error strings; empty list = clean."""
    errors: list[str] = []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [f"JSON parse error: {e}"]

    for key in REQUIRED_ROOT_KEYS:
        if key not in data:
            errors.append(f"Missing root key: '{key}'")

    evals = data.get("evals", [])
    if not isinstance(evals, list):
        errors.append("'evals' must be a list")
        return errors

    seen_ids: set = set()
    for i, ev in enumerate(evals):
        prefix = f"eval[{i}]"
        if not isinstance(ev, dict):
            errors.append(f"{prefix}: not a dict")
            continue
        for key in REQUIRED_EVAL_KEYS:
            if key not in ev:
                errors.append(f"{prefix}: missing required key '{key}'")
        eid = ev.get("id")
        if eid in seen_ids:
            errors.append(f"{prefix}: duplicate id '{eid}'")
        seen_ids.add(eid)
        assertions = ev.get("assertions", [])
        if not isinstance(assertions, list):
            errors.append(f"{prefix}: 'assertions' must be a list")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="loom eval schema validator")
    parser.add_argument("--skill", help="Run only for this skill name (e.g. weave-script)")
    parser.add_argument("--verbose", action="store_true", help="Print assertion lists")
    args = parser.parse_args()

    eval_files = sorted(SKILLS_DIR.glob("*/evals/evals.json"))
    if args.skill:
        eval_files = [f for f in eval_files if f.parts[-3] == args.skill]
        if not eval_files:
            print(f"No evals found for skill: {args.skill}", file=sys.stderr)
            return 1

    total_skills = 0
    total_evals = 0
    failed_skills = 0

    print(f"\nloom eval runner — repo: {REPO_ROOT}\n")
    print(f"{'Skill':<30} {'Evals':>5}  Status")
    print("─" * 55)

    for path in eval_files:
        skill_name = path.parts[-3]
        errors = validate_evals_file(path)
        data = {}
        try:
            data = json.loads(path.read_text())
        except Exception:
            pass
        evals = data.get("evals", [])
        count = len(evals)
        total_skills += 1
        total_evals += count

        if errors:
            failed_skills += 1
            status = "❌ FAIL"
            print(f"  {skill_name:<28} {count:>5}  {status}")
            for err in errors:
                print(f"    ⚠  {err}")
        else:
            status = "✅ OK"
            print(f"  {skill_name:<28} {count:>5}  {status}")
            if args.verbose:
                for ev in evals:
                    assertions = ev.get("assertions", [])
                    print(f"    [{ev['id']}] {ev['prompt'][:60]}")
                    for a in assertions:
                        print(f"         • {a}")

    print("─" * 55)
    print(f"  {'TOTAL':<28} {total_evals:>5}  {total_skills} skills")

    checked, fixture_errors = validate_fixtures()
    if fixture_errors:
        print(f"\n  ❌  {len(fixture_errors)} fixture schema error(s) across {checked} fixture(s):")
        for err in fixture_errors:
            print(f"    ⚠  {err}")
    else:
        print(f"\n  ✅  {checked} artifact fixture(s) match schemas/")

    if failed_skills or fixture_errors:
        if failed_skills:
            print(f"\n  {failed_skills} skill(s) failed validation. Fix errors above.\n")
        return 1
    else:
        print(f"\n  All {total_skills} skills passed schema validation.\n")

    # Skills that exist but have no evals.json
    all_skills = sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir())
    skills_with_evals = {path.parts[-3] for path in eval_files}
    missing = [s for s in all_skills if s not in skills_with_evals]
    if missing:
        print(f"  Skills without evals ({len(missing)}):")
        for s in missing:
            print(f"    ○ {s}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
