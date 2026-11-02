"""loom_state CLI — SA-first control plane (P2: Intake → Qualify → Vision freeze → Demo path).

Examples (synthetic):
  loom_state new --slug acme-pharma --display "Acme Pharma" --company "Northwind Pharmaceuticals" \\
      --opportunity "NW Pharma — SOC AI FY26" --entry-mode notes --solution security --notes call-notes.md
  loom_state keys list acme-pharma            # sibling picklist (status only)
  loom_state keys clone acme-pharma --from acme-retailsearch
  loom_state keys defer acme-pharma
  loom_state listen plan acme-pharma          # then run warp-listen
  loom_state listen record acme-pharma
  loom_state gaps list acme-pharma
  loom_state qualify record acme-pharma       # after thread-qualify
  loom_state qualify decide acme-pharma --status proceed --ae-aligned
  loom_state vision map add acme-pharma agent-builder --outcome … --proof …
  loom_state vision freeze acme-pharma        # after warp-spark Plan Contract
  loom_state vision confirm acme-pharma       # after confirmation + TL;DR refresh
  loom_state path commit acme-pharma --path custom
  loom_state next acme-pharma

Root: --root or $LOOM_ENGAGEMENTS_ROOT (default ~/engagements). Approver: --approver or $LOOM_APPROVER.
Never calls a cluster except `keys validate --probe` (read-only GET / and Kibana /api/status).
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from . import bootstrap, demopath, intake, keystore, qualify, state, vision
from .core import REPO_ROOT, LoomError, default_approver, find_git_worktree, find_identity_leaks, get_root


def _out(args, data, human=None):
    if args.json or human is None:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        human(data)


def _approver(args) -> str:
    who = (getattr(args, "approver", None) or default_approver() or "").strip()
    if not who:
        raise LoomError("An approver is required (--approver or LOOM_APPROVER).")
    return who


def _load(args) -> state.Engagement:
    return state.load(get_root(args.root), args.slug)


def _print_list(title, items):
    if items:
        print(f"  {title}:")
        for it in items:
            print(f"    · {it}")


# ── commands ──────────────────────────────────────────────────────────────

def cmd_new(args):
    eng, msgs = bootstrap.create(
        get_root(args.root), slug=args.slug, company=args.company, opportunity=args.opportunity,
        opportunity_id=args.opportunity_id, display=args.display, entry_mode=args.entry_mode,
        solution=args.solution, notes_files=[Path(p) for p in args.notes or []],
        import_dir=Path(args.import_dir) if args.import_dir else None,
        allow_suffix=not args.no_suffix, allow_git_root=args.allow_git_root)
    data = {"slug": eng.slug, "engagement_dir": str(eng.dir), "tag": f"loom:{eng.state['tag_id']}",
            "entry_mode": eng.state["entry_mode"], "messages": msgs, "next": state.derive(eng.state)}

    def human(d):
        print(f"✅  Created {d['slug']}  →  {d['engagement_dir']}")
        print(f"    tag {d['tag']} · space /s/{d['slug']} · entry mode {d['entry_mode']}")
        for m in d["messages"]:
            print(f"    {m}")
        print(f"\n    Next: {d['next']['next_action']}")
        print("    Keystore is optional for planning: `loom_state keys …` or `keys defer`.")
    _out(args, data, human)


def cmd_inputs_add(args):
    eng = _load(args)
    msgs = [bootstrap.add_input(eng, Path(p)) for p in args.files]
    eng.save()
    _out(args, {"messages": msgs}, lambda d: [print(f"  {m}") for m in d["messages"]])


def _ks_human(d):
    ks = d.get("keystore", d)
    print(f"  keystore: {ks.get('status')}" + (" (deferred)" if ks.get("deferred") else ""))
    if ks.get("missing"):
        print(f"  missing: {', '.join(ks['missing'])}")
    for k in ("copied", "warnings"):
        if d.get(k):
            print(f"  {k}: {', '.join(d[k])}")
    if d.get("skipped"):
        for k, why in sorted(d["skipped"].items()):
            print(f"  skipped {k}: {why}")
    if d.get("shared_cluster"):
        print(f"  shared cluster → INDEX_PREFIX={d['index_prefix']} (distinct from siblings)")
    if d.get("elastic_version"):
        print(f"  Elasticsearch {d['elastic_version']} · Kibana {d.get('kibana_version')}")


def cmd_keys(args):
    root = get_root(args.root)
    eng = state.load(root, args.slug)
    action = args.keys_action
    if action == "status":
        vals = keystore.parse_env(eng.dir / ".env")
        status, missing = keystore.compute_status(vals)
        ks = eng.state.get("keystore", {})
        data = {"status": ks.get("status") if ks.get("status") == "validated" else status, "missing": missing,
                "deferred": ks.get("deferred", False), "path": str(eng.dir / ".env"),
                "source": ks.get("source"), "cloned_from": ks.get("cloned_from"),
                "elastic_version": ks.get("elastic_version")}
        _out(args, data, _ks_human)
        return
    if action == "list":
        sibs = [{k: s[k] for k in ("slug", "has_env", "summary")} for s in keystore.siblings(root, eng.slug)]
        mine = keystore.parse_env(eng.dir / ".env").get("ELASTICSEARCH_URL", "")
        for s, full in zip(sibs, keystore.siblings(root, eng.slug)):
            s["same_cluster"] = bool(mine) and keystore._norm_url(mine) == keystore._norm_url(full["es_url"])

        def human(d):
            print(f"  Sibling keystores under {root} (status only — no values):")
            for s in d or []:
                if s["has_env"]:
                    print(f"    {s['slug']:<28} {s['summary']}" + ("  [same cluster]" if s["same_cluster"] else ""))
            if not any(s["has_env"] for s in d or []):
                print("    (none)")
        _out(args, sibs, human)
        return
    if action == "init":
        data = keystore.init_from_sample(eng)
    elif action == "set":
        updates = {}
        for pair in args.pairs:
            if "=" not in pair:
                raise LoomError(f"Expected KEY=VALUE, got '{pair}'")
            k, v = pair.split("=", 1)
            if v == "-":
                v = getpass.getpass(f"{k}: ")
            updates[k.strip()] = v.strip()
        data = keystore.set_values(eng, updates)
    elif action == "clone":
        data = keystore.clone(eng, root, args.source, include_secrets=not args.no_secrets,
                              index_prefix=args.index_prefix, keep=tuple(args.keep or ()))
    elif action == "defer":
        data = keystore.defer(eng)
    elif action == "validate":
        data = keystore.validate(eng, probe=args.probe)
    else:
        raise LoomError(f"unknown keys action {action}")
    eng.save()
    _out(args, data, _ks_human)


def cmd_listen(args):
    eng = _load(args)
    if args.listen_action == "plan":
        _out(args, intake.listen_plan(eng))
        return
    data = intake.listen_record(eng, backfill=args.backfill_gap_ids, strict_excerpts=not args.allow_unverified_excerpts)

    def human(d):
        print(f"✅  discovery-parser complete · {d['claims']} claims · {d['gaps']} gaps")
        _print_list("closed by re-inference (Path A)", d["closed_by_reinference"])
        _print_list("new gaps", d["new_gaps"])
        _print_list("warnings", d["warnings"])
        print(f"\n    Next: {state.derive(eng.state, intake.compute_stale(eng))['next_action']}")
    _out(args, data, human)


def cmd_scan(args):
    eng = _load(args)
    data = intake.scan_record(eng) if args.scan_action == "record" else intake.scan_skip(eng)
    _out(args, data, lambda d: print(f"  diagnostic-analyzer: {d['status']}"))


def cmd_gaps(args):
    eng = _load(args)
    if args.gaps_action == "list":
        rows = intake.gap_rows(eng)

        def human(rs):
            if not rs:
                print("  No gaps.")
            for r in rs:
                flag = "BLOCKING" if r["blocking"] else r["impact"]
                print(f"  {r['gap_id']:<28} {r['status']:<14} {flag}")
                print(f"      {r['question']}")
                print(f"      Update in Inputs: {r['update_in']}  ·  or: loom_state gaps respond {eng.slug} {r['gap_id']} …")
        _out(args, rows, human)
        return
    data = intake.respond(eng, args.gap_id, args.status, args.by or default_approver(), args.response, args.rationale)
    _out(args, data, lambda d: print(f"  {args.gap_id} → {d['status']} (refresh: loom_state qualify status {eng.slug})"))


def _readiness_human(d):
    print(f"  recommended: {d['recommended_status']} · suggested: {d['suggested_status']}")
    print("  MEDDPIC: " + ", ".join(f"{k}={v}" for k, v in d["meddpic"].items()))
    _print_list("open blocking gaps", d["open_blocking_gaps"])


def cmd_qualify(args):
    eng = _load(args)
    a = args.qualify_action
    if a == "plan":
        _out(args, qualify.plan(eng))
    elif a == "record":
        data = qualify.record(eng)

        def human(d):
            if d.get("unchanged"):
                print(f"  unchanged — decision {d['decision']} still current")
                return
            print(f"✅  opportunity-review awaiting decision (recommended: {d['recommended_status']})")
            _readiness_human(d["readiness"])
        _out(args, data, human)
    elif a == "status":
        _out(args, qualify.readiness(eng), _readiness_human)
    elif a == "decide":
        data = qualify.decide(eng, args.status, _approver(args), args.rationale, args.ae_aligned, args.ae_note,
                              tuple(args.accept_risk or ()))

        def human(d):
            print(f"✅  Recorded {d['decision']} · approvals[] updated")
            if d["accepted_risk"]:
                print("  accepted risk: " + ", ".join(r["gap_id"] for r in d["accepted_risk"]))
            print(f"\n    Next: {state.derive(eng.state)['next_action']}")
        _out(args, data, human)
    elif a == "design-anyway":
        data = qualify.design_anyway(eng, _approver(args), args.rationale)
        _out(args, data, lambda d: print("✅  Design anyway recorded (accepted risk) — Vision unlocked"))


def cmd_vision(args):
    eng = _load(args)
    a = args.vision_action
    if a == "plan":
        _out(args, vision.plan(eng))
    elif a == "map":
        m = args.map_action
        if m == "show":
            _out(args, vision.load_map(eng, create=True))
            return
        if m == "add":
            msgs = vision.map_add(eng, args.cap_id, args.name, args.outcome, args.proof, args.origin)
        elif m == "exclude":
            msgs = vision.map_exclude(eng, args.cap_id, args.reason)
        else:
            msgs = vision.map_token_visibility(eng, args.state == "on")
        _out(args, {"messages": msgs}, lambda d: [print(f"  {x}") for x in d["messages"] or ["  map updated"]])
    elif a == "freeze":
        data = vision.freeze(eng, _approver(args))

        def human(d):
            print(f"✅  Vision frozen ({d['mode']}) · {len(d['capabilities'])} capabilities "
                  f"· SA-added: {', '.join(d['sa_added']) or 'none'}")
            if d["token_visibility"]:
                print("  D-036 AI Cost + Usage dashboard included")
            _print_list("warnings", d["warnings"])
            print(f"\n    Next: {d['next']}")
        _out(args, data, human)
    elif a == "confirm":
        data = vision.confirm(eng, _approver(args))
        _out(args, data, lambda d: print("✅  Confirmation approved · ideation complete · next: demo path"))


def cmd_path(args):
    eng = _load(args)
    a = args.path_action
    if a == "plan":
        _out(args, demopath.plan(eng))
        return
    if a == "check":
        data = demopath.check(eng)
    else:
        data = demopath.commit(eng, args.path, _approver(args), args.rationale, args.standard_demo)

    def human(d):
        if "path" in d:
            print(f"✅  Demo path committed: {d['path']}" + (f" ({d['standard_demo']})" if d.get("standard_demo") else ""))
        print(f"  audit: {d['overall_status']} · ready {len(d['ready'])} · red {len(d['red'])}")
        for owner, ids in d["amber_by_owner"].items():
            if ids:
                print(f"  amber · {owner}: {', '.join(ids)}")
        _print_list("warnings", d["warnings"])
    _out(args, data, human)


def overview(root: Path, slug: str, use_fs: bool = True) -> dict:
    eng = state.load(root, slug)
    stale = intake.compute_stale(eng) if use_fs else {}
    return state.derive(eng.state, stale)


def cmd_next(args):
    data = overview(get_root(args.root), args.slug, use_fs=not args.no_fs)

    def human(d):
        print(f"\n  Overview · {d['slug']}")
        if d.get("company"):
            print(f"  Sales: {d['company']}")
        print(f"  Phase: {d['phase']}")
        print(f"  Next:  {d['next_action']}")
        if d.get("command"):
            print(f"         $ {d['command']}")
        print(f"  Qualification: {d['qualification']} · Vision: {d['vision']} · Path: {d['path']} · Keystore: {d['keystore']}")
        _print_list("Blockers", d["blockers"])
        _print_list("Notes", d["notes"])
        print()
    _out(args, data, human)


def cmd_hygiene(args):
    root = get_root(args.root)
    findings, ok = [], []
    try:
        tracked = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files", "--cached"], capture_output=True,
                                 text=True, check=True).stdout.splitlines()
        envs = [f for f in tracked if Path(f).name == ".env" or Path(f).name.startswith(".env.") and
                not f.endswith(".example")]
        findings += [f"loom repo tracks credential file: {f} (git rm --cached {f})" for f in envs]
        if not envs:
            ok.append("loom repo tracks no .env files")
    except (OSError, subprocess.CalledProcessError):
        findings.append("could not inspect loom git index")
    wt = find_git_worktree(root) if root.exists() else None
    if wt:
        findings.append(f"engagements root {root} is inside git work tree {wt}")
    else:
        ok.append("engagements root is outside git")
    for d in sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []:
        sp = d / f"{d.name}-pipeline-state.json"
        if not sp.exists():
            continue
        st = json.loads(sp.read_text())
        ident = st.get("identity", {})
        env = d / ".env"
        if env.exists():
            mode = env.stat().st_mode
            if mode & (stat.S_IRGRP | stat.S_IROTH):
                findings.append(f"{d.name}/.env is group/world readable (chmod 600)")
            if find_identity_leaks(env.read_text(), ident):
                findings.append(f"{d.name}/.env contains private identity")
        for rel in (f"demo/{d.name}-ideation.md", f"demo/{d.name}-capability-map.json", ".env.example"):
            p = d / rel
            if p.exists() and find_identity_leaks(p.read_text(), ident):
                findings.append(f"{d.name}/{rel} contains private identity (public artifact)")
    data = {"ok": ok, "findings": findings}

    def human(dd):
        for o in dd["ok"]:
            print(f"  ✅  {o}")
        for f in dd["findings"]:
            print(f"  ❌  {f}")
    _out(args, data, human)
    if findings:
        sys.exit(1)


# ── parser ────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=argparse.SUPPRESS, help="Override LOOM_ENGAGEMENTS_ROOT")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Machine-readable output")

    p = argparse.ArgumentParser(prog="loom_state", description=__doc__.split("\n")[0], parents=[common],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def group(name, help_text, dest):
        gp = sub.add_parser(name, parents=[common], help=help_text)
        return gp.add_subparsers(dest=dest, required=True)

    def leaf(grp, name, func, help_text=None):
        lp = grp.add_parser(name, parents=[common], help=help_text)
        lp.add_argument("slug")
        lp.set_defaults(func=func)
        return lp

    n = sub.add_parser("new", parents=[common], help="Create engagement (SB-01)")
    n.add_argument("--slug", required=True, help="Public demo slug, e.g. acme-pharma")
    n.add_argument("--display", help="Public display name, e.g. 'Acme Pharma'")
    n.add_argument("--company", help="Private: real company (pipeline-state only)")
    n.add_argument("--opportunity", help="Private: opportunity name")
    n.add_argument("--opportunity-id", help="Private: SFDC opportunity id")
    n.add_argument("--entry-mode", choices=bootstrap.ENTRY_MODES, default="notes")
    n.add_argument("--solution", choices=bootstrap.SOLUTIONS, default="unknown")
    n.add_argument("--notes", nargs="*", help="Notes files to copy into inputs/")
    n.add_argument("--import", dest="import_dir", help="AE/SDR package dir (entry mode import)")
    n.add_argument("--no-suffix", action="store_true", help="Fail instead of suffixing a colliding slug")
    n.add_argument("--allow-git-root", action="store_true", help=argparse.SUPPRESS)
    n.set_defaults(func=cmd_new)

    ig = group("inputs", "Files under inputs/ (Path A source of truth)", "inputs_action")
    leaf(ig, "add", cmd_inputs_add).add_argument("files", nargs="+")

    kg = group("keys", "Engagement keystore (SB-02)", "keys_action")
    for name, text in (("status", "Keystore status (no values)"), ("list", "Sibling picklist (status only)"),
                       ("init", "Load from sample (.env.example)"), ("defer", "Set up later"),
                       ("validate", "Completeness check; --probe for read-only version check")):
        lp = leaf(kg, name, cmd_keys, text)
        if name == "validate":
            lp.add_argument("--probe", action="store_true", help="Read-only GET / + Kibana /api/status")
    ks = leaf(kg, "set", cmd_keys, "Enter values manually (VALUE '-' prompts without echo)")
    ks.add_argument("pairs", nargs="+", metavar="KEY=VALUE")
    kc = leaf(kg, "clone", cmd_keys, "Clone values from a sibling engagement")
    kc.add_argument("--from", dest="source", required=True, help="Sibling slug")
    kc.add_argument("--no-secrets", action="store_true", help="Endpoints only (no API keys / tokens)")
    kc.add_argument("--index-prefix", help="INDEX_PREFIX on a shared cluster (default derived from slug)")
    kc.add_argument("--keep", nargs="*", choices=keystore.CLONE_OPT_IN, help="Opt-in keys to copy")

    lg = group("listen", "Evidence extraction (warp-listen)", "listen_action")
    leaf(lg, "plan", cmd_listen, "Inputs, outputs, and contract for warp-listen")
    lr = leaf(lg, "record", cmd_listen, "Validate + register warp-listen outputs")
    lr.add_argument("--backfill-gap-ids", action="store_true")
    lr.add_argument("--allow-unverified-excerpts", action="store_true")

    sg = group("scan", "Optional diagnostic (warp-scan)", "scan_action")
    leaf(sg, "record", cmd_scan)
    leaf(sg, "skip", cmd_scan)

    gg = group("gaps", "Gaps inbox (Path B accelerator)", "gaps_action")
    leaf(gg, "list", cmd_gaps)
    gr = leaf(gg, "respond", cmd_gaps)
    gr.add_argument("gap_id")
    gr.add_argument("--status", choices=["open", "answered", "accepted_risk", "deferred"], default="answered")
    gr.add_argument("--response")
    gr.add_argument("--rationale")
    gr.add_argument("--by")

    qg = group("qualify", "Qualification (thread-qualify) + Record decision", "qualify_action")
    leaf(qg, "plan", cmd_qualify)
    leaf(qg, "record", cmd_qualify, "Register thread-qualify outputs (awaiting decision)")
    leaf(qg, "status", cmd_qualify, "Readiness: MEDDPIC, open blocking gaps, suggested status")
    qd = leaf(qg, "decide", cmd_qualify, "Record decision")
    qd.add_argument("--status", choices=qualify.STATUSES, required=True)
    qd.add_argument("--rationale")
    qd.add_argument("--ae-aligned", action="store_true", help="AE/SDR reviewed the opportunity summary")
    qd.add_argument("--ae-note")
    qd.add_argument("--accept-risk", nargs="*", metavar="GAP_ID")
    qd.add_argument("--approver")
    qo = leaf(qg, "design-anyway", cmd_qualify, "Accept risk after continue_discovery")
    qo.add_argument("--rationale", required=True)
    qo.add_argument("--approver")

    vg = group("vision", "Vision (warp-spark): capability map, freeze, confirm", "vision_action")
    leaf(vg, "plan", cmd_vision)
    for name, text in (("freeze", "Freeze vision + capability map"), ("confirm", "Approve refreshed confirmation")):
        leaf(vg, name, cmd_vision, text).add_argument("--approver")
    mp = vg.add_parser("map", parents=[common], help="Edit the capability map")
    mg = mp.add_subparsers(dest="map_action", required=True)
    leaf(mg, "show", cmd_vision)
    ma = leaf(mg, "add", cmd_vision, "Add a catalog chip or custom feature request")
    ma.add_argument("cap_id", nargs="?", help="Catalog id (omit with --name for a custom request)")
    ma.add_argument("--name")
    ma.add_argument("--outcome")
    ma.add_argument("--proof")
    ma.add_argument("--origin", choices=["vision", "sa_added", "sa_requested"])
    me = leaf(mg, "exclude", cmd_vision, "Move to Out of Scope")
    me.add_argument("cap_id", help="Capability id or out-of-scope name")
    me.add_argument("--reason")
    mt = leaf(mg, "token-visibility", cmd_vision, "D-036 AI Cost dashboard on/off")
    mt.add_argument("state", choices=["on", "off"])

    pg = group("path", "Demo path: audit check + commit (D-049)", "path_action")
    leaf(pg, "plan", cmd_path)
    leaf(pg, "check", cmd_path)
    pc = leaf(pg, "commit", cmd_path)
    pc.add_argument("--path", choices=["custom", "predefined"], required=True)
    pc.add_argument("--standard-demo")
    pc.add_argument("--rationale")
    pc.add_argument("--approver")

    nx = sub.add_parser("next", parents=[common], help="Overview: derived phase, next action, blockers")
    nx.add_argument("slug")
    nx.add_argument("--no-fs", action="store_true", help="Derive from pipeline-state only (skip staleness hashes)")
    nx.set_defaults(func=cmd_next)

    h = sub.add_parser("hygiene", parents=[common], help="No .env / customer identity where it must not be")
    h.set_defaults(func=cmd_hygiene)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    args.root = getattr(args, "root", None)
    args.json = getattr(args, "json", False)
    try:
        args.func(args)
    except LoomError as e:
        print(f"❌  {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.exit(main())
