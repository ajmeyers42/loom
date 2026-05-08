#!/usr/bin/env python3
"""
wind-pulse — live checks for a loom engagement workspace.

Reads `{engagement}/.env`, then validates:
  • Elasticsearch: cluster health, data model indices / data streams (doc counts)
  • Kibana saved objects: every object listed in `kibana-objects/*.ndjson` (and optional
    `kibana/**/*.ndjson`) via GET /api/saved_objects/{type}/{id}
  • Observability SLOs: all SLOs whose tags include demobuilder:<engagement_id> (D-026)
  • Agent Builder: agent id from AGENT_BUILDER_AGENT_ID or parsed from kibana/deploy_fraud_assistant_agent.py
  • ML jobs: state + datafeed state from {slug}-ml-config.json (if present)
  • ELSER: inference endpoint allocation from {slug}-data-model.json (if present)
  • Workflows: GET /api/workflows + GET /api/alerting/rules/_find for "Invoke an Agent" (or
    DEMO_STATUS_WORKFLOW_RULE_NAME); 404 on /api/workflows often means wrong KIBANA_SPACE_PATH
  • Saved-object tag ref (D-026): each NDJSON object should reference tag id demobuilder:<slug>
    — run kibana/apply_loom_tags.py after import if missing

Output format: SKILL.md Step 3 spec with ✅/❌/⚠️ symbols and a FIX COMMANDS block.

Usage:
  cd ~/engagements/{slug}
  python3 /path/to/loom/skills/wind-pulse/demo_status.py
  python3 .../demo_status.py --engagement-dir /path/to/engagement

Optional env overrides:
  DEMO_STATUS_SKIP_NDJSON=1  — skip saved-object line-by-line checks (not recommended)
  DEMO_STATUS_WORKFLOW_RULE_NAME  — override alerting rule name for workflows readiness signal
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


# ── helpers ──────────────────────────────────────────────────────────────────

def load_dotenv(env_path: Path) -> None:
    if not env_path.is_file():
        print(f"ERROR: No .env at {env_path}", file=sys.stderr)
        sys.exit(1)
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ[k.strip()] = v.strip().strip('"').strip("'")


def normalize_api_key(raw: str) -> str:
    raw = (raw or "").strip().replace(" ", "")
    if not raw:
        return raw
    if ":" in raw:
        return base64.b64encode(raw.encode("utf-8")).decode("ascii")
    return raw


def engagement_id_for_tag() -> str:
    """D-026 — match kibana_env / bootstrap."""
    override = os.environ.get("DEMO_ASSET_TAG", "").strip()
    prefix = os.environ.get("INDEX_PREFIX", "").strip()
    slug = os.environ.get("DEMO_SLUG", "demo")
    raw = override or (prefix if prefix else slug)
    s = re.sub(r"[-_\s]+", "", raw).lower()
    return s or "demo"


def p(name: str) -> str:
    prefix = os.environ.get("INDEX_PREFIX", "").strip()
    if not prefix:
        return name
    if name.startswith(prefix):
        return name
    return f"{prefix}{name}"


def kb_url_path(path: str) -> str:
    space = os.environ.get("KIBANA_SPACE_PATH", "").strip()
    if not path.startswith("/"):
        path = "/" + path
    return f"{space}{path}" if space else path


def kb_headers() -> dict:
    kb_key = normalize_api_key(
        os.environ.get("KIBANA_API_KEY") or os.environ.get("ES_API_KEY", "")
    )
    return {
        "Authorization": f"ApiKey {kb_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "kbn-xsrf": "wind-pulse",
    }


def es_headers() -> dict:
    es_key = normalize_api_key(os.environ.get("ES_API_KEY", ""))
    return {
        "Authorization": f"ApiKey {es_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def kb_get(path: str) -> tuple[int, dict | list | None]:
    base = os.environ.get("KIBANA_URL", "").rstrip("/")
    url = f"{base}{kb_url_path(path)}"
    req = urllib.request.Request(url, method="GET", headers=kb_headers())
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode()
            if not raw:
                return resp.status, {}
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            parsed = None
        return e.code, parsed


def es_req(method: str, path: str, body: dict | None = None) -> dict:
    es_url = os.environ.get("ELASTICSEARCH_URL", "").rstrip("/")
    url = f"{es_url}{path}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=es_headers())
    with urllib.request.urlopen(req, timeout=90) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def collect_ndjson_objects(engagement_dir: Path) -> list[dict]:
    """Each item: {file, type, id, title}."""
    out: list[dict] = []
    globs = [
        engagement_dir / "kibana-objects",
        engagement_dir / "kibana",
    ]
    seen: set[tuple[str, str]] = set()
    for root in globs:
        if not root.is_dir():
            continue
        for f in sorted(root.rglob("*.ndjson")):
            try:
                text = f.read_text()
            except OSError:
                continue
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = o.get("type")
                oid = o.get("id")
                if not t or not oid:
                    continue
                key = (t, oid)
                if key in seen:
                    continue
                seen.add(key)
                title = (o.get("attributes") or {}).get("title") or oid
                out.append(
                    {
                        "file": str(f.relative_to(engagement_dir)),
                        "type": t,
                        "id": oid,
                        "title": title,
                    }
                )
    return out


def parse_default_agent_id(engagement_dir: Path) -> str | None:
    """Best-effort: AGENT_BUILDER_AGENT_ID default in deploy_fraud_assistant_agent.py."""
    path = engagement_dir / "kibana" / "deploy_fraud_assistant_agent.py"
    if not path.is_file():
        return None
    text = path.read_text()
    m = re.search(
        r'AGENT_ID\s*=\s*os\.environ\.get\s*\(\s*["\']AGENT_BUILDER_AGENT_ID["\']\s*,\s*["\']([^"\']+)["\']\s*\)',
        text,
    )
    return m.group(1) if m else None


def get_path(doc: dict, dotted: str):
    cur = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def has_non_empty(doc: dict, dotted: str) -> bool:
    v = get_path(doc, dotted)
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, list):
        return len(v) > 0
    return True


def collect_uppercase_field_paths(value, prefix: str = "") -> list[str]:
    out: list[str] = []
    if isinstance(value, dict):
        for k, v in value.items():
            path = f"{prefix}.{k}" if prefix else k
            if any(ch.isupper() for ch in k):
                out.append(path)
            out.extend(collect_uppercase_field_paths(v, path))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            out.extend(collect_uppercase_field_paths(item, f"{prefix}[{i}]"))
    return out


# ── symbols ───────────────────────────────────────────────────────────────────

OK = "✅ "
FAIL = "❌ "
WARN = "⚠️  "
BAR = "━" * 54


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="loom wind-pulse checks")
    ap.add_argument(
        "--engagement-dir",
        type=Path,
        default=Path.cwd(),
        help="Engagement workspace (contains .env and kibana-objects/)",
    )
    args = ap.parse_args()
    engagement_dir = args.engagement_dir.resolve()

    load_dotenv(engagement_dir / ".env")

    es_url = os.environ.get("ELASTICSEARCH_URL", "").rstrip("/")
    kb_url = os.environ.get("KIBANA_URL", "").rstrip("/")
    if not es_url.startswith("http"):
        print("ERROR: ELASTICSEARCH_URL must start with http(s)://", file=sys.stderr)
        sys.exit(1)
    if not kb_url.startswith("http"):
        print("ERROR: KIBANA_URL must start with http(s)://", file=sys.stderr)
        sys.exit(1)

    slug = os.environ.get("DEMO_SLUG", "?")
    prefix = os.environ.get("INDEX_PREFIX", "").strip()
    tag_needle = f"demobuilder:{engagement_id_for_tag()}"

    print(BAR)
    print(f" DEMO STATUS — {slug}")
    print(BAR)
    print(f" Engagement:  {engagement_dir}")
    print(f" INDEX_PREFIX: {repr(prefix) if prefix else '(none)'}")
    print(f" Loom tag: {tag_needle}")
    print()

    failures: list[str] = []
    warnings: list[str] = []
    fix_cmds: list[str] = []

    # ── Elasticsearch ─────────────────────────────────────────────────────────
    print("CLUSTER")
    live_es_ver = "?"
    try:
        info = es_req("GET", "/")
        live_es_ver = info.get("version", {}).get("number", "?")
        ch = es_req("GET", "/_cluster/health")
        st = ch.get("status", "?")
        nodes = ch.get("number_of_nodes", "?")
        unassigned = ch.get("unassigned_shards", 0)
        symbol = OK if st == "green" else (WARN if st == "yellow" else FAIL)
        print(f"  {symbol}Elasticsearch {live_es_ver}  health={st}  nodes={nodes}"
              + (f"  unassigned={unassigned}" if unassigned else ""))
        if st == "red":
            failures.append("cluster health red")
            fix_cmds.append("# Diagnose unassigned shards:\ncurl -s -H \"Authorization: ApiKey $ES_API_KEY\" \"$ELASTICSEARCH_URL/_cluster/allocation/explain\" | python3 -m json.tool")
        elif st == "yellow":
            warnings.append(f"cluster health yellow ({unassigned} unassigned) — safe on single-node")
        # D-020: compare .env ELASTIC_VERSION to live cluster
        env_ver = os.environ.get("ELASTIC_VERSION", "").strip()
        if env_ver and live_es_ver != "?" and env_ver != live_es_ver:
            warnings.append(
                f"ELASTIC_VERSION in .env ({env_ver}) != live cluster ({live_es_ver}) — "
                "update .env to match (D-020); artifacts may target the wrong version"
            )
            print(f"  {WARN}ELASTIC_VERSION mismatch: .env={env_ver}  cluster={live_es_ver} (D-020)")
    except Exception as e:
        print(f"  {FAIL}Elasticsearch: {e}")
        failures.append(f"elasticsearch: {e}")
        print()
        sys.exit(1)

    try:
        kst, kbody = kb_get("/api/status")
        if kst != 200:
            failures.append(f"kibana /api/status HTTP {kst}")
            print(f"  {FAIL}Kibana /api/status HTTP {kst}")
        elif isinstance(kbody, dict):
            lvl = kbody.get("status", {}).get("overall", {}).get("level", "?")
            kver = kbody.get("version", {}).get("number", "?")
            sym = OK if lvl in ("available", "green") else WARN
            print(f"  {sym}Kibana {kver}  status={lvl}")
        else:
            warnings.append("kibana status body unexpected type")
            print(f"  {WARN}Kibana /api/status: unexpected body type")
    except Exception as e:
        failures.append(f"kibana: {e}")
        print(f"  {FAIL}Kibana: {e}")
    print()

    # ── Indices ───────────────────────────────────────────────────────────────
    dm_path = engagement_dir / f"{slug}-data-model.json"
    dm: dict = {}
    if dm_path.is_file():
        dm = json.loads(dm_path.read_text())
        print("INDICES")
        for ds in dm.get("data_streams") or []:
            ds_name = None
            if isinstance(ds, str):
                ds_name = ds
            elif isinstance(ds, dict):
                if isinstance(ds.get("instances"), list) and ds.get("instances"):
                    # Use the first concrete instance as representative stream for health checks.
                    ds_name = ds["instances"][0]
                elif isinstance(ds.get("name"), str):
                    ds_name = ds.get("name")
                elif isinstance(ds.get("pattern"), str):
                    ds_name = ds.get("pattern")
            if not ds_name:
                continue
            idx = p(ds_name)
            try:
                c = es_req("GET", f"/{idx}/_count")["count"]
                sym = OK if c > 0 else WARN
                print(f"  {sym}{idx}  {c} docs")
                if c == 0:
                    warnings.append(f"{idx} has 0 docs")
                    continue

                # Check 2b: ECS baseline field population
                sample = es_req(
                    "GET",
                    f"/{idx}/_search",
                    {
                        "size": 5,
                        "sort": [{"@timestamp": {"order": "desc"}}],
                        "_source": True,
                    },
                )
                hits = [h.get("_source", {}) for h in (sample.get("hits", {}).get("hits") or [])]
                if not hits:
                    warnings.append(f"{idx} has docs but sample query returned no hits")
                    continue

                uppercase_paths = []
                for doc in hits:
                    uppercase_paths.extend(collect_uppercase_field_paths(doc))
                uppercase_paths = sorted(set(uppercase_paths))
                if uppercase_paths:
                    failures.append(f"{idx} contains uppercase field names")
                    print(f"  {FAIL}{idx} uppercase fields detected (example: {uppercase_paths[0]})")
                    fix_cmds.append(
                        f"# Normalize uppercase fields before demo:\n"
                        f"# add ingest rename pipeline + clean reload for {idx}"
                    )

                if ds_name.startswith("metrics-"):
                    missing_metrics = False
                    for doc in hits:
                        if not has_non_empty(doc, "@timestamp"):
                            missing_metrics = True
                        if not has_non_empty(doc, "event.dataset"):
                            missing_metrics = True
                        if not has_non_empty(doc, "host.name"):
                            missing_metrics = True
                        if not (has_non_empty(doc, "service.type") or has_non_empty(doc, "agent.type")):
                            missing_metrics = True
                    if missing_metrics:
                        failures.append(f"{idx} missing ECS baseline metric fields")
                        print(f"  {FAIL}{idx} missing one or more required metric ECS fields (`host.name`, `event.dataset`, `service.type|agent.type`)")
                        fix_cmds.append(
                            f"# Ensure default pipeline populates ECS fields for {idx}\n"
                            f"python3 bootstrap.py --step 4"
                        )

                    # Check 2c: entity discoverability baseline
                    host_agg = es_req(
                        "GET",
                        f"/{idx}/_search",
                        {"size": 0, "aggs": {"hosts": {"terms": {"field": "host.name", "size": 1}}}},
                    )
                    host_buckets = ((host_agg.get("aggregations") or {}).get("hosts") or {}).get("buckets") or []
                    if not host_buckets:
                        failures.append(f"{idx} has no host entities discoverable")
                        print(f"  {FAIL}{idx} has no host.name aggregation buckets — Infrastructure UI may be empty")

                if ds_name.startswith("logs-"):
                    missing_logs = False
                    for doc in hits:
                        if not has_non_empty(doc, "@timestamp"):
                            missing_logs = True
                        if not has_non_empty(doc, "event.dataset"):
                            missing_logs = True
                        if not (
                            has_non_empty(doc, "host.name")
                            or has_non_empty(doc, "container.id")
                            or has_non_empty(doc, "kubernetes.pod.name")
                        ):
                            missing_logs = True
                    if missing_logs:
                        failures.append(f"{idx} missing logs baseline entity fields")
                        print(f"  {FAIL}{idx} missing logs entity identity (`host.name` or `container.id` or `kubernetes.pod.name`)")

                    security_like = "security" in ds_name or any(
                        has_non_empty(doc, "event.category") for doc in hits
                    )
                    if security_like:
                        missing_security = False
                        for doc in hits:
                            if not has_non_empty(doc, "event.kind"):
                                missing_security = True
                            if not has_non_empty(doc, "event.type"):
                                missing_security = True
                            if not (has_non_empty(doc, "user.name") or has_non_empty(doc, "host.name")):
                                missing_security = True
                        if missing_security:
                            failures.append(f"{idx} missing security baseline fields")
                            print(f"  {FAIL}{idx} missing security fields (`event.kind`, `event.type`, `user.name|host.name`)")
            except Exception as e:
                print(f"  {FAIL}{idx}: {e}")
                failures.append(f"count {idx}")
                fix_cmds.append(f"python3 bootstrap.py  # reload data for {idx}")
        for idx_name in dm.get("indices") or []:
            index_name = idx_name if isinstance(idx_name, str) else (idx_name or {}).get("name")
            if not index_name:
                continue
            name = p(index_name)
            try:
                c = es_req("GET", f"/{name}/_count")["count"]
                sym = OK if c > 0 else WARN
                print(f"  {sym}{name}  {c} docs")
                if c == 0:
                    warnings.append(f"{name} has 0 docs")
            except Exception as e:
                print(f"  {FAIL}{name}: {e}")
                failures.append(f"count {name}")
                fix_cmds.append(f"python3 bootstrap.py  # reload data for {name}")
        print()
    else:
        warnings.append(f"no {dm_path.name} — data model index checks skipped")

    # ── ML Jobs ───────────────────────────────────────────────────────────────
    ml_path = engagement_dir / f"{slug}-ml-config.json"
    if ml_path.is_file():
        ml_cfg = json.loads(ml_path.read_text())
        print("ML JOBS")
        for job_cfg in ml_cfg.get("jobs") or []:
            job_id = job_cfg.get("job_id", "?")
            datafeed_id = job_cfg.get("datafeed", {}).get("datafeed_id", f"datafeed-{job_id}")
            try:
                js = es_req("GET", f"/_ml/anomaly_detectors/{job_id}/_stats")
                job_state = ((js.get("jobs") or [{}])[0]).get("state", "?")
                ds = es_req("GET", f"/_ml/datafeeds/{datafeed_id}/_stats")
                df_state = ((ds.get("datafeeds") or [{}])[0]).get("state", "?")
                sym = OK if job_state == "opened" and df_state == "started" else WARN
                print(f"  {sym}{job_id}  job={job_state}  datafeed={df_state}")
                if job_state != "opened":
                    warnings.append(f"ML job {job_id} state={job_state} (expected opened)")
                    fix_cmds.append(f"curl -s -XPOST -H \"Authorization: ApiKey $ES_API_KEY\" -H 'Content-Type: application/json' \"$ELASTICSEARCH_URL/_ml/anomaly_detectors/{job_id}/_open\"")
                if df_state != "started":
                    warnings.append(f"ML datafeed {datafeed_id} state={df_state} (expected started)")
                    fix_cmds.append(f"curl -s -XPOST -H \"Authorization: ApiKey $ES_API_KEY\" -H 'Content-Type: application/json' \"$ELASTICSEARCH_URL/_ml/datafeeds/{datafeed_id}/_start\"")
            except Exception as e:
                print(f"  {WARN}{job_id}: {e} (skip — may not be configured for this engagement)")
                warnings.append(f"ml job {job_id}: {e}")
        print()

    # ── ELSER ─────────────────────────────────────────────────────────────────
    elser_endpoint = None
    for idx_name in dm.get("indices") or []:
        if "semantic" in idx_name:
            elser_endpoint = p(os.environ.get("ELSER_ENDPOINT_NAME", "elser-v2-endpoint"))
            break
    if elser_endpoint is None and dm.get("elser_endpoint"):
        elser_endpoint = p(dm["elser_endpoint"])
    if elser_endpoint:
        print("ELSER")
        try:
            ep = es_req("GET", f"/_inference/sparse_embedding/{elser_endpoint}")
            allocs = (ep.get("service_settings") or {}).get("num_allocations", "?")
            sym = OK if isinstance(allocs, int) and allocs > 0 else WARN
            print(f"  {sym}{elser_endpoint}  num_allocations={allocs}")
            if isinstance(allocs, int) and allocs == 0:
                warnings.append(f"ELSER endpoint {elser_endpoint} has 0 allocations — still loading?")
        except Exception as e:
            print(f"  {WARN}{elser_endpoint}: {e} (not deployed or different name)")
            warnings.append(f"elser endpoint {elser_endpoint}: {e}")
        print()

    # ── Kibana Space ─────────────────────────────────────────────────────────
    space_path = os.environ.get("KIBANA_SPACE_PATH", "").strip()
    if space_path:
        # Extract space id from /s/{id}
        space_id = space_path.lstrip("/").lstrip("s/").split("/")[0] if "/s/" in space_path else space_path.strip("/")
        # Space API is always on default space (no KIBANA_SPACE_PATH prefix)
        base_kb = os.environ.get("KIBANA_URL", "").rstrip("/")
        req_space = urllib.request.Request(
            f"{base_kb}/api/spaces/space/{urllib.parse.quote(space_id, safe='')}",
            method="GET", headers=kb_headers()
        )
        try:
            with urllib.request.urlopen(req_space, timeout=30) as r:
                sp_body = json.loads(r.read().decode())
                sp_name = sp_body.get("name", space_id)
                print(f"  {OK}Kibana space '{space_id}' ({sp_name}) exists — KIBANA_SPACE_PATH={space_path}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"  {FAIL}Kibana space '{space_id}' NOT FOUND — create it or fix KIBANA_SPACE_PATH in .env")
                failures.append(f"kibana space '{space_id}' not found")
                fix_cmds.append(
                    f"# Create Kibana space '{space_id}':\n"
                    f"curl -s -XPOST -H 'Authorization: ApiKey $ES_API_KEY' -H 'kbn-xsrf: x' "
                    f"-H 'Content-Type: application/json' \"$KIBANA_URL/api/spaces/space\" "
                    f"-d '{{\"id\":\"{space_id}\",\"name\":\"{space_id}\",\"description\":\"Loom engagement {space_id}\"}}'"
                )
            else:
                warnings.append(f"kibana space check HTTP {e.code}")
                print(f"  {WARN}Kibana space check HTTP {e.code}")
        except Exception as ex:
            warnings.append(f"kibana space check: {ex}")
    else:
        print(f"  {WARN}KIBANA_SPACE_PATH not set — assets deploy to default Space (set for isolation)")
        warnings.append("KIBANA_SPACE_PATH not set — assets in default Space; set to /s/{DEMO_SLUG} for isolation")

    # ── Kibana saved objects ──────────────────────────────────────────────────
    print("KIBANA")
    if os.environ.get("DEMO_STATUS_SKIP_NDJSON"):
        warnings.append("DEMO_STATUS_SKIP_NDJSON set — NDJSON object checks skipped")
        print(f"  {WARN}NDJSON checks skipped (DEMO_STATUS_SKIP_NDJSON=1)")
    else:
        objs = collect_ndjson_objects(engagement_dir)
        if not objs:
            warnings.append("no *.ndjson under kibana-objects/ or kibana/ — no saved object inventory")
            print(f"  {WARN}No *.ndjson found — add exports under kibana-objects/")
        else:
            objs.sort(key=lambda x: (0 if x["type"] == "dashboard" else 1, x["file"], x["type"]))
            tag_ref_id = f"loom-{engagement_id_for_tag()}"
            for o in objs:
                path = f"/api/saved_objects/{o['type']}/{urllib.parse.quote(str(o['id']), safe='')}"
                code, body = kb_get(path)
                label = f"{o['type']}:{o['id']}"
                if code == 200:
                    refs = (body or {}).get("references") or []
                    has_tag = any(
                        isinstance(r, dict)
                        and r.get("type") == "tag"
                        and r.get("id") == tag_ref_id
                        for r in refs
                    )
                    tag_note = " [tag ✓]" if has_tag else " [no loom tag]"
                    if not has_tag:
                        warnings.append(
                            f"{label} missing loom tag ref"
                        )
                    print(f"  {OK}{label}  ({o['title'][:50]}){tag_note}")
                else:
                    print(f"  {FAIL}{label}  HTTP {code}  [{o['file']}]")
                    failures.append(f"saved_object {label}")
                    fix_cmds.append(
                        f"# Re-import NDJSON for {label}:\n"
                        f"python3 kibana/deploy_kibana_gaps.py --skip-agent --skip-slos\n"
                        f"python3 kibana/apply_loom_tags.py"
                    )

    # ── SLOs ──────────────────────────────────────────────────────────────────
    print()
    print("SLOs")
    tagged_ids: set[str] = set()
    code, body = kb_get("/api/observability/slos?page=1&perPage=500")
    if code != 200:
        print(f"  {FAIL}GET /api/observability/slos HTTP {code}")
        failures.append("list slos")
    else:
        raw_list = (body or {}).get("results") or (body or {}).get("slos") or []
        ours: list[dict] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            slo = item.get("slo") if "slo" in item else item
            if not isinstance(slo, dict):
                continue
            tags = slo.get("tags") or item.get("tags") or []
            if tag_needle in tags:
                ours.append(slo)
        if not ours:
            warnings.append(
                f"no SLOs tagged {tag_needle} — SLOs not deployed or D-026 tags missing"
            )
            print(f"  {WARN}No SLOs tagged {tag_needle}")
        tagged_ids = {s.get("id") for s in ours if s.get("id")}
        for slo in ours:
            sid = slo.get("id", "?")
            name = slo.get("name", sid)
            print(f"  {OK}SLO {sid} — {name[:50]}")

    exp_path = engagement_dir / "kibana" / "status-expected.json"
    if exp_path.is_file():
        try:
            exp = json.loads(exp_path.read_text())
            for sid in exp.get("slo_ids") or []:
                if sid in tagged_ids:
                    continue
                c2, b2 = kb_get(f"/api/observability/slos/{urllib.parse.quote(sid, safe='')}")
                if c2 == 200:
                    nm = (b2 or {}).get("name") or (b2 or {}).get("slo", {}).get("name", sid)
                    print(f"  {OK}SLO (expected) {sid} — {str(nm)[:50]}")
                else:
                    print(f"  {FAIL}SLO (expected) {sid}  HTTP {c2}")
                    failures.append(f"slo {sid}")
                    fix_cmds.append("python3 kibana/deploy_kibana_gaps.py --skip-agent --skip-dashboards")
        except (OSError, json.JSONDecodeError) as e:
            warnings.append(f"status-expected.json: {e}")

    # ── Agent Builder ─────────────────────────────────────────────────────────
    print()
    print("AGENT BUILDER")
    agent_id = os.environ.get("AGENT_BUILDER_AGENT_ID", "").strip()
    if not agent_id:
        agent_id = parse_default_agent_id(engagement_dir) or ""
    if agent_id:
        code, body = kb_get(f"/api/agent_builder/agents/{agent_id}")
        if code == 200 and isinstance(body, dict) and body.get("id") == agent_id:
            print(f"  {OK}agent `{agent_id}`")
        else:
            print(f"  {FAIL}agent `{agent_id}`  HTTP {code}")
            failures.append(f"agent {agent_id}")
            fix_cmds.append("python3 kibana/deploy_fraud_assistant_agent.py")
    else:
        warnings.append("no AGENT_BUILDER_AGENT_ID — set env var or add kibana/deploy_fraud_assistant_agent.py")
        print(f"  {WARN}(skip — set AGENT_BUILDER_AGENT_ID or add kibana/deploy_fraud_assistant_agent.py)")

    # ── Workflows ─────────────────────────────────────────────────────────────
    print()
    print("WORKFLOWS")
    wf_id = os.environ.get("AGENT_BUILDER_WORKFLOW_ID", "").strip()
    rule_name = os.environ.get("DEMO_STATUS_WORKFLOW_RULE_NAME", "Invoke an Agent").strip()
    q = urllib.parse.urlencode(
        {"search_fields": "name", "search": rule_name, "per_page": 25, "page": 1}
    )
    rcode, rbody = kb_get(f"/api/alerting/rules/_find?{q}")
    rule_total = 0
    if rcode == 200 and isinstance(rbody, dict):
        rule_total = int(rbody.get("total", len(rbody.get("data") or [])))
    if rcode == 200 and rule_total > 0:
        print(f"  {OK}Alerting rule \"{rule_name}\" — {rule_total} match(es) (workflows readiness ✓)")
    else:
        print(f"  {WARN}No alerting rules matching \"{rule_name}\" (HTTP {rcode}, total={rule_total})")
        warnings.append(f"alerting rule \"{rule_name}\" not found — workflows may not be configured")

    wf_code, wf_body = kb_get("/api/workflows")
    if wf_code == 404:
        print(
            f"  {WARN}GET /api/workflows → 404 (feature not enabled or wrong Space)\n"
            "    → If Workflows is enabled in Kibana UI, set KIBANA_SPACE_PATH in .env\n"
            "      to the Space where Workflows is enabled (e.g. KIBANA_SPACE_PATH=/s/my-space)"
        )
        if rule_total > 0:
            print(f"    → Alerting rule check passed — treat Workflows as ready")
    elif wf_code != 200:
        print(f"  {WARN}GET /api/workflows HTTP {wf_code}")
        warnings.append("workflows API unexpected status")
    else:
        workflows = wf_body if isinstance(wf_body, list) else (wf_body or {}).get("workflows") or []
        ids = [w.get("id") for w in workflows if isinstance(w, dict)]
        print(f"  {OK}GET /api/workflows → {len(ids)} workflow(s)")
        if wf_id:
            if wf_id in ids:
                print(f"  {OK}AGENT_BUILDER_WORKFLOW_ID `{wf_id}` present")
            else:
                print(f"  {FAIL}workflow `{wf_id}` not in list")
                failures.append(f"workflow {wf_id}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print(BAR)
    if failures:
        print(f" OVERALL: {FAIL}NOT READY  ({len(failures)} failure(s))")
        print()
        print(" FAILURES (fix these before the demo):")
        for f in failures:
            print(f"   {FAIL}{f}")
    elif warnings:
        print(f" OVERALL: {OK}READY (with warnings)")
    else:
        print(f" OVERALL: {OK}READY")

    if warnings:
        print()
        print(" WARNINGS (demo can proceed, but note these):")
        for w in warnings:
            print(f"   {WARN}{w}")

    if fix_cmds:
        print()
        print(BAR)
        print(" FIX COMMANDS — paste to resolve failures")
        print(BAR)
        print(f"set -a && source {engagement_dir}/.env && set +a")
        for cmd in dict.fromkeys(fix_cmds):  # deduplicate, preserve order
            print(cmd)
    elif not failures:
        print()
        print(BAR)
        print(" RECOMMENDED — run before the demo")
        print(BAR)
        print(f"set -a && source {engagement_dir}/.env && set +a")
        print("# Warm ELSER endpoint (prevents cold-start latency during demo):")
        print(f"curl -s -XPOST -H \"Authorization: ApiKey $ES_API_KEY\" -H 'Content-Type: application/json' \\")
        print(f'  "$ELASTICSEARCH_URL/_inference/sparse_embedding/_warm" || true')

    print(BAR)


if __name__ == "__main__":
    main()
