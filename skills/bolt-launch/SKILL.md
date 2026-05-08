---
name: bolt-launch
status: DEPRECATED — replaced by finish-verify + bolt-bootstrap
description: >
  DEPRECATED as of 2026-05-05. This skill has been split into two focused agents:

  - finish-verify (Agent A): schema probing + asset authoring via elastic/agent-skills
  - bolt-bootstrap (Agent B): Terraform + bootstrap-data.py generation

  Use finish-verify → bolt-bootstrap instead of this skill.
  This file is retained as a reference during the transition.

  If the orchestrator routes here, redirect to finish-verify immediately.
---

> ⛔ **DEPRECATED — DO NOT USE FOR NEW ENGAGEMENTS**
>
> This skill has been replaced by the two-stage deployment pipeline:
>
> **Stage 8b:** `finish-verify` — schema probe + asset authoring via elastic/agent-skills
> **Stage 9:** `bolt-bootstrap` — Terraform HCL + bootstrap-data.py generation
>
> Read `../finish-verify/SKILL.md` instead.
> See `docs/decisions.md` D-045, D-046, D-047 for rationale.
>
> This file is retained as a reference for understanding the prior bootstrap.py
> structure during the transition period. It will be removed once bolt-ech
> and bolt-serverless are validated end-to-end.

---



# Demo Deploy

You are deploying a demo environment to an Elastic cluster. You generate a Python
deployment script (`bootstrap.py`) from the pipeline outputs, then execute it. The script
is the deployment record — it documents exactly what was created, in what order, and why.

Every step is idempotent: if the script is interrupted and re-run, it picks up where it
left off without creating duplicates or overwriting data that's already correct.

## Automation contract (skills — not one-off scripts, not manual UI)

**Single deployment surface:** `bootstrap.py` in the engagement workspace is the only
required executable for “deploy the demo.” It must perform **every** automated provisioning
step that **this engagement’s** script, checklist, data model, and platform audit require —
using Elasticsearch APIs for cluster-side work and **Kibana / Kibana-adjacent APIs** for
anything the story needs in the UI (saved objects, Observability, Security, Stack Management,
etc.), with `KIBANA_API_KEY` where applicable (see `references/env-reference.md`). Do **not**
hand off with a separate `deploy_*.py` beside bootstrap, “run these scripts in order,” or
“click through Kibana to finish” unless the **platform audit** records a genuine blocker and
the deploy log documents the exception.

**Scenario-driven — not a fixed stack:** No engagement is required to use SLOs, Agent Builder,
Security rules, or any other specific feature. **Derive** bootstrap contents from:

- `demo/{slug}-demo-script.md` and `deploy/{slug}-demo-checklist.md` — what scenes and clicks must work
- `demo/{slug}-platform-audit.json` — what is licensed, version-supported, and enabled
- `data/{slug}-data-model.json` — indices, pipelines, seed data
- `data/{slug}-ml-config.json` (if any) — ML and anomaly injection
- Optional specs (`demo/{slug}-*-dashboards-spec.md`, `demo/{slug}-agent-builder-spec.md`, etc.)

Skip entire subsystems when out of scope (e.g. pure Elasticsearch relevance demos may only
need data views + saved searches + dashboards; a SIEM demo may emphasize detection rules
and timelines; an Observability demo may emphasize SLOs and APM — **implement only what is
scoped**).

**Skill catalog (`elastic/agent-skills`) — pick what matches the scenario:**

The **full** `elastic/agent-skills` install includes **Search, Observability, and Security**
specialists. Keep them **available** for every engagement; **invoke** only what the script
and audit require (a non-Security demo does not call Security APIs — but the skills must
still be present so hybrid and Sec-first demos are supported without a different install).

Use these specialists to **author** payloads, NDJSON, and API bodies before or while writing
`bootstrap.py`. This table is a **menu**, not a mandatory checklist:

| Typical need | Skill (plugin) | Notes |
|--------------|----------------|--------|
| Dashboards / Lens / saved objects | `kibana-dashboards` | Any vertical — viz as code |
| Observability SLOs | `observability-manage-slos` | When the script calls for SLOs |
| Alerting rules (including SLO burn rate) | `kibana-alerting-rules` | Rule types vary by use case |
| Connectors | `kibana-connectors` | Before Workflows that notify |
| **Security / SIEM** | `security-detection-rule-management`, `security-alert-triage`, `security-case-management`, `security-generate-security-sample-data`, other `security-*` | First-class — use when demo is Sec or hybrid; sample data for POCs |
| Agent Builder | `elastic/kibana-agent-builder-sdk` + `demo/{slug}-agent-builder-spec.md` | When script includes agents |
| ES|QL / analytics | `elasticsearch-esql` | Query validation and panels |

The deploying agent **implements** chosen payloads inside `bootstrap.py` (or loads JSON
adjacent files). “Placeholder only” assets are **incomplete** unless `{slug}-demo-checklist.md`
or validator explicitly allowed thin shells for a pilot.

**Anti-pattern:** Copying a prior engagement’s `bootstrap.py` or Kibana steps wholesale.
Each demo gets a **generated** script aligned to its artifacts.

**Elastic deployability and datatypes (`docs/decisions.md` D-025):** Do not author assets that
cannot be applied with supported APIs. Mappings and documents use **Elasticsearch field types**;
Agent Builder ES|QL tool `params.*.type` values must match what the Kibana server validates
(typically ES-style: `keyword`, `text`, `integer`, `date`, … — verify per stack). Security
rules, SLOs, and saved objects follow **product** schemas for the target version.

**Reference files — read before building:**

| File | When to read |
|------|-------------|
| `references/feature-compatibility.md` | Version gates, ILM vs DSL, feature availability by deployment type |
| `references/inference-config.md` | ELSER/reranker service names and model IDs by deployment type |
| `references/kibana-api-registry.md` | Kibana API paths, probe endpoints, auth requirements |
| `references/pipeline-constants.md` | Seed thresholds, UUID5 namespace, manifest index name, kbn-xsrf value |
| `references/terraform-patterns.md` | HCL patterns when `DEPLOY_MODE=terraform` |
| `references/serverless-differences.md` | Serverless behavioral quirks, ML field names, Liquid syntax, saved objects |
| `references/workflow-patterns.md` | Working Workflow YAML patterns, stale-read warning, DELETE endpoint, search-by-name |
| `references/asset-manifest.md` | Dynamic manifest schema, `_manifest_add_es` / `_manifest_add_kibana` helpers (D-039) |
| `references/teardown-dispatch.md` | Deletion ordering and dispatch table (referenced by generated teardown.py) |
| `hive-mind/patterns/agent-builder/AGENT_BUILDER_API_MANAGEMENT.md` | Agent Builder CRUD, tool types, system prompts (D-034) |
| `hive-mind/patterns/dashboards/DASHBOARD_NDJSON_FORMAT.md` | Dashboard NDJSON format, Lens panel types, stable UUIDs (D-034) |

Do not iterate past 30 minutes on an undocumented Workflow or Agent Builder API without
surfacing it as a blocker and asking for the `elastic/workflows` or
`elastic/kibana-agent-builder-sdk` reference repos (paths in `references/reference-repos.md`).

**Deploy mode:** Check `DEPLOY_MODE` from `.env` before generating:
- `python` (default) — generate `deploy/bootstrap.py` as a full Python deployment driver
- `terraform` — generate `deploy/main.tf` + `deploy/providers.tf` + `deploy/{slug}.tfvars` + `deploy/bootstrap-data.py` (data/ops only). See `references/terraform-patterns.md`.

## Step 0: Review gate (before any live cluster changes)

**Do not** execute `bootstrap.py` against a **live** cluster (or run `bolt-spin`
to create resources) until the SA has:

1. **Reviewed** the generated **`bootstrap.py`** (what it will create or mutate).
2. **Reviewed** analysis outputs the deploy relies on: **`demo/{slug}-platform-audit`**, **`deploy/{slug}-risks`**,
   **`deploy/{slug}-demo-checklist.md`**, and any committed **`deploy/kibana-objects/`**, **`deploy/kibana/`**, or
   **`deploy/elasticsearch/`** files the script imports.
3. **Explicitly approved** provision/deploy for this session (same as `AGENTS.md`).

Allowed without that approval: **author** `bootstrap.py`, **`--dry-run`**, local edits to NDJSON,
connectivity checks that do not mutate production. See **`docs/decisions.md` D-024**.

## Step 1: Load the Environment

Read `{engagement_dir}/.env` (engagement directory = `{engagement_dir}`). All subsequent API calls use these credentials. Never
hardcode credentials in the script itself — always read from the `.env`.

If `.env` doesn't exist: stop and tell the user to run `bolt-spin` first, or
to create a `.env` from the `.env.example` template.

Verify the `.env` has all required fields:
- `ELASTICSEARCH_URL` — non-empty, starts with `https://` or `http://`
- `KIBANA_URL` — non-empty
- `ES_API_KEY` — non-empty
- `DEPLOYMENT_TYPE` — one of: `serverless`, `ech`, `self_managed`, `docker`

Read `INDEX_PREFIX` (may be blank). If set, prepend it to every index name, template name,
and pipeline name in the deployment. Apply consistently so a prefix of `cb-` makes
`fraud-claims` → `cb-fraud-claims` everywhere including query references.

Read optional **`DEMO_ASSET_TAG`** — overrides the engagement id used in **`demobuilder:<id>`**
tags when set (see **`references/loom-tagging.md`**, **`docs/decisions.md` D-026**).

## Step 2: Read Pipeline Outputs

Load all available artifacts from the workspace:
- `data/{slug}-data-model.json` — required. Defines all indices, templates, pipelines, build order.
- `data/{slug}-ml-config.json` — optional. ML jobs, datafeeds, injection plan.
- `deploy/{slug}-integrations-manifest.json` — optional. Fleet integration packages to install
  at step 1c. If present, include step 1c in the generated bootstrap; if absent, omit step 1c
  entirely (no stub, no comment). Also read `demo/{slug}-integration-assets.md` for any
  `use_as_is` or `clone_and_modify` assets that should be imported in step 13.
- `demo/{slug}-platform-audit.json` — read `deployment_type` and feature availability to
  adapt the bootstrap to the specific platform.
- `demo/{slug}-demo-script.md`, `deploy/{slug}-demo-checklist.md`, and any supplemental specs
  (`demo/{slug}-*-dashboards-spec.md`, `demo/{slug}-agent-builder-spec.md`, Security plans, etc.) —
  required context for **step 13** so every scene that depends on a Kibana, Security, or
  Observability asset has a matching API step when those features are in scope.
- Optional: `{slug}-kibana-*.json` or other sidecar JSON if earlier stages materialized
  them; otherwise derive payloads using the **skill catalog** that matches this scenario.

Extract the build order from the data model — this is the sequence the script must follow.

**Kibana and ES collateral as files:** If the engagement workspace includes
`deploy/kibana-objects/{slug}-*.ndjson`, `deploy/kibana/workflows/*`, `deploy/kibana/agent/*.json`, or declarative
`deploy/elasticsearch/**` JSON, **`bootstrap.py` must load and apply them** via APIs (saved objects
import, Workflows, Agent Builder, ES `PUT`s) — single script, no parallel `deploy_*.py`. Paths
are relative to `{engagement_dir}` (**D-024**).

## Step 2b: Generation Checklist (run BEFORE authoring any script or HCL)

Before writing a single line of `bootstrap.py` or `main.tf`, mechanically verify the following against the pipeline outputs and reference files. If any item fails, **stop and resolve it first**.

| # | Check | How to verify | Fail action |
|---|---|---|---|
| 1 | **Reference files read** | Did you read `terraform-patterns.md`, `kibana-api-registry.md`, `pipeline-constants.md`, `asset-manifest.md`? | Read them now |
| 2 | **DEPLOY_MODE set** | `.env` contains `DEPLOY_MODE=terraform` or `DEPLOY_MODE=python` | Ask SA if missing |
| 3 | **Integration schema probed (D-043)** | For every index any asset queries: run `GET /_index_template/*`, then `GET /_component_template/<name>@package` (integration) or `GET /<index>/_mapping` (custom). Record actual field names. | Probe now; do not proceed until field schema is confirmed |
| 4 | **Integration-first + package assets (D-043, D-032)** | Observability/Security streams use Fleet integration naming. No Prometheus-scraper or custom DCGM/kube-state streams unless SA-approved exception. **Also:** run `GET /api/fleet/epm/packages/<name>/assets` to enumerate what dashboards, rules, ML jobs, and data views the package ships — use those first; author custom assets only for scenes the package does not cover. Managed assets used as-is or referenced by ID; clone with `[{SLUG}]` prefix only when modification is needed (D-032). | Replace with correct integration stream; inventory package assets before authoring anything custom |
| 5 | **Dashboard composition — embed existing assets (D-043)** | Custom dashboards must include any already-deployed SLOs (`slo_overview`/`slo_burn_rate`/`slo_error_budget` panel types), ML anomaly results (via `vis` + `ref_id`), and other relevant saved visualizations rather than re-creating them. Probe `GET /api/observability/slos`, `GET /api/ml/anomaly_detectors`, `GET /api/saved_objects/_find?type=visualization` before authoring dashboard panels. | Add embed panels for any found assets |
| 5 | **Dashboard format (9.4+)** | Dashboards use the Kibana 9.4 declarative API (`POST /api/dashboards`, `type: "vis"` panels). NDJSON import (`/api/saved_objects/_import`) is 8.x only and broken on 9.4. Author `deploy/kibana-objects/dash-*.json` via `kibana-dashboards.js`. | Run `kibana-dashboards` skill |
| 6 | **Alerting actions shape** | Any alerting rule must use `"group": "query matched"` (not `"default"`) and include `"frequency"` object | See kibana-api-registry.md#alerting-rules |
| 7 | **Cases payload** | `POST /api/cases` body must NOT include `"status"` — use PATCH after create | See kibana-api-registry.md#cases |
| 8 | **Agent Builder skill_ids** | Agent Builder create must include `"skill_ids"` key (even if `[]`); requires probe of `/api/agent_builder/skills` first | See kibana-api-registry.md#d-029 |
| 9 | **ML job lifecycle** | ML job sequence: create → `_open` → datafeed create → `_start`; Terraform uses `ml_job_state` + `ml_datafeed_state` resources | See terraform-patterns.md#ml-job-lifecycle |
| 10 | **attempt_or_skip scope** | `attempt_or_skip` only wraps GET probes for optional features; never wraps in-scope asset creation | See kibana-api-registry.md#attempt_or_skip |
| 11 | **D-026 tags on every asset** | `merge_tags()` called on every resource that accepts a `tags` or `labels` field | Check rule/SLO/agent/workflow payloads |
| 12 | **Provider versions (TF only)** | `elasticstack` + `ec` provider pins reflect latest minor (D-041) | Check reference-repos.md |
| 13 | **`disabled_features = []` on every space (TF only)** | Every `elasticstack_kibana_space` resource has `disabled_features = []` | See terraform-patterns.md#kibana-space |
| 14 | **Field population confirmed (D-044)** | For every custom index, produce a table of (field → viz that uses it → seed value/derivation). Every viz-queried field must be non-null in 100% of seed docs. Derived fields (`risk_label`, `on_track`, etc.) computed and stored at seed time. | Fix seed data or mapping before proceeding |

**Hard gate — asset ordering (D-043, D-044):** No dashboard, alert, SLO, workflow, or Agent Builder tool that queries an index may be authored or deployed until checklist rows 3 and 14 are complete for that index. If the integration template exists but no data has arrived yet, the `@package` component template field list is the authoritative schema source. For custom indices, at least one document must exist — with all viz-queried fields populated — before dashboard authoring begins.

## Step 3: Generate `bootstrap.py`

Write a complete, executable Python script to `{engagement_dir}/deploy/bootstrap.py`.

The script structure:

```python
#!/usr/bin/env python3
"""
Loom bootstrap — {Company} ({slug})
Generated: {date}
Deployment: {type} at {ELASTICSEARCH_URL}

Engagement dir is `{engagement_dir}` (default parent `~/engagements` per docs/engagements-path.md).
After `GET /`, print cluster version and warn if `ELASTIC_VERSION` in `.env` disagrees (D-020).

Usage:
  python3 bootstrap.py                    # deploy everything
  python3 bootstrap.py --dry-run         # print what would be done, no API calls
  python3 bootstrap.py --skip-data       # skip data loading (re-run after a config change)
  python3 bootstrap.py --step N          # resume from step N (see step list below)
  python3 bootstrap.py --only GROUP      # deploy only a named group (e.g. --only kibana, --only ml, --only data)

Steps:
  1.  Connectivity check (includes version validation vs ELASTIC_VERSION)
  1b. Kibana Space — ensure /s/{DEMO_SLUG} exists (create if absent, idempotent)
  1c. Fleet integration packages — install EPM packages from `deploy/{slug}-integrations-manifest.json`
      (idempotent; skipped automatically if manifest absent; must run before ILM/templates)
  2.  ILM / Data Stream Lifecycle policies
  3.  Enrich policies (create + execute)
  4.  Ingest pipelines
  5.  Component templates
  6.  Index templates (data streams)
  7.  Static indices (create if not exists)
  8.  ELSER inference endpoint
  9.  Semantic indices (requires ELSER from step 8)
  10. Load seed data
  11. ML anomaly detection jobs
  12. ML datafeeds (create + start)
  13. Kibana & platform UI assets (all API — see “Step 13” below; implement only sub-steps
      required by this engagement’s script, audit, and validator)
  14. Anomaly injection
  15. Warm ELSER endpoint
"""

import os, sys, json, time, argparse, re
import urllib.request, urllib.error

# ── Credentials (from .env) ─────────────────────────────────────────────────
ES_URL       = os.environ.get("ELASTICSEARCH_URL", "").rstrip("/")
KB_URL       = os.environ.get("KIBANA_URL", "").rstrip("/")
API_KEY      = os.environ.get("ES_API_KEY", "")
KB_KEY       = os.environ.get("KIBANA_API_KEY", "")  # used for all Kibana asset operations
DEP_TYPE     = os.environ.get("DEPLOYMENT_TYPE", "ech")
PREFIX       = os.environ.get("INDEX_PREFIX", "")
SLUG         = os.environ.get("DEMO_SLUG", "demo")
SPACE_PATH   = os.environ.get("KIBANA_SPACE_PATH", "").strip()  # e.g. /s/2026citizens-ai

def p(name): return f"{PREFIX}{name}" if PREFIX else name  # apply index prefix

# ── Loom engagement tag (D-026) — merge into every API payload that has "tags" ──
def _engagement_id_for_tag() -> str:
    override = os.environ.get("DEMO_ASSET_TAG", "").strip()
    raw = override or (PREFIX.strip() if PREFIX.strip() else SLUG)
    s = re.sub(r"[-_\s]+", "", raw).lower()
    return s or "demo"

def loom_tags() -> list[str]:
    return [f"demobuilder:{_engagement_id_for_tag()}"]

def merge_tags(existing):
    return sorted(set((existing or []) + loom_tags()))

# ── HTTP helpers ─────────────────────────────────────────────────────────────
def es(method, path, body=None, *, ok=(200,201)):
    """Call Elasticsearch API. Raises on unexpected status."""
    ...

def kb(method, path, body=None, *, ok=(200,)):
    """Call Kibana API. Uses KIBANA_API_KEY (KB_KEY) for all Kibana asset operations
    (Agent Builder, Workflows, Dashboards, Connectors, Saved Objects)."""
    ...

def step(n, label):
    """Print step header and check if we should skip."""
    ...

# ── Step implementations ──────────────────────────────────────────────────────
def check_connectivity():   ...

def ensure_kibana_space():
    """Step 1b — create /s/{DEMO_SLUG} if absent. Idempotent; 409 = already exists."""
    space_id = SLUG.strip().lower()
    if not space_id:
        return
    # Space management API MUST use the default-space base URL (no SPACE_PATH prefix)
    import urllib.error
    headers = {"Authorization": f"ApiKey {KB_KEY}", "Content-Type": "application/json", "kbn-xsrf": "loom"}
    req = urllib.request.Request(f"{KB_URL}/api/spaces/space/{space_id}", method="GET", headers=headers)
    try:
        urllib.request.urlopen(req, timeout=30)
        print(f"  Kibana space '{space_id}' already exists"); return
    except urllib.error.HTTPError as e:
        if e.code != 404: raise
    body = json.dumps({
        "id": space_id,
        "name": os.environ.get("ENGAGEMENT", space_id),
        "description": f"Loom engagement {space_id}",
        "disabledFeatures": [],                          # enable all Kibana features in this space
        "solution": os.environ.get("KIBANA_SOLUTION", "es")  # "es", "oblt", or "security" per demo
    }).encode()
    req = urllib.request.Request(f"{KB_URL}/api/spaces/space", data=body, method="POST", headers=headers)
    try:
        urllib.request.urlopen(req, timeout=30)
        print(f"  Kibana space '{space_id}' created")
    except urllib.error.HTTPError as e:
        if e.code == 409: print(f"  Kibana space '{space_id}' already exists (409)")
        else: raise

def create_ilm_policies():  ...  # skipped on serverless (uses DSL)
def create_dsl_policies():  ...  # serverless only
def create_enrich_policies():    ...
def execute_enrich_policies():   ...
def create_pipelines():     ...
def create_component_templates(): ...
def create_index_templates():    ...
def create_static_indices():     ...
def deploy_elser():         ...
def create_semantic_indices():   ...
def load_seed_data():       ...
def create_ml_jobs():       ...
def start_datafeeds():      ...
def import_kibana_objects():     ...
def inject_anomalies():     ...
def warm_elser():           ...

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ...
```

### Critical implementation details for each step

**Connectivity check (step 1)**
```python
resp = es("GET", "/")
version = resp["version"]["number"]
print(f"  Connected: {ES_URL}")
print(f"  Version:   {version}")
print(f"  Prefix:    '{PREFIX}' ({'applied' if PREFIX else 'none — using default index names'})")
# D-020: warn if .env ELASTIC_VERSION disagrees with live cluster
env_ver = os.environ.get("ELASTIC_VERSION", "").strip()
if env_ver and env_ver != version:
    print(f"  ⚠  ELASTIC_VERSION in .env ({env_ver}) != cluster ({version}) — update .env (D-020)")
# D-033: 9.4+ baseline gate — halt on older clusters
major, minor = (int(x) for x in version.split(".")[:2])
if (major, minor) < (9, 4):
    skip_check = os.environ.get("SKIP_VERSION_CHECK", "").lower() == "true"
    if not skip_check:
        print(f"  ⛔ Cluster version {version} is below the 9.4 baseline (D-033).")
        print(f"     Set SKIP_VERSION_CHECK=true in .env to override (unsupported).")
        sys.exit(1)
    print(f"  ⚠  Version {version} below 9.4 baseline — SKIP_VERSION_CHECK override active")
# D-039: initialise dynamic manifest and ensure manifest index exists
# See references/asset-manifest.md for schema and helpers
_manifest_init()
_ensure_manifest_index()
_manifest["es_version"] = version
_manifest_push()
```
Fail fast and clearly if connectivity fails — don't attempt subsequent steps.

**Kibana Space (step 1b)**

Run `ensure_kibana_space()` immediately after connectivity. This step uses the **default-space
base URL** (`KB_URL/api/spaces/space`) — never the `SPACE_PATH`-prefixed URL — because the
space does not yet exist when this call is first made. All subsequent Kibana calls (step 13
and beyond) use `SPACE_PATH` as the prefix through the `kb()` helper:

```python
def kb(method, path, body=None, *, ok=(200,)):
    """Kibana API with SPACE_PATH prefix (set by KIBANA_SPACE_PATH in .env)."""
    full_path = f"{SPACE_PATH}{path}" if SPACE_PATH else path
    ...
```

**ILM / DSL (step 2) — deployment-type-aware**
```python
if DEP_TYPE == "serverless":
    # Serverless uses Data Stream Lifecycle, not ILM
    # Apply DSL via index template `lifecycle` block — no separate ILM API call
    print("  Serverless detected — using Data Stream Lifecycle (skipping ILM API)")
else:
    # Create ILM policy via /_ilm/policy/{name}
    for policy in data_model["ilm_policies"]:
        resp = es("PUT", f"/_ilm/policy/{p(policy['name'])}", policy["definition"])
        print(f"  ILM policy: {p(policy['name'])} → {resp.get('acknowledged')}")
```

**Enrich policies (step 3)**
Enrich policies MUST be executed (not just created) before any pipeline that references
them. The execute call is synchronous but can take seconds on large lookup indices.
```python
es("PUT", f"/_enrich/policy/{p(policy['name'])}", policy["match"])
es("POST", f"/_enrich/policy/{p(policy['name'])}/_execute")
# Poll until complete:
while True:
    status = es("GET", f"/_enrich/policy/{p(policy['name'])}")
    if status["policies"][0]["match"].get("indices"):
        break
    time.sleep(1)
```

**Idempotent index creation (step 7)**
Check existence before creating — never overwrite an existing index's data:
```python
try:
    es("HEAD", f"/{p(index['name'])}", ok=(200,))
    print(f"  {p(index['name'])}: exists — skipping")
except:
    es("PUT", f"/{p(index['name'])}", index["mapping"])
    print(f"  {p(index['name'])}: created")
```

**ELSER endpoint (step 8) — EIS for ECH, managed for Serverless (D-028)**

```python
endpoint_id = p("elser")
task_type   = "sparse_embedding"

# GET response wraps endpoints in {"endpoints": [...]} on 9.x — unwrap before checking
try:
    resp      = es("GET", f"/_inference/{task_type}/{endpoint_id}", ok=(200,))
    endpoints = resp.get("endpoints") or []
    existing  = endpoints[0] if endpoints else resp
    svc       = existing.get("service", "")
    expected  = "elser" if DEP_TYPE == "serverless" else "elastic"
    if svc == expected:
        print(f"  ELSER endpoint '{endpoint_id}': exists on correct service='{svc}' — skipping")
        _manifest_add_es("inference_endpoint", endpoint_id, task_type=task_type)
        return
    elif svc:
        print(f"  ELSER endpoint '{endpoint_id}': found but service='{svc}' != expected '{expected}' — deleting to recreate")
        es("DELETE", f"/_inference/{task_type}/{endpoint_id}", ok=(200, 204))
except RuntimeError as e:
    if "404" not in str(e):
        raise

if DEP_TYPE == "serverless":
    # Serverless: managed endpoint — use "elser" service, no model_id
    # See references/inference-config.md for canonical config (D-028, D-042)
    body = {"service": "elser", "service_settings": {"num_allocations": 1, "num_threads": 1}}
else:
    # ECH 9.4+: use Elastic Inference Service — do NOT deploy on ML node (D-028)
    # See references/inference-config.md for canonical config (D-042)
    body = {"service": "elastic", "service_settings": {"model_id": ".elser-2", "num_allocations": 1, "num_threads": 1}}

es("PUT", f"/_inference/{task_type}/{endpoint_id}", body)
print(f"  ELSER endpoint '{endpoint_id}': deploying via {'Serverless managed' if DEP_TYPE == 'serverless' else 'EIS'}...")
_manifest_add_es("inference_endpoint", endpoint_id, task_type=task_type)  # D-039
# EIS endpoints are ready immediately; Serverless managed may need a warm-up call
if DEP_TYPE != "serverless":
    print("  EIS endpoint ready (no model allocation needed)")
```

Cold ELSER inference on Serverless can take 30+ seconds on the first call. The warm-up
step (step 15) handles this, but allow extra time on first deploy.

**Seed data loading (step 10)**
Generate realistic synthetic data from the sample data spec in the data model. Use
`_bulk` API with batches of 500 documents. Check existing doc count first:
```python
count = es("GET", f"/{p(ds['index'])}/_count")["count"]
if count >= ds["seed_document_count"] * 0.9:  # 90% threshold — already loaded
    print(f"  {p(ds['index'])}: {count} docs exist — skipping load")
    continue
# Generate and bulk-index
```

**Data generation** — synthesize realistic values from the sample data spec:
- Use the `key_entities` distribution weights to sample realistic field values
- Generate `demo_critical_docs` first and index them individually (verified)
- Fill remaining doc count with randomized but realistic values
- For `days_since_filed`, `@timestamp`, etc. — use realistic date arithmetic from "now"
- **Derived fields must be computed at seed time (D-044).** Fields like `risk_label` derived from `risk_score` must be calculated in Python before indexing — never stored as null with the expectation that a query will derive them later.

**Post-seed validation gate (D-044):** After each `_bulk_index` call for a custom index, assert every viz-queried field is non-null across all documents:
```python
def assert_viz_fields_populated(index, viz_fields):
    """Fail fast if any field used by a visualization is null in any document."""
    total = es("GET", f"/{index}/_count")["count"]
    for field in viz_fields:
        populated = es("POST", f"/{index}/_count",
                       {"query": {"exists": {"field": field}}})["count"]
        if populated < total:
            raise RuntimeError(
                f"SEED VALIDATION FAIL: {index}.{field} null in "
                f"{total - populated}/{total} docs — fix seed data before deploying vizzes"
            )
# Call immediately after _bulk_index for every custom index
```

**ML jobs (step 11)**
```python
try:
    es("GET", f"/_ml/anomaly_detectors/{job['job_id']}", ok=(200,))
    print(f"  ML job {job['job_id']}: exists — skipping")
except:
    es("PUT", f"/_ml/anomaly_detectors/{job['job_id']}", job["analysis_config_etc"])
```

**Step 13 — Kibana & platform UI assets (complete everything in scope)**

**Not** “import NDJSON only.” Implement **every** Kibana API and related call that this
engagement’s **script + audit + validator** require — **omit** sub-bullets that are out of
scope. Honor `KIBANA_SPACE_PATH` in `.env` by prefixing paths (`/s/{space}/api/...`). Use
`KIBANA_API_KEY` for Kibana calls.

**13a — Data views** *(when the demo uses Discover, Lens, or dashboards bound to indices)*  
`POST /api/data_views/data_view` for each index pattern the script references (count and
names come from the data model + script — not a fixed pair). Idempotent: list existing
titles, skip if present.

**13b — Observability SLOs** *(when the script / checklist explicitly includes SLOs)*  
`POST /api/observability/slos` per `observability-manage-slos`. Indicator types vary (KQL,
APM, Synthetics, etc.). Treat `409` as already created.

**13c — Connectors + Alerting rules** *(when the script needs alerts — SLO burn, metric threshold, etc.)*

**⚠ `.cases` connector is UI-ONLY (confirmed 9.4):** Do NOT generate `POST /api/actions/connector` calls with `connector_type_id: ".cases"` — the API rejects them with `400`. The `.cases` connector is auto-provisioned by Kibana per solution space. Instead, generate a printed manual step instructing the SA to wire Cases actions from the Kibana UI:
```
⚠  MANUAL: Kibana → Stack Management → Rules → [rule name] → Edit
   → Add action → Kibana Cases → set owner=Observability → Save
```

For the **ServiceNow `.webhook` connector**, the `config.headers` field must be a plain JSON object (`{"Content-Type": "application/json"}`), NOT an array of `{key, value}` pairs.

`POST /api/alerting/rule/{id}` with the correct `rule_type_id` for that scenario (e.g. SLO
burn rate: `slo.rules.burnRate`, `consumer`: `slo`) — validate with `kibana-alerting-rules`
for the target version.

**SLO stack docs:** Elastic Guide (concepts, create SLO, burn-rate alerts, troubleshoot incl.
reset) plus the API hub — see **`docs/references-observability-slo.md`** in loom. Use the **`current`** Guide branch for 9.x stacks (D-033/D-025) and re-check pages when the stack version changes.

**13d — Saved objects / Dashboards** *(when dashboards/visualizations are in scope)*

**Managed and package assets first (D-032, D-043):** Before authoring any custom dashboard or visualization:
1. Run `GET /api/fleet/epm/packages/<name>/assets` — note any shipped dashboards; link or reference them from the custom dashboard rather than rebuilding equivalent panels.
2. Run `GET /api/observability/slos` — for each SLO in scope, plan an `slo_overview`, `slo_burn_rate`, or `slo_error_budget` embed panel in the relevant custom dashboard.
3. Run `GET /_ml/anomaly_detectors` + `GET /api/saved_objects/_find?type=ml-telemetry` — embed ML results (swimlane, heatmap) via `type: "vis"` with `ref_id` pointing to the ML job's results saved object.
4. Run `GET /api/saved_objects/_find?type=visualization` — inventory other already-deployed Lens/aggregation visualizations that belong in the story.

**Custom dashboard panels** are authored only for content not covered by the above. Panels that embed existing saved objects use `"type": "vis", "config": { "ref_id": "<id>" }`. SLO panels use `"type": "slo_overview"` (or `slo_burn_rate`, `slo_error_budget`, `slo_alerts`) with `"config": { "sloId": "<id>", "instanceId": "*" }`.

Author `deploy/kibana-objects/dash-*.json` via `kibana-dashboards.js` (`POST /api/dashboards` on 9.4+). Apply `INDEX_PREFIX` to index names in ES|QL queries before deploy.

**Stable UUIDs for dashboards and saved objects** — always use deterministic UUIDs derived
from the engagement ID + object name so re-deploys produce the same IDs and avoid duplicates:

```python
import uuid
_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # UUID namespace (URL)

def stable_id(name: str) -> str:
    """Generate a stable UUID from engagement slug + object name."""
    return str(uuid.uuid5(_NS, f"{SLUG}:{name}"))
```

Use `stable_id("dashboard-name")` whenever authoring dashboard or saved object IDs.
This makes teardown reliable (IDs are known at generation time) and prevents duplicate
panels when bootstrap is re-run. Reference: `hive-mind/patterns/dashboards/DASHBOARD_NDJSON_FORMAT.md`.

**Kibana APIs (rules, connectors, saved objects):** See **`docs/references-kibana-apis.md`**
— Kibana Guide `current` for **Saved Objects** and **Alerting** (rules and connectors). SLO
burn-rate rules are one `rule_type_id` under Alerting; the Observability SLO reference
**`docs/references-observability-slo.md`** stays focused on SLOs + SLO burn-rate behavior (**D-025**).

**13e — Agent Builder** *(when the agent spec exists and audit allows it)*  
`PUT/POST` under `/api/agent_builder/...` per `demo/{slug}-agent-builder-spec.md` — not a
manual “Create agent” handoff.

**13g — Security / SIEM** *(when demo is Sec or hybrid)*

Use `security-*` skills as appropriate. For detection rules:

- **Custom demo rules (authored from scratch):** Upsert by `rule_id` — check existence
  first, POST if absent, PUT if present (increment `version`). Include `loom_tags()`
  and `BOOTSTRAP_VERSION` (D-026, D-030).

- **Elastic-managed / prebuilt rules (D-032):** Never modify the original. Clone instead:

```python
# 1. Fetch the prebuilt rule as a template
existing = kb("GET", f"/api/detection_engine/rules?rule_id={source_rule_id}", ok=(200,))
# 2. Strip immutable/read-only fields
READ_ONLY = {"id","created_at","updated_at","updated_by","created_by",
             "immutable","rule_source","revision","execution_summary"}
clone = {k: v for k, v in existing.items() if k not in READ_ONLY}
# 3. Assign demo identity
clone["rule_id"]     = f"demo-{source_rule_id}"
clone["name"]        = f"[{SLUG}] {existing['name']}"
clone["description"] = f"[v{BOOTSTRAP_VERSION}] Clone of '{existing['name']}' — {purpose}"
clone["tags"]        = merge_tags(clone.get("tags", []))
clone["version"]     = 1
# 4. Idempotent create — check if clone already exists
try:
    kb("GET", f"/api/detection_engine/rules?rule_id={clone['rule_id']}", ok=(200,))
    print(f"  SIEM rule '{clone['rule_id']}': already exists — skipping")
except RuntimeError as e:
    if "404" not in str(e): raise
    kb("POST", "/api/detection_engine/rules", clone, ok=(200, 201))
        _manifest_add_kibana(SPACE_ID, "siem_rule", clone["rule_id"], name=clone["name"])  # D-039
    print(f"  SIEM rule '{clone['rule_id']}': created")
```

Teardown deletes cloned rules by `rule_id`. Elastic-managed originals are left untouched.

**13h — Workflows** *(when in scope and supported)*

Deploy workflows via `POST /api/workflows` with `{"workflows": [{"yaml": "<yaml string>"}]}`.
The correct endpoint is `/api/workflows` — NOT `/api/workchat/workflows` (which returns 404 on 9.4).
Workflow YAML must use `triggers:` (plural array), not `trigger:` (singular).
Always check `created[0].valid == true` in the response. See `references/kibana-api-registry.md` for full format details.

Every engagement with Agent Builder should also deploy `deploy/demo-refresh-workflow.yaml` — a manually triggered workflow that checks ML anomaly readiness and writes a status record. See step 13l below.

**13i — Cases configuration** *(when Security, Observability, or hybrid cases are in scope)*

**⚠ `configure` prerequisite (confirmed 9.4):** `POST /api/cases` returns `400` unless `POST /api/cases/configure` has been called first for each `owner`. Call it once per owner type BEFORE creating any cases:

```python
for owner in ["observability", "securitySolution", "cases"]:
    # GET first — returns [] (empty array) if never configured
    existing = kb("GET", f"/api/cases/configure?owner={owner}", ok=(200,))
    if existing and isinstance(existing, list) and len(existing) > 0:
        continue  # already configured
    kb("POST", "/api/cases/configure", {
        "connector":    {"id": "none", "name": "none", "type": ".none", "fields": None},
        "closure_type": "close-by-user",
        "owner":        owner,
    }, ok=(200, 201))
```

The `"type": ".none"` connector in the configure body is valid and means "no external connector attached". The `owner` must match the solution area of the space.

**13i — Probe-based feature detection** *(for optional capabilities — applies alongside D-033 version gate)*

`attempt_or_skip` is ONLY for probing whether optional tech-preview features exist on the cluster. It MUST NOT be used to swallow `400` errors on in-scope asset creation. A `400` means the payload is wrong — the script must halt and report the error so it can be fixed.

```python
def attempt_or_skip(label: str, fn) -> bool:
    """
    Use ONLY for optional tech-preview feature probes (GET 404/403).
    NEVER wrap in-scope asset creation (alerting rules, cases, agents, SLOs).
    Returns True if succeeded, False if skipped.
    400 errors re-raise — they indicate a bad payload, not a missing feature.
    """
    try:
        fn()
        return True
    except RuntimeError as e:
        code = str(e)[:3]
        if code in ("404", "403"):
            print(f"  ⚠ {label}: feature not available on this cluster — skipped (probe: {code})")
            return False
        # 400 = bad payload on our end — never silently skip, always halt
        raise

# Correct: probing optional features
available_workflows    = attempt_or_skip("Workflows",     lambda: kb("GET", "/api/workflows"))
available_agent_builder = attempt_or_skip("Agent Builder", lambda: kb("GET", "/api/agent_builder/agents"))

# WRONG — never wrap in-scope creates:
# attempt_or_skip("Alerting rule", lambda: create_rule(...))   ← DO NOT DO THIS
# attempt_or_skip("Cases",         lambda: create_case(...))   ← DO NOT DO THIS
```

This complements the version gate (D-033) — it catches feature-flag or license-level unavailability that version numbers don't predict. See `references/kibana-api-registry.md#attempt_or_skip` for full decision table. Reference: `hive-mind/patterns/deployment/SERVERLESS_FEATURE_DETECTION.md`.

**13j — Token Visibility dashboard** *(when Agent Builder is in scope and INCLUDE_TOKEN_VISIBILITY=true)*

Deploy the AI Cost + Usage dashboard from `skills/weave-cost/SKILL.md`.
Create the `{prefix}agent-sessions` index, load 30-60 seed session documents, and build
the ES|QL dashboard panels. This is a standard deliverable for any Agent Builder demo (D-036).

*13k — Other** *(streams, Fleet, synthetics, etc.)*  
If the platform audit and script call for them, add the matching API steps — do not assume
this list is exhaustive.

**13l — Demo Refresh Workflow + `refresh.py`** *(standard deliverable for any Agent Builder or ML engagement)*

Every engagement that includes Agent Builder or ML anomaly detection should include two refresh artifacts:

1. **`deploy/demo-refresh-workflow.yaml`** — A manually-triggered Kibana Workflow that checks ML anomaly readiness, key index health, and writes a status record to the `{prefix}agent-sessions` index. Scope the checks to the engagement's actual ML jobs and indices. Deploy in bootstrap step 13h alongside the other workflows. This is a demo deliverable — it shows Workflows capability to the customer.

2. **`deploy/refresh.py`** — A standalone Python script for pre-demo operational maintenance: anomaly re-injection, ELSER warmup, case timestamp refresh, session cleanup, and readiness summary table. Run 15–30 minutes before any demo. Generated once per engagement. Key flags: `--inject-anomaly`, `--skip-cases`, `--dry-run`.

**13m — Engagement tagging (`demobuilder:<id>`)** *(D-026 — REQUIRED on every create payload that has a `tags` field)*

**`merge_tags()` must be called on EVERY asset with a `tags` field.** This includes SLOs, alerting rules, Kibana Workflows, Cases, Agent Builder agents (labels field), Agent Builder ES|QL tools, ML job tags, and SIEM rule tags. The function is defined in bootstrap.py and must not be skipped:

```python
def merge_tags(existing):
    return sorted(set((existing or []) + [f"demobuilder:{_engagement_id()}"]))
```

Usage:
```python
# SLOs
"tags": merge_tags(["gpu", "operator", "demo"])

# Alerting rules
"tags": merge_tags(["llm-obs", "demo"])

# Workflows
"tags": merge_tags(["workflow", "demo"])

# Cases
"tags": merge_tags(["incident", "priority-1"])

# Agent Builder agent labels
"labels": merge_tags(["rag", "agent"])
```

Indices remain distinguished by `p(name)`. Saved objects should carry the tag in export or via follow-up tagging when the stack supports it.

**Example — saved objects import (multipart for NDJSON):**
```python
with open("kibana-objects/{slug}-dashboards.ndjson", "rb") as f:
    kb("POST", "/api/saved_objects/_import?overwrite=true", f, content_type="multipart/form-data")
```

If a required artifact type is missing for **this** engagement, **stop** and run the
corresponding skills to generate it; **do not** complete `bolt-launch` with “TODO: add in
Kibana” for an in-scope asset.

**Anomaly injection (step 14)**
Run the injection spec from `data/{slug}-ml-config.json`. Sleep `2 × bucket_span` after
injection before verifying anomaly scores:
```python
for entity in injection_plan["target_entities"]:
    # Generate skewed events for this entity during the anomaly period
    # Index via _bulk
    ...
print(f"  Anomaly injection complete. Waiting {2 * bucket_span_minutes}m for ML to process...")
time.sleep(bucket_span_seconds * 2)
```

**ELSER warm-up (step 15)**
```python
resp = es("POST", f"/{p(semantic_index)}/_search", {
    "query": {"semantic": {"field": "body_semantic", "query": "warmup"}}
})
latency = resp["took"]
print(f"  ELSER warm: {latency}ms {'✅' if latency < 2000 else '⚠️ slow — run again'}")
```

**Asset manifest — final write (step 16)**

After all steps complete successfully, do a final upsert of the manifest so it reflects
the full deployed state. This is the definitive copy teardown will read (D-039).

The manifest uses the **dynamic open-list schema** from `references/asset-manifest.md`.
Helpers `_manifest_add_es()` and `_manifest_add_kibana()` were called after each
resource creation step. The final write stamps `deployed_at`.

```python
def write_final_manifest():
    _manifest["deployed_at"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
    _manifest_push()
    print(f"  Manifest written: loom-manifests/{_engagement_id_for_tag()}")
```

The manifest is written incrementally after each step (partial deploys leave a valid
manifest for partial teardown). The final write closes out the `deployed_at` timestamp.

## Step 3b: Terraform Mode Generation (when `DEPLOY_MODE=terraform`)

When `.env` contains `DEPLOY_MODE=terraform`, generate HCL + `bootstrap-data.py` instead
of a single `bootstrap.py`. Read `references/terraform-patterns.md` for all HCL patterns.

**File layout:**
```
{slug}/deploy/
  providers.tf          # validated provider pins (elasticstack + ec)
  variables.tf          # variable declarations
  main.tf               # all Terraform resources (ILM/DSL, templates, indices, ML, Kibana, Agent Builder, Workflows)
  {slug}.tfvars         # engagement-specific values; no credentials
  bootstrap-data.py     # enrich execute, bulk ingest, ELSER warm, anomaly injection, manifest write
  .terraform.lock.hcl   # committed
```

**Step 0b — provider version validation (D-041):**
Before generating any HCL, check the latest provider releases via GitHub API and compare
against the planned pins. Report result. Confirm with SA before proceeding if a newer
version is available.

**Generate `providers.tf`:**
See `references/terraform-patterns.md#providers-tf` for the template.

**Generate `main.tf`:**
All Terraform-manageable resources from the data model, scoped to the engagement:
- ILM (ECH) or DSL block (Serverless) via `locals.use_dsl`
- Component templates, index templates, indices, data streams
- Ingest pipelines, enrich policies (create only — execution in `bootstrap-data.py`)
- ML jobs, datafeeds, job state
- ELSER inference endpoint (service conditional on deployment type)
- Kibana space, data views, connectors, alerting rules, SLOs, saved objects import
- Agent Builder tools, workflows, agents (`kibana_agentbuilder_*` resources — confirmed in provider)
- D-026 tagging via `locals.common_tags`
- Stable UUIDs via `uuidv5` for Kibana objects

**Generate `bootstrap-data.py`:**
Python for operations Terraform cannot perform:
1. Version gate 9.4+ and optional `user_settings_json` patch for new ECH deployments
2. Tech preview probe per space: `PUT /api/spaces/space/{id}` + GET probe for Agent Builder / Workflows; halt (not skip) if unavailable on a scope-required feature
3. Enrich policy execution + polling
4. Bulk seed data ingestion + `demo_critical_docs` individual verification (D-004)
5. Cases configure (per owner) + sample cases
6. ELSER warm-up inference call
7. Anomaly injection + sleep(2 × bucket_span)
8. D-039 manifest write (`_manifest_add_es` / `_manifest_add_kibana`)

**Hard gate before generating (D-038):**
```
if DEPLOY_MODE == "terraform":
    required = ["deploy/kibana-objects/{slug}-dashboards.ndjson", "deploy/bootstrap-data.py scaffold"]
    if any artifact is missing:
        HALT — do not generate main.tf
        instruct: "Author the missing NDJSON first using the kibana-dashboards skill"
```

**Terraform approval gate (D-024 compliant):**
`terraform plan` output is the approval artifact — cleaner and more auditable than reading Python.
Present the plan to the SA before running `terraform apply`.

**Execution:**
```bash
set -a && source {engagement_dir}/.env && set +a
cd {engagement_dir}/deploy
terraform init
terraform plan -var-file="{slug}.tfvars" -out="{slug}.tfplan"
# SA reviews plan ← D-024 gate
terraform apply "{slug}.tfplan"
python3 bootstrap-data.py
```

## Step 4: Execute the Script

Source the `.env` and run (Python mode):

```bash
set -a && source {engagement_dir}/.env && set +a
python3 {engagement_dir}/deploy/bootstrap.py
```

Stream output to the terminal so the SE can watch progress. Each step prints:
```
[Step 1/15] Connectivity check
  Connected: https://abc123.es.io:443
  Version:   9.3.1
  Prefix:    '' (none — using default index names)
  ✅ Done (0.4s)

[Step 2/15] ILM / Data Stream Lifecycle
  Serverless detected — using Data Stream Lifecycle
  ✅ Done (skipped)

[Step 3/15] Enrich policies
  store-location-enrich: created
  store-location-enrich: executing...
  store-location-enrich: complete (1.2s)
  ✅ Done (1.6s)
...
```

On completion:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 BOOTSTRAP COMPLETE — {Company}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Cluster:   {ES_URL}
 Duration:  {total_seconds}s
 Indices:   {N} created
 Documents: {N} loaded
 ML jobs:   {N} running
 Kibana:    {N} objects imported

 To re-run a step:     python3 deploy/bootstrap.py --step N
 To skip data reload:  python3 deploy/bootstrap.py --skip-data
 To verify:            python3 deploy/bootstrap.py --dry-run

 ⚠️  Pre-demo: clear test sessions 10 min before going live:
 POST /{slug}-sessions/_delete_by_query
   {"query":{"range":{"@timestamp":{"lt":"now-10m"}}}}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Step 4b: Post-Deploy Verification (run after every deployment)

After `terraform apply + bootstrap-data.py` (or `bootstrap.py` in Python mode) completes, verify runtime health — HTTP 200 at creation time is necessary but not sufficient. Assets can be stored but non-functional.

Run these checks in order. Log each result. If any check fails, fix it before handing off to the SA.

| Asset | Verification | Pass condition |
|---|---|---|
| **Elasticsearch cluster** | `GET /` | `status: green` or `yellow`; version ≥ 9.4 |
| **Data streams** | `GET /_data_stream/{prefix}*` | At least 1 doc per stream (for seeded streams) |
| **ELSER endpoint** | `POST /{semantic-idx}/_search` with semantic query | Responds in < 2000ms; no `503` |
| **ML jobs** | `GET /_ml/anomaly_detectors/{job_id}` | `state: opened` |
| **ML datafeeds** | `GET /_ml/datafeeds/datafeed-{job_id}` | `state: started` |
| **Dashboards** | `GET /api/saved_objects/_find?type=dashboard` in target space | Returns N dashboards (N = number authored) |
| **Data views** | `GET /api/data_views` in each space | Returns N data views matching script references |
| **Agent Builder** | `GET /api/agent_builder/agents/{id}` in target space | Agent exists; `skill_ids` and `tool_ids` populated |
| **SLOs** | `GET /api/observability/slos/{id}` | `summary.status: NO_DATA` or `HEALTHY` (not `404`) |
| **Alerting rules** | `GET /api/alerting/rules/_find` | Rules exist and `enabled: true` |
| **Workflows** | `GET /api/workflows` | Workflows listed; `valid: true` |
| **Asset manifest** | `GET /loom-manifests/_doc/{engagement_id}` | Document exists; `deployed_at` set |

**Dashboard editability check (critical — prevents the "dashboards are empty/uneditable" failure mode):**
After dashboard deploy via `kibana-dashboards.js`, navigate to one panel in Kibana and confirm:
1. Panel renders data (not "No results found" or "Unknown column" ES|QL errors)
2. Panel can be opened in edit mode without errors
3. Every ES|QL query references field names confirmed during the Step 2b integration probe (D-043)

If dashboards render empty or throw `verification_exception — Unknown column`: the field name in the query does not match the actual mapping. Re-run the integration probe (`GET /_component_template/<name>@package`) and correct the field reference.

## Step 5: Write the Deploy Log

`deploy/{slug}-deploy-log.md`:

```
# Deploy Log — {Company}
**Date:** {date} | **Duration:** {N}s | **Status:** ✅ Complete

## Environment
Cluster: {ES_URL}
Deployment type: {type}
Index prefix: {PREFIX or 'none'}

## What Was Created
| Resource | Name | Status |
|---|---|---|
[one row per created artifact]

## Seed Data
| Index | Documents loaded | Demo-critical docs verified |
|---|---|---|

## ML Jobs
| Job | Status | Last bucket | Anomaly score on target |
|---|---|---|---|

## Kibana Objects
| Type | Name | Status |
|---|---|---|

## To re-run (if something changed):
source {engagement_dir}/.env && python3 {engagement_dir}/deploy/bootstrap.py --skip-data
```

## Platform-Specific Adaptations

The script auto-adapts based on `DEPLOYMENT_TYPE` in the `.env`. **Baseline: 9.4+ (D-033).**
Clusters below 9.4 are rejected at step 1 unless `SKIP_VERSION_CHECK=true` is set.

| Behavior | Serverless | ECH 9.4+ |
|---|---|---|
| ILM | Skipped (DSL in template) | Created (hot-only by default, D-027) |
| ELSER inference | `service: "elser"` (managed, no model_id) | `service: "elastic"` via EIS (D-028) |
| ML node check | Skipped (auto-scaled) | Checked — anomaly detection only |
| Kibana Workflows | Supported | Supported 9.4+ (feature-flag check, D-011) |
| Agent Builder | Supported | Supported (feature-flag check, D-011) |
| Asset manifest | Written to cluster (D-031) | Written to cluster (D-031) |

## What Good Looks Like

**Clean first run:** All 15 steps succeed (step 13 covers every **in-scope** Kibana/Security/
Observability API the story needs — no manual UI follow-up for those). No existing resources
— everything created fresh. ELSER warms in < 2s when semantic search is in scope. ML anomaly
visible within 2 bucket spans when ML is in scope. Duration varies by scenario (simple search
demo vs. full hybrid Sec + Obs + agents).

**Idempotent re-run:** Bootstrap run again after a partial failure. Steps 1–7 skip
(resources exist), step 8 picks up (ELSER wasn't deployed). Remaining steps complete.
No duplicate data, no errors on existing resources.

**Multi-customer, same cluster:** Engagement A uses `INDEX_PREFIX=cb-`; engagement B uses
`INDEX_PREFIX=acme-`. Both sets of indices coexist. Each bootstrap only touches its own
prefixed resources.

**Prefix copy workflow:** (see `docs/engagements-path.md` — default root `~/engagements`)
```bash
ROOT="${DEMOBUILDER_ENGAGEMENTS_ROOT:-$HOME/engagements}"
cp "$ROOT/engagement-a/.env" "$ROOT/engagement-b/.env"
# Edit engagement-b/.env: DEMO_SLUG, ENGAGEMENT, INDEX_PREFIX for the new customer
set -a && source "$ROOT/engagement-b/.env" && set +a
python3 "$ROOT/engagement-b/deploy/bootstrap.py"
```
