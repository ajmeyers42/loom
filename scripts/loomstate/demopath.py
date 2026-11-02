"""Demo path (SB-07): audit the selected capability map, commit predefined | custom (D-049)."""

from __future__ import annotations

import re

from .core import LoomError, find_section, md_sections, now_iso, read_json, sha256_file, sha256_paths
from .intake import AUDIT_JSON, IDEATION, MAP, PROFILE
from .schema import validate
from .state import Engagement
from .vision import _in_scope, catalog, load_map

AUDIT_MD = "demo/{slug}-platform-audit.md"
PREDEFINED_REC = "opportunity/{slug}-predefined-recommendation.md"
RED = ("blocked", "upgrade_required")
AMBER = ("setup_required", "unverified")


def _require_vision(eng: Engagement) -> dict:
    ide = eng.stage("ideation")
    if ide.get("status") != "complete":
        raise LoomError("Demo path needs a frozen vision with approved confirmation (`vision freeze` → `vision confirm`).")
    cmap = load_map(eng)
    if cmap["status"] != "frozen" or ide.get("map_hash") != sha256_file(eng.path(MAP)):
        raise LoomError("Capability map changed since freeze — re-freeze and re-confirm before auditing.")
    return cmap


def plan(eng: Engagement) -> dict:
    cmap = _require_vision(eng)
    cat = catalog()
    return {
        "skills": ["skills/thread-audit/SKILL.md", "skills/thread-suggest/SKILL.md"],
        "audit_scope": [{"capability_id": c["id"], "name": c["name"], "origin": c["origin"],
                         "audit_feature": cat.get(c["id"], {}).get("audit_feature"),
                         "default_remediation_owner": cat.get(c["id"], {}).get("default_remediation_owner", "pipeline")}
                        for c in _in_scope(cmap)],
        "stamp": {"meta.scope_source": "capability_map", "meta.capability_map_hash": sha256_file(eng.path(MAP))},
        "outputs": [eng.rel(AUDIT_JSON), eng.rel(AUDIT_MD), f"{eng.rel(PREDEFINED_REC)} (predefined only)"],
        "catalog": "skills/thread-suggest/references/standard-demos.md",
        "then": "loom_state path check  →  loom_state path commit --path custom|predefined",
    }


def check(eng: Engagement) -> dict:
    cmap = _require_vision(eng)
    apath = eng.path(AUDIT_JSON)
    audit = read_json(apath)
    errors = list(validate(audit, "platform-audit"))
    warnings = []
    for t in (AUDIT_MD,):
        if not eng.path(t).exists():
            errors.append(f"missing {eng.rel(t)}")
    meta = audit.get("meta", {})
    if meta.get("slug") not in (None, eng.slug):
        errors.append(f"audit meta.slug '{meta.get('slug')}' != '{eng.slug}'")
    if meta.get("scope_source") != "capability_map":
        errors.append("audit meta.scope_source must be 'capability_map' (audit the frozen selected map)")
    map_hash = sha256_file(eng.path(MAP))
    if meta.get("capability_map_hash") != map_hash:
        errors.append("audit meta.capability_map_hash does not match the frozen capability map — re-run thread-audit")

    rows = {r.get("capability_id"): r for r in audit.get("feature_audit", []) if r.get("capability_id")}
    scope_ids = [c["id"] for c in _in_scope(cmap)]
    missing = [cid for cid in scope_ids if cid not in rows]
    if missing:
        errors.append(f"audit has no row for selected capabilities: {', '.join(missing)}")
    extra = sorted(set(rows) - set(scope_ids))
    if extra:
        warnings.append(f"audit rows outside the selected map (ignored): {', '.join(extra)}")

    owners: dict[str, list[str]] = {"pipeline": [], "manual_once": [], "customer": []}
    red, ready = [], []
    for cid in scope_ids:
        r = rows.get(cid)
        if not r:
            continue
        status = r.get("status")
        if status == "ready":
            ready.append(cid)
            continue
        if status in RED:
            red.append(cid)
        owner = r.get("remediation_owner")
        if status in AMBER and owner not in owners:
            errors.append(f"row '{cid}' ({status}) needs remediation_owner: pipeline | manual_once | customer")
        elif owner in owners:
            owners[owner].append(cid)
    if errors:
        raise LoomError("platform audit check failed:\n  " + "\n  ".join(errors))
    return {"overall_status": audit.get("overall_status"), "ready": ready, "amber_by_owner": owners, "red": red,
            "warnings": warnings, "map_hash": map_hash}


def _standard_demo_from_rec(text: str) -> str | None:
    body = find_section(md_sections(text), "recommended demo") or ""
    m = re.search(r"\*\*(.+?)\*\*", body)
    return m.group(1).strip() if m else None


def commit(eng: Engagement, path: str, approver: str, rationale: str | None = None,
           standard_demo: str | None = None) -> dict:
    if path not in ("custom", "predefined"):
        raise LoomError("--path must be custom or predefined")
    result = check(eng)
    if result["red"]:
        raise LoomError("Selected capabilities are blocked / need upgrade: " + ", ".join(result["red"]) +
                        "\n  Descope them (`vision map exclude …`) or choose an alternative, then re-freeze.")
    artifacts = [AUDIT_JSON, AUDIT_MD, MAP, IDEATION]
    if path == "predefined":
        rec = eng.path(PREDEFINED_REC)
        if not rec.exists():
            raise LoomError(f"Predefined path needs {eng.rel(PREDEFINED_REC)} (thread-suggest output).")
        standard_demo = standard_demo or _standard_demo_from_rec(rec.read_text())
        if not standard_demo:
            raise LoomError("Could not read the recommended standard demo — pass --standard-demo NAME.")
        artifacts.append(PREDEFINED_REC)

    eng.set_stage("platform-audit", "complete", overall_status=result["overall_status"], map_hash=result["map_hash"],
                  input_hash=sha256_paths([eng.path(MAP), eng.path(IDEATION), eng.path(PROFILE)], eng.dir),
                  amber_by_owner=result["amber_by_owner"], ready_count=len(result["ready"]))
    eng.set_stage("build-path", "complete", path=path, custom_required=(path == "custom"),
                  standard_demo=standard_demo if path == "predefined" else None,
                  pipeline_ends_here=(path == "predefined"), decided_by=approver, decided_at=now_iso())
    eng.state["path"] = path
    eng.approve("demo_path_commit", approver, artifacts, rationale, decision=path)
    eng.save()
    return {"path": path, "standard_demo": standard_demo, **result}
