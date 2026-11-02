"""Pre-P2 (legacy) package handling: legacy slug rewrite on import, schema migration on record."""

from __future__ import annotations

import re
from collections import Counter

from .schema import load_schema

DROPPED_IMPACT = "resolved"
FALLBACK_IMPACT = "low"


def _enum(schema: str, *path: str) -> set:
    node = load_schema(schema)
    for part in path:
        node = node[part]
    return {v for v in node["enum"] if v is not None}


def detect_prefix(names: list[str], suffixes) -> tuple[str | None, int]:
    """Most common file prefix in front of a known artifact suffix (e.g. ``2026NorthwindSOC``) and its file count."""
    votes = Counter(n[: -len(s)] for n in names for s in suffixes if n.endswith(s) and len(n) > len(s))
    return votes.most_common(1)[0] if votes else (None, 0)


def rewrite_text(text: str, legacy: str, slug: str) -> tuple[str, int]:
    return re.subn(re.escape(legacy), slug, text, flags=re.IGNORECASE)


def rewrite_json(value, legacy: str, slug: str):
    """Replace the legacy slug in every string value of a JSON document; returns (value, count)."""
    if isinstance(value, str):
        return rewrite_text(value, legacy, slug)
    if isinstance(value, list):
        out, n = [], 0
        for v in value:
            nv, c = rewrite_json(v, legacy, slug)
            out.append(nv)
            n += c
        return out, n
    if isinstance(value, dict):
        out, n = {}, 0
        for k, v in value.items():
            out[k], c = rewrite_json(v, legacy, slug)
            n += c
        return out, n
    return value, 0


def migrate_discovery(discovery: dict) -> tuple[list[str], list[str]]:
    """Normalize pre-P2 enum values in place. Returns (warnings, gap_ids closed as resolved).

    Gap ids must already be assigned (backfill runs first) so resolved gaps close under a stable id.
    """
    impacts = _enum("discovery", "$defs", "gap", "properties", "impact")
    severities = _enum("discovery", "properties", "pain_points", "items", "properties", "severity")
    warnings, closed, kept = [], [], []
    for g in discovery.get("gaps", []):
        impact = g.get("impact")
        where = f"legacy gap {g.get('gap_id')} ({g.get('field')})"
        if impact == DROPPED_IMPACT:
            closed.append(g.get("gap_id"))
            warnings.append(f"{where} impact 'resolved' → removed (recorded in closed_gaps)")
            continue
        if impact not in impacts:
            g["legacy_impact"] = impact
            g["impact"] = FALLBACK_IMPACT
            warnings.append(f"{where} impact '{impact}' → '{FALLBACK_IMPACT}' (kept as legacy_impact)")
        kept.append(g)
    if "gaps" in discovery:
        discovery["gaps"] = kept
    for i, p in enumerate(discovery.get("pain_points", [])):
        sev = p.get("severity")
        if sev is not None and sev not in severities:
            p["legacy_severity"] = sev
            p["severity"] = None
            warnings.append(f"legacy pain_points[{i}] ({p.get('label')}) severity '{sev}' → null "
                            "(kept as legacy_severity)")
    return warnings, [c for c in closed if c]


def migrate_profile(profile: dict) -> list[str]:
    """Fill pre-P2 profile omissions in place (missing MEDDPIC notes → "")."""
    warnings = []
    for dim, val in (profile.get("meddpic") or {}).items():
        if isinstance(val, dict) and "notes" not in val:
            val["notes"] = ""
            warnings.append(f'legacy profile meddpic.{dim}.notes missing → ""')
    return warnings
