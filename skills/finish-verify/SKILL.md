---
name: finish-verify
description: >
  Agent A of the two-stage deployment pipeline. Probes the target cluster to confirm what
  already exists (schemas, packages, managed assets), then calls the appropriate
  elastic/agent-skills and hive-mind skills to author syntactically correct, version-accurate
  asset definitions. Outputs an asset-bundle/ directory containing all verified artifacts
  ready for bolt-bootstrap. No custom API code is written here — skills author
  assets; this skill orchestrates them.

  ALWAYS use this skill when the user says "verify assets", "build the asset bundle",
  "run asset verification", or when the orchestrator reaches Stage 8 (deploy preparation).
  This skill MUST complete before bolt-bootstrap runs — bootstrap-generator
  requires asset-bundle/asset-schema.json as a mandatory input (D-045).
---

# Demo Asset Verifier

You are the verification and authoring gate between the planning pipeline and deployment.
Your job is to confirm what already exists on the target cluster, then produce a complete
`asset-bundle/` of validated, version-accurate asset definitions by calling the appropriate
elastic/agent-skills and hive-mind skills. You do not write raw API code.

**This skill enforces D-043, D-045.** No asset is authored without confirmed schema.
No deployment proceeds without this skill's output.

## Prerequisites

Before starting, confirm these exist in `{engagement_dir}`:
- `.env` with `ELASTICSEARCH_URL`, `KIBANA_URL`, `ES_API_KEY`, `KIBANA_API_KEY`, `DEPLOYMENT_TYPE`
- `demo/{slug}-demo-script.md`
- `data/{slug}-data-model.json`
- `demo/{slug}-platform-audit.json`

If `.env` is missing: stop and tell the SA to run `bolt-spin` first.
If any of the pipeline outputs are missing: run the appropriate upstream stage first.

---

## Step 0: Version Gate and Platform Fingerprint (D-020, D-033)

```
GET /                     → confirmed_version, deployment_type_hint
GET {kibana}/api/status   → kibana_version, kibana_status
```

Write to `asset-bundle/asset-schema.json`:
```json
{
  "slug": "{slug}",
  "generated_at": "{ISO-8601}",
  "platform": {
    "es_version": "{confirmed_version}",
    "kibana_version": "{kibana_version}",
    "deployment_type": "{DEPLOYMENT_TYPE from .env}",
    "version_gate_passed": true
  }
}
```

**Version gate (D-033):** If `es_version` < 9.4 and `SKIP_VERSION_CHECK` is not set, halt:
```
⛔ Cluster version {version} is below the 9.4 baseline (D-033).
   Update the cluster or set SKIP_VERSION_CHECK=true in .env to override.
```

If version gate passes, continue. The `asset-schema.json` file gates all subsequent steps —
`bolt-bootstrap` will not run without it.

---

## Step 1: Mandatory Probe Sequence (D-043 Rule 3)

Run all probes that apply to this engagement's scope. Record results in `asset-bundle/asset-schema.json`.
**No asset is authored until this step completes.** If a probe fails with an unexpected error, halt and report before proceeding.

### 1a: Installed Fleet packages and their assets

Run for every package referenced in the data model or demo script:
```
GET /api/fleet/epm/packages/{package_name}
GET /api/fleet/epm/packages/{package_name}/assets
```

For each package, record in `asset-schema.json`:
```json
"fleet_packages": {
  "{package_name}": {
    "version": "...",
    "installed": true,
    "ships": {
      "dashboards": ["id1", "id2"],
      "ml_jobs": ["job_id1"],
      "detection_rules": ["rule_id1"],
      "data_views": ["data_view_id1"],
      "ingest_pipelines": ["pipeline_id1"]
    }
  }
}
```

**D-032 gate:** Any asset class that a package ships is a managed asset. Do NOT author a custom
replacement for these in Step 2. Record them in `asset-bundle/asset-index.json` as `source: "package"`.

### 1b: Integration stream schemas

For every `logs-*` or `metrics-*` data stream in the data model:
```
GET /_component_template/{integration}.{dataset}@package
GET /_data_stream/{stream_name}
```

Record confirmed field names in `asset-schema.json`:
```json
"confirmed_schemas": {
  "{stream_name}": {
    "source": "package_component_template",
    "fields": ["@timestamp", "host.name", "event.dataset", ...]
  }
}
```

**If the component template does not exist:** the stream is Path B (managed template) or custom.
Record `"source": "managed_template"` or `"source": "custom"` and proceed to 1c.

### 1c: Custom index schemas

For every custom index in the data model:
```
GET /{index}/_mapping
```

If the index does not yet exist (new engagement), record `"source": "data_model_spec"` and use
the field list from `data/{slug}-data-model.json` as the authoritative schema source.

### 1d: Existing Kibana assets

Run these probes to prevent re-authoring what already exists:
```
GET /api/observability/slos                                          → existing SLOs
GET /api/ml/anomaly_detectors                                        → existing ML jobs
GET /api/saved_objects/_find?type=visualization&fields=id,title      → existing vizzes
GET /api/saved_objects/_find?type=dashboard&fields=id,title          → existing dashboards
GET /api/detection_engine/rules/_find?filter=alert.attributes.enabled:true  → existing rules
```

### 1e: Feature availability probes (D-011)

```
GET /api/agent_builder/agents      → 404 means Agent Builder not enabled
GET /api/agent_builder/skills      → enumerate available platform skills (D-029)
GET /api/workflows                 → 404 means Workflows not enabled
```

Record:
```json
"feature_flags": {
  "agent_builder": true,
  "workflows": true,
  "agent_builder_skill_ids": ["data-exploration", "visualization-creation"]
}
```

**If a feature is not enabled but is in scope:** surface as a blocker before Step 2.
Do not author assets for a disabled feature.

### 1f: ML field names on Serverless (D-012)

If `DEPLOYMENT_TYPE=serverless` and ML scenes are in the demo script:
```
GET .ml-anomalies-*/_mapping
```
Record actual field names. These override any field names from prior loom sessions.

### Write final asset-schema.json

After all probes, write the complete `asset-bundle/asset-schema.json`. This file is the
single source of truth for Step 2. Every field referenced in any authored asset must exist
in this schema.

Announce completion:
```
✅ Step 1 complete — asset-schema.json written
   Confirmed schemas: {N} indices / streams
   Fleet packages: {package list}
   Existing managed assets: {summary}
   Feature flags: Agent Builder={bool}, Workflows={bool}
```

---

## Step 2: Author Assets via Skill Dispatch (D-007, D-017, D-032, D-047)

For each asset class in scope, call the appropriate skill. **Do not write raw API code.**
Pass `asset-bundle/asset-schema.json` as a required input to every skill call so field
references are validated against confirmed schema.

### Skill dispatch table

| Asset class | Skill to call | hive-mind context to pass |
|---|---|---|
| Kibana dashboards, Lens panels | `kibana/kibana-dashboards` | `hive-mind/patterns/dashboards/DASHBOARD_NDJSON_FORMAT.md` |
| Vega / Vega-Lite visualizations | `kibana/kibana-vega` | — |
| Observability SLOs | `observability/manage-slos` | — |
| Alerting rules (inc. SLO burn-rate) | `kibana/kibana-alerting-rules` | — |
| Kibana connectors | `kibana/kibana-connectors` | — |
| Agent Builder agents + tools | `kibana/agent-builder` | `hive-mind/patterns/agent-builder/AGENT_BUILDER_API_MANAGEMENT.md` |
| Workflow YAML authoring | `hive-workflows` | `hive-mind/patterns/workflows/WORKFLOWS_API_REFERENCE.md` + `WORKFLOW_YAML_STEP_TYPES.md` |
| SIEM detection rules | `security/detection-rule-management` | — |
| Security sample data | `security/generate-security-sample-data` | — |
| ES|QL query validation | `elasticsearch/elasticsearch-esql` | — |
| Bulk seed data loading | `elasticsearch/elasticsearch-file-ingest` | — |

**Before calling any dashboard skill:** check `asset-schema.json` `existing_assets.dashboards`.
If an equivalent dashboard already exists (same index pattern, similar panels), prefer embedding
the existing dashboard rather than re-creating it.

**Before calling any SLO skill:** check `asset-schema.json` `existing_assets.slos`.
Embed existing SLOs via `slo_overview` / `slo_burn_rate` panel types in custom dashboards
rather than creating duplicate SLOs.

**Before calling the security/detection-rule-management skill:** check `asset-schema.json`
`fleet_packages.{package}.ships.detection_rules`. For any rule a package already ships,
use the D-032 clone pattern (the skill implements this natively) — do not author a parallel
custom rule for the same signal.

### Output contract for each skill call

Each skill call must produce one or more files in `asset-bundle/`:

```
asset-bundle/
  kibana/
    dash-{name}.json          ← dashboard API payloads (POST /api/dashboards)
    ndjson-{name}.ndjson      ← saved objects NDJSON for import (8.x fallback only)
  observability/
    slo-{name}.json           ← SLO API payloads
  security/
    rule-{name}.json          ← detection rule JSON (custom or cloned)
    sample-data-{name}.json   ← security sample event documents
  alerting/
    rule-{name}.json          ← alerting rule API payloads
  connectors/
    connector-{name}.json     ← connector API payloads
  agent-builder/
    agent-{name}.json         ← Agent Builder agent + tools API payloads
  workflows/
    workflow-{name}.yaml      ← Workflow YAML
  elasticsearch/
    mapping-{index}.json      ← index mappings (from data model)
    pipeline-{name}.json      ← ingest pipeline processor chains
    seed/
      {index}-seed.json       ← seed document arrays
  asset-schema.json           ← written in Step 1 (do not overwrite; append only)
  asset-index.json            ← inventory of all authored assets (written at end of Step 2)
```

### asset-index.json format

```json
{
  "slug": "{slug}",
  "generated_at": "{ISO-8601}",
  "assets": [
    {
      "type": "dashboard",
      "id": "{stable-uuid5}",
      "name": "{human name}",
      "file": "asset-bundle/kibana/dash-main.json",
      "source": "authored",
      "deployment_method": "kibana_api",
      "scene": "Scene 2 — Claims Overview"
    },
    {
      "type": "slo",
      "id": "{existing-slo-id}",
      "name": "{slo name}",
      "file": null,
      "source": "package",
      "deployment_method": "existing_reference",
      "note": "Shipped by kubernetes package — referenced by ID in custom dashboard"
    }
  ]
}
```

`deployment_method` values:
- `kibana_api` — deployed via Kibana API in Terraform or bootstrap-data.py
- `terraform_resource` — deployed as a Terraform resource
- `existing_reference` — already exists on cluster; referenced by ID; not re-deployed
- `ndjson_import` — imported via saved objects API (fallback only)

---

## Step 3: ES|QL Validation Gate (D-025)

After all assets are authored, call `elasticsearch/elasticsearch-esql` skill to validate
every ES|QL query that appears in:
- Dashboard panels (ES|QL text-based layers)
- Agent Builder tool bodies
- Alerting rule queries
- `demo/{slug}-demo-script.md` script query blocks

For each query:
1. Run it against the live cluster
2. Confirm it returns results (or expected empty set for parameterized queries)
3. Record `validation_status: "passed"` or `"failed"` in `asset-index.json`

**Any `validation_status: "failed"` query blocks the corresponding asset from deployment.**
Surface failures to the SA with the actual error before proceeding.

---

## Step 4: Field Population Pre-check (D-044)

For every custom index in the data model, before writing the seed file:

1. Inventory every field used in a visualization query (from dashboard and agent tool assets authored in Step 2)
2. Confirm each field is in `asset-schema.json` `confirmed_schemas.{index}.fields`
3. Confirm each field will be non-null in every seed document (check `data/{slug}-data-model.json` field population checklist from Step 4)
4. Record the result in `asset-index.json`:

```json
{
  "type": "field_population_check",
  "index": "{index}",
  "viz_queried_fields": ["risk_label", "entity_type", "risk_score"],
  "all_non_null_confirmed": true
}
```

**If `all_non_null_confirmed: false`:** halt and report to the SA. Do not proceed to Step 5.
This is a no-go blocker for `bolt-bootstrap`.

---

## Step 5: Write Handoff Summary

Announce the asset bundle is ready:

```
✅ finish-verify complete

asset-bundle/ → {engagement_dir}/deploy/asset-bundle/

AUTHORED ASSETS
───────────────
  dashboards:        {N}  (kibana/dash-*.json)
  SLOs:              {N}  ({N} existing referenced, {N} new)
  detection rules:   {N}  ({N} package-shipped, {N} cloned, {N} custom)
  alerting rules:    {N}
  Agent Builder:     {N} agents, {N} tools
  Workflows:         {N}
  Connectors:        {N}
  Seed data:         {N} indices, {total_docs} documents

ES|QL VALIDATION
─────────────────
  Passed: {N}/{total} queries
  Failed: {N}  ← BLOCKED (resolve before running bolt-bootstrap)

FIELD POPULATION
─────────────────
  All viz-queried fields confirmed non-null: {yes/no}
  Blocked indices: {list or "none"}

NEXT STEP
─────────
  Review asset-bundle/ contents, then run: bolt-bootstrap
  (bolt-bootstrap reads asset-bundle/asset-schema.json and
   asset-bundle/asset-index.json as required inputs — D-045)
```

---

## What Good Looks Like

**Clean pass:** All schemas confirmed, fleet packages probed, all ES|QL queries pass validation,
all viz-queried fields confirmed non-null. Asset bundle is written. SA reviews `asset-index.json`
and sees that 3 of 5 dashboards are existing package assets referenced by ID — not re-authored.
`bolt-bootstrap` can run immediately.

**Blocked on failed query:** One Agent Builder tool ES|QL query returns `Unknown column [risk_label]`.
Verifier reports the failure, identifies that `risk_label` was not included in the seed spec,
and provides the fix: update `data/{slug}-data-model.json` Step 4 field population checklist,
re-run `weave-model` for that index's seed spec, re-run `finish-verify`. No deployment
proceeds until the fix is verified.

**Feature flag blocker:** Agent Builder probe returns 404 — feature not enabled on the target
cluster. Verifier surfaces the blocker, recommends scoping Agent Builder scenes out of the
demo (referencing the platform audit), and proceeds to author remaining in-scope assets only.
