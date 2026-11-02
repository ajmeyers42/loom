"""Route handlers → loom_state CLI (in-process), JSON envelope for the UI."""

from __future__ import annotations

import base64
import contextlib
import io
import json
import re
import tempfile
import threading
from pathlib import Path
from typing import Any

from loomstate import bootstrap, cli, intake, state
from loomstate.core import LoomError, find_identity_leaks, get_root, is_cloud_synced

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Soft cap for browser → JSON uploads (notes / small attachments). Larger diagnostics stay CLI-path.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

_lock = threading.Lock()


class AdapterError(Exception):
    def __init__(self, code: str, message: str, http: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http = http


def _parse_cli_json(stdout: str) -> dict | list:
    text = (stdout or "").strip()
    if not text:
        return {}
    return json.loads(text)


def _run_cli(root: Path, argv: list[str]) -> dict | list:
    out, err = io.StringIO(), io.StringIO()
    with _lock, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli.main([*argv, "--root", str(root), "--json"])
    if rc != 0:
        msg = (err.getvalue() or out.getvalue()).strip()
        msg = msg.removeprefix("❌  ").strip()
        http = 404 if "No pipeline-state" in msg or "does not match folder" in msg else 409 if "stale" in msg.lower() else 400
        raise AdapterError("loom_error", msg, http=http)
    return _parse_cli_json(out.getvalue())


def _overview(root: Path, slug: str, *, use_fs: bool = True) -> dict:
    return cli.overview(root, slug, use_fs=use_fs)


def _envelope(data: Any, *, root: Path, slug: str | None = None, use_fs: bool = True,
              extra_warnings: list[str] | None = None) -> dict:
    warnings: list[str] = list(extra_warnings or [])
    if isinstance(data, dict):
        w = data.get("warnings")
        if isinstance(w, list):
            warnings.extend(str(x) for x in w)
        elif isinstance(w, str) and w:
            warnings.append(w)
        for key in ("messages",):
            for m in data.get(key) or []:
                if isinstance(m, str) and m.lower().startswith("warning:"):
                    warnings.append(m)
    st = _overview(root, slug, use_fs=use_fs) if slug else None
    return {"ok": True, "data": data, "warnings": warnings, "state": st}


def _identity_from_private(company: str, opportunity: str, opportunity_id: str | None) -> dict:
    return {
        "company_name": company or "",
        "opportunity_name": opportunity or "",
        "opportunity_id": opportunity_id or "",
        "legacy_slugs": [],
    }


def _scan_shared_surface(payload: Any, identity: dict) -> None:
    text = json.dumps(payload, ensure_ascii=False)
    leaks = find_identity_leaks(text, identity)
    if leaks:
        raise AdapterError("identity_leak", f"Response would expose private identity ({', '.join(leaks)})", http=500)


def validate_slug_param(slug: str) -> None:
    if not SLUG_RE.match(slug):
        raise AdapterError("invalid_slug", "Invalid slug format", http=400)


def list_engagements(root: Path) -> list[dict]:
    if not root.exists():
        return []
    rows = []
    for d in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        sp = d / f"{d.name}-pipeline-state.json"
        if not sp.exists():
            continue
        st = json.loads(sp.read_text())
        rows.append({
            "slug": st.get("slug", d.name),
            "display_name": st.get("identity", {}).get("public_display_name") or st.get("display_name"),
            "phase": state.derive(st).get("phase"),
        })
    return rows


def hygiene(root: Path) -> dict:
    out, err = io.StringIO(), io.StringIO()
    with _lock, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            cli.main(["hygiene", "--root", str(root), "--json"])
        except SystemExit:
            pass  # cmd_hygiene exits 1 when findings exist; JSON is already on stdout
    return _parse_cli_json(out.getvalue())


class LoomAdapter:
    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()

    def cloud_sync_warning(self) -> str | None:
        return ("engagements root is cloud-synced — prefer keeping .env on a local symlink "
                "target") if is_cloud_synced(self.root) else None

    def validate_public_fields(self, *, company: str, opportunity: str, slug: str, display: str,
                               opportunity_id: str | None = None) -> dict:
        ident = _identity_from_private(company, opportunity, opportunity_id)
        ident["public_display_name"] = display
        errors = {}
        for label, value in (("slug", slug), ("display_name", display)):
            if not value:
                continue
            leaks = find_identity_leaks(value.replace("-", " "), ident)
            if leaks:
                errors[label] = leaks
        return {"valid": not errors, "errors": errors}

    def get_engagements(self) -> dict:
        return _envelope(list_engagements(self.root), root=self.root, slug=None)

    def get_hygiene(self) -> dict:
        return _envelope(hygiene(self.root), root=self.root, slug=None)

    def get_next(self, slug: str, *, fs: bool = True) -> dict:
        validate_slug_param(slug)
        argv = ["next", slug]
        if not fs:
            argv.append("--no-fs")
        data = _run_cli(self.root, argv)
        return _envelope(data, root=self.root, slug=slug, use_fs=fs)

    def create_engagement(self, body: dict) -> dict:
        argv = ["new", "--slug", body["slug"]]
        if body.get("display"):
            argv.extend(["--display", body["display"]])
        if body.get("company"):
            argv.extend(["--company", body["company"]])
        if body.get("opportunity"):
            argv.extend(["--opportunity", body["opportunity"]])
        if body.get("opportunity_id"):
            argv.extend(["--opportunity-id", body["opportunity_id"]])
        if body.get("entry_mode"):
            argv.extend(["--entry-mode", body["entry_mode"]])
        if body.get("solution"):
            argv.extend(["--solution", body["solution"]])
        if body.get("import_dir"):
            argv.extend(["--import", str(body["import_dir"])])
        notes = body.get("notes_paths") or body.get("notes") or []
        pending_note = body.get("note_text") and body.get("note_filename")
        if notes and not pending_note:
            argv.append("--notes")
            argv.extend(str(p) for p in notes)
        data = _run_cli(self.root, argv)
        slug = data["slug"]
        if pending_note:
            self._add_note_text(slug, body["note_filename"], body["note_text"])
        ident = _identity_from_private(body.get("company", ""), body.get("opportunity", ""), body.get("opportunity_id"))
        _scan_shared_surface({k: data[k] for k in data if k != "next"}, ident)
        return _envelope(data, root=self.root, slug=slug, use_fs=True)

    def _add_note_text(self, slug: str, filename: str, content: str) -> None:
        validate_slug_param(slug)
        self._add_upload(slug, {"filename": filename, "content": content})

    @staticmethod
    def _safe_upload_name(filename: str) -> str:
        name = Path(filename or "").name.strip()
        if not name or name in (".", "..") or "/" in name or "\\" in name:
            raise AdapterError("bad_filename", "Upload filename required (basename only)", http=400)
        return name

    def _add_upload(self, slug: str, item: dict) -> str:
        """Write one upload into inputs/ using the client filename (not a temp basename)."""
        validate_slug_param(slug)
        name = self._safe_upload_name(item.get("filename", ""))
        raw: bytes
        if item.get("content_base64") is not None:
            try:
                raw = base64.b64decode(item["content_base64"], validate=True)
            except Exception as e:
                raise AdapterError("bad_base64", f"Invalid content_base64 for {name}: {e}", http=400) from e
        elif item.get("content") is not None:
            raw = str(item["content"]).encode("utf-8")
        else:
            raise AdapterError("missing_content", f"Upload {name} needs content or content_base64", http=400)
        if len(raw) > MAX_UPLOAD_BYTES:
            raise AdapterError(
                "too_large",
                f"{name} exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB UI upload limit — use CLI inputs add",
                http=400,
            )
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / name
            src.write_bytes(raw)
            eng = state.load(self.root, slug)
            msg = bootstrap.add_input(eng, src)
            eng.save()
            return msg

    def keys_status(self, slug: str) -> dict:
        validate_slug_param(slug)
        data = _run_cli(self.root, ["keys", "status", slug])
        ident = state.load(self.root, slug).state.get("identity", {})
        _scan_shared_surface(data, ident)
        return _envelope(data, root=self.root, slug=slug)

    def keys_siblings(self, slug: str) -> dict:
        validate_slug_param(slug)
        data = _run_cli(self.root, ["keys", "list", slug])
        return _envelope(data, root=self.root, slug=slug)

    def keys_action(self, slug: str, action: str, body: dict | None = None) -> dict:
        validate_slug_param(slug)
        body = body or {}
        if action == "set":
            pairs = body.get("pairs") or []
            if not pairs and body.get("key") and "value" in body:
                pairs = [f"{body['key']}={body['value']}"]
            argv = ["keys", "set", slug, *pairs]
        elif action == "clone":
            argv = ["keys", "clone", slug, "--from", body["source"]]
            if body.get("index_prefix"):
                argv.extend(["--index-prefix", body["index_prefix"]])
            if body.get("no_secrets"):
                argv.append("--no-secrets")
        elif action == "defer":
            argv = ["keys", "defer", slug]
        elif action == "validate":
            argv = ["keys", "validate", slug]
            if body.get("probe"):
                argv.append("--probe")
        else:
            raise AdapterError("unknown_action", f"Unknown keys action {action}", http=400)
        data = _run_cli(self.root, argv)
        # Never return secret values — status shape only
        if action == "set":
            for k in list(data.keys()):
                if k.upper().endswith("_KEY") or k.upper().endswith("_TOKEN"):
                    data.pop(k, None)
        ident = state.load(self.root, slug).state.get("identity", {})
        _scan_shared_surface(data, ident)
        return _envelope(data, root=self.root, slug=slug)

    def inputs_add(self, slug: str, body: dict) -> dict:
        validate_slug_param(slug)
        uploads = list(body.get("uploads") or [])
        if body.get("filename") and (
            body.get("content") is not None or body.get("content_base64") is not None
        ):
            uploads.insert(
                0,
                {
                    "filename": body["filename"],
                    "content": body.get("content"),
                    "content_base64": body.get("content_base64"),
                },
            )
        messages: list[str] = []
        if uploads:
            for item in uploads:
                messages.append(self._add_upload(slug, item))
            return _envelope({"messages": messages}, root=self.root, slug=slug)
        paths = body.get("paths") or []
        # Legacy: body.files as server-local paths (strings only)
        legacy = body.get("files")
        if legacy and all(isinstance(p, str) for p in legacy):
            paths = list(paths) + list(legacy)
        if not paths:
            raise AdapterError(
                "missing_files",
                "Provide uploads[{filename,content|content_base64}], filename+content, or paths",
                http=400,
            )
        data = _run_cli(self.root, ["inputs", "add", slug, *paths])
        return _envelope(data, root=self.root, slug=slug)

    def listen_plan(self, slug: str) -> dict:
        validate_slug_param(slug)
        data = _run_cli(self.root, ["listen", "plan", slug])
        return _envelope(data, root=self.root, slug=slug)

    def listen_record(self, slug: str) -> dict:
        validate_slug_param(slug)
        data = _run_cli(self.root, ["listen", "record", slug])
        return _envelope(data, root=self.root, slug=slug)

    def gaps_list(self, slug: str) -> dict:
        validate_slug_param(slug)
        data = _run_cli(self.root, ["gaps", "list", slug])
        eng = state.load(self.root, slug)
        claims = []
        dpath = eng.path(intake.DISCOVERY)
        if dpath.exists():
            disc = json.loads(dpath.read_text())
            for c in disc.get("claims") or []:
                claims.append({
                    "claim_id": c.get("claim_id"),
                    "text": c.get("text") or c.get("claim"),
                    "source_ref": c.get("source_ref"),
                })
        payload = {"gaps": data, "claims": claims}
        ident = eng.state.get("identity", {})
        _scan_shared_surface(payload, ident)
        return _envelope(payload, root=self.root, slug=slug)

    def gaps_respond(self, slug: str, body: dict) -> dict:
        validate_slug_param(slug)
        argv = ["gaps", "respond", slug, body["gap_id"], "--status", body.get("status", "answered")]
        if body.get("response"):
            argv.extend(["--response", body["response"]])
        if body.get("rationale"):
            argv.extend(["--rationale", body["rationale"]])
        data = _run_cli(self.root, argv)
        return _envelope(data, root=self.root, slug=slug)


def assert_root_allowed(root: Path) -> None:
    from loomstate.core import find_git_worktree

    wt = find_git_worktree(root)
    if wt:
        raise SystemExit(f"Refusing to start: engagements root {root} is inside git work tree {wt}")


def default_root() -> Path:
    return get_root(None)
