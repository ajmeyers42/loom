---
name: bolt-ech
description: >
  ECH (Elastic Cloud Hosted) deployment variant for bolt-bootstrap. Generates
  Terraform HCL targeting the elasticstack provider for all infrastructure resources and
  bootstrap-data.py for data operations only. Terraform-first (D-038). Targets 9.4+
  ECH clusters.
---

# Demo Bootstrap — ECH Variant

You are generating Terraform HCL and bootstrap-data.py for an ECH deployment.
Read `references/terraform-patterns.md` and `references/feature-compatibility.md` now
before writing any resource. Every pattern comes from those reference files — not memory.

**ECH-specific rules (all sourced from `references/` files):**
- ILM policies: use `elasticstack_elasticsearch_index_lifecycle` resource
- Inference (ELSER): `service: "elastic"` with `model_id: ".elser-2"` (EIS) — see `references/inference-config.md`
- Kibana dashboards: use `elasticstack_kibana_dashboard` resource (9.4+ declarative API)
- Agent Builder: `elasticstack_kibana_agentbuilder_agent`, `elasticstack_kibana_agentbuilder_tool` (D-040)
- Workflows: `elasticstack_kibana_agentbuilder_workflow` (D-040)
- Kibana space: `elasticstack_kibana_space` with `disabled_features = []` and `solution` variable (D-029)
- ML jobs: `elasticstack_elasticsearch_ml_job` + `elasticstack_elasticsearch_ml_datafeed` with lifecycle resources for open/start state

## Step 1: Read Reference Files

Before writing any HCL, read:
```
skills/bolt-launch/references/terraform-patterns.md    ← ECH HCL patterns
skills/bolt-launch/references/feature-compatibility.md ← version-specific behavior
skills/bolt-launch/references/inference-config.md      ← ELSER/EIS config for ECH
skills/bolt-launch/references/kibana-api-registry.md   ← API shapes (used in bootstrap-data.py)
skills/bolt-launch/references/pipeline-constants.md    ← thresholds, UUID5 namespace, header values
skills/bolt-launch/references/asset-manifest.md        ← D-039 manifest helpers
```

## Step 2: Generate `deploy/providers.tf`

```hcl
terraform {
  required_providers {
    elasticstack = {
      source  = "elastic/elasticstack"
      version = "~> {CURRENT_VERSION}"  # from references/reference-repos.md
    }
    ec = {
      source  = "elastic/ec"
      version = "~> {CURRENT_VERSION}"  # from references/reference-repos.md — only if provisioning
    }
  }
}

provider "elasticstack" {
  elasticsearch {
    endpoints = [var.elasticsearch_url]
    api_key   = var.es_api_key
  }
  kibana {
    endpoints = [var.kibana_url]
    api_key   = var.kibana_api_key
  }
}
```

## Step 3: Generate `deploy/{slug}.tfvars`

Source all values from `.env` and `asset-bundle/asset-index.json`. Never hardcode credentials:
```hcl
elasticsearch_url = ""  # from ELASTICSEARCH_URL in .env
kibana_url        = ""  # from KIBANA_URL in .env
es_api_key        = ""  # from ES_API_KEY in .env — sensitive, use TF_VAR_ env var
kibana_api_key    = ""  # from KIBANA_API_KEY in .env — sensitive, use TF_VAR_ env var
index_prefix      = ""  # from INDEX_PREFIX in .env
demo_slug         = ""  # from DEMO_SLUG in .env
kibana_solution   = ""  # from KIBANA_SOLUTION in .env
bootstrap_version = ""  # from BOOTSTRAP_VERSION constant
engagement_tag    = ""  # demobuilder:{engagement_id} — from D-026 formula
```

## Step 4: Generate `deploy/main.tf`

Process `asset-bundle/asset-index.json` entries in build-order from `asset-bundle/asset-schema.json`.
For each entry, generate the appropriate Terraform resource. Use patterns from `references/terraform-patterns.md`.

### Resource ordering (dependencies must come first)
1. Kibana space
2. ILM policies (ECH only — skip on Serverless)
3. Component templates
4. Index templates (reference ILM policy)
5. Indices and data streams (reference index templates)
6. Inference endpoints (ELSER via EIS)
7. Ingest pipelines
8. Enrich policies (create only; execution in bootstrap-data.py)
9. ML jobs + datafeeds
10. Kibana connectors
11. Alerting rules + SLO burn-rate rules
12. Data views
13. Dashboards (reference data views)
14. SLOs
15. Agent Builder tools
16. Agent Builder agents (reference tools)
17. Workflows (reference connectors)
18. SIEM detection rules

### Tagging contract (D-026)
Every Terraform resource that accepts `tags` (or equivalent) must include:
```hcl
tags = concat(
  ["demobuilder:${var.engagement_tag}"],
  var.additional_tags
)
```
Define `additional_tags = []` in tfvars as an extension point.

### Stable UUIDs
All Kibana saved object IDs use `uuid5(NS, "${var.demo_slug}:{asset_name}")` from
`references/pipeline-constants.md` UUID5 namespace. This ensures idempotent re-deploy.

### ILM (ECH hot-only default — D-027)
```hcl
resource "elasticstack_elasticsearch_index_lifecycle" "main" {
  name = "${var.index_prefix}main-policy"
  hot {
    set_priority { priority = 100 }
  }
  delete {
    min_age = "90d"
    delete {}
  }
}
```
Add warm/cold/frozen phases only when explicitly required by the engagement. Never add
`rollover` to plain index ILM policies.

## Step 5: Generate `deploy/bootstrap-data.py`

Read `skills/bolt-launch/templates/bootstrap-template.py` as the base structure.
Fill in engagement-specific values. Operations list (D-046 — nothing else):

```python
#!/usr/bin/env python3
"""
bootstrap-data.py — {Company} ({slug})
Generated: {date} | Deployment: ECH {version}
Data operations ONLY. Infrastructure is managed by Terraform (main.tf).

Operations: enrich execute, seed data, field validation, ELSER warmup,
anomaly injection, manifest write.

Usage:
  python3 bootstrap-data.py              # run all operations
  python3 bootstrap-data.py --dry-run    # print what would run, no API calls
  python3 bootstrap-data.py --step N     # resume from step N
"""
import os, sys, json, time, argparse, re, uuid
import urllib.request, urllib.error

BOOTSTRAP_VERSION = "{version}"  # D-030 — bump on any structural change

# ── Credentials ──────────────────────────────────────────────────────────────
ES_URL   = os.environ.get("ELASTICSEARCH_URL", "").rstrip("/")
KB_URL   = os.environ.get("KIBANA_URL", "").rstrip("/")
API_KEY  = os.environ.get("ES_API_KEY", "")
KB_KEY   = os.environ.get("KIBANA_API_KEY", "")
DEP_TYPE = os.environ.get("DEPLOYMENT_TYPE", "ech")
PREFIX   = os.environ.get("INDEX_PREFIX", "")
SLUG     = os.environ.get("DEMO_SLUG", "demo")

def p(name): return f"{PREFIX}{name}" if PREFIX else name

# ── Engagement tag (D-026) ────────────────────────────────────────────────────
def _engagement_id_for_tag() -> str:
    override = os.environ.get("DEMO_ASSET_TAG", "").strip()
    raw = override or (PREFIX.strip() if PREFIX.strip() else SLUG)
    return re.sub(r"[-_\s]+", "", raw).lower() or "demo"

def loom_tags() -> list: return [f"demobuilder:{_engagement_id_for_tag()}"]
def merge_tags(existing): return sorted(set((existing or []) + loom_tags()))

# ── HTTP helpers ──────────────────────────────────────────────────────────────
def es(method, path, body=None, *, ok=(200, 201)):
    url = f"{ES_URL}{path}"
    headers = {"Authorization": f"ApiKey {API_KEY}", "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code not in ok:
            raise RuntimeError(f"ES {method} {path} → {e.code}: {e.read().decode()[:300]}")
        return json.loads(e.read()) if e.code in (200, 201) else {}

# ── D-033 Version gate ─────────────────────────────────────────────────────
def step1_connectivity():
    resp = es("GET", "/")
    version = resp["version"]["number"]
    print(f"  Connected: {ES_URL} | Version: {version}")
    major, minor = (int(x) for x in version.split(".")[:2])
    if (major, minor) < (9, 4) and os.environ.get("SKIP_VERSION_CHECK", "").lower() != "true":
        print(f"  ⛔ Version {version} below 9.4 baseline (D-033). Set SKIP_VERSION_CHECK=true to override.")
        sys.exit(1)
    env_ver = os.environ.get("ELASTIC_VERSION", "").strip()
    if env_ver and env_ver != version:
        print(f"  ⚠  ELASTIC_VERSION in .env ({env_ver}) != cluster ({version}) — update .env (D-020)")
    _manifest_init(); _ensure_manifest_index()
    _manifest["es_version"] = version; _push_manifest()

# ── D-039 Dynamic manifest ────────────────────────────────────────────────────
MANIFEST_INDEX = "loom-manifests"
_manifest = {"engagement_id": _engagement_id_for_tag(), "slug": SLUG,
             "bootstrap_version": BOOTSTRAP_VERSION,
             "assets": {"elasticsearch": [], "kibana": {"by_space": {}}}}

def _manifest_init(): pass  # initialised above
def _ensure_manifest_index():
    try: es("HEAD", f"/{MANIFEST_INDEX}", ok=(200,))
    except: es("PUT", f"/{MANIFEST_INDEX}", {"settings": {"number_of_shards": 1, "number_of_replicas": 0}})

def _manifest_add_es(type_, id_, **meta):
    _manifest["assets"]["elasticsearch"].append({"type": type_, "id": id_, **meta})

def _manifest_add_kibana(space_id, type_, id_, **meta):
    _manifest["assets"]["kibana"]["by_space"].setdefault(space_id, [])
    _manifest["assets"]["kibana"]["by_space"][space_id].append({"type": type_, "id": id_, **meta})

def _push_manifest():
    eid = _manifest["engagement_id"]
    es("PUT", f"/{MANIFEST_INDEX}/_doc/{eid}", _manifest, ok=(200, 201))

# ── D-044 Field population assertion ─────────────────────────────────────────
def assert_viz_fields_populated(index, viz_fields):
    total = es("GET", f"/{index}/_count")["count"]
    for field in viz_fields:
        n = es("POST", f"/{index}/_count", {"query": {"exists": {"field": field}}})["count"]
        if n < total:
            raise RuntimeError(
                f"SEED VALIDATION FAIL [{index}.{field}]: "
                f"{total - n}/{total} docs have null — fix seed data before deploying vizzes (D-044)"
            )
    print(f"  ✅ {index}: all {len(viz_fields)} viz-queried fields populated across {total} docs")

# ── Step implementations (engagement-specific content below) ─────────────────
def step2_enrich_execute(): ...   # POST /_enrich/policy/{name}/_execute + poll
def step3_seed_data(): ...        # bulk index from asset-bundle/elasticsearch/seed/
def step4_assert_viz_fields(): ...# call assert_viz_fields_populated() per custom index
def step5_elser_warmup(): ...     # warm inference endpoint with test query
def step6_anomaly_injection(): ...# inject anomaly docs (if ML in scope)
def step7_manifest_write(): _push_manifest()

STEPS = [
    (1, "Connectivity + version gate + manifest init", step1_connectivity),
    (2, "Enrich policy execution",                      step2_enrich_execute),
    (3, "Seed data loading",                            step3_seed_data),
    (4, "Viz field population assertions (D-044)",      step4_assert_viz_fields),
    (5, "ELSER endpoint warmup",                        step5_elser_warmup),
    (6, "Anomaly injection",                            step6_anomaly_injection),
    (7, "Manifest write (D-039)",                       step7_manifest_write),
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--step", type=int, default=1)
    args = parser.parse_args()
    for n, label, fn in STEPS:
        if n < args.step: continue
        print(f"\n── Step {n}: {label}")
        if args.dry_run: print("  [dry-run — skipping]"); continue
        fn()
    print("\n✅ bootstrap-data.py complete")
```

Fill in the engagement-specific implementations for steps 2–6 from the asset-bundle seed files
and `data/{slug}-data-model.json`.
