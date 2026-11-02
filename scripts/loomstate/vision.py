"""Vision (SB-05): capability-map edit model, freeze, confirmation approval (D-050, D-036)."""

from __future__ import annotations

import json
import re
from functools import lru_cache

from .core import (
    CATALOG_PATH,
    LoomError,
    find_identity_leaks,
    find_section,
    md_sections,
    now_iso,
    read_json,
    replace_md_section,
    sha256_file,
    sha256_paths,
    slugify,
    write_json,
    write_text_atomic,
)
from .intake import CONFIRMATION, DISCOVERY, IDEATION, MAP
from .qualify import DEMO_GOALS, SUMMARY
from .schema import validate
from .state import Engagement

TOKEN_VIS_ID = "ai-cost-dashboard"
MAP_SOFT_LIMIT = 4
REQUIRED_SECTIONS = {
    "chosen archetype": ("chosen archetype",),
    "top wow moments": ("top 3 wow moments", "top wow moments"),
    "elastic capability map": ("elastic capability map",),
    "data strategy": ("data strategy",),
    "out of scope": ("out of scope",),
    "minimum bar": ("minimum bar",),
}
CONFIRMATION_SECTIONS = {
    "What We'll Show You": ("what we'll show you", "what we will show you"),
    "How We Define a Successful Evaluation": ("how we define a successful evaluation",),
}
CONFIRMATION_BANNED = ("predefined", "custom build", "standard demo", "bootstrap", "champion", "deal stage",
                       "ICP", "ACV")


@lru_cache(maxsize=1)
def catalog() -> dict[str, dict]:
    data = json.loads(CATALOG_PATH.read_text())
    return {c["id"]: c for c in data["capabilities"]}


def catalog_for(solution: str) -> list[dict]:
    if solution in ("cross_solution", "unknown", "", None):
        return list(catalog().values())
    return [c for c in catalog().values() if solution in c["solutions"]]


def _empty_map(eng: Engagement) -> dict:
    return {"slug": eng.slug, "status": "draft", "updated_at": now_iso(), "frozen_at": None,
            "token_visibility": {"included": False, "opted_out": False}, "capabilities": [], "out_of_scope": []}


def load_map(eng: Engagement, create: bool = False) -> dict:
    p = eng.path(MAP)
    if not p.exists():
        if create:
            return _empty_map(eng)
        raise LoomError(f"No capability map yet ({eng.rel(MAP)}). Add capabilities with `vision map add`.")
    data = read_json(p)
    errors = validate(data, "capability-map")
    if errors:
        raise LoomError(f"{eng.rel(MAP)} invalid:\n  " + "\n  ".join(errors))
    return data


def _in_scope(cmap: dict, include_implied: bool = True) -> list[dict]:
    return [c for c in cmap["capabilities"] if c["in_scope"] and (include_implied or c["origin"] != "implied")]


def _apply_token_visibility(cmap: dict) -> None:
    tv = cmap.setdefault("token_visibility", {"included": False, "opted_out": False})
    ab = any(c["id"] == "agent-builder" and c["in_scope"] for c in cmap["capabilities"])
    has = next((c for c in cmap["capabilities"] if c["id"] == TOKEN_VIS_ID), None)
    if ab and not tv.get("opted_out"):
        if not has:
            entry = catalog()[TOKEN_VIS_ID]
            cmap["capabilities"].append({
                "id": TOKEN_VIS_ID, "name": entry["name"],
                "outcome": "Shows exactly what each agent session costs — tokens, model, trend",
                "proof_point": "AI Cost + Usage dashboard populated from agent sessions during the demo",
                "origin": "implied", "in_scope": True, "catalog": True, "implied_by": "agent-builder",
            })
        else:
            has["in_scope"] = True
        tv["included"] = True
    else:
        if has and has["origin"] == "implied":
            cmap["capabilities"].remove(has)
        tv["included"] = bool(has and has["in_scope"] and has["origin"] != "implied")


def _touch(eng: Engagement, cmap: dict) -> list[str]:
    """Persist a map edit; a frozen map returns to draft and invalidates downstream freeze/audit."""
    msgs = []
    _apply_token_visibility(cmap)
    if cmap["status"] == "frozen":
        cmap["status"] = "draft"
        cmap["frozen_at"] = None
        msgs.append("map was frozen — now draft; re-run `vision freeze` and `vision confirm`")
        ide = eng.stage("ideation")
        if ide.get("status") in ("complete", "awaiting_confirmation"):
            eng.set_stage("ideation", "stale", reason="capability map edited after freeze")
    cmap["updated_at"] = now_iso()
    errors = validate(cmap, "capability-map")
    if errors:
        raise LoomError("capability map invalid:\n  " + "\n  ".join(errors))
    write_json(eng.path(MAP), cmap)
    n = len(_in_scope(cmap, include_implied=False))
    if n > MAP_SOFT_LIMIT:
        msgs.append(f"warning: {n} capabilities in scope — stories land best with 2–4")
    eng.save()
    return msgs


def map_add(eng: Engagement, cap_id: str | None, name: str | None, outcome: str | None, proof: str | None,
            origin: str | None) -> list[str]:
    cmap = load_map(eng, create=True)
    cat = catalog()
    if cap_id and cap_id in cat:
        entry_name = name or cat[cap_id]["name"]
        is_catalog = True
        origin = origin or "sa_added"
    else:
        if not name:
            raise LoomError(f"'{cap_id}' is not in the capability catalog — pass --name for a custom feature request.")
        cap_id = cap_id or slugify(name)
        entry_name = name
        is_catalog = False
        origin = origin or "sa_requested"
    existing = next((c for c in cmap["capabilities"] if c["id"] == cap_id), None)
    if existing:
        existing.update({"in_scope": True, "name": entry_name})
        if outcome:
            existing["outcome"] = outcome
        if proof:
            existing["proof_point"] = proof
        if existing["origin"] == "implied":
            existing["origin"] = origin
            existing["implied_by"] = None
    else:
        cmap["capabilities"].append({"id": cap_id, "name": entry_name, "outcome": outcome, "proof_point": proof,
                                     "origin": origin, "in_scope": True, "catalog": is_catalog, "implied_by": None})
    cmap["out_of_scope"] = [o for o in cmap["out_of_scope"] if o.get("capability_id") != cap_id]
    msgs = _touch(eng, cmap)
    if cap_id == "agent-builder" and cmap["token_visibility"].get("included"):
        msgs.append("D-036: AI Cost + Usage dashboard auto-included (opt out: vision map token-visibility off)")
    return msgs


def map_exclude(eng: Engagement, name_or_id: str, reason: str | None) -> list[str]:
    cmap = load_map(eng, create=True)
    cap = next((c for c in cmap["capabilities"] if c["id"] == name_or_id), None)
    if cap:
        cap["in_scope"] = False
        entry = {"name": cap["name"], "reason": reason, "capability_id": cap["id"]}
    else:
        entry = {"name": name_or_id, "reason": reason, "capability_id": name_or_id if name_or_id in catalog() else None}
    cmap["out_of_scope"] = [o for o in cmap["out_of_scope"] if o["name"] != entry["name"]] + [entry]
    return _touch(eng, cmap)


def map_token_visibility(eng: Engagement, on: bool) -> list[str]:
    cmap = load_map(eng, create=True)
    cmap.setdefault("token_visibility", {})["opted_out"] = not on
    return _touch(eng, cmap)


def plan(eng: Engagement) -> dict:
    gate = vision_gate(eng)
    cmap = load_map(eng, create=True)
    mode = gate["mode"]
    inputs = [eng.rel(t) for t in (DEMO_GOALS, "opportunity/{slug}-opportunity-profile.json", DISCOVERY)
              if eng.path(t).exists()]
    return {
        "skill": "skills/warp-spark/SKILL.md",
        "mode": mode,
        "inputs": inputs,
        "outputs": [eng.rel(IDEATION), eng.rel(MAP)],
        "public_identity": eng.state["identity"]["public_display_name"],
        "identity_rule": "ideation.md is a public artifact — use the Acme display name, never the company name.",
        "required_sections": [v[0] for v in REQUIRED_SECTIONS.values()],
        "catalog": [{"id": c["id"], "name": c["name"]} for c in catalog_for(eng.state.get("solution", ""))],
        "current_map": [{"id": c["id"], "origin": c["origin"], "in_scope": c["in_scope"]} for c in cmap["capabilities"]],
        "then": "loom_state vision freeze  →  refresh confirmation + summary TL;DR  →  loom_state vision confirm",
    }


def vision_gate(eng: Engagement) -> dict:
    stages = eng.stages
    scratch = eng.state.get("entry_mode") == "scratch" and stages.get("discovery-parser", {}).get("status") != "complete"
    if scratch:
        return {"mode": "Mode 3 (scratch)"}
    op = stages.get("opportunity-review", {})
    decision = op.get("decision")
    if decision == "proceed" or (decision == "continue_discovery" and op.get("design_anyway")):
        mode = "Mode 1 (demo-goals)" if eng.path(DEMO_GOALS).exists() else "Mode 2 (discovery)"
        return {"mode": mode}
    if decision == "not_qualified":
        raise LoomError("Vision is locked: qualification decision is not_qualified.")
    if decision == "continue_discovery":
        raise LoomError("Vision is locked on continue_discovery — close gaps and re-decide, or "
                        "`loom_state qualify design-anyway --rationale …` (accept risk).")
    raise LoomError("Vision is locked until a qualification decision is recorded (`loom_state qualify decide`).")


def _parse_map_table(body: str) -> list[dict]:
    rows = [ln for ln in body.splitlines() if ln.strip().startswith("|")]
    if len(rows) < 3:
        return []
    header = [h.strip().lower() for h in rows[0].strip("|").split("|")]
    caps = []
    for ln in rows[2:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        row = dict(zip(header, cells))
        name = row.get("capability", "")
        if not name or name.startswith("{"):
            continue
        m = re.search(r"`([a-z0-9-]+)`", name)
        cid = m.group(1) if m else slugify(re.sub(r"`[^`]*`", "", name))
        clean = re.sub(r"\s*`[^`]*`\s*", " ", name).strip() or cid
        raw_origin = row.get("origin", "vision").lower()
        origin = next((o for key, o in (("implied", "implied"), ("sa added", "sa_added"), ("sa_added", "sa_added"),
                                        ("sa requested", "sa_requested"), ("sa_requested", "sa_requested"))
                       if raw_origin.startswith(key)), "vision")
        caps.append({"id": cid, "name": clean, "outcome": row.get("outcome enabled") or None,
                     "proof_point": row.get("proof point") or None,
                     "origin": origin,
                     "in_scope": True, "catalog": cid in catalog(), "implied_by": None})
    return caps


def _render_map(cmap: dict) -> str:
    label = {"vision": "vision", "sa_added": "SA added", "sa_requested": "SA requested", "implied": "implied (D-036)"}
    lines = ["| Capability | Origin | Outcome Enabled | Proof Point |", "|---|---|---|---|"]
    for c in _in_scope(cmap):
        lines.append(f"| {c['name']} `{c['id']}` | {label[c['origin']]} | {c.get('outcome') or ''} | "
                     f"{c.get('proof_point') or ''} |")
    return "\n".join(lines)


def freeze(eng: Engagement, approver: str) -> dict:
    gate = vision_gate(eng)
    ipath = eng.path(IDEATION)
    if not ipath.exists():
        raise LoomError(f"{eng.rel(IDEATION)} not found — run warp-spark (Plan Contract) first.")
    text = ipath.read_text()
    sections = md_sections(text)
    errors, warnings = [], []
    for label, prefixes in REQUIRED_SECTIONS.items():
        body = find_section(sections, *prefixes)
        if body is None:
            errors.append(f"ideation.md missing section: {prefixes[0].title()}")
        elif not body.strip() and label != "elastic capability map":
            errors.append(f"ideation.md section is empty: {prefixes[0].title()}")

    if eng.path(MAP).exists():
        cmap = load_map(eng)
    else:
        cmap = _empty_map(eng)
        cmap["capabilities"] = _parse_map_table(find_section(sections, "elastic capability map") or "")
        if cmap["capabilities"]:
            warnings.append("capability map parsed from ideation.md table (origin defaults to vision)")
    _apply_token_visibility(cmap)
    scope = _in_scope(cmap)
    if not scope:
        errors.append("capability map has no in-scope capabilities")
    for c in scope:
        if not (c.get("outcome") and c.get("proof_point")):
            errors.append(f"capability '{c['id']}' needs an outcome and proof point (why it is in the story)")
    n = len(_in_scope(cmap, include_implied=False))
    if n > MAP_SOFT_LIMIT:
        warnings.append(f"{n} capabilities in scope — stories land best with 2–4")

    identity = eng.state.get("identity", {})
    leaks = find_identity_leaks(text, identity) + find_identity_leaks(json.dumps(cmap), identity)
    if leaks:
        errors.append(f"private identity in public artifact (ideation / map): {', '.join(sorted(set(leaks)))} — "
                      f"use '{identity.get('public_display_name')}'")
    h1 = next((ln for ln in text.splitlines() if ln.startswith("# ")), "")
    if identity.get("public_display_name", "").lower() not in h1.lower() and eng.slug not in h1:
        warnings.append("ideation.md H1 should name the public display name / slug")
    if errors:
        raise LoomError("vision freeze failed:\n  " + "\n  ".join(errors))

    text = replace_md_section(text, "Elastic Capability Map", _render_map(cmap))
    oos_body = find_section(md_sections(text), "out of scope") or ""
    extra = [f"- {o['name']}" + (f" — {o['reason']}" if o.get("reason") else "")
             for o in cmap["out_of_scope"] if o["name"].lower() not in oos_body.lower()]
    if extra:
        text = replace_md_section(text, "Out of Scope", (oos_body + "\n" + "\n".join(extra)).strip())
    if cmap["token_visibility"].get("included"):
        tv_body = find_section(md_sections(text), "operational transparency")
        if tv_body is None or "yes" not in tv_body.lower():
            text = replace_md_section(text, "Operational Transparency",
                                      "- **AI cost/usage dashboard:** yes — included with Agent Builder (D-036)\n"
                                      "- **Scope:** {prefix}agent-sessions index, per-session token tracking, "
                                      "model cost breakdown (skills/weave-cost/SKILL.md)")
    write_text_atomic(ipath, text)
    cmap["status"] = "frozen"
    cmap["frozen_at"] = now_iso()
    cmap["updated_at"] = cmap["frozen_at"]
    write_json(eng.path(MAP), cmap)

    eng.approve("vision_freeze", approver, [IDEATION, MAP], None, mode=gate["mode"])
    eng.set_stage("ideation", "awaiting_confirmation", mode=gate["mode"], frozen_at=cmap["frozen_at"],
                  map_hash=sha256_file(eng.path(MAP)), ideation_hash=sha256_file(ipath),
                  input_hash=sha256_paths([eng.path(DEMO_GOALS), eng.path(DISCOVERY)], eng.dir),
                  token_visibility=cmap["token_visibility"].get("included", False), reason=None)
    eng.save()
    return {"mode": gate["mode"], "capabilities": [c["id"] for c in scope],
            "sa_added": [c["id"] for c in scope if c["origin"] in ("sa_added", "sa_requested")],
            "token_visibility": cmap["token_visibility"].get("included", False), "warnings": warnings,
            "next": "Refresh opportunity confirmation (What We'll Show You / How We Define a Successful Evaluation) "
                    "and opportunity-summary TL;DR ('Demo direction: …'), then `loom_state vision confirm`."}


def confirm(eng: Engagement, approver: str) -> dict:
    ide = eng.stage("ideation")
    if ide.get("status") != "awaiting_confirmation":
        raise LoomError("Nothing to confirm — freeze the vision first (`loom_state vision freeze`).")
    if ide.get("map_hash") != sha256_file(eng.path(MAP)) or ide.get("ideation_hash") != sha256_file(eng.path(IDEATION)):
        raise LoomError("Ideation or capability map changed since freeze — re-run `loom_state vision freeze`.")
    errors = []
    cpath = eng.path(CONFIRMATION)
    if not cpath.exists():
        errors.append(f"missing {eng.rel(CONFIRMATION)}")
    else:
        ctext = cpath.read_text()
        csections = md_sections(ctext)
        for title, prefixes in CONFIRMATION_SECTIONS.items():
            if find_section(csections, *prefixes) is None:
                errors.append(f"confirmation missing refreshed section '{title}' (warp-spark Post-Ideation Refresh)")
        hits = [t for t in CONFIRMATION_BANNED if re.search(r"\b" + re.escape(t) + r"\b", ctext, re.IGNORECASE)]
        if hits:
            errors.append(f"confirmation is customer-facing — remove internal terms: {', '.join(hits)}")
    spath = eng.path(SUMMARY)
    if spath.exists():
        tldr = find_section(md_sections(spath.read_text()), "tl;dr") or ""
        if "demo direction:" not in tldr.lower():
            errors.append("opportunity-summary TL;DR not refreshed — add 'Demo direction: …' line")
    if errors:
        raise LoomError("vision confirm failed:\n  " + "\n  ".join(errors))
    eng.approve("confirmation_approve", approver, [CONFIRMATION, SUMMARY, IDEATION], None)
    eng.set_stage("ideation", "complete", confirmed_at=now_iso())
    eng.save()
    return {"status": "complete"}
