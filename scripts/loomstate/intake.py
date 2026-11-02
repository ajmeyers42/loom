"""Intake (SB-03): listen plan/record, optional scan, gaps inbox (Path A / Path B), staleness."""

from __future__ import annotations

import re

from . import keystore, legacy
from .core import GAP_ID_RE, LoomError, now_iso, read_json, sha256_file, sha256_paths, slugify, write_json
from .schema import validate
from .state import Engagement

DISCOVERY = "demo/{slug}-discovery.json"
GAPS_MD = "opportunity/{slug}-gaps.md"
CONFIRMATION = "opportunity/{slug}-confirmation.md"
GAP_RESPONSES = "opportunity/{slug}-gap-responses.json"
CURRENT_STATE = "demo/{slug}-current-state.json"
PROFILE = "opportunity/{slug}-opportunity-profile.json"
MAP = "demo/{slug}-capability-map.json"
IDEATION = "demo/{slug}-ideation.md"
AUDIT_JSON = "demo/{slug}-platform-audit.json"

SALES_JARGON = ("champion", "deal stage", "ICP", "ACV")
BLOCKING_IMPACT = "blocks_demo_build"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def inputs_hash(eng: Engagement) -> str:
    return sha256_paths([eng.dir / "inputs"], eng.dir)


def qualify_input_hash(eng: Engagement) -> str:
    return sha256_paths([eng.path(DISCOVERY), eng.path(GAPS_MD), eng.path(CURRENT_STATE)], eng.dir)


def input_files(eng: Engagement) -> list[dict]:
    base = eng.dir / "inputs"
    return [{"file": f.relative_to(eng.dir).as_posix(), "sha256": sha256_file(f)}
            for f in sorted(base.rglob("*")) if f.is_file() and not f.name.startswith(".")]


def listen_plan(eng: Engagement) -> dict:
    files = input_files(eng)
    if not files and eng.state.get("entry_mode") != "import":
        raise LoomError("inputs/ is empty — add notes first (loom_state inputs add FILE…).")
    prior = eng.stage("discovery-parser").get("gap_fields", {})
    return {
        "skill": "skills/warp-listen/SKILL.md",
        "slug": eng.slug,
        "slug_rule": "Use this slug verbatim for every output filename — never re-derive it from the company name.",
        "inputs": files,
        "outputs": [eng.rel(DISCOVERY), eng.rel(GAPS_MD), eng.rel(CONFIRMATION)],
        "contract": [
            "Every claims[] item and pain_points[].source_ref points at a file under inputs/ with a verbatim excerpt.",
            "Every gaps[] item has gap_id (g_<field>) — reuse prior ids for the same field.",
            "Confirmation is customer-facing (real company name OK; no sales jargon, no competitors).",
        ],
        "prior_gap_ids": prior,
        "then": "loom_state listen record",
    }


def _check_source_ref(eng: Engagement, ref: dict, where: str, errors: list[str], warnings: list[str],
                      strict_excerpts: bool, cache: dict) -> None:
    rel = ref.get("file", "")
    path = eng.dir / rel
    if not rel.startswith("inputs/") or not path.is_file():
        errors.append(f"{where}: source_ref file '{rel}' not found under inputs/")
        return
    excerpt = ref.get("excerpt")
    if excerpt:
        text = cache.setdefault(rel, _norm(path.read_text(errors="replace")))
        if _norm(excerpt) not in text:
            (errors if strict_excerpts else warnings).append(
                f"{where}: excerpt not found verbatim in {rel}: {excerpt[:60]!r}")


def backfill_gap_ids(discovery: dict) -> list[str]:
    assigned, used = [], {g.get("gap_id") for g in discovery.get("gaps", []) if g.get("gap_id")}
    for g in discovery.get("gaps", []):
        if g.get("gap_id"):
            continue
        base = "g_" + (slugify(g.get("field", "") or g.get("question", "gap"), "_") or "gap")
        gid, n = base, 2
        while gid in used:
            gid = f"{base}_{n}"
            n += 1
        g["gap_id"] = gid
        used.add(gid)
        assigned.append(gid)
    return assigned


def listen_record(eng: Engagement, backfill: bool = False, strict_excerpts: bool = True,
                  migrate: bool | None = None) -> dict:
    dpath = eng.path(DISCOVERY)
    discovery = read_json(dpath)
    errors: list[str] = []
    warnings: list[str] = []
    importing = eng.state.get("entry_mode") == "import"
    migrate = importing if migrate is None else migrate

    assigned = []
    if backfill or importing or migrate:
        assigned = backfill_gap_ids(discovery)
        if assigned:
            warnings.append(f"backfilled gap_id for {len(assigned)} gap(s): {', '.join(assigned)}")
    migrated_closed: list[str] = []
    if migrate:
        notes, migrated_closed = legacy.migrate_discovery(discovery)
        warnings.extend(notes)

    meta = discovery.setdefault("meta", {})
    if meta.get("slug") and meta["slug"] != eng.slug:
        errors.append(f"discovery meta.slug '{meta['slug']}' != engagement slug '{eng.slug}' (slug is never re-derived)")
    meta["slug"] = eng.slug
    meta.setdefault("inputs", [f["file"] for f in input_files(eng)])

    errors.extend(validate(discovery, "discovery"))
    for t in (GAPS_MD, CONFIRMATION):
        if not eng.path(t).exists():
            errors.append(f"missing {eng.rel(t)}")

    cache: dict = {}
    claims = discovery.get("claims", [])
    if not claims:
        (warnings if importing else errors).append(
            "no claims[] with source_ref — evidence must link to inputs/ (SB-03)")
    for i, c in enumerate(claims):
        if isinstance(c.get("source_ref"), dict):
            _check_source_ref(eng, c["source_ref"], f"claims[{i}] {c.get('claim_id', '')}", errors, warnings,
                              strict_excerpts, cache)
    for i, p in enumerate(discovery.get("pain_points", [])):
        if isinstance(p.get("source_ref"), dict):
            _check_source_ref(eng, p["source_ref"], f"pain_points[{i}]", errors, warnings, strict_excerpts, cache)
    for g in discovery.get("gaps", []):
        if isinstance(g.get("source_ref"), dict):
            _check_source_ref(eng, g["source_ref"], f"gap {g.get('gap_id')}", errors, warnings, strict_excerpts, cache)

    gaps = discovery.get("gaps", [])
    ids = [g.get("gap_id") for g in gaps]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        errors.append(f"duplicate gap_id(s): {', '.join(dupes)}")
    st = eng.stage("discovery-parser")
    prior_fields: dict = st.get("gap_fields", {})
    for g in gaps:
        old = prior_fields.get(g.get("field"))
        if old and old != g.get("gap_id"):
            errors.append(f"gap_id must stay stable: field '{g.get('field')}' was {old}, now {g.get('gap_id')}")

    confirmation = eng.path(CONFIRMATION)
    if confirmation.exists():
        text = confirmation.read_text()
        hits = [t for t in SALES_JARGON if re.search(r"\b" + re.escape(t) + r"\b", text, re.IGNORECASE)]
        if hits:
            warnings.append(f"confirmation uses internal sales language: {', '.join(hits)}")

    if errors:
        raise LoomError("listen record failed:\n  " + "\n  ".join(errors))

    write_json(dpath, discovery)
    current_ids = {g["gap_id"] for g in gaps}
    prior_ids = set(prior_fields.values())
    closed = sorted(prior_ids - current_ids)
    eng.set_stage(
        "discovery-parser", "complete",
        input_hash=inputs_hash(eng),
        output_hash=sha256_file(dpath),
        gap_fields={g["field"]: g["gap_id"] for g in gaps},
        claim_count=len(claims),
        gap_count=len(gaps),
        closed_gaps=sorted(set(st.get("closed_gaps", [])) | set(closed) | set(migrated_closed)),
    )
    warnings.extend(keystore.refresh_kibana_solution(eng))
    eng.save()
    return {"gaps": len(gaps), "claims": len(claims), "closed_by_reinference": closed,
            "new_gaps": sorted(current_ids - prior_ids) if prior_ids else [], "warnings": warnings}


def scan_record(eng: Engagement) -> dict:
    p = eng.path(CURRENT_STATE)
    read_json(p)
    eng.set_stage("diagnostic-analyzer", "complete", input_hash=sha256_file(p))
    eng.save()
    return eng.stage("diagnostic-analyzer")


def scan_skip(eng: Engagement) -> dict:
    eng.set_stage("diagnostic-analyzer", "skipped", reason="no diagnostic provided")
    eng.save()
    return eng.stage("diagnostic-analyzer")


# ── Gaps inbox ────────────────────────────────────────────────────────────

def load_responses(eng: Engagement) -> dict:
    p = eng.path(GAP_RESPONSES)
    if not p.exists():
        return {"slug": eng.slug, "responses": {}}
    data = read_json(p)
    errors = validate(data, "gap-responses")
    if errors:
        raise LoomError(f"{eng.rel(GAP_RESPONSES)} invalid:\n  " + "\n  ".join(errors))
    return data


def is_blocking(gap: dict) -> bool:
    return gap.get("impact") == BLOCKING_IMPACT or bool(gap.get("blocks_qualification"))


def gap_rows(eng: Engagement) -> list[dict]:
    discovery = read_json(eng.path(DISCOVERY))
    responses = load_responses(eng)["responses"]
    first_input = next((f["file"] for f in input_files(eng)), "inputs/")
    rows = []
    for g in discovery.get("gaps", []):
        resp = responses.get(g["gap_id"], {})
        rows.append({
            "gap_id": g["gap_id"],
            "field": g.get("field"),
            "question": g.get("question"),
            "impact": g.get("impact"),
            "blocking": is_blocking(g),
            "status": resp.get("status", "open"),
            "response": resp.get("response"),
            "update_in": g.get("suggested_input") or (g.get("source_ref") or {}).get("file") or first_input,
        })
    return rows


def open_blocking(eng: Engagement) -> list[str]:
    return [r["gap_id"] for r in gap_rows(eng)
            if r["blocking"] and r["status"] not in ("answered", "accepted_risk")]


def respond(eng: Engagement, gap_id: str, status: str, by: str, response: str | None = None,
            rationale: str | None = None) -> dict:
    if not GAP_ID_RE.match(gap_id):
        raise LoomError(f"Invalid gap id '{gap_id}'")
    known = {r["gap_id"] for r in gap_rows(eng)}
    if gap_id not in known:
        raise LoomError(f"Unknown gap '{gap_id}'. Known: {', '.join(sorted(known)) or '(none)'}")
    if status == "accepted_risk" and not (rationale or "").strip():
        raise LoomError("accepted_risk requires --rationale")
    if not (by or "").strip():
        raise LoomError("--by (or LOOM_APPROVER) is required")
    data = load_responses(eng)
    data["responses"][gap_id] = {
        "status": status,
        "response": response,
        "rationale": rationale,
        "responded_by": by.strip(),
        "responded_at": now_iso(),
    }
    data["updated_at"] = now_iso()
    errors = validate(data, "gap-responses")
    if errors:
        raise LoomError("gap-responses invalid:\n  " + "\n  ".join(errors))
    write_json(eng.path(GAP_RESPONSES), data)
    return data["responses"][gap_id]


# ── Staleness (content hashes, D8) ────────────────────────────────────────

def compute_stale(eng: Engagement) -> dict[str, str]:
    stale: dict[str, str] = {}
    stages = eng.stages
    dp = stages.get("discovery-parser", {})
    if dp.get("status") == "complete" and dp.get("input_hash") and dp["input_hash"] != inputs_hash(eng):
        stale["discovery-parser"] = "inputs/ changed since last listen"
    op = stages.get("opportunity-review", {})
    if op.get("status") in ("complete", "awaiting_decision") and op.get("input_hash") \
            and op["input_hash"] != qualify_input_hash(eng):
        stale["opportunity-review"] = "discovery/gaps changed since qualify"
    ide = stages.get("ideation", {})
    if ide.get("status") in ("complete", "awaiting_confirmation"):
        if ide.get("map_hash") and ide["map_hash"] != sha256_file(eng.path(MAP)):
            stale["ideation"] = "capability map edited after freeze"
        elif ide.get("ideation_hash") and ide["ideation_hash"] != sha256_file(eng.path(IDEATION)):
            stale["ideation"] = "ideation.md edited after freeze"
    pa = stages.get("platform-audit", {})
    if pa.get("status") == "complete" and pa.get("map_hash") and pa["map_hash"] != sha256_file(eng.path(MAP)):
        stale["platform-audit"] = "capability map changed since audit"
    return stale
