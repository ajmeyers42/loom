"""Kibana space solution suggestion (KIBANA_SOLUTION): infer from the engagement, SA can override.

Rule: observability / security only when the evidence is clear; anything else is ``classic``.
The result is a *suggestion* (``state.kibana_solution.source == "inferred"``) until the SA confirms or
changes it in input settings (``loom_state keys set KIBANA_SOLUTION=…`` → source ``sa``).
"""

from __future__ import annotations

import re

KIBANA_SOLUTIONS = ("classic", "es", "oblt", "security")
DEFAULT_SOLUTION = "classic"
AREA_TO_SOLUTION = {"observability": "oblt", "security": "security"}

# A side is "clear" with at least CLEAR_MIN distinct signal terms and at least twice the other side's.
CLEAR_MIN = 3

OBSERVABILITY_TERMS = (
    r"observability", r"\bapm\b", r"opentelemetry", r"\botel\b", r"\bedot\b", r"distributed trac(?:e|ing)",
    r"\bslos?\b", r"service level (?:objective|indicator)", r"\bmttr\b", r"root cause", r"\bsre\b",
    r"on-?call", r"infrastructure monitoring", r"synthetic monitoring", r"uptime", r"log (?:monitoring|aggregation)",
)
SECURITY_TERMS = (
    r"\bsiem\b", r"\bsoc\b", r"security operations", r"threat (?:hunting|detection|intel)", r"detection (?:rules?|engineering)",
    r"\bedr\b", r"\bxdr\b", r"endpoint security", r"\bmitre\b", r"incident response", r"attack discovery",
    r"alert triage", r"security analytics", r"malware", r"ransomware", r"cyber ?security",
)
TEXT_SUFFIXES = {".md", ".txt", ".json", ".csv", ".yaml", ".yml", ".html", ""}
MAX_BYTES = 400_000


def _score(text: str, terms: tuple[str, ...]) -> list[str]:
    return [t for t in terms if re.search(t, text, re.IGNORECASE)]


def _notes_text(eng) -> str:
    chunks: list[str] = []
    budget = MAX_BYTES
    paths = sorted((eng.dir / "inputs").rglob("*")) if (eng.dir / "inputs").exists() else []
    disc = eng.dir / "demo" / f"{eng.slug}-discovery.json"
    if disc.exists():
        paths.append(disc)
    for p in paths:
        if not p.is_file() or p.name.startswith(".") or p.suffix.lower() not in TEXT_SUFFIXES or budget <= 0:
            continue
        try:
            data = p.read_text(errors="ignore")[:budget]
        except OSError:
            continue
        budget -= len(data)
        chunks.append(data)
    return "\n".join(chunks)


def infer(eng, profile: dict | None = None) -> dict:
    """Return ``{"value", "confidence": "clear"|"unclear", "reason", "signals"}``. Never raises."""
    explicit = eng.state.get("solution")
    if explicit in AREA_TO_SOLUTION:
        return {"value": AREA_TO_SOLUTION[explicit], "confidence": "clear",
                "reason": f"engagement solution is {explicit}", "signals": {}}
    area = ((profile or {}).get("demo_scope_signals") or {}).get("primary_solution_area")
    if area in AREA_TO_SOLUTION:
        return {"value": AREA_TO_SOLUTION[area], "confidence": "clear",
                "reason": f"opportunity profile primary_solution_area is {area}", "signals": {}}

    text = _notes_text(eng)
    obs, sec = _score(text, OBSERVABILITY_TERMS), _score(text, SECURITY_TERMS)
    signals = {"observability": len(obs), "security": len(sec)}
    for name, hits, other in (("observability", obs, sec), ("security", sec, obs)):
        if len(hits) >= CLEAR_MIN and len(hits) >= 2 * len(other):
            return {"value": AREA_TO_SOLUTION[name], "confidence": "clear", "signals": signals,
                    "reason": f"notes point to {name} ({len(hits)} signals vs {len(other)})"}
    why = "no clear observability or security signal"
    if area:
        why += f" (profile primary_solution_area is {area})"
    elif obs or sec:
        why = f"mixed or weak signals (observability {len(obs)}, security {len(sec)})"
    return {"value": DEFAULT_SOLUTION, "confidence": "unclear", "reason": why, "signals": signals}
