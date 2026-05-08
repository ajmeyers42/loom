---
name: wind-pulse
description: >
  Checks the live health and readiness of a deployed Elastic demo environment. Reads
  credentials from the engagement's .env file, queries Elasticsearch and Kibana directly,
  and produces a compact terminal status report covering cluster health, index doc counts,
  ML job state, ELSER endpoint responsiveness, **every saved object in engagement NDJSON**
  (especially dashboards), **tagged SLOs**, Agent Builder, optional workflows, and anomaly
  injection readiness. Runs in under 60 seconds.

  ALWAYS use this skill when the user says "demo status", "is the demo ready", "check the
  cluster", "pre-demo check", "what's the state of the demo", "is [slug] deployed and
  ready", "is everything still up", "check that the cluster is healthy", "run a status
  check", or "quick check before the demo". Also trigger when the user comes back after
  a gap (overnight, weekend) and wants to confirm nothing fell over, or when bootstrap.py
  ran and they want to confirm it actually worked.
---

# Demo Status

You are running a live health check against a deployed Elastic demo environment. This is
not a deep audit — it is a fast pre-demo pulse check that tells the SE exactly what is
working, what is broken, and what command fixes each broken thing.

The entire check must complete in under 60 seconds. Every item has a clear pass/fail and
a specific remediation for any failure.

## Step 0: Inventory script (run first)

Use the repo script **`skills/wind-pulse/demo_status.py`** so **every Kibana saved object
exported in NDJSON** is checked (not only dashboards by title search). From the engagement
workspace:

```bash
cd "${DEMOBUILDER_ENGAGEMENTS_ROOT:-$HOME/engagements}/{slug}"
python3 "$DEMOBUILDER_REPO/skills/wind-pulse/demo_status.py"
# or: python3 /path/to/loom/skills/wind-pulse/demo_status.py --engagement-dir .
```

**What it validates**

| Source | Check |
|--------|--------|
| `kibana-objects/**/*.ndjson`, `kibana/**/*.ndjson` | `GET /api/saved_objects/{type}/{id}` for **each** line (dashboard, lens, index-pattern, etc.) |
| `{slug}-data-model.json` | Doc counts for listed data streams / indices (`p(name)`) |
| Observability SLOs | List with `perPage=500`, filter tags **`demobuilder:<engagement_id>`** (**D-026**) |
| Optional `kibana/status-expected.json` | Extra **`slo_ids`** via GET-by-id (see `references/status-expected.example.json`) |
| Agent | `AGENT_BUILDER_AGENT_ID` or default from `kibana/deploy_fraud_assistant_agent.py` |
| Workflows + alerting | `GET /api/alerting/rules/_find` for **`DEMO_STATUS_WORKFLOW_RULE_NAME`** (default **Invoke an Agent**); `GET /api/workflows` — **404** often means set **`KIBANA_SPACE_PATH`** to the Space where Workflows is enabled |
| Saved-object tag refs (D-026) | Each NDJSON object should reference tag id **`loom-<engagement_id>`** — run engagement **`kibana/apply_loom_tags.py`** after import if missing |

**Env overrides:** `DEMO_STATUS_SKIP_NDJSON=1` skips NDJSON line checks (not recommended). `KIBANA_SPACE_PATH` is honored like bootstrap. `DEMO_STATUS_WORKFLOW_RULE_NAME` overrides the default alerting rule name used as a Workflows readiness signal.

Then run the manual / supplemental checks below (ML, ELSER warm latency, demo-critical docs, etc.), or extend the script when a new asset class is always created.

## Step 1: Load the Environment

Read `{engagement_dir}/.env`. All API calls use these credentials. Never hardcode.

If `.env` doesn't exist, stop immediately:
```
ERROR: No .env found at {engagement_dir}/.env
Run bolt-spin first, or create .env from the template.
```

Extract and validate these fields:
- `ELASTICSEARCH_URL` — must be non-empty, starts with `https://` or `http://`
- `KIBANA_URL` — must be non-empty
- `ES_API_KEY` — must be non-empty
- `DEPLOYMENT_TYPE` — one of `serverless`, `ech`, `self_managed`, `docker`
- `INDEX_PREFIX` — may be empty; if set, prefix is applied via `p(name)`
- `DEMO_SLUG` — used to locate `{slug}-data-model.json` and `{slug}-ml-config.json`

Define the prefix helper used throughout:
```python
def p(name): return f"{PREFIX}{name}" if PREFIX else name
```

Read the pipeline artifacts:
- `{slug}-data-model.json` — required for index checks and doc count expectations
- `{slug}-ml-config.json` — optional; if absent, skip ML section and note it

## Step 2: Run the Checks

### Check 1 — Connectivity and Cluster Health

```
GET /
```
Extract: Elasticsearch version, cluster name.

```
GET /_cluster/health
```
Extract: `status` (green/yellow/red), `number_of_nodes`, `unassigned_shards`,
`active_primary_shards`.

```
GET {KIBANA_URL}/api/status
Authorization: ApiKey {ES_API_KEY}
```
Extract: overall status (`green`/`yellow`/`red`), Kibana version.

**Pass criteria:**
- ES responds with HTTP 200
- `cluster_health.status` is `green` (warn on yellow, fail on red)
- Kibana `/api/status` responds with HTTP 200

**Failures:**
```
❌  Cannot reach Elasticsearch at {ES_URL}
    → Check VPN / check that ELASTICSEARCH_URL in .env is correct
    → curl -s -H "Authorization: ApiKey $ES_API_KEY" "{ES_URL}/"

❌  Cluster health: RED ({N} unassigned shards)
    → GET /_cluster/allocation/explain  to find the blocked shard
    → python3 bootstrap.py --step 1    to recheck after resolving

⚠️  Cluster health: YELLOW ({N} unassigned shards)
    → Likely replica unassigned on single-node cluster — safe to demo, note for customer

❌  Cannot reach Kibana at {KIBANA_URL}
    → Verify KIBANA_URL in .env and confirm Kibana is running
```

### Check 2 — Indices

For each index defined in `{slug}-data-model.json`, run:

```
HEAD /{p(index.name)}
GET  /{p(index.name)}/_count
```

For each index with `demo_critical_docs` defined in the data model's `sample_data`,
run a targeted spot-check query. Example:

```json
GET /{p("fraud-claims")}/_search
{
  "size": 0,
  "query": {
    "bool": {
      "must": [
        { "term": { "vendor_id": "VND-0412" } },
        { "term": { "claim_type": "debit_card" } }
      ]
    }
  },
  "aggs": {
    "sla_breach_count": {
      "filter": { "term": { "sla_breach": true } }
    }
  }
}
```

Adapt the spot-check query to the actual `demo_critical_docs` fields in the data model —
do not hardcode VND-0412 unless that's what the data model specifies for this engagement.

**Pass criteria per index:**
- HEAD returns 200 (index exists)
- Doc count `>=` `seed_document_count` × 0.9 (within 10% of expected)
- Demo-critical docs are present (spot-check query returns expected count)

**Failures:**
```
❌  {p(index.name)}   index does not exist
    → Run: python3 bootstrap.py --step {build_step_number}

❌  {p(index.name)}   0 docs  (expected ≥ {seed_document_count})
    → Run: python3 bootstrap.py --step {data_load_step_number}

⚠️  {p(index.name)}   {N} docs  (expected ≥ {seed_document_count}, got {pct}%)
    → Partial load. Run: python3 bootstrap.py --skip-data  (checks threshold, tops up)

❌  Demo-critical docs: VND-0412 claims not found
    → The Friday scenario cannot run. Re-run seed: python3 bootstrap.py --step 10
```

For indices with `seed_document_count: 0` (e.g., `fraud-escalations` which starts empty),
report the actual count without a failure — empty is expected:
```
  ✅  {p("fraud-escalations")}   0 docs  (empty — populated live by agent during demo)
```

### Check 2b — ECS Baseline Field Population (logs/metrics/security)

For each logs/metrics data stream in `{slug}-data-model.json`, sample documents and validate
baseline fields needed for out-of-box UIs (not only custom dashboards):

```json
GET /{stream}/_search
{
  "size": 5,
  "sort": [{ "@timestamp": "desc" }],
  "_source": true
}
```

**Metrics stream pass criteria (`metrics-*`):**
- Every sampled doc has `@timestamp`
- Every sampled doc has `event.dataset`
- Every sampled doc has `host.name` (or explicitly documented container-only metric strategy)
- Every sampled doc has at least one of `service.type` or `agent.type`

**Logs stream pass criteria (`logs-*`):**
- Every sampled doc has `@timestamp`
- Every sampled doc has `event.dataset`
- Every sampled doc has at least one identity field: `host.name` OR `container.id` OR `kubernetes.pod.name`

**Security raw event pass criteria** (when sampled docs include security categories or stream is security-scoped):
- `event.kind` present (`event` for raw events)
- `event.category` and `event.type` present
- At least one principal/entity field: `user.name` or `host.name`

**Lowercase compliance (all sampled docs):**
- Fail if any top-level field name contains uppercase letters
- Warn if nested keys include uppercase letters (normalize via ingest rename pipeline)

**Failures:**
```
❌  {stream} missing `host.name` in sampled metrics docs
    → Infrastructure UI hosts/entities will be empty.
    → Fix: add/verify default ingest pipeline mapping source host field to `host.name`

❌  {stream} has uppercase field names (`DCGM_FI_DEV_GPU_UTIL`)
    → ECS/tooling compatibility risk.
    → Fix: rename at ingest to lowercase ECS fields and re-seed from clean deploy.
```

### Check 2c — Entity Discoverability Baseline (Infrastructure / Security)

Confirm baseline discoverability from indexed data, independent of custom visualizations:

- Metrics entities:
  - `terms` agg on `host.name` (and `kubernetes.pod.name` / `container.id` when expected)
  - Require at least one bucket for each expected entity dimension
- Security entities:
  - `terms` agg on `host.name` and `user.name` for security streams
  - Require at least one populated entity bucket for whichever entity the scenario uses

If buckets are empty while doc counts are non-zero, mark **NOT READY** — this indicates field
population mismatch even though ingestion succeeded.

### Check 3 — ML Jobs

Skip this section and note "No ml-config.json found" if the file is absent.

For each job defined in `{slug}-ml-config.json`:

```
GET /_ml/anomaly_detectors/{job.job_id}/_stats
```
Extract: `state` (should be `opened`), `data_counts.latest_record_timestamp`.

```
GET /_ml/datafeeds/{datafeed.datafeed_id}/_stats
```
Extract: `state` (should be `started`), `timing_stats.bucket_count`.

Check for recent anomalies on the target entity (use the `target_entity` field from the
ML config injection plan):

```json
GET /_ml/anomaly_detectors/{job.job_id}/results/records
{
  "sort": "record_score",
  "descending": true,
  "record_score": 50,
  "page": { "size": 5 }
}
```

**Pass criteria:**
- Job `state` is `opened`
- Datafeed `state` is `started`
- `latest_record_timestamp` is within 2× the `bucket_span` of now (datafeed is current)
- At least one anomaly record with `record_score` ≥ 75 exists for the target entity

**Failures:**
```
❌  {job_id}   state: closed (expected: opened)
    → Run: POST /_ml/anomaly_detectors/{job_id}/_open

❌  {datafeed_id}   state: stopped (expected: started)
    → Run: POST /_ml/datafeeds/{datafeed_id}/_start

⚠️  ML last bucket: {N}h ago  (bucket_span: {B}m — expected within {2B}m)
    → Datafeed may be stopped or lagging. Check:
       GET /_ml/datafeeds/{datafeed_id}/_stats

⚠️  No anomaly ≥ 75 on target entity {entity}
    → Anomaly injection may not have run, or the anomaly bucket hasn't processed yet.
       Re-run injection: python3 bootstrap.py --step 14
       Then wait {2 × bucket_span} minutes and recheck.
```

Report the most recent anomaly score:
```
  ✅  {job_id}   open | datafeed running
      Last bucket: {timestamp} | Anomaly score on {entity}: {score} ✅
```

If score exists but is below 75:
```
  ⚠️  {job_id}   open | datafeed running
      Last bucket: {timestamp} | Anomaly score on {entity}: {score} (< 75 — recheck after next bucket)
```

### Check 4 — ELSER Endpoint

```
GET /_inference/sparse_embedding/{p("elser-v2-endpoint")}
```
Extract: `service_settings.num_allocations`.

If allocated, run a warm-up timing query against the semantic index (use the index with
`semantic_text` mapping from the data model):

```json
GET /{p("fraud-claims-semantic")}/_search
{
  "size": 1,
  "query": {
    "semantic": {
      "field": "claim_description_semantic",
      "query": "debit card transaction dispute"
    }
  }
}
```
Capture `took` (milliseconds).

**Pass criteria:**
- Endpoint exists and `num_allocations` ≥ 1
- Semantic query responds in < 2000ms (first call after cold-start may be slow;
  if > 2000ms on first call, re-run to confirm it was a cold-start, not a problem)

**Failures:**
```
❌  ELSER endpoint not found: {p("elser-v2-endpoint")}
    → Run: python3 bootstrap.py --step 8

❌  ELSER endpoint exists but num_allocations: 0  (model not loaded)
    → Model is still loading or failed to start. Wait 90s and recheck.
       GET /_inference/sparse_embedding/{p("elser-v2-endpoint")}

⚠️  ELSER warm latency: {N}ms  (> 2000ms — cold start expected)
    → Run one more query to confirm. If still slow after second call:
       POST /_inference/sparse_embedding/{p("elser-v2-endpoint")}/_warm
```

### Check 5 — Kibana objects (dashboards and all committed NDJSON)

**Do not rely on `_find` by title alone** — that can miss objects or match the wrong space.

**Primary:** **`demo_status.py`** (Step 0) — parses **every** line in `kibana-objects/*.ndjson`
(and `kibana/**/*.ndjson`) and calls **`GET /api/saved_objects/{type}/{id}`** for each. That
includes **dashboards**, **Lens**, **index-patterns**, **search** sessions, **maps**, etc.,
exactly as exported for the engagement.

**Agent Builder** agents are **not** always in NDJSON; the script checks
**`/api/agent_builder/agents/{id}`** using `AGENT_BUILDER_AGENT_ID` or the default in
`kibana/deploy_fraud_assistant_agent.py`.

**Workflows:** **`GET /api/workflows`** — if **404**, Workflows is not enabled (note and skip).
If **200**, confirm **`AGENT_BUILDER_WORKFLOW_ID`** appears when that env var is set.

**SLOs:** Prefer the **loom tag** filter in **`demo_status.py`**; add optional
**`kibana/status-expected.json`** for explicit **`slo_ids`** on noisy shared clusters.

**Supplemental (optional):** `_find` by title for a quick human spot-check, or
**`GET {KIBANA_URL}/internal/elastic_assistant/conversations`** only if the demo script
requires it.

**Pass criteria:**
- **`demo_status.py`** reports **OK** for every NDJSON object, tagged SLOs, and agent (and
  workflow id when configured).

**Failures:**
```
❌  saved_object dashboard:xyz  HTTP 404
    → Import failed or wrong space. Re-run: python3 bootstrap.py step 13 / deploy_kibana_gaps.py

❌  Agent GET 404
    → Run: python3 kibana/deploy_fraud_assistant_agent.py

❌  Workflow id not in GET /api/workflows
    → Create workflow or fix AGENT_BUILDER_WORKFLOW_ID

⚠️  Agent tool references index {index_name} which has 0 docs
    → Agent will return empty results. Load data first (Check 2 failure above).
```

### Check 6 — Anomaly Injection Readiness

Determine whether the demo is approaching (within 2 hours of scheduled start time). If
the user provides a demo time, compare it against the current UTC timestamp.

Check whether the injection target documents have been primed by querying the expected
anomalous SKUs or entities directly. For Citizens Bank this means vendor VND-0412 with
`sla_breach: true` claims — use the appropriate field from `demo_critical_docs` in the
data model for this engagement.

```json
GET /{p("fraud-claims")}/_search
{
  "size": 0,
  "query": {
    "bool": {
      "must": [
        { "term": { "vendor_id": "VND-0412" } },
        { "term": { "sla_breach": true } }
      ]
    }
  }
}
```

**Pass criteria:**
- Injection target documents are present in sufficient quantity (per `demo_critical_docs`)
- If T-2h or less: recommend running ELSER warm-up and ML datafeed confirmation
- If T+: (post-demo) skip this section

**Readiness messages:**
```
  ✅  Injection SKUs primed — VND-0412 anomaly docs present (4 SLA-breach claims)

  ⚠️  T-2h or less before demo — run final checks:
      1. python3 bootstrap.py --step 15   # ELSER warm-up
      2. Confirm ML datafeed current (Check 3 above)
      3. Open dashboard tabs in browser now to warm tile cache

  ℹ️  Demo time not specified — skipping countdown check
      Pass demo_time="HH:MM UTC" to enable T-minus readiness guidance
```

## Step 3: Render the Status Report

After all checks complete, render the terminal report. Keep it compact — the SE reads
this in a terminal window before a demo, not in a document viewer.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DEMO STATUS — {Demo Name / Company}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Cluster:  {ELASTICSEARCH_URL}  ({health_status}, {N} nodes)
 Kibana:   {KIBANA_URL}  ({kibana_status})
 Checked:  {YYYY-MM-DD HH:MM UTC}
 Prefix:   {PREFIX or '(none)'}   (applied to all resources)

INDICES
  ✅  {p("fraud-claims")}              {N} docs   (expected ≥ {min})
  ✅  {p("fraud-claims-semantic")}     {N} docs   (expected ≥ {min})
  ✅  {p("fraud-escalations")}         0 docs     (empty — populated live by agent)
  ✅  {p("sla-monitoring-telemetry")}  {N} docs   (expected ≥ {min})
  ✅  Demo-critical docs: VND-0412 present (7/7 claims), 4 SLA-breach docs confirmed

ML JOBS
  ✅  {job_id}   open | datafeed running
      Last bucket: {timestamp} | Anomaly score on {entity}: {score} ✅

ELSER
  ✅  {p("elser-v2-endpoint")}   allocated ({N}) | warm latency: {N}ms ✅

KIBANA
  ✅  {Dashboard Name} dashboard  reachable
  ✅  {agent_name}                responds to test prompt

ANOMALY INJECTION
  ✅  VND-0412 SLA-breach docs primed (4 claims, sla_breach=true)

OVERALL: ✅ READY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**If any check fails**, replace `✅ READY` with `❌ NOT READY` and list each failure with
its remediation inline. Present failures first, warnings after, passes last.

```
OVERALL: ❌ NOT READY  (2 failures, 1 warning)

FAILURES (fix these before the demo):
  ❌  {p("fraud-claims-semantic")}  0 docs
      → Run: python3 bootstrap.py --step 10
  ❌  ELSER endpoint not allocated
      → Run: python3 bootstrap.py --step 8

WARNINGS (demo can proceed, but note these):
  ⚠️  ML last bucket: 6h ago
      → Datafeed may have stopped. Check:
         GET /_ml/datafeeds/{datafeed_id}/_stats
      → Restart: POST /_ml/datafeeds/{datafeed_id}/_start
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Step 4: Convenience — Print the Fix Script

If any failures were found, output a single block of commands the SE can paste directly
into their terminal to attempt remediation:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 FIX COMMANDS — paste to resolve failures
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
set -a && source {engagement_dir}/.env && set +a
python3 {engagement_dir}/bootstrap.py --step 8
python3 {engagement_dir}/bootstrap.py --step 10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If everything passes, output the ELSER warm-up command as a proactive step:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 RECOMMENDED — run before the demo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
set -a && source {engagement_dir}/.env && set +a
python3 {engagement_dir}/bootstrap.py --step 15   # ELSER warm-up
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## API Reference

All Elasticsearch calls use:
```
Authorization: ApiKey {ES_API_KEY}
Content-Type: application/json
```

All Kibana calls use:
```
Authorization: ApiKey {ES_API_KEY}
kbn-xsrf: true
Content-Type: application/json
```

Key endpoints used in this skill:

| Check | Endpoint |
|---|---|
| ES connectivity | `GET {ES_URL}/` |
| Cluster health | `GET {ES_URL}/_cluster/health` |
| Kibana health | `GET {KB_URL}/api/status` |
| Index exists | `HEAD {ES_URL}/{p(index)}` |
| Doc count | `GET {ES_URL}/{p(index)}/_count` |
| Doc search | `POST {ES_URL}/{p(index)}/_search` |
| ML job stats | `GET {ES_URL}/_ml/anomaly_detectors/{job_id}/_stats` |
| Datafeed stats | `GET {ES_URL}/_ml/datafeeds/{datafeed_id}/_stats` |
| ML anomaly records | `GET {ES_URL}/_ml/anomaly_detectors/{job_id}/results/records` |
| Open ML job | `POST {ES_URL}/_ml/anomaly_detectors/{job_id}/_open` |
| Start datafeed | `POST {ES_URL}/_ml/datafeeds/{datafeed_id}/_start` |
| ELSER endpoint | `GET {ES_URL}/_inference/sparse_embedding/{p("elser-v2-endpoint")}` |
| Semantic query | `POST {ES_URL}/{p(semantic_index)}/_search` |
| Kibana saved objects (inventory) | `GET {KB_URL}/api/saved_objects/{type}/{id}` (per NDJSON line) — see `demo_status.py` |
| Kibana saved objects (ad hoc) | `GET {KB_URL}/api/saved_objects/_find?type=dashboard&...` |

## What Good Looks Like

**Clean green:** All indices have expected doc counts, ML job is open with datafeed
running, ELSER endpoint is allocated and responds in < 500ms, Kibana dashboards and agent
are reachable. Output ends with `OVERALL: ✅ READY`. SE runs the ELSER warm-up command
and opens browser tabs.

**ELSER cold-start:** First warm-up query took 8 seconds — this is expected. Second query
took 320ms. Status check passes with a note: "First semantic query was slow (cold start).
Endpoint is warm now — stay on Kibana; don't let it idle for > 30 minutes."

**Datafeed stopped overnight:** ML job is open but datafeed state is `stopped`. Last
bucket was 9 hours ago. Status report shows ⚠️ warning, prints the `_start` command.
SE pastes the fix command, datafeed restarts, anomaly score re-appears within 2 bucket
spans.

**Missing semantic index:** `fraud-claims-semantic` has 0 docs. ELSER endpoint is fine.
Status report shows ❌, prints `python3 bootstrap.py --step 10`. SE runs it, encoding
takes 10–20 minutes (ELSER at ingest). SE re-runs `wind-pulse` to confirm.

**Multi-prefix environment:** Two deployments share one cluster — `cb-` for Citizens Bank,
`ihg-` for IHG. Each `.env` has its own `INDEX_PREFIX`. Running `wind-pulse` in each
workspace checks only that prefix's resources. No cross-contamination.
