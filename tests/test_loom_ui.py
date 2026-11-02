"""Loom UI adapter + HTTP server tests (S0–S2)."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from loomstate import cli  # noqa: E402
from loom_ui.adapter import AdapterError, LoomAdapter, assert_root_allowed  # noqa: E402
from loom_ui.server import serve  # noqa: E402
from test_loom_state import COMPANY, FIX, OPP, P2Base, SECRET, SLUG  # noqa: E402


class UIAdapterBase(P2Base):
    def setUp(self):
        super().setUp()
        self.adapter = LoomAdapter(self.root)

    def envelope_data(self, env: dict):
        self.assertTrue(env.get("ok"), env)
        return env["data"]


class TestAdapterS0(UIAdapterBase):
    def test_next_matches_cli_no_fs(self):
        self.create()
        cli_next = self.cli("next", SLUG, "--no-fs")
        ui = self.adapter.get_next(SLUG, fs=False)
        self.assertEqual(ui["data"], cli_next)

    def test_list_engagements_after_create(self):
        self.create()
        rows = self.envelope_data(self.adapter.get_engagements())
        self.assertTrue(any(r["slug"] == SLUG for r in rows))


class TestAdapterS1(UIAdapterBase):
    def test_create_parity_and_identity_rejection(self):
        body = {
            "slug": "northwind-demo",
            "display": "Northwind Demo",
            "company": COMPANY,
            "opportunity": OPP,
            "entry_mode": "notes",
            "solution": "security",
            "notes_paths": [str(FIX / "notes" / "call-notes.md")],
        }
        with self.assertRaises(AdapterError):
            self.adapter.create_engagement(body)

    def test_create_via_adapter(self):
        body = {
            "slug": "ui-acme-pharma",
            "display": "Acme Pharma",
            "company": COMPANY,
            "opportunity": OPP,
            "entry_mode": "notes",
            "solution": "security",
            "notes_paths": [str(FIX / "notes" / "call-notes.md")],
        }
        out = self.adapter.create_engagement(body)
        self.assertEqual(out["data"]["slug"], "ui-acme-pharma")
        example = (self.root / "ui-acme-pharma" / ".env.example").read_text()
        self.assertNotIn("Northwind", example)

    def test_keys_set_never_returns_secret(self):
        self.create()
        self.adapter.keys_action(SLUG, "set", {"pairs": [f"ES_API_KEY={SECRET}", "ELASTICSEARCH_URL=https://es.example:443"]})
        status = self.envelope_data(self.adapter.keys_status(SLUG))
        blob = json.dumps(status)
        self.assertNotIn(SECRET, blob)
        self.assertNotIn("ES_API_KEY=", blob.split("missing")[-1])  # no value echo

    def test_kibana_solution_override(self):
        self.create()
        ks = self.envelope_data(self.adapter.keys_status(SLUG))["kibana_solution"]
        self.assertFalse(ks["confirmed"])
        self.adapter.keys_action(SLUG, "set", {"pairs": ["KIBANA_SOLUTION=oblt"]})
        ks2 = self.envelope_data(self.adapter.keys_status(SLUG))["kibana_solution"]
        self.assertTrue(ks2["confirmed"])
        self.assertEqual(ks2["value"], "oblt")

    def test_kibana_solution_invalid(self):
        self.create()
        with self.assertRaises(AdapterError):
            self.adapter.keys_action(SLUG, "set", {"pairs": ["KIBANA_SOLUTION=bogus"]})


class TestAdapterS2(UIAdapterBase):
    def test_inputs_plan_record_flow(self):
        self.create()
        self.adapter.inputs_add(SLUG, {"filename": "extra.md", "content": "follow-up note"})
        plan = self.envelope_data(self.adapter.listen_plan(SLUG))
        self.assertIn("skill", plan)
        self.put("listen/discovery.json", "demo/{slug}-discovery.json")
        self.put("listen/gaps.md", "opportunity/{slug}-gaps.md")
        self.put("listen/confirmation.md", "opportunity/{slug}-confirmation.md")
        rec = self.adapter.listen_record(SLUG)
        self.assertTrue(rec["ok"])
        self.assertGreater(rec["data"]["claims"], 0)

    def test_inputs_preserves_filename_and_base64(self):
        import base64

        self.create()
        self.adapter.inputs_add(SLUG, {"filename": "ae-email.md", "content": "buyer named"})
        dest = self.root / SLUG / "inputs" / "ae-email.md"
        self.assertTrue(dest.is_file(), "upload must use client filename, not temp basename")
        self.assertEqual(dest.read_text(), "buyer named")
        blob = b"%PDF-fake-bytes"
        out = self.adapter.inputs_add(
            SLUG,
            {
                "uploads": [
                    {
                        "filename": "deck-notes.pdf",
                        "content_base64": base64.b64encode(blob).decode("ascii"),
                    }
                ]
            },
        )
        self.assertTrue(out["ok"])
        pdf = self.root / SLUG / "inputs" / "deck-notes.pdf"
        self.assertEqual(pdf.read_bytes(), blob)

    def test_inputs_rejects_path_traversal_filename(self):
        self.create()
        with self.assertRaises(AdapterError) as ctx:
            self.adapter.inputs_add(SLUG, {"filename": "../../evil.md", "content": "x"})
        self.assertEqual(ctx.exception.code, "bad_filename")

    def test_inputs_upload_shows_stale_after_listen_record(self):
        self.create()
        self.put("listen/discovery.json", "demo/{slug}-discovery.json")
        self.put("listen/gaps.md", "opportunity/{slug}-gaps.md")
        self.put("listen/confirmation.md", "opportunity/{slug}-confirmation.md")
        self.cli("listen", "record", SLUG)
        out = self.adapter.inputs_add(SLUG, {"filename": "follow-up.md", "content": "new buyer info"})
        blockers = out.get("state", {}).get("blockers") or []
        self.assertTrue(any("stale" in b.lower() for b in blockers), blockers)


class HTTPServerTests(P2Base):
    def setUp(self):
        super().setUp()
        os.environ["LOOM_APPROVER"] = "sa@example.com"
        self.httpd, self.token = serve(self.root, 0)
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        super().tearDown()

    def req(self, path, *, method="GET", body=None, token=None, origin=None):
        headers = {"Accept": "application/json"}
        if token is not False:
            headers["X-Loom-Token"] = token if token is not None else self.token
        if origin:
            headers["Origin"] = origin
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        r = urllib.request.Request(f"{self.base}{path}", data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(r, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_missing_token_401(self):
        code, body = self.req("/api/engagements", token=False)
        self.assertEqual(code, 401)
        self.assertFalse(body.get("ok"))

    def test_bad_origin_403(self):
        code, _ = self.req("/api/engagements", origin="http://evil.example:9999")
        self.assertEqual(code, 403)

    def test_bad_slug_400(self):
        code, body = self.req("/api/e/../etc/next")
        self.assertIn(code, (400, 404))

    def test_no_stack_trace_on_error(self):
        code, body = self.req("/api/e/no-such-slug/next")
        self.assertEqual(code, 404)
        self.assertIn("error", body)
        self.assertNotIn("Traceback", json.dumps(body))

    def test_create_and_overview_roundtrip(self):
        self.create()
        code, body = self.req(f"/api/e/{SLUG}/next?fs=0")
        self.assertEqual(code, 200)
        self.assertEqual(body["data"]["slug"], SLUG)

    def test_http_inputs_multi_upload(self):
        import base64

        self.create()
        code, body = self.req(
            f"/api/e/{SLUG}/inputs",
            method="POST",
            body={
                "uploads": [
                    {"filename": "notes-a.md", "content": "doc a"},
                    {"filename": "notes-b.md", "content": "doc b"},
                ]
            },
        )
        self.assertEqual(code, 200)
        self.assertTrue(body.get("ok"))
        self.assertTrue((self.root / SLUG / "inputs" / "notes-a.md").is_file())
        self.assertTrue((self.root / SLUG / "inputs" / "notes-b.md").is_file())
        code2, body2 = self.req(
            f"/api/e/{SLUG}/inputs",
            method="POST",
            body={"filename": "scan.pdf", "content_base64": base64.b64encode(b"pdf").decode("ascii")},
        )
        self.assertEqual(code2, 200)
        self.assertEqual((self.root / SLUG / "inputs" / "scan.pdf").read_bytes(), b"pdf")


class TestRootGuard(unittest.TestCase):
    def test_refuses_git_root(self):
        with tempfile.TemporaryDirectory() as td:
            git = Path(td) / ".git"
            git.mkdir()
            root = Path(td) / "engagements"
            root.mkdir()
            with self.assertRaises(SystemExit):
                assert_root_allowed(root)


if __name__ == "__main__":
    unittest.main()
