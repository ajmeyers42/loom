#!/usr/bin/env python3
"""
compare_engagements.py — functional comparison of a legacy engagement vs a P2 re-run.

Read-only on both trees. Reports are engagement data: write them under the sandbox
engagements root, never into the loom repo.

Usage:
  # H0 — fingerprint the legacy snapshot (prove it is never modified)
  python3 scripts/compare_engagements.py manifest <legacy-dir> > <sandbox>/legacy.manifest.json

  # H7 — compare
  python3 scripts/compare_engagements.py compare --legacy <legacy-dir> --candidate <candidate-dir> \
      [--legacy-prefix 2026foo] [--legacy-manifest <sandbox>/legacy.manifest.json] \
      [--through listen|qualify|vision|path] [--out <sandbox>/comparison.md] [--json]

Exit codes: 0 — all candidate gates pass; 1 — a gate failed (see report); 2 — usage error.
Gates apply to the candidate only. Legacy results are the baseline: differences are
classified (same / changed / improved / regressed / info), not failed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loomstate.core import find_identity_leaks, find_section, md_sections, sha256_file  # noqa: E402
from loomstate.schema import validate  # noqa: E402

# Artifact discovery ignores VCS / tool dirs; the unmodified-legacy manifest covers everything but build caches.
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "continual-learning"}
MANIFEST_SKIP_DIRS = {"node_modules", "__pycache__", ".venv"}

ARTIFACTS = {
    # key: (relative candidates with {p}, schema or None)
    "discovery":                 (["demo/{p}-discovery.json"], "discovery"),
    "gaps":                      (["opportunity/{p}-gaps.md"], None),
    "confirmation":              (["opportunity/{p}-confirmation.md"], None),
    "opportunity-summary":       (["opportunity/{p}-opportunity-summary.md"], None),
    "opportunity-profile":       (["opportunity/{p}-opportunity-profile.json"], "opportunity-profile"),
    "demo-goals":                (["opportunity/{p}-demo-goals.md"], None),
    "gap-responses":             (["opportunity/{p}-gap-responses.json"], "gap-responses"),
    "current-state":             (["demo/{p}-current-state.json"], None),
    "ideation":                  (["demo/{p}-ideation.md"], None),
    "capability-map":            (["demo/{p}-capability-map.json"], "capability-map"),
    "platform-audit":            (["demo/{p}-platform-audit.json"], "platform-audit"),
    "platform-audit-md":         (["demo/{p}-platform-audit.md"], None),
    "predefined-recommendation": (["opportunity/{p}-predefined-recommendation.md"], None),
    "pipeline-state":            (["{p}-pipeline-state.json"], "pipeline-state"),
    "demo-script":               (["demo/{p}-demo-script.md"], None),
    "data-model":                (["data/{p}-data-model.json"], None),
    "demo-checklist":            (["deploy/{p}-demo-checklist.md"], None),
}

THROUGH = {
    "listen":  ["discovery-parser"],
    "qualify": ["discovery-parser", "opportunity-review"],
    "vision":  ["discovery-parser", "opportunity-review", "ideation"],
    "path":    ["discovery-parser", "opportunity-review", "ideation", "platform-audit", "build-path"],
}
GATE_APPROVALS = {
    "opportunity-review": ("qualification_decision",),
    "ideation": ("vision_freeze", "confirmation_approve"),
    "build-path": ("demo_path_commit",),
}
SHARED_KEYS = ("ideation", "capability-map", "platform-audit", "platform-audit-md", "predefined-recommendation",
               "demo-script", "data-model", "demo-checklist")


# ── tree helpers ────────────────────────────────────────────────────────────

def iter_files(root: Path, skip=SKIP_DIRS):
    for p in sorted(root.rglob("*")):
        if p.is_file() and not any(part in skip for part in p.relative_to(root).parts):
            yield p


def manifest(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): sha256_file(p) for p in iter_files(root, MANIFEST_SKIP_DIRS)}


def detect_prefix(root: Path) -> str:
    votes = Counter()
    for suffix in ("-discovery.json", "-opportunity-profile.json", "-pipeline-state.json", "-ideation.md",
                   "-platform-audit.json", "-demo-script.md"):
        for p in iter_files(root):
            if p.name.endswith(suffix):
                votes[p.name[: -len(suffix)]] += 1
    if not votes:
        raise SystemExit(f"❌  no loom artifacts found under {root} — pass --legacy-prefix")
    return votes.most_common(1)[0][0]


def resolve(root: Path, prefix: str, key: str) -> Path | None:
    templates, _ = ARTIFACTS[key]
    for t in templates:
        p = root / t.format(p=prefix)
        if p.is_file():
            return p
    name = Path(templates[0].format(p=prefix)).name
    hits = [p for p in iter_files(root) if p.name == name]
    return hits[0] if hits else None


def load_json(path: Path | None):
    if not path:
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"__unparseable__": True}


def norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def tokens(s) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", norm(s)) if len(w) > 2}


def jaccard(a: set, b: set) -> float:
    return round(len(a & b) / len(a | b), 2) if a | b else 1.0


# ── report model ────────────────────────────────────────────────────────────

class Report:
    def __init__(self):
        self.rows: list[dict] = []
        self.gates: list[dict] = []

    def row(self, area, check, legacy, candidate, verdict, note=""):
        self.rows.append({"area": area, "check": check, "legacy": legacy, "candidate": candidate,
                          "verdict": verdict, "note": note})

    def gate(self, name, ok, detail="", pass_detail=""):
        """``detail`` explains a failure and is shown only when the gate fails."""
        self.gates.append({"gate": name, "ok": bool(ok), "detail": pass_detail if ok else detail})

    @property
    def ok(self):
        return all(g["ok"] for g in self.gates)


def missing(v) -> bool:
    return v is None or v in ("", "—")


def verdict(legacy, candidate, better=None):
    if missing(legacy) or missing(candidate):
        return "same" if missing(legacy) and missing(candidate) else "info"
    if legacy == candidate:
        return "same"
    if better is not None:
        return "improved" if better else "regressed"
    return "changed"


# ── area checks ─────────────────────────────────────────────────────────────

def check_inventory(r: Report, L: dict, C: dict):
    for key in ARTIFACTS:
        lp, cp = L["paths"].get(key), C["paths"].get(key)
        if not lp and not cp:
            continue
        r.row("inventory", key, "present" if lp else "absent", "present" if cp else "absent",
              "same" if bool(lp) == bool(cp) else ("improved" if cp else "info"))


def check_schemas(r: Report, L: dict, C: dict):
    for key, (_, schema) in ARTIFACTS.items():
        if not schema:
            continue
        lerr = cerr = None
        if L["paths"].get(key):
            lerr = len(validate(load_json(L["paths"][key]) or {}, schema))
        if C["paths"].get(key):
            cerrs = validate(load_json(C["paths"][key]) or {}, schema)
            cerr = len(cerrs)
            r.gate(f"schema:{key}", cerr == 0, "; ".join(cerrs[:3]))
        if lerr is None and cerr is None:
            continue
        better = None if lerr is None or cerr is None else (cerr < lerr if cerr != lerr else None)
        r.row("schema", f"{key} errors", lerr if lerr is not None else "—", cerr if cerr is not None else "—",
              verdict(lerr, cerr, better), "legacy predates P2 contracts" if lerr else "")


def check_discovery(r: Report, L: dict, C: dict):
    ld, cd = load_json(L["paths"].get("discovery")) or {}, load_json(C["paths"].get("discovery")) or {}
    if not cd:
        r.gate("discovery present", False, "candidate discovery JSON missing")
        return
    for label, getter in (
        ("customer.industry", lambda d: (d.get("customer") or {}).get("industry")),
        ("demo_scope.recommended_type", lambda d: (d.get("demo_scope") or {}).get("recommended_type")),
        ("elastic_relationship.status", lambda d: (d.get("elastic_relationship") or {}).get("status")),
        ("deal_context.stage", lambda d: (d.get("deal_context") or {}).get("stage")),
        ("deal_context.urgency", lambda d: (d.get("deal_context") or {}).get("urgency")),
    ):
        lv, cv = getter(ld), getter(cd)
        r.row("discovery", label, lv, cv, verdict(norm(lv), norm(cv)))
    for label, key in (("contacts", "contacts"), ("pain_points", "pain_points"), ("gaps", "gaps"),
                       ("claims", "claims")):
        lv, cv = len(ld.get(key) or []), len(cd.get(key) or [])
        r.row("discovery", f"{label} count", lv, cv,
              verdict(lv, cv, (cv > lv) if key == "claims" and cv != lv else None))
    lp = set().union(*[tokens(p.get("label")) for p in ld.get("pain_points") or []] or [set()])
    cp = set().union(*[tokens(p.get("label")) for p in cd.get("pain_points") or []] or [set()])
    r.row("discovery", "pain label token overlap (jaccard)", "", jaccard(lp, cp), "info",
          "< 0.3 → review: same notes should surface similar pains")
    lg = {norm(g.get("field")) for g in ld.get("gaps") or []}
    cg = {norm(g.get("field")) for g in cd.get("gaps") or []}
    r.row("discovery", "gap fields only in legacy", "", sorted(lg - cg)[:8], "info")
    r.row("discovery", "gap fields only in candidate", "", sorted(cg - lg)[:8], "info")

    # candidate evidence (read-only re-verification of listen record)
    cache, bad, refs = {}, [], 0
    items = [("claims", c.get("claim_id"), c.get("source_ref")) for c in cd.get("claims") or []]
    items += [("pain_points", p.get("label"), p.get("source_ref")) for p in cd.get("pain_points") or []]
    for kind, ident, ref in items:
        if not ref:
            continue
        refs += 1
        path = C["dir"] / (ref.get("file") or "")
        if not str(ref.get("file", "")).startswith("inputs/") or not path.is_file():
            bad.append(f"{kind}:{ident} file {ref.get('file')}")
            continue
        text = cache.setdefault(path, norm(path.read_text(errors="replace")))
        if ref.get("excerpt") and norm(ref["excerpt"]) not in text:
            bad.append(f"{kind}:{ident} excerpt")
    n_claims = len(cd.get("claims") or [])
    importing = C["state"].get("entry_mode") == "import"
    r.gate("evidence: claims present", n_claims > 0 or importing, "0 claims",
           f"{n_claims} claims" if n_claims else "exempt (import)")
    r.gate("evidence: source_refs verify", not bad, "; ".join(bad[:5]), f"{refs} verified")
    r.gate("gaps: every gap has gap_id", all(g.get("gap_id") for g in cd.get("gaps") or []))
    r.row("discovery", "verified source_refs", 0, refs - len(bad), "improved" if refs - len(bad) else "same")


def check_qualification(r: Report, L: dict, C: dict):
    lp, cp = load_json(L["paths"].get("opportunity-profile")) or {}, load_json(C["paths"].get("opportunity-profile")) or {}
    stage = (C["state"].get("stages") or {}).get("opportunity-review") or {}
    r.row("qualify", "qualification_status (recommendation)", lp.get("qualification_status"),
          cp.get("qualification_status"), verdict(lp.get("qualification_status"), cp.get("qualification_status")))
    r.row("qualify", "recorded SA decision", "— (not recorded)", stage.get("decision") or "—",
          "improved" if stage.get("decision") else "info")
    lm, cm = lp.get("meddpic") or {}, cp.get("meddpic") or {}
    dims = sorted(set(lm) | set(cm))
    same = sum(1 for d in dims if (lm.get(d) or {}).get("status") == (cm.get(d) or {}).get("status"))
    r.row("qualify", "MEDDPIC dimensions with same status", "", f"{same}/{len(dims)}", "info",
          "differences are LLM variance unless new inputs explain them")
    if cp:
        r.gate("qualify: decision fields written by CLI", "qualification_decision" in cp
               or stage.get("design_anyway"), "profile lacks qualification_decision")


def _legacy_capabilities(ideation: str) -> list[str]:
    body = find_section(md_sections(ideation), "elastic capability map") or ""
    rows = [ln for ln in body.splitlines() if ln.strip().startswith("|")][2:]
    return [norm(re.sub(r"[`*]", "", ln.strip().strip("|").split("|")[0])) for ln in rows if ln.strip("| -")]


def check_vision(r: Report, L: dict, C: dict):
    lp, cp = L["paths"].get("ideation"), C["paths"].get("ideation")
    lt = lp.read_text(errors="replace") if lp else ""
    ct = cp.read_text(errors="replace") if cp else ""
    def arch(text: str) -> str:
        lines = [ln for ln in (find_section(md_sections(text), "chosen archetype") or "").splitlines() if ln.strip()]
        return norm(re.sub(r"[*_`#]", "", lines[0])) if lines else ""

    r.row("vision", "chosen archetype", arch(lt)[:80] or "—", arch(ct)[:80] or "—", verdict(arch(lt), arch(ct)))
    legacy_caps = _legacy_capabilities(lt) if lt else []
    cmap = load_json(C["paths"].get("capability-map")) or {}
    in_scope = [c for c in cmap.get("capabilities") or [] if c.get("in_scope", True)]
    cand_caps = [norm(f"{c.get('name', '')} {c.get('id', '')}") for c in in_scope]
    matched = [lc for lc in legacy_caps if any(jaccard(tokens(lc), tokens(cc)) >= 0.25 for cc in cand_caps)]
    r.row("vision", "capabilities (legacy table rows / candidate map in-scope)", len(legacy_caps), len(in_scope),
          "info", f"{len(matched)} legacy rows matched by name")
    r.row("vision", "legacy capabilities not in candidate map", "",
          [lc for lc in legacy_caps if lc not in matched][:8], "info")
    origins = Counter(c.get("origin") for c in in_scope)
    r.row("vision", "candidate map origins", "", dict(origins), "info")
    if cmap:
        r.gate("vision: map frozen", cmap.get("status") == "frozen", f"status={cmap.get('status')}")
        r.gate("vision: ≥1 SA-added capability", origins.get("sa_added", 0) + origins.get("sa_requested", 0) > 0)
        ids = {c.get("id") for c in in_scope}
        if "agent-builder" in ids:
            r.gate("vision: D-036 token visibility", "ai-cost-dashboard" in ids or cmap.get("token_visibility") is False)


def check_audit(r: Report, L: dict, C: dict):
    la, ca = load_json(L["paths"].get("platform-audit")) or {}, load_json(C["paths"].get("platform-audit")) or {}
    r.row("audit", "overall_status", la.get("overall_status"), ca.get("overall_status"),
          verdict(la.get("overall_status"), ca.get("overall_status")))
    lf = {norm(f.get("feature")): f.get("status") for f in la.get("feature_audit") or []}
    cf = {norm(f.get("feature") or f.get("capability_id")): f.get("status") for f in ca.get("feature_audit") or []}
    r.row("audit", "feature rows", len(lf), len(cf), "info", "candidate is scoped to the capability map")
    common = [k for k in lf if any(jaccard(tokens(k), tokens(c)) >= 0.4 for c in cf)]
    r.row("audit", "legacy features also audited", "", f"{len(common)}/{len(lf)}", "info")
    if ca:
        meta = ca.get("meta") or {}
        r.gate("audit: scope_source capability_map", meta.get("scope_source") == "capability_map")
        mp = C["paths"].get("capability-map")
        r.gate("audit: map hash current", mp is not None and meta.get("capability_map_hash") == sha256_file(mp))
        missing = [f.get("capability_id") for f in ca.get("feature_audit") or []
                   if f.get("status") != "ready" and not f.get("remediation_owner")]
        r.gate("audit: remediation_owner on non-ready rows", not missing, ", ".join(map(str, missing)))


def check_path(r: Report, L: dict, C: dict):
    legacy = ("predefined" if L["paths"].get("predefined-recommendation")
              else "custom (inferred: demo script)" if L["paths"].get("demo-script") else "unset")
    cand = C["state"].get("path", "unset")
    r.row("path", "demo path", legacy, cand, "same" if legacy.split()[0] == cand else "changed")


def check_state(r: Report, L: dict, C: dict, through: str):
    ls, cs = L["state"], C["state"]
    r.row("state", "input_hash style",
          "sha256" if any(str(s.get("input_hash", "")).startswith("sha256:") for s in (ls.get("stages") or {}).values())
          else ("mtime/other" if ls else "no state"), "sha256", "info")
    r.row("state", "approvals recorded", len(ls.get("approvals") or []), len(cs.get("approvals") or []),
          "improved" if len(cs.get("approvals") or []) > len(ls.get("approvals") or []) else "same")
    stages = cs.get("stages") or {}
    actions = {a.get("action") for a in cs.get("approvals") or []}
    for key in THROUGH[through]:
        st = (stages.get(key) or {}).get("status")
        r.gate(f"stage {key} complete", st == "complete", f"status={st}")
        for action in GATE_APPROVALS.get(key, ()):
            alt = {"qualification_decision": {"qualification_override"}}.get(action, set())
            r.gate(f"approval {action}", action in actions or bool(actions & alt))
    latest = {}  # artifact -> (action, hash) of the most recent approval that recorded it
    for a in cs.get("approvals") or []:
        for rel, h in (a.get("artifacts") or {}).items():
            latest[rel] = (a.get("action"), h)
    drift = []
    for rel, (action, h) in latest.items():
        cur = sha256_file(C["dir"] / rel) if (C["dir"] / rel).is_file() else None
        if h != "absent" and cur and cur != h:
            drift.append(f"{action}:{rel}")
    r.row("state", "approved artifacts edited since approval", "", sorted(set(drift))[:8] or "none",
          "info" if drift else "same", "expected only for living docs re-run after the gate")


def check_identity(r: Report, L: dict, C: dict):
    identity = C["state"].get("identity") or {}
    if not identity.get("company_name"):
        r.gate("identity: private identity recorded", False, "candidate state has no identity.company_name")
        return

    def scan(side: dict, keys) -> list[str]:
        hits = []
        for key in keys:
            p = side["paths"].get(key)
            if p and (leaks := find_identity_leaks(p.read_text(errors="replace"), identity)):
                hits.append(f"{key}: {', '.join(leaks)}")
        for name in (".env.example", ".env"):
            p = side["dir"] / name
            if p.is_file():
                values = "\n".join(ln.split("=", 1)[1] for ln in p.read_text(errors="replace").splitlines()
                                   if "=" in ln and not ln.lstrip().startswith("#"))
                if leaks := find_identity_leaks(values, identity):
                    hits.append(f"{name}: {', '.join(leaks)}")
        if leaks := find_identity_leaks(side["prefix"], identity):
            hits.append(f"file prefix: {', '.join(leaks)}")
        return hits

    lh = scan(L, SHARED_KEYS)
    if L["prefix"].lower() != C["prefix"].lower():
        identity = {**identity, "legacy_slugs": sorted(set(identity.get("legacy_slugs") or []) | {L["prefix"]})}
    ch = scan(C, SHARED_KEYS)
    r.row("identity", "private identity on shared artifacts", len(lh), len(ch),
          verdict(len(lh), len(ch), len(ch) < len(lh) if len(ch) != len(lh) else None),
          "; ".join(lh[:4]))
    r.gate("identity: no leaks on candidate shared artifacts", not ch, "; ".join(ch[:5]))


# ── driver ──────────────────────────────────────────────────────────────────

def side(root: Path, prefix: str | None) -> dict:
    prefix = prefix or detect_prefix(root)
    paths = {k: resolve(root, prefix, k) for k in ARTIFACTS}
    state = load_json(paths.get("pipeline-state")) or {}
    return {"dir": root, "prefix": prefix, "paths": paths, "state": state}


def compare(args) -> Report:
    r = Report()
    L = side(Path(args.legacy).expanduser().resolve(), args.legacy_prefix)
    C = side(Path(args.candidate).expanduser().resolve(), args.candidate_prefix or Path(args.candidate).name)
    if not C["state"]:
        r.gate("candidate pipeline-state present", False, "run loom_state new first")
    if args.legacy_manifest:
        before = json.loads(Path(args.legacy_manifest).read_text())
        after = manifest(L["dir"])
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        newly_covered = SKIP_DIRS - MANIFEST_SKIP_DIRS
        if changed and all(k not in before and newly_covered & set(k.split("/")) for k in changed):
            detail = (f"manifest predates full coverage ({len(changed)} files under "
                      f"{', '.join(sorted(newly_covered))} not fingerprinted) — regenerate it")
        else:
            detail = ", ".join(changed[:5])
        r.gate("legacy tree unmodified", not changed, detail, f"{len(after)} files")
    stages = THROUGH[args.through]
    sections = [check_inventory, check_schemas, check_discovery, check_qualification]
    sections += [fn for fn, stage in ((check_vision, "ideation"), (check_audit, "platform-audit"),
                                      (check_path, "build-path")) if stage in stages]
    for fn in sections + [check_identity]:
        fn(r, L, C)
    check_state(r, L, C, args.through)
    r.meta = {"legacy": str(L["dir"]), "legacy_prefix": L["prefix"], "candidate": str(C["dir"]),
              "candidate_prefix": C["prefix"], "through": args.through}
    return r


def render(r: Report) -> str:
    def cell(v):
        s = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v if v is not None else "—")
        return s.replace("|", "\\|")[:120]

    out = ["# Legacy vs P2 comparison", "",
           f"- Legacy: `{r.meta['legacy']}` (prefix `{r.meta['legacy_prefix']}`)",
           f"- Candidate: `{r.meta['candidate']}` (slug `{r.meta['candidate_prefix']}`), through `{r.meta['through']}`",
           f"- Result: **{'PASS' if r.ok else 'FAIL'}** — {sum(g['ok'] for g in r.gates)}/{len(r.gates)} gates",
           "", "## Gates (candidate)", "", "| Gate | Result | Detail |", "|---|---|---|"]
    out += [f"| {g['gate']} | {'✅' if g['ok'] else '❌'} | {cell(g['detail'])} |" for g in r.gates]
    counts = Counter(row["verdict"] for row in r.rows)
    out += ["", "## Comparison", "", "Verdicts: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())), ""]
    area = None
    for row in r.rows:
        if row["area"] != area:
            area = row["area"]
            out += ["", f"### {area}", "", "| Check | Legacy | Candidate | Verdict | Note |", "|---|---|---|---|---|"]
        out.append(f"| {row['check']} | {cell(row['legacy'])} | {cell(row['candidate'])} | {row['verdict']} | "
                   f"{cell(row['note'])} |")
    out += ["", "## Triage", "",
            "Classify every `regressed`/`changed` row and failed gate as **P2 bug**, **intentional contract "
            "change** (see docs/testing/p2-legacy-comparison.md §Expected differences), or **LLM variance**.", ""]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compare a legacy engagement with a P2 re-run (read-only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("manifest", help="sha256 manifest of a tree (prove legacy is untouched)")
    m.add_argument("dir")
    c = sub.add_parser("compare")
    c.add_argument("--legacy", required=True)
    c.add_argument("--candidate", required=True)
    c.add_argument("--legacy-prefix", help="Legacy artifact file prefix (auto-detected)")
    c.add_argument("--candidate-prefix", help="Candidate slug (default: candidate folder name)")
    c.add_argument("--legacy-manifest", help="Manifest captured at H0")
    c.add_argument("--through", choices=list(THROUGH), default="path")
    c.add_argument("--out", help="Write markdown report here (sandbox only)")
    c.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "manifest":
        print(json.dumps(manifest(Path(args.dir).expanduser().resolve()), indent=2, sort_keys=True))
        return 0
    report = compare(args)
    text = render(report)
    if args.out:
        out = Path(args.out).expanduser()
        repo = Path(__file__).resolve().parents[1]
        if repo in out.resolve().parents:
            print("❌  refusing to write an engagement report inside the loom repo", file=sys.stderr)
            return 2
        out.write_text(text)
    if args.json:
        print(json.dumps({"ok": report.ok, "meta": report.meta, "gates": report.gates, "rows": report.rows},
                         indent=2, ensure_ascii=False, default=str))
    elif not args.out:
        print(text)
    else:
        print(f"{'✅ PASS' if report.ok else '❌ FAIL'} — report: {args.out}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
