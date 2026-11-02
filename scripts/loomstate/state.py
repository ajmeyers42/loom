"""Pipeline-state load/save, stage + approval records, derived phase / next action."""

from __future__ import annotations

from pathlib import Path

from . import SCHEMA_VERSION
from .core import (
    LoomError,
    now_iso,
    read_json,
    sha256_file,
    state_path,
    write_json,
)
from .schema import validate

# Output contract per stage key (paths relative to engagement dir).
STAGE_OUTPUTS = {
    "discovery-parser": ["demo/{slug}-discovery.json", "opportunity/{slug}-gaps.md", "opportunity/{slug}-confirmation.md"],
    "diagnostic-analyzer": ["demo/{slug}-current-state.json"],
    "opportunity-review": [
        "opportunity/{slug}-opportunity-summary.md",
        "opportunity/{slug}-opportunity-profile.json",
        "opportunity/{slug}-demo-goals.md",
    ],
    "ideation": ["demo/{slug}-ideation.md", "demo/{slug}-capability-map.json"],
    "platform-audit": ["demo/{slug}-platform-audit.json", "demo/{slug}-platform-audit.md"],
    "build-path": [],
}

P2_STAGES = list(STAGE_OUTPUTS)


class Engagement:
    """Bound engagement: root dir + slug + loaded state."""

    def __init__(self, eng_dir: Path, state: dict):
        self.dir = eng_dir
        self.state = state

    @property
    def slug(self) -> str:
        return self.state["slug"]

    def path(self, template: str) -> Path:
        return self.dir / template.format(slug=self.slug)

    def rel(self, template: str) -> str:
        return template.format(slug=self.slug)

    @property
    def stages(self) -> dict:
        return self.state.setdefault("stages", {})

    def stage(self, key: str) -> dict:
        return self.stages.setdefault(key, {"status": "pending"})

    def set_stage(self, key: str, status: str, **fields) -> dict:
        st = self.stage(key)
        st["status"] = status
        st["updated_at"] = now_iso()
        outs = STAGE_OUTPUTS.get(key)
        if outs:
            st.setdefault("output", self.rel(outs[0]))
            st["outputs"] = [self.rel(o) for o in outs if self.path(o).exists()]
        for k, v in fields.items():
            if v is None:
                st.pop(k, None)
            else:
                st[k] = v
        return st

    def artifact_hashes(self, templates: list[str]) -> dict:
        out = {}
        for t in templates:
            rel = self.rel(t)
            out[rel] = sha256_file(self.dir / rel) or "absent"
        return out

    def approve(self, action: str, approver: str, templates: list[str], rationale: str | None = None,
                **extra) -> dict:
        if not (approver or "").strip():
            raise LoomError("An approver is required (--approver or LOOM_APPROVER).")
        rec = {
            "action": action,
            "approver": approver.strip(),
            "timestamp": now_iso(),
            "artifacts": self.artifact_hashes(templates),
        }
        if rationale:
            rec["rationale"] = rationale
        rec.update({k: v for k, v in extra.items() if v is not None})
        self.state.setdefault("approvals", []).append(rec)
        return rec

    def last_approval(self, action: str) -> dict | None:
        for rec in reversed(self.state.get("approvals", [])):
            if rec.get("action") == action:
                return rec
        return None

    def save(self) -> None:
        self.state["last_updated"] = now_iso()
        self.state["schema_version"] = SCHEMA_VERSION
        errors = validate(self.state, "pipeline-state")
        if errors:
            raise LoomError("pipeline-state failed schema validation:\n  " + "\n  ".join(errors))
        write_json(state_path(self.dir, self.slug), self.state)


def load(root: Path, slug: str) -> Engagement:
    eng_dir = root / slug
    sp = state_path(eng_dir, slug)
    if not sp.exists():
        raise LoomError(f"No pipeline-state for '{slug}' under {root} (expected {sp.name}). Run `loom_state new` first.")
    state = read_json(sp)
    if state.get("slug") != slug:
        raise LoomError(f"{sp.name} slug '{state.get('slug')}' does not match folder '{slug}'.")
    return Engagement(eng_dir, state)


def initial_state(slug: str, eng_dir: Path, identity: dict, entry_mode: str, solution: str, tag_id: str) -> dict:
    ts = now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "engagement_dir": str(eng_dir),
        "created_at": ts,
        "last_updated": ts,
        "tag_id": tag_id,
        "solution": solution,
        "identity": identity,
        "entry_mode": entry_mode,
        "path": "unset",
        "keystore": {"status": "empty", "deferred": False, "source": None, "cloned_from": None,
                     "validated_at": None, "elastic_version": None, "missing": [], "updated_at": None},
        "approvals": [],
        "stages": {k: {"status": "pending"} for k in P2_STAGES},
    }


# ── Derived phase / next action ───────────────────────────────────────────

def _done(stages: dict, key: str) -> bool:
    return stages.get(key, {}).get("status") in ("complete", "skipped")


def derive(state: dict, stale: dict | None = None) -> dict:
    """Compute Overview (phase, next action, blockers) from pipeline-state alone.

    ``stale`` optionally maps stage key -> reason (from filesystem hash checks).
    """
    stale = stale or {}
    stages = state.get("stages", {})
    entry = state.get("entry_mode", "notes")
    path = state.get("path", "unset")
    ks = state.get("keystore", {})
    blockers: list[str] = []
    notes: list[str] = []

    if ks.get("status") in (None, "empty", "partial"):
        label = "deferred" if ks.get("deferred") else ks.get("status", "empty")
        notes.append(f"keystore {label} — required before live verify / deploy / agent-runtime launch (not for planning)")
    ksol = state.get("kibana_solution") or {}
    if ksol.get("source") != "sa":
        notes.append(f"Kibana space solution suggested: {ksol.get('value', 'classic')}"
                     + (f" ({ksol['reason']})" if ksol.get("reason") else "")
                     + f" — confirm or override in input settings (keys set {state.get('slug')} "
                       "KIBANA_SOLUTION=classic|es|oblt|security)")

    for key, reason in stale.items():
        blockers.append(f"{key} is stale ({reason}) — re-run required")

    op = stages.get("opportunity-review", {})
    decision = op.get("decision")
    override = op.get("design_anyway", False)
    ideation = stages.get("ideation", {})
    bp = stages.get("build-path", {})

    def result(phase, action, command=None, extra_blockers=()):
        return {
            "slug": state.get("slug"),
            "company": (state.get("identity") or {}).get("company_name"),
            "public_display_name": (state.get("identity") or {}).get("public_display_name"),
            "phase": phase,
            "next_action": action,
            "command": command,
            "blockers": blockers + list(extra_blockers),
            "notes": notes,
            "path": path,
            "vision": _vision_label(ideation),
            "qualification": decision or op.get("recommended_status") or "pending",
            "keystore": ks.get("status", "empty") + (" (deferred)" if ks.get("deferred") else ""),
        }

    if decision == "not_qualified":
        return result("Qualify", "Stopped: recorded not_qualified — archive notes or retire the engagement", None,
                      ["qualification decision is not_qualified (custom build ended)"])

    scratch_no_discovery = entry == "scratch" and not _done(stages, "discovery-parser")

    if not scratch_no_discovery:
        if not _done(stages, "discovery-parser") or "discovery-parser" in stale:
            if entry == "import":
                return result("Intake", "Register the imported AE/SDR package (validates discovery + gaps)",
                              "loom_state listen record")
            return result("Intake", "Extract evidence from inputs/ with warp-listen, then register it",
                          "loom_state listen plan  →  warp-listen  →  loom_state listen record")
        st = op.get("status", "pending")
        if st in ("pending", "running", "stale") or "opportunity-review" in stale:
            return result("Qualify", "Run thread-qualify (MEDDPIC + demo-goals), then register it",
                          "loom_state qualify plan  →  thread-qualify  →  loom_state qualify record")
        if st == "awaiting_decision":
            return result("Qualify", "Record qualification decision", "loom_state qualify decide --status …")
        if decision == "continue_discovery" and not override:
            open_gaps = op.get("open_blocking_gaps", [])
            extra = [f"{len(open_gaps)} open blocking gap(s): {', '.join(open_gaps)}"] if open_gaps else []
            return result(
                "Qualify",
                "Parked on continue_discovery — close gaps (edit inputs/ → re-listen, or gaps respond) then re-decide; "
                "or Design anyway (accept risk)",
                "loom_state gaps list | loom_state qualify design-anyway --rationale …",
                extra,
            )

    ist = ideation.get("status", "pending")
    if ist in ("pending", "running", "stale") or "ideation" in stale:
        mode = "Mode 3 (scratch)" if scratch_no_discovery else (
            "Mode 1 (demo-goals)" if _done(stages, "opportunity-review") else "Mode 2 (discovery)")
        return result("Design", f"Draft vision + capability map with warp-spark ({mode}), then freeze",
                      "loom_state vision plan  →  warp-spark  →  loom_state vision freeze")
    if ist == "awaiting_confirmation":
        return result("Design", "Review refreshed customer confirmation + summary TL;DR, then approve",
                      "loom_state vision confirm")

    if not _done(stages, "build-path") or "platform-audit" in stale:
        return result("Design", "Audit the selected capability map (thread-audit), then commit the demo path",
                      "loom_state path plan  →  thread-audit [+ thread-suggest]  →  loom_state path commit --path …")

    if path == "predefined":
        demo = bp.get("standard_demo") or "standard demo"
        return result("Design", f"Demo path committed: predefined ({demo}) — hand off to the standard demo catalog; "
                                "custom Build stays locked", None)
    return result("Build & Validate", "Demo path committed: custom — continue to Build (P3: weave-script and "
                                      "conditional weave stages)", None)


def _vision_label(ideation: dict) -> str:
    st = ideation.get("status", "pending")
    return {"complete": "frozen + confirmation approved", "awaiting_confirmation": "frozen — confirmation pending"}.get(
        st, "not frozen" if st != "stale" else "stale — re-freeze")
