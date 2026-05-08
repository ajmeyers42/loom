# Demo Environment Reference

**Canonical source of truth** for all `.env` variables. All fields listed here are read by `bootstrap.py` / `bootstrap-data.py` at runtime — never hardcoded in scripts.

**Two paths to a populated `.env`:**
- **New deployment** — `bolt-spin` writes all available endpoints directly from the provisioning API response.
- **Existing deployment** — `bolt-spin` generates a pre-filled `.env-sample` scoped to your `DEPLOYMENT_TYPE`. Fill in values and save as `.env`.

## .env File — All Fields

```bash
# ── Identity ──────────────────────────────────────────────
DEMO_SLUG=citizens-bank          # slug used for file naming throughout pipeline
ENGAGEMENT=Citizens Bank         # human-readable company name
DEPLOYMENT_TYPE=serverless       # serverless | ech | self_managed | docker

# ── Cluster Endpoints (written by bolt-spin) ──────────────────────────
# New deployment: written automatically from provisioning API response.
# Existing deployment: see "Found at" comments for each field.
ELASTICSEARCH_URL=https://abc123.es.io:443
# Found at (existing): Cloud console → deployment → Copy endpoint → Elasticsearch
KIBANA_URL=https://abc123.kb.io:443
# Found at (existing): Cloud console → deployment → Copy endpoint → Kibana

# APM Server URL — Serverless Oblt / ECH with APM server
# Found at (existing): Cloud console → deployment → APM & Fleet → APM endpoint
# APM_SERVER_URL=

# Managed OTLP endpoint — Serverless (all types) / ECH 8.16+
# Use as OTEL_EXPORTER_OTLP_ENDPOINT for EDOT agents and OTel SDKs.
# Found at (existing Serverless): Cloud console → project → Endpoints → OpenTelemetry endpoint
# Found at (existing ECH 8.16+): Kibana → Observability → Add Data → OpenTelemetry
# MANAGED_OTLP_URL=

# Fleet Server URL — Serverless Oblt/Security / ECH with Fleet
# Found at (existing): Kibana → Fleet → Settings → Fleet Server hosts
# FLEET_SERVER_URL=

# Fleet Enrollment Token — Serverless Oblt/Security / ECH with Fleet
# Found at (existing): Kibana → Fleet → Enrollment tokens → create or copy existing
# FLEET_ENROLLMENT_TOKEN=

# Logstash URL — ECH with Logstash only
# Found at (existing): Cloud console → deployment → Copy endpoint → Logstash
# LOGSTASH_URL=

# ── Cluster Credentials ───────────────────────────────────
ES_API_KEY=VuaCfGcBCdbkQm...     # base64-encoded API key or ApiKey header value

# ── Kibana API Key (D-016) ────────────────────────────────────────────────────────
# Use KIBANA_API_KEY for ALL Kibana asset operations: Agent Builder, Workflows,
# Dashboards, Connectors, Saved Objects import. Do NOT use ES_API_KEY for Kibana APIs.
# Set this at provisioning time alongside ES_API_KEY.
KIBANA_API_KEY=

# Kibana Space — written by bolt-spin / bootstrap.py ensure_kibana_space().
# Set to /s/{DEMO_SLUG} for per-engagement asset isolation; leave blank for default Space only.
# All bootstrap Kibana API calls (saved objects, SLOs, Agent Builder, Workflows) target this Space.
# wind-pulse checks the space exists and warns if KIBANA_SPACE_PATH is unset.
KIBANA_SPACE_PATH=

# Kibana solution type — used when creating the Kibana space.
# es | oblt | security — match to the engagement's primary solution area.
KIBANA_SOLUTION=es

# ── ECH Deployment Pre-flight (Step 0) ───────────────────
# Optional. If set, bootstrap.py patches Kibana user_settings_json via the ECH
# Management API *before* the space is created — enabling Workflows and other
# deployment-level feature flags without a manual ECH-UI step + re-run.
# EC_API_KEY:    Elastic Cloud org-level API key (cloud.elastic.co → Account → API Keys)
# DEPLOYMENT_ID: found in the ECH URL  .../deployments/{DEPLOYMENT_ID}
# KIBANA_REF_ID: defaults to "main-kibana" — only override if the deployment uses a custom ref_id
# EC_API_KEY=
# DEPLOYMENT_ID=
# KIBANA_REF_ID=main-kibana

# ── Version (informational, set by bolt-spin) ──
# Must match live cluster version (D-020). Run: curl -s -H "Authorization: ApiKey $ES_API_KEY" $ELASTICSEARCH_URL | python3 -m json.tool | grep '"number"'
ELASTIC_VERSION=9.4.0

# ── Deploy Mode (D-038) ────────────────────────────────────
# python (default) — generated bootstrap.py drives all resource creation
# terraform — generated main.tf + bootstrap-data.py; requires terraform CLI
DEPLOY_MODE=python

# ── Index Namespace ───────────────────────────────────────
# Leave blank for isolated clusters (default — recommended)
# Set a short prefix when sharing a cluster across multiple demos
# Example: INDEX_PREFIX=cb-  →  fraud-claims becomes cb-fraud-claims
INDEX_PREFIX=

# ── Loom tagging (D-026) ────────────────────────────
# Optional. Overrides the engagement id used in loom:<id> tags on SLOs, rules, ML jobs,
# Agent Builder, etc. If unset, the id is derived from INDEX_PREFIX (normalized) or DEMO_SLUG.
# DEMO_ASSET_TAG=

# ── Token Visibility (D-036) ───────────────────────────────
# Set to false to skip AI Cost + Usage dashboard in Agent Builder demos.
# INCLUDE_TOKEN_VISIBILITY=true

# ── Reference Repo Path Overrides (optional) ──────────────
# Override default local clone paths for reference repos. See reference-repos.md.
# HIVE_MIND_PATH=../hive-mind
# WORKFLOWS_REPO_PATH=~/Documents/GitHub/workflows
# AGENT_BUILDER_SDK_PATH=~/Documents/GitHub/kibana-agent-builder-sdk
# VULCAN_PATH=../vulcan

# ── Cluster Metadata (informational) ──────────────────────
CLUSTER_NAME=loom-citizens-bank-20260415
REGION=us-east-1
PROVISIONED_BY=loom
```

---

## Endpoint Availability by Deployment Type

| Endpoint var | Serverless ES | Serverless Oblt | Serverless Security | ECH 8.16+ |
|---|:---:|:---:|:---:|:---:|
| `ELASTICSEARCH_URL` | ✅ | ✅ | ✅ | ✅ |
| `KIBANA_URL` | ✅ | ✅ | ✅ | ✅ |
| `APM_SERVER_URL` | — | ✅ | — | ✅ if APM node |
| `MANAGED_OTLP_URL` | ✅ | ✅ | ✅ | ✅ (8.16+) |
| `FLEET_SERVER_URL` | — | ✅ | ✅ | ✅ if Fleet node |
| `FLEET_ENROLLMENT_TOKEN` | — | ✅ | ✅ | ✅ if Fleet node |
| `LOGSTASH_URL` | — | — | — | ✅ if Logstash node |

## Multi-Customer Workflow

### New cluster per demo (recommended for isolation)

```bash
# Each demo gets its own cluster — no prefix needed ($LOOM_ENGAGEMENTS_ROOT set)
$LOOM_ENGAGEMENTS_ROOT/
├── {slug-A}/.env    → https://cluster-A.es.io  INDEX_PREFIX=
├── {slug-B}/.env    → https://cluster-B.es.io  INDEX_PREFIX=
└── {slug-C}/.env    → https://cluster-C.es.io  INDEX_PREFIX=
```

### Shared cluster (when you want to conserve cloud spend)

```bash
# One cluster, all demos on it — prefix separates namespaces
$LOOM_ENGAGEMENTS_ROOT/
├── {slug-A}/.env    → https://shared.es.io  INDEX_PREFIX=a-
├── {slug-B}/.env    → https://shared.es.io  INDEX_PREFIX=b-
└── {slug-C}/.env    → https://shared.es.io  INDEX_PREFIX=c-

# Copy workflow for a new demo on the same cluster:
ROOT="${LOOM_ENGAGEMENTS_ROOT:-$HOME/engagements}"
cp "$ROOT/{slug-A}/.env" "$ROOT/{slug-B}/.env"
# Then edit {slug-B}/.env:
#   DEMO_SLUG={slug-B}
#   ENGAGEMENT={Company B}
#   INDEX_PREFIX=b-
```

### Prefix behavior

When `INDEX_PREFIX=cb-` is set, bootstrap.py applies it everywhere:
- Index names: `fraud-claims` → `cb-fraud-claims`
- Pipeline names: `fraud-ingest-pipeline` → `cb-fraud-ingest-pipeline`
- Template names: `fraud-template` → `cb-fraud-template`
- ML job IDs: `fraud-sla-monitor` → `cb-fraud-sla-monitor`
- Kibana index patterns: automatically updated in saved objects on import

The demo script ES|QL queries also need updating when a prefix is in use — bootstrap.py
patches the query strings in the Kibana saved objects before import.

## .env.example Template

This file is safe to commit — it documents requirements without exposing credentials.
`bolt-spin` generates a deployment-type-scoped version automatically.
Every workspace should have one alongside the `.env`:

```bash
# .env.example — copy to .env and fill in values
# See: skills/bolt-launch/references/env-reference.md
# Generated by: bolt-spin

DEMO_SLUG=<slug-e.g.-citizens-bank>
ENGAGEMENT=<company-name>
DEPLOYMENT_TYPE=<serverless|ech|self_managed|docker>
DEPLOY_MODE=python   # python | terraform

# D-020: must match live cluster version
# Run: curl -s -H "Authorization: ApiKey $ES_API_KEY" $ELASTICSEARCH_URL | python3 -m json.tool | grep '"number"'
ELASTIC_VERSION=<e.g.-9.4.0>

# ── Required endpoints ────────────────────────────────────
ELASTICSEARCH_URL=<https://your-cluster.es.io:443>
# Found at: Cloud console → deployment → Copy endpoint → Elasticsearch
KIBANA_URL=<https://your-kibana.kb.io:443>
# Found at: Cloud console → deployment → Copy endpoint → Kibana

# ── Optional endpoints (populated for relevant deployment types) ──────────
# APM_SERVER_URL=<https://...>
# Found at: Cloud console → deployment → APM & Fleet → APM endpoint  [Serverless Oblt / ECH with APM]

# MANAGED_OTLP_URL=<https://...>
# Found at: Cloud console → project → Endpoints → OpenTelemetry endpoint  [Serverless]
#           Kibana → Observability → Add Data → OpenTelemetry  [ECH 8.16+]

# FLEET_SERVER_URL=<https://...>
# Found at: Kibana → Fleet → Settings → Fleet Server hosts  [Serverless Oblt/Security / ECH with Fleet]

# FLEET_ENROLLMENT_TOKEN=<token>
# Found at: Kibana → Fleet → Enrollment tokens  [Serverless Oblt/Security / ECH with Fleet]

# LOGSTASH_URL=<https://...>
# Found at: Cloud console → deployment → Copy endpoint → Logstash  [ECH with Logstash only]

# ── Credentials ──────────────────────────────────────────
ES_API_KEY=<your-es-api-key>
KIBANA_API_KEY=<your-kibana-api-key>   # Required — do NOT use ES_API_KEY for Kibana APIs (D-016)

KIBANA_SPACE_PATH=/s/<DEMO_SLUG>
KIBANA_SOLUTION=es   # es | oblt | security

INDEX_PREFIX=<optional-e.g.-cb->
# DEMO_ASSET_TAG=<optional-override-for-loom:-tags>
# INCLUDE_TOKEN_VISIBILITY=true

CLUSTER_NAME=<loom-slug-YYYYMMDD>
REGION=<e.g.-us-east-1>
PROVISIONED_BY=loom
```

## API Key Permissions Required

The `ES_API_KEY` must have at minimum:

```json
{
  "cluster": ["monitor", "manage_ilm", "manage_ingest_pipelines", "manage_ml",
              "manage_enrich", "manage_index_templates"],
  "indices": [{ "names": ["*"], "privileges": ["all"] }],
  "applications": [{ "application": "kibana-.kibana", "privileges": ["all"],
                     "resources": ["*"] }]
}
```

For serverless: the project API key created at provisioning time has sufficient scope.
For ECH/self-managed: create a dedicated key with the above privileges — do not use
the `elastic` superuser key for bootstrap scripts.
