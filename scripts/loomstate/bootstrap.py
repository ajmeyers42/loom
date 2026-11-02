"""Engagement bootstrap (SB-01): dual identity, unique public slug, folder layout, initial state."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .core import (
    SLUG_RE,
    SUBFOLDERS,
    LoomError,
    find_git_worktree,
    find_identity_leaks,
    is_cloud_synced,
    normalize_tag_id,
    write_text_atomic,
)
from .keystore import env_template, parse_env
from .state import Engagement, initial_state

ENTRY_MODES = ("import", "notes", "scratch")
SOLUTIONS = ("search", "observability", "security", "cross_solution", "unknown")

# Import package (warp-scout / Gem handoff) → engagement layout. Matched on filename suffix.
IMPORT_MAP = {
    "-discovery.json": "demo/{slug}-discovery.json",
    "-current-state.json": "demo/{slug}-current-state.json",
    "-architecture.md": "demo/{slug}-architecture.md",
    "-findings.md": "demo/{slug}-findings.md",
    "-gaps.md": "opportunity/{slug}-gaps.md",
    "-confirmation.md": "opportunity/{slug}-confirmation.md",
    "-opportunity-summary.md": "opportunity/{slug}-opportunity-summary.md",
    "-opportunity-profile.json": "opportunity/{slug}-opportunity-profile.json",
    "-demo-goals.md": "opportunity/{slug}-demo-goals.md",
}


def default_display(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.split("-"))


def taken_ids(root: Path) -> tuple[set[str], set[str]]:
    """Folder names (lowercased) and D-026 tag ids already used under root."""
    names, tags = set(), set()
    if not root.exists():
        return names, tags
    for d in root.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        names.add(d.name.lower())
        tags.add(normalize_tag_id(d.name))
        env = parse_env(d / ".env")
        for key in ("DEMO_ASSET_TAG", "INDEX_PREFIX"):
            if env.get(key):
                tags.add(normalize_tag_id(env[key]))
        sp = d / f"{d.name}-pipeline-state.json"
        if sp.exists():
            try:
                tid = json.loads(sp.read_text()).get("tag_id")
                if tid:
                    tags.add(tid)
            except json.JSONDecodeError:
                pass
    return names, tags


def unique_slug(root: Path, slug: str, allow_suffix: bool) -> tuple[str, list[str]]:
    names, tags = taken_ids(root)
    notes = []
    candidate, n = slug, 2
    while candidate.lower() in names or normalize_tag_id(candidate) in tags:
        if not allow_suffix:
            raise LoomError(f"Slug '{candidate}' collides with an existing engagement or loom:{normalize_tag_id(candidate)} "
                            "tag under this root. Choose another public slug.")
        candidate = f"{slug}-{n}"
        n += 1
    if candidate != slug:
        notes.append(f"'{slug}' collides under root (folder or loom:{normalize_tag_id(slug)} tag) — using '{candidate}'")
    return candidate, notes


def create(root: Path, *, slug: str, company: str | None, opportunity: str | None, opportunity_id: str | None,
           display: str | None, entry_mode: str, solution: str, notes_files: list[Path] | None = None,
           import_dir: Path | None = None, allow_suffix: bool = True, allow_git_root: bool = False) -> tuple[Engagement, list[str]]:
    messages: list[str] = []
    slug = (slug or "").strip().lower()
    if not SLUG_RE.match(slug):
        raise LoomError(f"Invalid public slug '{slug}': use lowercase letters, digits, and hyphens (e.g. acme-pharma).")
    if entry_mode not in ENTRY_MODES:
        raise LoomError(f"entry mode must be one of {ENTRY_MODES}")
    if solution not in SOLUTIONS:
        raise LoomError(f"solution must be one of {SOLUTIONS}")
    if entry_mode == "import" and not import_dir:
        raise LoomError("entry mode 'import' needs --import DIR (AE/SDR package with discovery + demo-goals).")

    identity = {
        "company_name": (company or "").strip() or None,
        "opportunity_name": (opportunity or "").strip() or None,
        "opportunity_id": (opportunity_id or "").strip() or None,
        "public_display_name": (display or "").strip() or default_display(slug),
    }
    for label, value in (("slug", slug), ("public display name", identity["public_display_name"])):
        leaks = find_identity_leaks(value.replace("-", " "), identity)
        if leaks:
            raise LoomError(f"Public {label} '{value}' contains private identity ({', '.join(leaks)}). "
                            "Use an acme-{industry|usecase} slug and an Acme display name.")
    if not slug.startswith("acme-"):
        messages.append(f"warning: public slug '{slug}' does not follow acme-{{industry|usecase}}")

    root.mkdir(parents=True, exist_ok=True)
    git_root = find_git_worktree(root)
    if git_root and not allow_git_root:
        raise LoomError(f"Engagements root {root} is inside a git work tree ({git_root}). "
                        "Customer artifacts must stay outside git (AGENTS.md).")
    if is_cloud_synced(root):
        messages.append("warning: engagements root is cloud-synced — prefer keeping .env on a local symlink "
                        "(docs/engagements-path.md)")

    slug, notes = unique_slug(root, slug, allow_suffix)
    messages.extend(notes)
    eng_dir = root / slug
    eng_dir.mkdir()
    for sub in SUBFOLDERS:
        (eng_dir / sub).mkdir()

    tag_id = normalize_tag_id(slug)
    eng = Engagement(eng_dir, initial_state(slug, eng_dir, identity, entry_mode, solution, tag_id))
    write_text_atomic(eng_dir / ".env.example",
                      env_template(slug, identity["public_display_name"], solution, example=True))

    for f in notes_files or []:
        messages.append(add_input(eng, f))
    if import_dir:
        messages.extend(import_package(eng, import_dir))

    eng.save()
    return eng, messages


def add_input(eng: Engagement, src: Path) -> str:
    src = Path(src).expanduser()
    if not src.is_file():
        raise LoomError(f"Input file not found: {src}")
    dest = eng.dir / "inputs" / src.name
    if dest.exists():
        raise LoomError(f"inputs/{src.name} already exists — edit it in place (Path A) or rename the new file.")
    shutil.copy2(src, dest)
    return f"added inputs/{src.name}"


def import_package(eng: Engagement, import_dir: Path) -> list[str]:
    import_dir = Path(import_dir).expanduser()
    if not import_dir.is_dir():
        raise LoomError(f"Import directory not found: {import_dir}")
    msgs = []
    found_goals = found_discovery = False
    for f in sorted(p for p in import_dir.rglob("*") if p.is_file() and not p.name.startswith(".")):
        if f.name in (".env", ".env.example") or f.name.endswith("-pipeline-state.json"):
            msgs.append(f"skipped {f.name} (keystore / state are never imported)")
            continue
        target = next((t for suf, t in IMPORT_MAP.items() if f.name.endswith(suf)), None)
        if target:
            dest = eng.path(target)
            if f.suffix == ".json":
                data = json.loads(f.read_text())
                if "slug" in data:
                    data["slug"] = eng.slug
                if isinstance(data.get("meta"), dict) and "slug" in data["meta"]:
                    data["meta"]["slug"] = eng.slug
                write_text_atomic(dest, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            else:
                shutil.copy2(f, dest)
            found_goals |= target.endswith("demo-goals.md")
            found_discovery |= target.endswith("discovery.json")
            msgs.append(f"imported {f.name} → {dest.relative_to(eng.dir)}")
        else:
            dest = eng.dir / "inputs" / f.name
            shutil.copy2(f, dest)
            msgs.append(f"imported {f.name} → inputs/{f.name}")
    if not found_discovery:
        raise LoomError("Import package has no *-discovery.json — use entry mode 'notes' instead.")
    if not found_goals:
        msgs.append("warning: import package has no *-demo-goals.md — vision will run in Mode 2")
    return msgs
