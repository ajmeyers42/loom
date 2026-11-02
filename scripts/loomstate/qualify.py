"""Qualify (SB-04): register thread-qualify output, readiness, Record decision, Design anyway."""

from __future__ import annotations

from . import keystore, legacy
from .core import LoomError, now_iso, read_json, sha256_file, write_json
from .intake import (
    CURRENT_STATE,
    DISCOVERY,
    GAP_RESPONSES,
    GAPS_MD,
    PROFILE,
    gap_rows,
    load_responses,
    open_blocking,
    qualify_input_hash,
    respond,
)
from .schema import validate
from .state import Engagement

SUMMARY = "opportunity/{slug}-opportunity-summary.md"
DEMO_GOALS = "opportunity/{slug}-demo-goals.md"
STATUSES = ("proceed", "continue_discovery", "not_qualified")


def plan(eng: Engagement) -> dict:
    if eng.stage("discovery-parser").get("status") != "complete":
        raise LoomError("Discovery is not registered yet — run `loom_state listen record` first.")
    inputs = [eng.rel(t) for t in (DISCOVERY, GAPS_MD, GAP_RESPONSES, CURRENT_STATE) if eng.path(t).exists()]
    return {
        "skill": "skills/thread-qualify/SKILL.md",
        "slug": eng.slug,
        "inputs": inputs,
        "outputs": [eng.rel(SUMMARY), eng.rel(PROFILE), eng.rel(DEMO_GOALS)],
        "contract": [
            "Profile 'slug' must equal this engagement slug; 'customer' is the real company (internal doc).",
            "qualification_status is the recommendation — the SA records the decision via `qualify decide`.",
            "Preserve any existing qualification_decision and accepted_risk on refresh.",
            "Read gap-responses.json (answered / accepted_risk) when present.",
        ],
        "then": "loom_state qualify record",
    }


def _profile(eng: Engagement) -> dict:
    profile = read_json(eng.path(PROFILE))
    errors = validate(profile, "opportunity-profile")
    if profile.get("slug") != eng.slug:
        errors.append(f"profile slug '{profile.get('slug')}' != engagement slug '{eng.slug}'")
    if errors:
        raise LoomError(f"{eng.rel(PROFILE)} invalid:\n  " + "\n  ".join(errors))
    return profile


def record(eng: Engagement, migrate: bool | None = None) -> dict:
    if eng.stage("discovery-parser").get("status") != "complete":
        raise LoomError("Discovery is not registered yet — run `loom_state listen record` first.")
    missing = [eng.rel(t) for t in (SUMMARY, DEMO_GOALS) if not eng.path(t).exists()]
    if missing:
        raise LoomError(f"thread-qualify outputs missing: {', '.join(missing)}")
    warnings: list[str] = []
    migrate = eng.state.get("entry_mode") == "import" if migrate is None else migrate
    if migrate:
        raw = read_json(eng.path(PROFILE))
        notes = legacy.migrate_profile(raw)
        if notes:
            write_json(eng.path(PROFILE), raw)
            warnings.extend(notes)
    profile = _profile(eng)
    warnings.extend(keystore.refresh_kibana_solution(eng, profile))
    st = eng.stage("opportunity-review")
    profile_hash = sha256_file(eng.path(PROFILE))
    in_hash = qualify_input_hash(eng)
    if st.get("decision") and st.get("decision_profile_hash") == profile_hash and st.get("input_hash") == in_hash:
        eng.save()
        return {"status": st["status"], "unchanged": True, "decision": st["decision"], "warnings": warnings}
    history = st.get("history", [])
    if st.get("decision"):
        history.append({"decision": st["decision"], "decided_at": st.get("decided_at"),
                        "superseded_at": now_iso(), "reason": "qualification refreshed"})
    recommended = profile.get("qualification_status")
    if profile.get("qualification_decision"):
        recommended = profile["qualification_decision"].get("recommended_status") or recommended
    eng.set_stage("opportunity-review", "awaiting_decision", input_hash=in_hash, recommended_status=recommended,
                  decision=None, decided_at=None, design_anyway=None, decision_profile_hash=None,
                  open_blocking_gaps=open_blocking(eng), history=history or None)
    eng.save()
    return {"status": "awaiting_decision", "recommended_status": recommended, "readiness": readiness(eng),
            "warnings": warnings}


def readiness(eng: Engagement) -> dict:
    profile = read_json(eng.path(PROFILE)) if eng.path(PROFILE).exists() else {}
    meddpic = {k: (v or {}).get("status") for k, v in (profile.get("meddpic") or {}).items()}
    blocking = open_blocking(eng)
    recommended = eng.stage("opportunity-review").get("recommended_status") or profile.get("qualification_status")
    if recommended == "not_qualified" or any(s == "disqualifying" for s in meddpic.values()):
        suggested = "not_qualified"
    elif blocking:
        suggested = "continue_discovery"
    else:
        suggested = recommended or "proceed"
    return {
        "recommended_status": recommended,
        "suggested_status": suggested,
        "open_blocking_gaps": blocking,
        "meddpic": meddpic,
        "gaps": gap_rows(eng),
    }


def decide(eng: Engagement, status: str, approver: str, rationale: str | None = None, ae_aligned: bool = False,
           ae_note: str | None = None, accept_risk: tuple[str, ...] = ()) -> dict:
    if status not in STATUSES:
        raise LoomError(f"status must be one of {STATUSES}")
    st = eng.stage("opportunity-review")
    if st.get("status") not in ("awaiting_decision", "complete"):
        raise LoomError("No qualification to decide on — run thread-qualify and `loom_state qualify record` first.")
    if st.get("input_hash") != qualify_input_hash(eng):
        raise LoomError("Discovery changed since qualify — re-run thread-qualify and `qualify record` before deciding.")
    if not (approver or "").strip():
        raise LoomError("An approver is required (--approver or LOOM_APPROVER).")
    if accept_risk and not (rationale or "").strip():
        raise LoomError("--accept-risk requires --rationale (recorded as the accepted-risk rationale).")
    for gid in accept_risk:
        respond(eng, gid, "accepted_risk", approver, rationale=rationale)

    ready = readiness(eng)
    blocking = ready["open_blocking_gaps"]
    if status == "proceed" and blocking:
        raise LoomError("Cannot record proceed with open blocking gaps: " + ", ".join(blocking) +
                        "\n  Close them (edit inputs/ → re-listen, or `gaps respond --status answered`), "
                        "or accept the risk explicitly (--accept-risk GAP --rationale …).")
    if status != ready["suggested_status"] and not (rationale or "").strip():
        raise LoomError(f"Decision '{status}' differs from suggested '{ready['suggested_status']}' — add --rationale.")

    profile = _profile(eng)
    responses = load_responses(eng)["responses"]
    live_gaps = {r["gap_id"] for r in ready["gaps"]}
    profile["qualification_status"] = status
    profile["qualification_decision"] = {
        "status": status,
        "recommended_status": ready["recommended_status"],
        "decided_by": approver.strip(),
        "decided_at": now_iso(),
        "rationale": rationale,
        "ae_alignment": {"confirmed": bool(ae_aligned), "note": ae_note},
        "open_blocking_gaps": blocking,
        "override": None,
    }
    profile["accepted_risk"] = [
        {"gap_id": gid, "rationale": r.get("rationale") or "", "accepted_by": r["responded_by"],
         "accepted_at": r["responded_at"]}
        for gid, r in sorted(responses.items()) if r["status"] == "accepted_risk" and gid in live_gaps
    ]
    profile["last_updated"] = now_iso()
    errors = validate(profile, "opportunity-profile")
    if errors:
        raise LoomError("profile failed validation after decision:\n  " + "\n  ".join(errors))
    write_json(eng.path(PROFILE), profile)

    eng.approve("qualification_decision", approver, [PROFILE, SUMMARY, GAPS_MD, GAP_RESPONSES], rationale,
                decision=status, ae_alignment=bool(ae_aligned))
    eng.set_stage("opportunity-review", "complete", decision=status, decided_at=now_iso(),
                  recommended_status=ready["recommended_status"], open_blocking_gaps=blocking,
                  design_anyway=False, decision_profile_hash=sha256_file(eng.path(PROFILE)))
    eng.save()
    return {"decision": status, "open_blocking_gaps": blocking, "accepted_risk": profile["accepted_risk"]}


def design_anyway(eng: Engagement, approver: str, rationale: str) -> dict:
    st = eng.stage("opportunity-review")
    if st.get("decision") != "continue_discovery":
        raise LoomError("Design anyway only applies after a recorded continue_discovery decision.")
    if not (rationale or "").strip():
        raise LoomError("Design anyway requires --rationale (accepted risk).")
    profile = _profile(eng)
    override = {"design_anyway": True, "approver": approver.strip(), "at": now_iso(), "rationale": rationale}
    profile["qualification_decision"]["override"] = override
    write_json(eng.path(PROFILE), profile)
    eng.approve("qualification_override", approver, [PROFILE, GAP_RESPONSES], rationale, decision="design_anyway")
    eng.set_stage("opportunity-review", "complete", design_anyway=True,
                  decision_profile_hash=sha256_file(eng.path(PROFILE)))
    eng.save()
    return override
