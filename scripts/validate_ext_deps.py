#!/usr/bin/env python3
"""
validate_ext_deps.py — external dependency currency check for loom

Reads docs/ext-registry.yaml and validates each dependency:
  • git repos:         checks local path exists, runs git fetch + status
  • cursor_plugin:     checks if plugin directory exists under known plugin paths
  • github_release:    compares latest GitHub release tag against providers.tf pin (optional)

Produces the Step 0 Reference Currency Gate report and exits non-zero if any
blocking dependency is stale or missing.

Usage:
  python3 scripts/validate_ext_deps.py                # full check
  python3 scripts/validate_ext_deps.py --fast         # skip network (git fetch, GitHub API)
  python3 scripts/validate_ext_deps.py --dep hive-mind  # check one dependency

Exit codes:
  0 — all blocking deps satisfied; non-blocking warnings may exist
  1 — one or more blocking deps are stale or missing
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "docs" / "ext-registry.yaml"

# Cursor plugin caches are nested. Claude and Agents installs are flat skill dirs.
# A sibling git clone also counts.
PLUGIN_SEARCH_ROOTS = [
    Path.home() / ".cursor" / "plugins",
    Path.home() / ".cursor" / "extensions",
    Path.home() / ".claude" / "skills",
    Path.home() / ".agents" / "skills",
    Path.home() / "Documents" / "GitHub" / "agent-skills",
]


# ── minimal YAML parser (fallback when PyYAML not installed) ─────────────────

def parse_registry_fallback(text: str) -> list[dict]:
    """Very basic YAML list parser — handles the specific format in ext-registry.yaml."""
    deps: list[dict] = []
    current: dict[str, Any] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "dependencies:":
            continue
        if stripped.startswith("- id:"):
            if current:
                deps.append(current)
            current = {"id": stripped.split(":", 1)[1].strip()}
        elif ":" in stripped and not stripped.startswith("-"):
            key, _, val = stripped.partition(":")
            val = val.strip().strip('"').strip("'")
            if val == "~" or val == "null":
                val = None
            elif val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            current[key.strip()] = val
    if current:
        deps.append(current)
    return deps


def load_registry() -> list[dict]:
    text = REGISTRY_PATH.read_text()
    if HAS_YAML:
        data = yaml.safe_load(text)
        return data.get("dependencies", [])
    return parse_registry_fallback(text)


# ── helpers ───────────────────────────────────────────────────────────────────

def resolve_path(dep: dict) -> Path | None:
    """Resolve local_path honoring env_override. Relative paths are relative to REPO_ROOT."""
    if not dep.get("local_path"):
        return None
    env_key = dep.get("env_override")
    if env_key:
        env_val = os.environ.get(env_key, "").strip()
        if env_val:
            p = Path(env_val).expanduser()
            return p if p.is_absolute() else REPO_ROOT / p
    raw = Path(dep["local_path"]).expanduser()
    return raw if raw.is_absolute() else (REPO_ROOT / raw).resolve()


def git_status(path: Path, fast: bool) -> tuple[str, str]:
    """Returns (status_symbol, message) for a git repo path."""
    if not path.exists():
        return "❌", f"not found at {path}"
    if not (path / ".git").exists():
        return "⚠️ ", f"path exists but is not a git repo: {path}"
    if not fast:
        try:
            subprocess.run(
                ["git", "-C", str(path), "fetch", "origin", "--quiet"],
                capture_output=True, timeout=15
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "status", "--short", "--branch"],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout.strip()
        first_line = output.splitlines()[0] if output else ""
        if "behind" in first_line:
            m = re.search(r"behind (\d+)", first_line)
            n = m.group(1) if m else "?"
            branch = re.sub(r"\.\.\..+", "", first_line.replace("## ", "")).strip()
            rev = _git_rev(path)
            return "⚠️ ", f"{n} commits behind — run: git -C {path} pull --ff-only  (rev {rev})"
        rev = _git_rev(path)
        return "✅", f"up to date (rev {rev})"
    except Exception as e:
        return "⚠️ ", f"git status failed: {e}"


def _git_rev(path: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip()
    except Exception:
        return "unknown"


def _looks_like_agent_skills(path: Path) -> bool:
    """True when path is an agent-skills root or a skills directory inside one."""
    if (path / "skills" / "elasticsearch").is_dir() or (path / "skills" / "cloud").is_dir():
        return True
    if (path / "elasticsearch").is_dir() and (path / "cloud").is_dir():
        return True
    if (path / "elasticsearch-esql").exists() or (path / "elasticsearch-esql" / "SKILL.md").exists():
        return True
    return False


def check_cursor_plugin(dep: dict) -> tuple[str, str]:
    plugin_id = dep.get("plugin_id", dep.get("id", ""))
    needle = plugin_id.split("/")[-1]
    found: list[Path] = []
    for base in PLUGIN_SEARCH_ROOTS:
        if not base.exists():
            continue
        if _looks_like_agent_skills(base):
            found.append(base)
        if needle and needle in base.name:
            found.append(base)
        # Plugin caches nest the skills dir several levels down.
        for hit in base.glob("**/skills/elasticsearch"):
            if hit.is_dir():
                found.append(hit.parent.parent)
                break
        for hit in base.glob("**/elasticsearch-esql/SKILL.md"):
            found.append(hit.parent.parent)
            break
    if found:
        rel = found[0]
        try:
            rel = found[0].relative_to(Path.home())
        except ValueError:
            pass
        extra = f" (+{len(found) - 1} more)" if len(found) > 1 else ""
        return "✅", f"installed at {rel}{extra}"
    install = dep.get("install_cmd", "")
    return "⚠️ ", f"not found in plugin paths — install: {install}"


def check_github_release(dep: dict, fast: bool) -> tuple[str, str]:
    if fast:
        return "⏭", "skipped (--fast)"
    url = dep.get("github_releases_url", "")
    if not url:
        return "⚠️ ", "no github_releases_url configured"
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/vnd.github+json",
                          "User-Agent": "loom-validate-ext-deps/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        latest = data.get("tag_name", "unknown")
        if latest.startswith("v0.0.0-"):
            return "⚠️ ", (
                f"latest tag {latest} is a pseudo-version — confirm the pin in "
                "deploy/providers.tf before generating HCL"
            )
        return "⚠️ ", (
            f"latest tag {latest} — compare it to the pin in deploy/providers.tf "
            "when generating HCL (no pin lives in this repo)"
        )
    except Exception as e:
        return "⚠️ ", f"could not fetch release info: {e}"


def is_in_scope(dep: dict) -> bool:
    """Rough scope check — always include always/optional; skip conditionals."""
    scope = str(dep.get("scope", "always")).lower()
    return scope in ("always", "")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="loom external dependency validator")
    parser.add_argument("--fast", action="store_true", help="Skip network checks (git fetch, GitHub API)")
    parser.add_argument("--dep", help="Check only this dependency id")
    parser.add_argument("--all-scopes", action="store_true", help="Check all entries regardless of scope")
    args = parser.parse_args()

    if not REGISTRY_PATH.exists():
        print(f"❌ Registry not found: {REGISTRY_PATH}", file=sys.stderr)
        return 1

    deps = load_registry()
    if args.dep:
        deps = [d for d in deps if d.get("id") == args.dep]
        if not deps:
            print(f"❌ Dependency '{args.dep}' not found in registry.", file=sys.stderr)
            return 1

    print(f"\n🔄  Reference Currency Gate")
    print(f"    Registry: {REGISTRY_PATH.relative_to(REPO_ROOT)}\n")

    col_w = max(len(d.get("id", "")) for d in deps) + 2
    blocking_failures = 0

    for dep in deps:
        dep_id = dep.get("id", "?")
        blocking = dep.get("blocking", False)
        optional = dep.get("optional", False)
        scope = str(dep.get("scope", "always"))
        check_type = dep.get("check_type", "git")

        if not args.all_scopes and scope not in ("always", ""):
            symbol, msg = "⏭", f"scope-conditional ({scope}) — skipped"
            print(f"  {dep_id:<{col_w}} {symbol}  {msg}")
            continue

        if check_type == "git":
            path = resolve_path(dep)
            if path is None:
                symbol, msg = "⚠️ ", "no local_path configured"
            elif optional and not path.exists():
                symbol, msg = "⏭", f"not installed — skipping  (install: {dep.get('install_cmd', '?')})"
            else:
                symbol, msg = git_status(path, args.fast)

        elif check_type == "cursor_plugin":
            symbol, msg = check_cursor_plugin(dep)

        elif check_type == "github_release":
            symbol, msg = check_github_release(dep, args.fast)

        else:
            symbol, msg = "⚠️ ", f"unknown check_type: {check_type}"

        print(f"  {dep_id:<{col_w}} {symbol}  {msg}")

        if blocking and symbol not in ("✅", "⏭"):
            blocking_failures += 1

    print()
    if blocking_failures:
        print(f"  ⛔ {blocking_failures} blocking dependency/dependencies require attention before continuing.\n")
        return 1
    else:
        print(f"  All checks passed (or warn-only). Pipeline may proceed.\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
