"""P2 acceptance tests for loom_state (synthetic Acme fixtures, temp engagements root).

Run: python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from loomstate import cli  # noqa: E402
from loomstate.core import sha256_file  # noqa: E402
from loomstate.schema import validate, validate_file  # noqa: E402

FIX = REPO / "tests" / "fixtures" / "p2-acme"
COMPANY = "Northwind Pharmaceuticals"
OPP = "NW Pharma — SOC AI FY26"
SLUG = "acme-pharma"
SECRET = "c2VjcmV0LWZpeHR1cmUta2V5"  # synthetic placeholder


class P2Base(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="loom-p2-"))
        os.environ["LOOM_APPROVER"] = "sa@example.com"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    # ── helpers ──
    def cli(self, *argv, ok=True):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                rc = cli.main([*argv, "--root", str(self.root), "--json"])
            except SystemExit as e:
                rc = e.code
        if ok and rc != 0:
            self.fail(f"loom_state {' '.join(argv)} failed ({rc}):\n{err.getvalue()}{out.getvalue()}")
        if not ok:
            self.assertNotEqual(rc, 0, f"expected failure: {' '.join(argv)}\n{out.getvalue()}")
            return err.getvalue()
        text = out.getvalue().strip()
        return json.loads(text) if text else None

    @property
    def eng(self) -> Path:
        return self.root / SLUG

    def state(self, slug=SLUG) -> dict:
        return json.loads((self.root / slug / f"{slug}-pipeline-state.json").read_text())

    def put(self, fixture: str, target: str, slug=SLUG):
        dest = self.root / slug / target.format(slug=slug)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(FIX / fixture, dest)
        return dest

    def create(self, entry_mode="notes", slug=SLUG, **extra):
        args = ["new", "--slug", slug, "--display", "Acme Pharma", "--company", COMPANY, "--opportunity", OPP,
                "--opportunity-id", "006FIXTURE", "--entry-mode", entry_mode, "--solution", "security"]
        if entry_mode == "notes":
            args += ["--notes", str(FIX / "notes" / "call-notes.md")]
        for k, v in extra.items():
            args += [f"--{k.replace('_', '-')}", v]
        return self.cli(*args)

    def listen(self, discovery: dict | None = None):
        if discovery is None:
            self.put("listen/discovery.json", "demo/{slug}-discovery.json")
        else:
            (self.eng / "demo" / f"{SLUG}-discovery.json").write_text(json.dumps(discovery))
        self.put("listen/gaps.md", "opportunity/{slug}-gaps.md")
        self.put("listen/confirmation.md", "opportunity/{slug}-confirmation.md")
        return self.cli("listen", "record", SLUG)

    def qualify_files(self, profile_status="continue_discovery"):
        p = json.loads((FIX / "qualify/opportunity-profile.json").read_text())
        p["qualification_status"] = profile_status
        (self.eng / "opportunity" / f"{SLUG}-opportunity-profile.json").write_text(json.dumps(p))
        self.put("qualify/opportunity-summary.md", "opportunity/{slug}-opportunity-summary.md")
        self.put("qualify/demo-goals.md", "opportunity/{slug}-demo-goals.md")
        return self.cli("qualify", "record", SLUG)

    def to_proceed(self):
        self.create()
        self.cli("keys", "defer", SLUG)
        self.listen()
        self.qualify_files("continue_discovery")
        self.cli("qualify", "decide", SLUG, "--status", "proceed", "--accept-risk", "g_economic_buyer",
                 "--rationale", "CISO sponsorship expected; accept for demo prep", "--ae-aligned")

    def build_map(self, with_agent_builder=True):
        for cid, outcome, proof in (
            ("detection-rules", "Noise becomes actionable alerts", "Rules fire on seeded events"),
            ("cases", "Multi-alert noise becomes one investigation", "Case groups the alert burst"),
            ("ai-assistant", "Guided triage cuts time-to-hypothesis", "Assistant explains the alert"),
            ("esql", "Pivot from alert to entity activity live", "ES|QL query returns host activity"),
        ):
            self.cli("vision", "map", "add", SLUG, cid, "--origin", "vision", "--outcome", outcome, "--proof", proof)
        if with_agent_builder:
            self.cli("vision", "map", "add", SLUG, "agent-builder", "--outcome",
                     "Conversational investigation path", "--proof", "Agent answers with tool calls")
        self.cli("vision", "map", "exclude", SLUG, "Custom search relevance UI", "--reason", "Not in SOC story")

    def to_vision_complete(self, with_agent_builder=True):
        self.to_proceed()
        self.build_map(with_agent_builder)
        self.put("vision/ideation.md", "demo/{slug}-ideation.md")
        self.cli("vision", "freeze", SLUG)
        self.put("vision/confirmation-refreshed.md", "opportunity/{slug}-confirmation.md")
        summary = self.eng / "opportunity" / f"{SLUG}-opportunity-summary.md"
        summary.write_text(summary.read_text().replace(
            "Economic buyer not yet identified.",
            "Economic buyer not yet identified. Demo direction: Operational Triage Console focused on alert "
            "fatigue, targeting SOC leadership, with guided triage as the lead outcome."))
        self.cli("vision", "confirm", SLUG)

    def put_audit(self, mutate=None):
        audit = json.loads((FIX / "path/platform-audit.json").read_text())
        audit["meta"]["capability_map_hash"] = sha256_file(self.eng / "demo" / f"{SLUG}-capability-map.json")
        if mutate:
            mutate(audit)
        (self.eng / "demo" / f"{SLUG}-platform-audit.json").write_text(json.dumps(audit))
        self.put("path/platform-audit.md", "demo/{slug}-platform-audit.md")


class TestBootstrapAndKeystore(P2Base):
    def test_create_dual_identity_and_layout(self):
        res = self.create()
        self.assertEqual(res["slug"], SLUG)
        self.assertEqual(res["tag"], "loom:acmepharma")
        for sub in ("inputs", "opportunity", "demo", "data", "deploy"):
            self.assertTrue((self.eng / sub).is_dir())
        self.assertTrue((self.eng / "inputs" / "call-notes.md").exists())
        st = self.state()
        self.assertEqual(st["identity"]["company_name"], COMPANY)
        self.assertEqual(st["identity"]["public_display_name"], "Acme Pharma")
        self.assertEqual(st["entry_mode"], "notes")
        self.assertEqual(st["path"], "unset")
        self.assertEqual(st["keystore"]["status"], "empty")
        self.assertEqual(validate(st, "pipeline-state"), [])
        example = (self.eng / ".env.example").read_text()
        self.assertNotIn("Northwind", example)
        self.assertIn("DEMO_SLUG=acme-pharma", example)
        self.assertIn("KIBANA_SPACE_PATH=/s/acme-pharma", example)
        self.assertIn("KIBANA_SOLUTION=security", example)

    def test_slug_unique_by_folder_and_tag_id(self):
        self.create()
        res = self.create()
        self.assertEqual(res["slug"], "acme-pharma-2")
        # loom:acmepharma collides with acme-pharma; loom:acmepharma2 with acme-pharma-2
        res = self.create(slug="acmepharma")
        self.assertEqual(res["slug"], "acmepharma-3")
        self.assertEqual(self.state("acmepharma-3")["tag_id"], "acmepharma3")
        self.cli("new", "--slug", SLUG, "--no-suffix", ok=False)

    def test_slug_and_display_reject_private_identity(self):
        err = self.cli("new", "--slug", "northwind-pharma", "--company", COMPANY, ok=False)
        self.assertIn("private identity", err)
        err = self.cli("new", "--slug", SLUG, "--display", "Northwind Demo", "--company", COMPANY, ok=False)
        self.assertIn("private identity", err)

    def test_root_inside_git_is_refused(self):
        (self.root / ".git").mkdir()
        err = self.cli("new", "--slug", SLUG, ok=False)
        self.assertIn("git work tree", err)

    def _sibling_with_env(self):
        self.cli("new", "--slug", "acme-retailsearch", "--display", "Acme Retail", "--solution", "search",
                 "--entry-mode", "scratch")
        self.cli("keys", "set", "acme-retailsearch", "ELASTICSEARCH_URL=https://shared.es.example:443",
                 "KIBANA_URL=https://shared.kb.example:443", f"ES_API_KEY={SECRET}", f"KIBANA_API_KEY={SECRET}k",
                 "INDEX_PREFIX=are-", "CLUSTER_NAME=shared-demo", "DEMO_ASSET_TAG=retail")
        env = self.root / "acme-retailsearch" / ".env"
        env.write_text(env.read_text() + "COMPANY_NAME=Contoso Retail\n")  # planted private var

    def test_keystore_clone_rules(self):
        self._sibling_with_env()
        self.create()
        listing = self.cli("keys", "list", SLUG)
        self.assertNotIn(SECRET, json.dumps(listing))
        sib = next(s for s in listing if s["slug"] == "acme-retailsearch")
        self.assertIn("complete", sib["summary"])

        res = self.cli("keys", "clone", SLUG, "--from", "acme-retailsearch")
        self.assertTrue(res["shared_cluster"])
        self.assertEqual(res["index_prefix"], "aph-")
        for k in ("DEMO_ASSET_TAG", "CLUSTER_NAME", "COMPANY_NAME", "DEMO_SLUG", "KIBANA_SPACE_PATH"):
            self.assertIn(k, res["skipped"])
        env_path = self.eng / ".env"
        env = env_path.read_text()
        self.assertIn("DEMO_SLUG=acme-pharma", env)
        self.assertIn("KIBANA_SPACE_PATH=/s/acme-pharma", env)
        self.assertIn("KIBANA_SOLUTION=security", env)
        self.assertIn("ENGAGEMENT=Acme Pharma", env)
        self.assertIn("INDEX_PREFIX=aph-", env)
        self.assertNotIn("Contoso", env)
        self.assertNotIn("CLUSTER_NAME=shared-demo", env)
        self.assertIn(SECRET, env)
        self.assertFalse(env_path.is_symlink())
        self.assertEqual(stat.S_IMODE(env_path.stat().st_mode), 0o600)
        st = self.state()["keystore"]
        self.assertEqual(st["status"], "complete")
        self.assertEqual(st["source"], "clone")
        self.assertEqual(st["cloned_from"], "acme-retailsearch")

        self.cli("keys", "clone", SLUG, "--from", "acme-retailsearch", "--index-prefix", "are-", ok=False)

    def test_keystore_clone_without_secrets_is_partial(self):
        self._sibling_with_env()
        self.create()
        res = self.cli("keys", "clone", SLUG, "--from", "acme-retailsearch", "--no-secrets")
        self.assertEqual(res["keystore"]["status"], "partial")
        self.assertNotIn(SECRET, (self.eng / ".env").read_text())

    def test_keystore_rejects_private_identity_and_rebinding(self):
        self.create()
        err = self.cli("keys", "set", SLUG, "ENGAGEMENT=Northwind Pharmaceuticals", ok=False)
        self.assertIn("private identity", err)
        self.cli("keys", "set", SLUG, "OPPORTUNITY_NAME=x", ok=False)
        self.cli("keys", "set", SLUG, "DEMO_SLUG=acme-other", ok=False)

    def test_keystore_sample_and_defer_do_not_mark_provisioned(self):
        self.create()
        self.cli("keys", "defer", SLUG)
        self.assertTrue(self.state()["keystore"]["deferred"])
        res = self.cli("keys", "init", SLUG)
        self.assertEqual(res["status"], "empty")
        sys.path.insert(0, str(REPO / "scripts"))
        import inventory  # noqa: PLC0415
        inferred = inventory.infer_state_from_files(self.eng, SLUG)
        self.assertEqual(inferred["stages"]["cloud-provision"]["status"], "pending")


class TestIntakeQualify(P2Base):
    def test_listen_requires_evidence_and_verbatim_excerpts(self):
        self.create()
        d = json.loads((FIX / "listen/discovery.json").read_text())
        d["claims"][0]["source_ref"]["excerpt"] = "invented quote that is not in the notes"
        self.put("listen/gaps.md", "opportunity/{slug}-gaps.md")
        self.put("listen/confirmation.md", "opportunity/{slug}-confirmation.md")
        (self.eng / "demo" / f"{SLUG}-discovery.json").write_text(json.dumps(d))
        err = self.cli("listen", "record", SLUG, ok=False)
        self.assertIn("excerpt not found", err)
        d["claims"] = []
        (self.eng / "demo" / f"{SLUG}-discovery.json").write_text(json.dumps(d))
        err = self.cli("listen", "record", SLUG, ok=False)
        self.assertIn("source_ref", err)

    def test_listen_record_and_gaps(self):
        self.create()
        res = self.listen()
        self.assertEqual((res["claims"], res["gaps"]), (3, 3))
        st = self.state()["stages"]["discovery-parser"]
        self.assertEqual(st["status"], "complete")
        self.assertTrue(st["input_hash"].startswith("sha256:"))
        self.assertEqual(validate_file(self.eng / "demo" / f"{SLUG}-discovery.json", "discovery"), [])
        rows = {r["gap_id"]: r for r in self.cli("gaps", "list", SLUG)}
        self.assertTrue(rows["g_economic_buyer"]["blocking"])
        self.assertEqual(rows["g_economic_buyer"]["update_in"], "inputs/call-notes.md")

    def test_gap_ids_must_stay_stable(self):
        self.create()
        self.listen()
        d = json.loads((FIX / "listen/discovery.json").read_text())
        d["gaps"][1]["gap_id"] = "g_volume"
        (self.eng / "demo" / f"{SLUG}-discovery.json").write_text(json.dumps(d))
        err = self.cli("listen", "record", SLUG, ok=False)
        self.assertIn("gap_id must stay stable", err)

    def test_continue_discovery_parks_then_path_a_closes_gap(self):
        self.create()
        self.listen()
        self.qualify_files("continue_discovery")
        self.assertEqual(self.state()["stages"]["opportunity-review"]["status"], "awaiting_decision")
        err = self.cli("qualify", "decide", SLUG, "--status", "proceed", ok=False)
        self.assertIn("open blocking gaps", err)
        self.cli("qualify", "decide", SLUG, "--status", "continue_discovery")
        nxt = self.cli("next", SLUG)
        self.assertEqual(nxt["phase"], "Qualify")
        self.assertIn("Parked", nxt["next_action"])
        err = self.cli("vision", "freeze", SLUG, ok=False)
        self.assertIn("locked", err)

        # Path A: add the AE follow-up under inputs/, re-listen → gap closes by re-inference
        self.cli("inputs", "add", SLUG, str(FIX / "notes" / "ae-followup.md"))
        nxt = self.cli("next", SLUG)
        self.assertEqual(nxt["phase"], "Intake")
        self.assertTrue(any("discovery-parser is stale" in b for b in nxt["blockers"]))
        d = json.loads((FIX / "listen/discovery.json").read_text())
        d["gaps"] = [g for g in d["gaps"] if g["gap_id"] != "g_economic_buyer"]
        d["claims"].append({"claim_id": "c_economic_buyer", "field": "meddpic.economic_buyer",
                            "text": "CISO owns the renewal budget",
                            "source_ref": {"file": "inputs/ae-followup.md",
                                           "excerpt": "the CISO, Marcus T., owns the SIEM renewal budget"}})
        res = self.listen(d)
        self.assertEqual(res["closed_by_reinference"], ["g_economic_buyer"])
        nxt = self.cli("next", SLUG)
        self.assertTrue(any("opportunity-review is stale" in b for b in nxt["blockers"]))
        self.cli("qualify", "decide", SLUG, "--status", "proceed", ok=False)  # stale qualify
        self.qualify_files("proceed")
        rec = self.state()["stages"]["opportunity-review"]
        self.assertEqual(rec["status"], "awaiting_decision")
        self.assertEqual(rec["history"][0]["decision"], "continue_discovery")
        self.cli("qualify", "decide", SLUG, "--status", "proceed", "--ae-aligned")
        profile = self.eng / "opportunity" / f"{SLUG}-opportunity-profile.json"
        self.assertEqual(validate_file(profile, "opportunity-profile"), [])
        p = json.loads(profile.read_text())
        self.assertEqual(p["qualification_decision"]["status"], "proceed")
        self.assertTrue(p["qualification_decision"]["ae_alignment"]["confirmed"])
        decisions = [a["decision"] for a in self.state()["approvals"] if a["action"] == "qualification_decision"]
        self.assertEqual(decisions, ["continue_discovery", "proceed"])
        self.assertEqual(self.cli("next", SLUG)["phase"], "Design")

    def test_path_b_gap_response_and_accepted_risk(self):
        self.create()
        self.listen()
        self.qualify_files("continue_discovery")
        self.cli("gaps", "respond", SLUG, "g_economic_buyer", "--status", "accepted_risk", ok=False)  # no rationale
        self.cli("gaps", "respond", SLUG, "g_economic_buyer", "--status", "answered",
                 "--response", "CISO owns budget (AE email)")
        resp = self.eng / "opportunity" / f"{SLUG}-gap-responses.json"
        self.assertEqual(validate_file(resp, "gap-responses"), [])
        status = self.cli("qualify", "status", SLUG)
        self.assertEqual(status["open_blocking_gaps"], [])
        err = self.cli("qualify", "decide", SLUG, "--status", "proceed", ok=False)
        self.assertIn("rationale", err)  # differs from recommendation
        self.cli("qualify", "decide", SLUG, "--status", "proceed", "--rationale", "EB answered via AE")
        self.assertEqual(self.state()["stages"]["opportunity-review"]["decision"], "proceed")

    def test_not_qualified_stops(self):
        self.create()
        self.listen()
        self.qualify_files("not_qualified")
        self.cli("qualify", "decide", SLUG, "--status", "not_qualified")
        nxt = self.cli("next", SLUG)
        self.assertIn("Stopped", nxt["next_action"])
        self.cli("vision", "freeze", SLUG, ok=False)

    def test_design_anyway_unlocks_vision(self):
        self.create()
        self.listen()
        self.qualify_files("continue_discovery")
        self.cli("qualify", "decide", SLUG, "--status", "continue_discovery")
        self.cli("qualify", "design-anyway", SLUG, "--rationale", "Demo date fixed; accept EB risk")
        self.assertEqual(self.cli("next", SLUG)["phase"], "Design")
        actions = [a["action"] for a in self.state()["approvals"]]
        self.assertIn("qualification_override", actions)

    def test_import_package_backfills_and_rebinds_slug(self):
        pkg = self.root.parent / f"{self.root.name}-pkg"
        pkg.mkdir()
        try:
            d = json.loads((FIX / "listen/discovery.json").read_text())
            for g in d["gaps"]:
                g.pop("gap_id")
            d["meta"]["slug"] = "northwind-pharmaceuticals"
            (pkg / "northwind-pharmaceuticals-discovery.json").write_text(json.dumps(d))
            shutil.copy(FIX / "listen/gaps.md", pkg / "northwind-pharmaceuticals-gaps.md")
            shutil.copy(FIX / "listen/confirmation.md", pkg / "northwind-pharmaceuticals-confirmation.md")
            shutil.copy(FIX / "qualify/demo-goals.md", pkg / "northwind-pharmaceuticals-demo-goals.md")
            shutil.copy(FIX / "notes/call-notes.md", pkg / "call-notes.md")
            self.create(entry_mode="import", **{"import": str(pkg)})
        finally:
            shutil.rmtree(pkg, ignore_errors=True)
        self.assertTrue((self.eng / "demo" / f"{SLUG}-discovery.json").exists())
        self.assertTrue((self.eng / "inputs" / "call-notes.md").exists())
        self.assertEqual(self.cli("next", SLUG)["phase"], "Intake")
        res = self.cli("listen", "record", SLUG)
        self.assertTrue(any("backfilled" in w for w in res["warnings"]))
        d = json.loads((self.eng / "demo" / f"{SLUG}-discovery.json").read_text())
        self.assertEqual(d["meta"]["slug"], SLUG)
        self.assertIn("g_meddpic_economic_buyer", [g["gap_id"] for g in d["gaps"]])

    def test_scratch_goes_straight_to_vision(self):
        self.create(entry_mode="scratch")
        nxt = self.cli("next", SLUG)
        self.assertEqual(nxt["phase"], "Design")
        self.assertIn("Mode 3", nxt["next_action"])


class TestVisionAndPath(P2Base):
    def test_full_custom_flow_and_resume(self):
        self.to_vision_complete()
        st = self.state()
        self.assertEqual(st["stages"]["ideation"]["status"], "complete")
        ideation = (self.eng / "demo" / f"{SLUG}-ideation.md").read_text()
        self.assertIn("`agent-builder` | SA added", ideation)
        self.assertIn("`ai-cost-dashboard` | implied (D-036)", ideation)
        self.assertIn("Custom search relevance UI", ideation)
        self.assertIn("AI cost/usage dashboard:** yes", ideation)
        self.assertNotIn("Northwind", ideation)
        cmap = json.loads((self.eng / "demo" / f"{SLUG}-capability-map.json").read_text())
        self.assertEqual(cmap["status"], "frozen")
        self.assertEqual(validate(cmap, "capability-map"), [])

        plan = self.cli("path", "plan", SLUG)
        self.assertEqual({r["capability_id"] for r in plan["audit_scope"]},
                         {"detection-rules", "cases", "ai-assistant", "esql", "agent-builder", "ai-cost-dashboard"})
        self.put_audit()
        chk = self.cli("path", "check", SLUG)
        self.assertEqual(chk["amber_by_owner"]["pipeline"], ["agent-builder", "ai-cost-dashboard"])
        self.assertEqual(chk["amber_by_owner"]["manual_once"], ["ai-assistant"])
        res = self.cli("path", "commit", SLUG, "--path", "custom")
        self.assertEqual(res["path"], "custom")

        st = self.state()
        self.assertEqual(st["path"], "custom")
        self.assertEqual(st["stages"]["build-path"]["status"], "complete")
        self.assertTrue(st["stages"]["build-path"]["custom_required"])
        self.assertEqual(st["stages"]["platform-audit"]["status"], "complete")
        self.assertEqual(validate(st, "pipeline-state"), [])
        actions = [a["action"] for a in st["approvals"]]
        for a in ("qualification_decision", "vision_freeze", "confirmation_approve", "demo_path_commit"):
            self.assertIn(a, actions)
        for a in st["approvals"]:
            self.assertTrue(all(v.startswith("sha256:") or v == "absent" for v in a["artifacts"].values()))

        # Resume from pipeline-state alone
        nxt = self.cli("next", SLUG, "--no-fs")
        self.assertEqual(nxt["phase"], "Build & Validate")
        self.assertEqual(nxt["company"], COMPANY)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            try:
                cli.main(["hygiene", "--root", str(self.root), "--json"])
            except SystemExit:
                pass
        report = json.loads(out.getvalue())
        self.assertFalse([f for f in report["findings"] if SLUG in f], report)

    def test_confirm_requires_refresh(self):
        self.to_proceed()
        self.build_map(with_agent_builder=False)
        self.put("vision/ideation.md", "demo/{slug}-ideation.md")
        res = self.cli("vision", "freeze", SLUG)
        self.assertFalse(res["token_visibility"])
        err = self.cli("vision", "confirm", SLUG, ok=False)
        self.assertIn("What We'll Show You", err)
        self.assertIn("TL;DR", err)
        self.cli("path", "plan", SLUG, ok=False)  # audit locked until confirmation approved

    def test_freeze_blocks_private_identity_and_missing_sections(self):
        self.to_proceed()
        self.build_map()
        ide = self.put("vision/ideation.md", "demo/{slug}-ideation.md")
        ide.write_text(ide.read_text().replace("Acme Pharma (public demo identity)", COMPANY))
        err = self.cli("vision", "freeze", SLUG, ok=False)
        self.assertIn("private identity", err)
        ide.write_text((FIX / "vision/ideation.md").read_text().replace("## Minimum Bar", "## Fallback"))
        err = self.cli("vision", "freeze", SLUG, ok=False)
        self.assertIn("Minimum Bar", err)

    def test_token_visibility_opt_out(self):
        self.to_proceed()
        self.build_map()
        self.cli("vision", "map", "token-visibility", SLUG, "off")
        cmap = json.loads((self.eng / "demo" / f"{SLUG}-capability-map.json").read_text())
        self.assertNotIn("ai-cost-dashboard", [c["id"] for c in cmap["capabilities"]])

    def test_custom_feature_request(self):
        self.to_proceed()
        self.cli("vision", "map", "add", SLUG, "--name", "Entity risk timeline", "--outcome", "x", "--proof", "y")
        cmap = json.loads((self.eng / "demo" / f"{SLUG}-capability-map.json").read_text())
        cap = cmap["capabilities"][0]
        self.assertEqual((cap["id"], cap["origin"], cap["catalog"]), ("entity-risk-timeline", "sa_requested", False))

    def test_map_edit_after_freeze_requires_refreeze(self):
        self.to_vision_complete()
        self.cli("vision", "map", "add", SLUG, "workflows", "--outcome", "Automate enrichment", "--proof", "Run")
        self.assertEqual(self.state()["stages"]["ideation"]["status"], "stale")
        self.assertEqual(self.cli("next", SLUG)["phase"], "Design")
        self.cli("path", "check", SLUG, ok=False)

    def test_audit_must_cover_selected_map_and_block_red(self):
        self.to_vision_complete()
        self.put_audit(lambda a: a["feature_audit"].pop())
        err = self.cli("path", "check", SLUG, ok=False)
        self.assertIn("ai-cost-dashboard", err)
        self.put_audit(lambda a: a["meta"].update(capability_map_hash="sha256:" + "0" * 64))
        self.cli("path", "check", SLUG, ok=False)
        self.put_audit(lambda a: a["feature_audit"][4].update(remediation_owner=None))
        err = self.cli("path", "check", SLUG, ok=False)
        self.assertIn("remediation_owner", err)
        self.put_audit(lambda a: a["feature_audit"][4].update(status="blocked"))
        err = self.cli("path", "commit", SLUG, "--path", "custom", ok=False)
        self.assertIn("blocked", err)

    def test_predefined_path_locks_build(self):
        self.to_vision_complete(with_agent_builder=False)
        self.put_audit(lambda a: a.update(feature_audit=a["feature_audit"][:4]))
        self.cli("path", "commit", SLUG, "--path", "predefined", ok=False)  # needs recommendation
        self.put("path/predefined-recommendation.md", "opportunity/{slug}-predefined-recommendation.md")
        res = self.cli("path", "commit", SLUG, "--path", "predefined")
        self.assertEqual(res["standard_demo"], "Elastic Security — SIEM and Threat Detection")
        st = self.state()
        self.assertEqual(st["path"], "predefined")
        self.assertTrue(st["stages"]["build-path"]["pipeline_ends_here"])
        nxt = self.cli("next", SLUG)
        self.assertEqual(nxt["phase"], "Design")
        self.assertIn("custom Build stays locked", nxt["next_action"])


class TestCompareHarness(P2Base):
    """compare_engagements.py: legacy baseline vs a P2 re-run (synthetic legacy tree)."""

    def _legacy(self) -> Path:
        legacy = self.root.parent / f"{self.root.name}-legacy" / "2026NorthwindSOC"
        p = "2026northwind-soc"
        (legacy / "demo" / "raw").mkdir(parents=True)
        (legacy / "opportunity").mkdir()
        shutil.copy(FIX / "notes/call-notes.md", legacy / "demo" / "raw" / "call-notes.md")
        d = json.loads((FIX / "listen/discovery.json").read_text())
        d.pop("claims")
        for g in d["gaps"]:
            g.pop("gap_id")
        (legacy / "demo" / f"{p}-discovery.json").write_text(json.dumps(d))
        shutil.copy(FIX / "qualify/opportunity-profile.json", legacy / "opportunity" / f"{p}-opportunity-profile.json")
        (legacy / "demo" / f"{p}-ideation.md").write_text(
            (FIX / "vision/ideation.md").read_text().replace("Acme Pharma", COMPANY))
        audit = json.loads((FIX / "path/platform-audit.json").read_text())
        audit["meta"].pop("scope_source")
        (legacy / "demo" / f"{p}-platform-audit.json").write_text(json.dumps(audit))
        (legacy / "demo" / f"{p}-demo-script.md").write_text(f"# Demo Script — {COMPANY}\n")
        self.addCleanup(shutil.rmtree, legacy.parent, ignore_errors=True)
        return legacy

    def _compare(self, legacy, *extra):
        import compare_engagements  # noqa: PLC0415
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = compare_engagements.main(["compare", "--legacy", str(legacy), "--candidate", str(self.eng),
                                           "--json", *extra])
        return rc, json.loads(out.getvalue())

    def test_compare_passes_and_classifies(self):
        legacy = self._legacy()
        import compare_engagements  # noqa: PLC0415
        manifest = self.root / "legacy.manifest.json"
        manifest.write_text(json.dumps(compare_engagements.manifest(legacy)))
        self.to_vision_complete()
        self.put_audit()
        self.cli("path", "commit", SLUG, "--path", "custom")

        rc, rep = self._compare(legacy, "--legacy-manifest", str(manifest))
        failed = [g for g in rep["gates"] if not g["ok"]]
        self.assertEqual((rc, failed), (0, []))
        self.assertEqual(rep["meta"]["legacy_prefix"], "2026northwind-soc")
        rows = {(r["area"], r["check"]): r for r in rep["rows"]}
        self.assertEqual(rows[("identity", "private identity on shared artifacts")]["verdict"], "improved")
        self.assertEqual(rows[("discovery", "claims count")]["verdict"], "improved")
        self.assertEqual(rows[("path", "demo path")]["verdict"], "same")
        self.assertGreater(rows[("schema", "discovery errors")]["legacy"], 0)

        (legacy / "demo" / "2026northwind-soc-demo-script.md").write_text("edited")
        rc, rep = self._compare(legacy, "--legacy-manifest", str(manifest))
        self.assertEqual(rc, 1)
        self.assertIn("legacy tree unmodified", [g["gate"] for g in rep["gates"] if not g["ok"]])

    def test_compare_fails_on_candidate_leak_and_incomplete_stage(self):
        legacy = self._legacy()
        self.to_vision_complete()
        rc, rep = self._compare(legacy, "--through", "vision")
        self.assertEqual(rc, 0, [g for g in rep["gates"] if not g["ok"]])
        rc, rep = self._compare(legacy)
        self.assertIn("stage build-path complete", [g["gate"] for g in rep["gates"] if not g["ok"]])
        (self.eng / "demo" / f"{SLUG}-demo-script.md").write_text(f"Welcome {COMPANY}\n")
        rc, rep = self._compare(legacy, "--through", "vision")
        self.assertEqual(rc, 1)
        self.assertIn("identity: no leaks on candidate shared artifacts", [g["gate"] for g in rep["gates"] if not g["ok"]])


class TestFunctionalTestFixes(P2Base):
    """Regressions from the P2 legacy-comparison functional test (synthetic fixtures only)."""

    LEGACY_PKG = FIX / "legacy-pkg"
    LEGACY_SLUG = "2026NorthwindSOC"

    def _import_legacy(self):
        return self.create(entry_mode="import", **{"import": str(self.LEGACY_PKG)})

    # 1 — map_exclude duplicate Out-of-Scope line
    def test_exclude_catalog_id_uses_catalog_name_and_freeze_dedupes(self):
        self.to_proceed()
        for cid in ("detection-rules", "cases", "esql"):
            self.cli("vision", "map", "add", SLUG, cid, "--origin", "vision", "--outcome", "o", "--proof", "p")
        self.cli("vision", "map", "add", SLUG, "workflows", "--outcome", "o", "--proof", "p")
        self.cli("vision", "map", "exclude", SLUG, "ai-assistant", "--reason", "Not in this demo")
        self.cli("vision", "map", "exclude", SLUG, "ai-assistant", "--reason", "Not in this demo")
        cmap = json.loads((self.eng / "demo" / f"{SLUG}-capability-map.json").read_text())
        oos = [o for o in cmap["out_of_scope"] if o.get("capability_id") == "ai-assistant"]
        self.assertEqual(len(oos), 1)
        self.assertEqual(oos[0]["name"], "Elastic AI Assistant (Security / Observability)")
        ide = self.put("vision/ideation.md", "demo/{slug}-ideation.md")
        ide.write_text(ide.read_text().replace(
            "## Out of Scope\n", "## Out of Scope\n- Elastic AI Assistant — not in this demo\n"))
        self.cli("vision", "freeze", SLUG)
        from loomstate.core import find_section, md_sections  # noqa: PLC0415
        body = find_section(md_sections(ide.read_text()), "out of scope")
        self.assertEqual(sum("assistant" in ln.lower() for ln in body.splitlines()), 1, body)
        self.assertNotIn("ai-assistant —", body)

    # 2 + 3 — import a pre-P2 package end-to-end
    def test_legacy_import_migrates_and_rewrites_legacy_slug(self):
        res = self._import_legacy()
        self.assertEqual(self.state()["identity"]["legacy_slugs"], [self.LEGACY_SLUG])
        for f in self.eng.rglob("*"):
            if f.is_file() and "inputs" not in f.relative_to(self.eng).parts and not f.name.endswith("-state.json"):
                self.assertNotIn(self.LEGACY_SLUG.lower(), f.read_text().lower(), f)
        self.assertIn(self.LEGACY_SLUG, (self.eng / "inputs" / "call-notes.md").read_text())
        self.assertTrue(any("legacy slug" in m for m in res["messages"]), res["messages"])

        res = self.cli("listen", "record", SLUG)
        joined = "\n".join(res["warnings"])
        self.assertIn("backfilled gap_id", joined)
        self.assertIn("'resolved'", joined)
        self.assertIn("'schedule_only' → 'low'", joined)
        self.assertIn("severity 'out_of_scope' → null", joined)
        d = json.loads((self.eng / "demo" / f"{SLUG}-discovery.json").read_text())
        self.assertEqual(validate(d, "discovery"), [])
        self.assertNotIn("demo_scope.data_strategy", [g["field"] for g in d["gaps"]])
        infosec = next(g for g in d["gaps"] if g["field"] == "infosec_review")
        self.assertEqual((infosec["impact"], infosec["legacy_impact"]), ("low", "out_of_scope"))
        self.assertEqual(d["pain_points"][2]["legacy_severity"], "out_of_scope")
        self.assertIn("g_demo_scope_data_strategy", self.state()["stages"]["discovery-parser"]["closed_gaps"])

        res = self.cli("qualify", "record", SLUG)
        self.assertTrue(any("meddpic.economic_buyer.notes" in w for w in res["warnings"]), res)
        profile = self.eng / "opportunity" / f"{SLUG}-opportunity-profile.json"
        self.assertEqual(validate_file(profile, "opportunity-profile"), [])
        self.assertEqual(self.state()["stages"]["opportunity-review"]["status"], "awaiting_decision")

    def test_notes_mode_does_not_migrate_without_flag(self):
        self.create()
        d = json.loads((FIX / "listen/discovery.json").read_text())
        d["gaps"][2]["impact"] = "schedule_only"
        (self.eng / "demo" / f"{SLUG}-discovery.json").write_text(json.dumps(d))
        self.put("listen/gaps.md", "opportunity/{slug}-gaps.md")
        self.put("listen/confirmation.md", "opportunity/{slug}-confirmation.md")
        err = self.cli("listen", "record", SLUG, ok=False)
        self.assertIn("schedule_only", err)
        res = self.cli("listen", "record", SLUG, "--migrate-legacy")
        self.assertTrue(any("schedule_only" in w for w in res["warnings"]))

    # 3 + 12 — identity tokens
    def test_identity_tokens_substring_and_common_words(self):
        from loomstate.core import find_identity_leaks  # noqa: PLC0415
        ident = {"company_name": COMPANY, "public_display_name": "Acme Pharma"}
        self.assertEqual(find_identity_leaks("2026NorthwindSOC-discovery.json", ident), ["Northwind"])
        self.assertEqual(find_identity_leaks("folder 2026Acmeshop", {**ident, "legacy_slugs": ["2026Acmeshop"]}),
                         ["2026Acmeshop"])
        short = {"company_name": "Zeta Labs", "public_display_name": "Acme Labs"}
        self.assertEqual(find_identity_leaks("zetaflow pipeline", short), [])
        self.assertEqual(find_identity_leaks("the Zeta team", short), ["Zeta"])
        summit = {"company_name": "Summit Lending", "public_display_name": "Acme Lending"}
        self.assertEqual(find_identity_leaks("we reached the summit of the hill", summit), [])
        self.assertEqual(find_identity_leaks("Summit Lending renewal", summit), ["Summit Lending"])

    # 4 — KIBANA_SOLUTION: inferred suggestion, classic unless clearly oblt / security, SA can override
    OBS_NOTES = ("They want observability across services: APM traces with OpenTelemetry, SLOs for checkout, "
                 "and faster root cause analysis to cut MTTR.")
    SEC_NOTES = ("The SOC needs a SIEM with threat hunting and detection rules, plus incident response "
                 "playbooks and alert triage for ransomware.")

    def _notes(self, text: str) -> str:
        f = self.root / "extra-notes.md"
        f.write_text(text)
        return str(f)

    def _solution(self, slug=SLUG) -> dict:
        return self.state(slug)["kibana_solution"]

    def test_kibana_solution_classic_when_not_clear(self):
        self.create(solution="cross_solution")  # fixture notes: 2 security signals — not clear
        rec = self._solution()
        self.assertEqual((rec["value"], rec["source"], rec["confidence"]), ("classic", "inferred", "unclear"))
        self.assertIn("KIBANA_SOLUTION=classic", (self.eng / ".env.example").read_text())
        ks = self.cli("keys", "status", SLUG)["kibana_solution"]
        self.assertEqual((ks["value"], ks["confirmed"], ks["options"]), ("classic", False, ["classic", "es", "oblt", "security"]))
        self.assertTrue(any("suggested: classic" in n for n in self.cli("next", SLUG)["notes"]))
        self.cli("new", "--slug", "acme-search", "--display", "Acme Search", "--entry-mode", "scratch",
                 "--solution", "search")
        self.assertEqual(self._solution("acme-search")["value"], "classic")

    def test_kibana_solution_inferred_from_notes_and_declared_solution(self):
        for slug, text, solution, want in (
            ("acme-obs", self.OBS_NOTES, "cross_solution", "oblt"),
            ("acme-sec", self.SEC_NOTES, "unknown", "security"),
            ("acme-mix", self.OBS_NOTES + " " + self.SEC_NOTES, "cross_solution", "classic"),
            ("acme-declared", "General planning notes.", "observability", "oblt"),
        ):
            self.cli("new", "--slug", slug, "--display", "Acme Test", "--entry-mode", "notes",
                     "--solution", solution, "--notes", self._notes(text))
            (self.root / "extra-notes.md").unlink()
            rec = self._solution(slug)
            self.assertEqual((rec["value"], rec["source"]), (want, "inferred"), slug)
            self.assertIn(f"KIBANA_SOLUTION={want}", (self.root / slug / ".env.example").read_text())

    def test_kibana_solution_profile_area_and_sa_override(self):
        self.create(solution="cross_solution")
        self.listen()
        p = json.loads((FIX / "qualify/opportunity-profile.json").read_text())
        p["demo_scope_signals"]["primary_solution_area"] = "observability"
        (self.eng / "opportunity" / f"{SLUG}-opportunity-profile.json").write_text(json.dumps(p))
        self.put("qualify/opportunity-summary.md", "opportunity/{slug}-opportunity-summary.md")
        self.put("qualify/demo-goals.md", "opportunity/{slug}-demo-goals.md")
        out = self.cli("qualify", "record", SLUG)
        self.assertTrue(any("KIBANA_SOLUTION=oblt suggested" in w for w in out["warnings"]))
        self.assertIn("KIBANA_SOLUTION=oblt", (self.eng / ".env.example").read_text())
        self.cli("keys", "set", SLUG, "ELASTICSEARCH_URL=https://x.es.example:443")
        self.assertIn("KIBANA_SOLUTION=oblt", (self.eng / ".env").read_text())
        # SA overrides in input settings: sticks, remembers the suggestion, silences the note
        self.cli("keys", "set", SLUG, "KIBANA_SOLUTION=bogus", ok=False)
        self.cli("keys", "set", SLUG, "KIBANA_SOLUTION=classic")
        rec = self._solution()
        self.assertEqual((rec["value"], rec["source"], rec["suggested"]), ("classic", "sa", "oblt"))
        self.assertFalse(any("Kibana space solution" in n for n in self.cli("next", SLUG)["notes"]))
        self.cli("qualify", "record", SLUG)
        self.assertEqual(self._solution()["value"], "classic")
        self.assertIn("KIBANA_SOLUTION=classic", (self.eng / ".env").read_text())
        ks = self.cli("keys", "status", SLUG)["kibana_solution"]
        self.assertEqual((ks["confirmed"], ks["suggested"]), (True, "oblt"))

    # 11 — soft-limit warning only on crossing
    def test_soft_limit_warns_once_on_crossing(self):
        self.to_proceed()
        warned = []
        for cid in ("detection-rules", "cases", "ai-assistant", "esql", "workflows", "attack-discovery"):
            msgs = self.cli("vision", "map", "add", SLUG, cid, "--outcome", "o", "--proof", "p")["messages"]
            warned.append(any("capabilities in scope" in m for m in msgs))
        self.assertEqual(warned, [False, False, False, False, True, False])
        msgs = self.cli("vision", "map", "exclude", SLUG, "Something else")["messages"]
        self.assertFalse(any("capabilities in scope" in m for m in msgs))


class TestCompareHarnessFixes(P2Base):
    _legacy = TestCompareHarness._legacy
    _compare = TestCompareHarness._compare

    # 5 — manifest covers .git / continual-learning
    def test_manifest_covers_git_and_continual_learning(self):
        import compare_engagements  # noqa: PLC0415
        legacy = self._legacy()
        for rel in (".git/HEAD", "continual-learning/notes.md", "node_modules/x/index.js"):
            (legacy / rel).parent.mkdir(parents=True, exist_ok=True)
            (legacy / rel).write_text("x")
        m = compare_engagements.manifest(legacy)
        self.assertIn(".git/HEAD", m)
        self.assertIn("continual-learning/notes.md", m)
        self.assertNotIn("node_modules/x/index.js", m)
        manifest = self.root / "legacy.manifest.json"
        manifest.write_text(json.dumps(m))
        self.to_vision_complete()
        (legacy / ".git" / "HEAD").write_text("changed")
        rc, rep = self._compare(legacy, "--legacy-manifest", str(manifest), "--through", "vision")
        self.assertIn("legacy tree unmodified", [g["gate"] for g in rep["gates"] if not g["ok"]])

    def _design_anyway(self):
        self.create()
        self.listen()
        self.qualify_files("continue_discovery")
        self.cli("qualify", "decide", SLUG, "--status", "continue_discovery")
        self.cli("qualify", "design-anyway", SLUG, "--rationale", "Demo date fixed; accept EB risk")

    # 6 — --through limits rows; missing side is info
    def test_through_limits_sections_and_missing_is_info(self):
        legacy = self._legacy()
        self._design_anyway()
        rc, rep = self._compare(legacy, "--through", "qualify")
        self.assertEqual(rc, 0, [g for g in rep["gates"] if not g["ok"]])
        self.assertFalse({r["area"] for r in rep["rows"]} & {"vision", "audit", "path"})
        rows = {(r["area"], r["check"]): r for r in rep["rows"]}
        self.assertEqual(rows[("schema", "platform-audit errors")]["verdict"], "info")

    # 7 — failure detail never shown on a passing gate
    def test_gate_detail_only_on_failure(self):
        legacy = self._legacy()
        self._design_anyway()
        rc, rep = self._compare(legacy, "--through", "qualify")
        gates = {g["gate"]: g for g in rep["gates"]}
        self.assertTrue(gates["qualify: decision fields written by CLI"]["ok"])
        self.assertNotIn("lacks", gates["qualify: decision fields written by CLI"]["detail"])
        self.assertNotIn("status=", gates["stage opportunity-review complete"]["detail"])

    # 8 — drift compares against the latest approval only
    def test_drift_ignores_superseded_approvals(self):
        legacy = self._legacy()
        self._design_anyway()
        rc, rep = self._compare(legacy, "--through", "qualify")
        rows = {(r["area"], r["check"]): r for r in rep["rows"]}
        self.assertEqual(rows[("state", "approved artifacts edited since approval")]["candidate"], "none")
        profile = self.eng / "opportunity" / f"{SLUG}-opportunity-profile.json"
        profile.write_text(profile.read_text().replace("Alert fatigue", "Alert fatigue (edited)"))
        rc, rep = self._compare(legacy, "--through", "qualify")
        rows = {(r["area"], r["check"]): r for r in rep["rows"]}
        self.assertEqual(rows[("state", "approved artifacts edited since approval")]["candidate"],
                         [f"qualification_override:opportunity/{SLUG}-opportunity-profile.json"])

    def test_import_candidate_claims_gate_reads_exempt(self):
        legacy = self._legacy()
        self.create(entry_mode="import", **{"import": str(TestFunctionalTestFixes.LEGACY_PKG)})
        self.cli("listen", "record", SLUG)
        rc, rep = self._compare(legacy, "--through", "listen")
        gates = {g["gate"]: g for g in rep["gates"]}
        self.assertEqual(gates["evidence: claims present"]["detail"], "exempt (import)")


class TestFixtureSchemas(unittest.TestCase):
    # 10 — scope_source matches thread-audit
    def test_platform_audit_scope_source_ad_hoc(self):
        audit = json.loads((FIX / "path/platform-audit.json").read_text())
        audit["meta"]["scope_source"] = "ad_hoc"
        self.assertEqual(validate(audit, "platform-audit"), [])

    # 9 — every catalog audit_feature names a real thread-audit requirements row
    def test_catalog_audit_features_exist_in_thread_audit_table(self):
        import re  # noqa: PLC0415
        catalog = json.loads((REPO / "skills/references/capability-catalog.json").read_text())
        skill = (REPO / "skills/thread-audit/SKILL.md").read_text()
        table = skill.split("### Feature Requirements Reference", 1)[1].split("**Deployment type caveats", 1)[0]
        rows = {re.sub(r"\\\|", "|", ln.split(" | ")[0].lstrip("| ").strip())
                for ln in table.splitlines() if ln.startswith("| ") and not ln.startswith("| Feature")}
        by_id = {c["id"]: c["audit_feature"] for c in catalog["capabilities"]}
        for cid, feature in by_id.items():
            self.assertIn(feature, rows, cid)
        self.assertIn("SLO", by_id["slos"])
        self.assertIn("alerting", by_id["alerting"].lower())
        self.assertIn("risk", by_id["entity-analytics"].lower())

    def test_fixtures_validate(self):
        self.assertEqual(validate_file(FIX / "listen/discovery.json", "discovery"), [])
        self.assertEqual(validate_file(FIX / "qualify/opportunity-profile.json", "opportunity-profile"), [])
        self.assertEqual(validate_file(FIX / "path/platform-audit.json", "platform-audit"), [])

    def test_catalog_md_lists_every_id(self):
        catalog = json.loads((REPO / "skills/references/capability-catalog.json").read_text())
        md = (REPO / "skills/references/capability-catalog.md").read_text()
        for c in catalog["capabilities"]:
            self.assertIn(f"`{c['id']}`", md)


if __name__ == "__main__":
    unittest.main()
