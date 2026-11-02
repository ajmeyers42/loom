"""Shared helpers: paths, slugs, hashing, atomic IO, identity-leak scans."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "schemas"
SKILLS_DIR = REPO_ROOT / "skills"
CATALOG_PATH = SKILLS_DIR / "references" / "capability-catalog.json"

SUBFOLDERS = ("inputs", "opportunity", "demo", "data", "deploy")

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
GAP_ID_RE = re.compile(r"^g_[a-z0-9_]+$")

CLOUD_SYNC_MARKERS = ("CloudStorage", "Google Drive", "GoogleDrive", "OneDrive", "Dropbox", "iCloud")

GENERIC_NAME_TOKENS = {
    "the", "inc", "llc", "ltd", "corp", "corporation", "company", "co", "group",
    "holdings", "bank", "global", "international", "services", "systems",
    "technologies", "solutions", "partners", "and", "of",
    "financial", "insurance", "health", "healthcare", "energy", "capital", "lending", "mutual",
}
# Company first words that are everyday English: as a lone token they would flag ordinary prose.
# The full company name (and any legacy slug) is still protected.
COMMON_WORD_TOKENS = {
    "purpose", "summit", "target", "square", "block", "united", "american", "first", "general",
    "national", "pacific", "atlantic", "pioneer", "liberty", "guardian", "frontier", "horizon",
    "keystone", "fidelity", "principal", "sovereign", "standard", "central", "southern", "northern",
    "western", "eastern", "beacon", "compass", "anchor", "harbor", "bridge", "vista", "prime",
    "premier", "advance", "discover", "insight", "signal", "progressive", "citizens", "heritage",
    "legacy", "evergreen", "integrity", "unity", "trust", "secure", "direct", "smart", "bright",
}
SUBSTRING_TOKEN_MIN = 6


class LoomError(Exception):
    """User-facing error; CLI prints the message and exits non-zero."""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_root(override: str | None = None) -> Path:
    raw = (override or os.environ.get("LOOM_ENGAGEMENTS_ROOT", "")).strip()
    return Path(raw).expanduser().resolve() if raw else (Path.home() / "engagements").resolve()


def engagement_dir(root: Path, slug: str) -> Path:
    return root / slug


def state_path(eng_dir: Path, slug: str) -> Path:
    return eng_dir / f"{slug}-pipeline-state.json"


def artifact(eng_dir: Path, slug: str, template: str) -> Path:
    return eng_dir / template.format(slug=slug)


def normalize_tag_id(raw: str) -> str:
    """D-026 engagement id normalization (``acme-pharma`` -> ``acmepharma``)."""
    s = re.sub(r"[-_\s]+", "", raw or "").lower()
    return s or "demo"


def loom_tag(slug: str, index_prefix: str = "", demo_asset_tag: str = "") -> str:
    raw = demo_asset_tag.strip() or index_prefix.strip() or slug
    return f"loom:{normalize_tag_id(raw)}"


def slugify(text: str, sep: str = "-") -> str:
    s = re.sub(r"[^a-z0-9]+", sep, (text or "").lower()).strip(sep)
    return re.sub(re.escape(sep) + "+", sep, s)


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return sha256_bytes(path.read_bytes())


def sha256_paths(paths: list[Path], base: Path) -> str:
    """Content hash over files (and files under dirs), stable across mtime changes."""
    h = hashlib.sha256()
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(f for f in p.rglob("*") if f.is_file() and not f.name.startswith(".")))
        elif p.is_file():
            files.append(p)
    if not files:
        return "none"
    for f in sorted(set(files)):
        rel = f.relative_to(base).as_posix() if f.is_relative_to(base) else f.as_posix()
        h.update(rel.encode())
        h.update(b"\0")
        h.update(f.read_bytes())
        h.update(b"\0")
    return "sha256:" + h.hexdigest()


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise LoomError(f"Missing file: {path}")
    except json.JSONDecodeError as e:
        raise LoomError(f"Invalid JSON in {path}: {e}")


def write_text_atomic(path: Path, text: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_json(path: Path, data: dict) -> None:
    write_text_atomic(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def find_git_worktree(path: Path) -> Path | None:
    """Return the enclosing git work tree root, if any (walks up from path)."""
    p = path if path.is_dir() else path.parent
    while True:
        if (p / ".git").exists():
            return p
        if p.parent == p:
            return None
        p = p.parent


def is_cloud_synced(path: Path) -> bool:
    s = str(path)
    return any(m in s for m in CLOUD_SYNC_MARKERS)


def identity_tokens(identity: dict) -> list[str]:
    """Strings that must never appear on public demo artifacts."""
    tokens: list[str] = []
    for key in ("company_name", "opportunity_name", "opportunity_id"):
        val = (identity or {}).get(key) or ""
        if val.strip():
            tokens.append(val.strip())
    tokens.extend(s.strip() for s in (identity or {}).get("legacy_slugs") or [] if s and s.strip())
    company = (identity or {}).get("company_name") or ""
    for word in re.findall(r"[A-Za-z0-9]+", company):
        if len(word) >= 4 and word.lower() not in GENERIC_NAME_TOKENS | COMMON_WORD_TOKENS:
            tokens.append(word)
            break
    return tokens


def find_identity_leaks(text: str, identity: dict) -> list[str]:
    """Long tokens match as case-insensitive substrings (catch ``2026NorthwindAgents``); short ones on word bounds."""
    hits = []
    for tok in identity_tokens(identity):
        if len(tok) >= SUBSTRING_TOKEN_MIN:
            found = tok.lower() in text.lower()
        else:
            found = re.search(r"(?<![A-Za-z0-9])" + re.escape(tok) + r"(?![A-Za-z0-9])", text, re.IGNORECASE)
        if found:
            hits.append(tok)
    return sorted(set(hits))


def md_sections(text: str) -> dict[str, str]:
    """Map lowercase H2 titles to their body text."""
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m and not line.startswith("###"):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = m.group(1).strip().lower()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def find_section(sections: dict[str, str], *prefixes: str) -> str | None:
    for title, body in sections.items():
        if any(title.startswith(p.lower()) for p in prefixes):
            return body
    return None


def replace_md_section(text: str, title_prefix: str, new_body: str) -> str:
    """Replace the body of the first H2 whose title starts with title_prefix (append if absent)."""
    lines = text.splitlines()
    start = end = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s+", line) and not line.startswith("###"):
            title = line[2:].strip().lower()
            if start is None and title.startswith(title_prefix.lower()):
                start = i
            elif start is not None:
                end = i
                break
    body_lines = new_body.rstrip("\n").splitlines()
    if start is None:
        suffix = ["", f"## {title_prefix}", *body_lines, ""]
        return "\n".join(lines + suffix) + "\n"
    end = end if end is not None else len(lines)
    out = lines[: start + 1] + body_lines + [""] + lines[end:]
    return "\n".join(out).rstrip("\n") + "\n"


def default_approver() -> str:
    env = os.environ.get("LOOM_APPROVER", "").strip()
    if env:
        return env
    return os.environ.get("USER", "").strip()
