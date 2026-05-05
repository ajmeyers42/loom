---
name: demo-data-modeler
description: >
  Reads a demo script and discovery profile to generate all Elasticsearch data artifacts
  needed to build the demo environment: index mappings, data stream templates, component
  templates, ILM policies, ingest pipelines, enrich policies, and sample data specifications.
  Produces a master build manifest and individual artifact files in correct build order.

  ALWAYS use this skill when the user says "generate the mappings", "build the data model",
  "create the index templates", "what indices do we need", or has a demo script and wants to
  start building the technical environment. Also trigger after demo-script-template completes
  when the user is ready to move from planning to building. Run before demo-ml-designer —
  ML jobs depend on the data model being defined first.
---

# Demo Data Modeler

You are generating the Elasticsearch data artifacts for a pre-sales demo environment.
Everything you produce must be valid, runnable Elasticsearch configuration — not pseudocode,
not placeholders. An SE should be able to take your output, run it against a cluster, and
have a working data layer.

**Deployability (D-025):** Every field type, API body, and pipeline processor you write must
be valid for the **resolved target stack version**. Generic or invented types are not
acceptable — use `keyword`, `text`, `date`, `semantic_text`, etc. as the stack requires.

## Step 0: Resolve the Target Stack Version

**Baseline: 9.4+ (D-033).** All generated artifacts use **9.4 ECH / Serverless API shapes**.
Pre-9.4 compatibility shims are not generated. If the engagement's cluster is confirmed to be
below 9.4, flag it as a blocker in `{slug}-risks.md` and do not proceed to artifact generation
until the cluster is updated.

**Confirm the live version** before authoring any mapping, template, or pipeline:

1. **`demo/{slug}-platform-audit.json`** — read `platform.version` and `platform.version_verified`
2. **`demo/{slug}-current-state.json`** — read `version` (from diagnostic analyzer output)
3. **`.env`** — read `ELASTIC_VERSION` (informational; treat as unverified unless also in audit)
4. **Ask the SA** — if none of the above are available, ask before proceeding

If the version is unverified (no live `GET /` or diagnostic), state this explicitly in the
data model output header and flag it as a risk in `deploy/{slug}-risks.md`.

**9.4 API shapes to use (D-033):**
- **Inference endpoints:** EIS (`service: "elastic"`, `model_id: ".elser-2"`) for ECH;
  `service: "elser"` for Serverless. Do not use `service: "elasticsearch"` for embeddings (D-028).
- **Inference GET response:** `{"endpoints": [...]}` wrapper — unwrap before reading `service`.
- **ILM:** Hot-only by default; never `rollover` on plain indices (D-027).
- **Data views:** `POST /api/data_views/data_view` (9.x shape).
- **Agent Builder:** v0.2.0 shape — `configuration.skill_ids` and typed tool list (D-029).
- **Alerting rules:** 9.x `windows` array schema for SLO burn-rate rules.

See `docs/decisions.md` **D-025**, **D-033** and `skills/demo-deploy/references/serverless-differences.md`.

## Step 0b: Check for Vulcan Outputs (optional fast path)

Before extracting requirements from scratch, check whether `demo-vulcan-generate` has
already run for this engagement. If **`data/{slug}-vulcan-queries.json`** exists, use it as a
pre-built input — it contains cluster-validated ES|QL queries, parameter shapes, and a
data profile summary that saves significant hand-authoring work.

**When Vulcan outputs are present:**

1. Read `data/{slug}-vulcan-queries.json` — extract `queries[]`, `index_name_map`,
   `data_profile_summary`, `integration_grounded`, and `include_rag`.
2. For each query, confirm the referenced index names and fields match what the demo script
   expects. Flag any mismatches as a data model risk.
3. Use the parameterized queries (`query_type: "parameterized"`) directly as Agent Builder
   tool ES|QL bodies — copy them into the index specs and agent-builder-spec section.
4. Use the RAG pipeline spec (if `include_rag: true`) to drive `semantic_text` field
   placement and inference endpoint wiring.
5. If `data/seed/*.csv` files exist under `{engagement_dir}/data/seed/`, reference them
   as the `seed_data_source` for each dataset in the build manifest rather than generating
   synthetic docs from scratch.

**Integration-grounded data (`integration_grounded: true`):**
When Vulcan ran with EPR grounding, index names will follow `logs-<integration>.*` or
`metrics-<integration>.*` conventions. Use these exact names and preserve the integration
field alignment — do not rename fields or re-map index names, as this would break
compatibility with shipped integration dashboards.

**When Vulcan outputs are absent:** proceed with Step 1 as normal.

---

## Step 1: Extract the Data Requirements

Read the demo script (`demo/{slug}-demo-script.md`) and discovery JSON (`demo/{slug}-discovery.json`).
If Vulcan outputs were present (Step 0b), use the `data_profile_summary` and `index_name_map`
from `data/{slug}-vulcan-queries.json` to seed the index list rather than re-deriving it.

From the script, identify every index, data stream, pipeline, and data element referenced:

- **Every index name** mentioned in queries (`FROM fraud-claims`, `GET associate-sessions/_doc/...`)
- **Every field** used in an ES|QL query, displayed in Kibana, or referenced in an agent tool
- **Every computed or derived field** (e.g., `discrepancy_pct = (system_on_hand - stock_on_hand) / system_on_hand * 100`)
- **Every ingest-time enrichment** (geo_point lookups, enrich processor joins)
- **Every feature-specific field type** (`semantic_text` for ELSER, `geo_point` for spatial, `nested` for multi-turn conversation history)
- **Every data relationship** (which index is written by an ingest pipeline processing another index)

Group them into:
1. **Data streams** — append-only, time-series (events, transactions, logs)
2. **Regular indices** — mutable documents (positions, sessions, metadata)
3. **System indices** — Kibana/agent artifacts (sessions, telemetry, fulfillment records)

## Step 2: Design Each Index

For each index, define:

**Field types** — use the most specific type that fits the query pattern:
- Identifiers (`store_id`, `sku`, `session_id`): `keyword`
- Free text for full-text search: `text` with `.keyword` sub-field for aggregations
- Semantic/ELSER search: `semantic_text` with `inference_id` pointing to the EIS ELSER endpoint (see D-028)
- Counts and quantities: `integer` or `long`
- Rates and percentages: `float` or `double`
- Timestamps: `date`
- Locations: `geo_point`
- Computed at ingest: add as regular fields (populated by ingest pipeline script processor)
- Multi-value arrays with sub-structure: `nested`
- Booleans: `boolean`

**Step 2a — Logs/Metrics naming contract (Hybrid OOTB foundation):**

For every logs or metrics data stream, choose exactly one strategy and record it in the data
model manifest:

1. **Path A — Fleet integration package (required for Observability and Security domains; preferred everywhere else):**
   - Use integration-native naming: `logs-<integration>.<dataset>-<namespace>` or
     `metrics-<integration>.<dataset>-<namespace>`
   - Declare `strategy: "fleet_integration"` with `package`, `dataset`, `namespace`
   - Example: `metrics-nvidia_gpu.stats-default`, `logs-kubernetes.container_logs-default`
   - The package provides ECS mappings, ingest pipelines, dashboards, and often ML/rules
   - **Before recording any field name**, confirm the schema via `GET /_component_template/<package>.<dataset>@package`. Do not guess or infer field names — use only what the probe returns (D-043 Rule 3).
   - **Before authoring any asset** (dashboard, alert, ML job, data view), enumerate what the package already ships: `GET /api/fleet/epm/packages/<name>/assets`. Use those assets as the primary demo deliverable. Author custom assets only for scenes or signals the package does not cover. Do not duplicate a shipped dashboard or rule with a custom version without SA approval.
   - **Do not invent Prometheus-scraper stream names** (`metrics-gpu.dcgm.prometheus-*`, `metrics-k8s.state.prometheus-*`, etc.) for technology that has a shipped Fleet integration. Check EPR first.

2. **Path B — Managed templates fallback (custom/demo-only and search use cases):**
   - Use `logs-demo.<dataset>-<namespace>` or `metrics-demo.<dataset>-<namespace>` for demo-only streams; use engagement-prefixed names (e.g. `lg-clinical-corpus`) for custom search indices
   - Declare `strategy: "managed_templates"` or `strategy: "custom"`
   - Compose templates using Elastic-managed ECS building blocks:
     - Logs: `composed_of: ["logs@mappings", "logs@settings", "ecs@mappings", "<custom>"]`
     - Metrics: `composed_of: ["metrics@mappings", "metrics@settings", "ecs@mappings", "<custom>"]`
   - Custom component templates define only non-ECS fields
   - Custom search indices (Path B, `strategy: "custom"`) may be iterated: author mapping → deploy → test query → refine. This is normal and expected (D-043 Rule 2).

**No third path:** reject arbitrary names (`security-events-*`, `metrics-gpu.*`, `metrics-k8s.state.prometheus-*`) unless they fit Path A or Path B. Prometheus-exporter-named streams are not Path A — they are custom streams that bypass the integration package.

**Lowercase rule (mandatory):**
- All generated field names must be lowercase snake_case / dotted ECS style.
- If a source emits uppercase or mixed-case fields (`DCGM_FI_DEV_GPU_UTIL`), add an ingest
  pipeline rename step to lowercase ECS-compliant names at write time.
- Do not leave uppercase source fields in final indexed documents.

See `references/mapping-patterns.md` for Path A/Path B examples, `ecs@mappings` behavior,
and lowercase rename patterns.

**Do not use `dynamic: true` on production-intent indices.** Explicit mappings only.
On indices where dynamic mapping is acceptable (e.g., enrichment lookup tables), set
`dynamic: false` (accept but don't index unmapped fields) or `dynamic: strict` (reject).

**Shard count:**
- Data streams / high-volume indices: 1 primary shard per ~50GB expected data, minimum 1
- Small lookup/metadata indices (< 1GB): 1 primary shard
- Default replica count: 1 (adjust based on platform audit output)

**ILM (see D-027):**
- **Default: hot-only.** Generate a hot phase (`set_priority`) + `delete` phase unless the
  engagement explicitly requires tiered storage as part of the demo story.
- **Plain indices (non-data-stream):** never use `rollover` — requires `index.lifecycle.rollover_alias`
  and ERRORs immediately on any index without a write alias. `forcemerge` in hot also requires
  rollover; omit it too.
- **Data streams:** `rollover` is valid and appropriate when the engagement calls for it.
- **Warm/cold/frozen phases:** only include when (a) the engagement requires it AND (b) those
  node roles are present on the target cluster (`GET /_nodes?filter_path=nodes.*.roles`).
- Lookup/seed data indices: no ILM needed.

**Inference endpoints (see D-028):**
- Use **EIS** (`service: "elastic"`) for all text embedding and reranking inference — never
  deploy these models on the cluster's ML nodes.
- Reserve ML nodes for anomaly detection jobs, data frame analytics, and tasks that require
  local execution.
- EIS sparse embedding: `PUT /_inference/sparse_embedding/{id}` with `service: "elastic"`,
  `model_id: ".elser-2"`
- EIS reranking: `PUT /_inference/rerank/{id}` with `service: "elastic"`,
  `model_id: "elastic-reranker-v1"`
- Map `semantic_text` fields to the EIS inference endpoint id, not a local `.elser-*` deployment.

## Step 3: Design the Ingest Pipelines

For each pipeline, write the full processor chain. Common patterns:

**Enrich processor** (adds fields from a lookup index):
```json
{
  "enrich": {
    "policy_name": "store-location-enrich",
    "field": "store_id",
    "target_field": "store_meta",
    "max_matches": 1
  }
}
```
Enrich policies must be created and executed before the pipeline references them.

**Script processor** (computed fields):
```json
{
  "script": {
    "lang": "painless",
    "source": "ctx.discrepancy_pct = ctx.system_on_hand > 0 ? Math.round(((ctx.system_on_hand - ctx.stock_on_hand) / (float)ctx.system_on_hand) * 1000) / 10.0 : 0.0;"
  }
}
```

**Upsert via pipeline + update_by_query pattern:** When an ingest pipeline needs to update
a document in a different index (e.g., transactions updating inventory-positions), use a
script processor to emit to the secondary index via the `_index` rerouting or a subsequent
bulk action. For the scripted_upsert pattern:
```json
{
  "script": {
    "lang": "painless",
    "source": "...",
    "params": { ... }
  },
  "upsert": { ... }
}
```

**Date/timestamp normalization:**
```json
{ "date": { "field": "@timestamp", "formats": ["ISO8601", "epoch_millis"] } }
```

## Step 4: Define the Sample Data Specification

**If Vulcan CSVs exist** (`{engagement_dir}/data/seed/*.csv`), use them as the seed data
source for each matching dataset. In the build manifest, set:

```json
{
  "index": "<index-name>",
  "seed_data_source": "vulcan-csv",
  "seed_csv": "data/seed/<dataset_name>.csv",
  "seed_document_count": "<row count from data_profile_summary>",
  "demo_critical_docs": [ ... ]
}
```

`bootstrap.py` will read the CSV via pandas and bulk-index it, preserving Vulcan's realistic
field distributions. Add `demo_critical_docs` on top — the CSV provides the background data;
demo-critical documents ensure scenario-specific docs are present regardless of CSV content.

**If no Vulcan CSVs**, specify the seed data schema and value constraints as normal:

For each index, specify what the seed data should look like — not the actual data (that
is generated by a separate script), but the schema and value constraints:

```json
{
  "index": "inventory-positions",
  "seed_document_count": 500,
  "key_entities": [
    { "field": "store_id", "values": ["1842", "2051", "2089"], "distribution": "weighted_to_1842" },
    { "field": "sku", "range": "100000-999999", "count": 500 }
  ],
  "demo_critical_docs": [
    {
      "description": "SKU 174239 at store 1842 — low stock vs high system_on_hand (Scenario 1)",
      "fields": { "store_id": "1842", "sku": "174239", "stock_on_hand": 23, "system_on_hand": 47 }
    }
  ],
  "field_ranges": {
    "stock_on_hand": "0-200",
    "system_on_hand": "0-200",
    "discrepancy_pct": "computed"
  }
}
```

**Demo-critical documents are non-negotiable.** The scenarios in the script depend on
specific field values existing. Enumerate every document that must be present for a
scenario to work.

**Field population requirement (D-044) — mandatory for every custom index:**

For every field in the mapping:

1. **Every field must have a non-null value in every seed document.** Null fields are invisible to ES|QL. A field present in the mapping but null in `_source` causes `Unknown column` errors in visualizations.
2. **Derived fields must be computed at seed time.** If a field is derived from another (e.g., `risk_label` from `risk_score`, `on_track` from `days_behind_plan`), compute the value and store it during seeding. Do not defer derivation to query time.
3. **If a field has no meaningful value for a specific document, use a sentinel.** For keyword arrays with no items, store `["none"]`. For optional scores with no reading, store `0.0`. Document the sentinel in the data model.
4. **At the end of the sample data spec, produce a field population checklist** — a table of every (index, field) pair used by any viz query with a confirmation that it will be non-null in all seed docs.

| Index | Field | Viz that queries it | Seed value / derivation |
|---|---|---|---|
| `entity-store` | `risk_label` | `d3-highrisk` | `"HIGH"` if `risk_score >= 7.0`, else `"MEDIUM"` if `>= 4.0`, else `"LOW"` |
| `entity-store` | `entity_type` | `d3-vendors` | Explicitly set per entity: `"vendor"` or `"site"` |

## Step 4b: Define Data Views (D-043)

**A data view is a time-axis declaration, not just an index alias.** Before writing outputs, inventory every date field per index and decide which data views are required. Do not defer this to bootstrap or dashboard build time.

For each index, produce a table:

| Date field | Type | Semantic meaning | Dashboard use case |
|---|---|---|---|
| `@timestamp` | `date` | When did this event occur? | Volume/trend charts |
| `updated_at` | `date` | When was this record last scored/refreshed? | Current-state metrics |
| `start_date` | `date` | When did this project begin? | Timeline / cohort views |
| `target_completion` | `date` | When is the work due? | Deadline / burndown views |

**Rules:**
- If all planned visualizations for an index share the same time semantic → one data view suffices.
- If any visualization group has a different time semantic → create a separate data view named `{index}-{semantic}` (e.g., `tf-portfolio-projects-deadline` with `timeFieldName: target_completion`).
- For `textBased` (ES|QL) vizzes, add the appropriate `WHERE {field} >= ?_tstart AND {field} <= ?_tend` in the query body — the data view's `timeFieldName` does NOT inject this automatically.
- Seed data MUST populate every `timeFieldName` field with a non-null value so documents are visible when the dashboard time picker is active.

Add a `data_views` section to the data model JSON output listing every data view with its `id` (stable UUID5), `title`, `timeFieldName`, and `semantic`.

## Step 5: Write the Outputs

### Output 1: `data/{slug}-data-model.json`

Master manifest — one document describing everything that needs to be built:

```json
{
  "slug": "",
  "build_order": [
    { "step": 1, "artifact": "elser-inference-endpoint", "type": "inference", "reason": "required before semantic_text mapping" },
    { "step": 2, "artifact": "store-location-enrich-policy", "type": "enrich_policy", "reason": "required before ingest pipeline" },
    { "step": 3, "artifact": "store-transactions-pipeline", "type": "ingest_pipeline", "reason": "required before data stream template" },
    { "step": 4, "artifact": "store-transactions-template", "type": "index_template" },
    { "step": 5, "artifact": "inventory-positions", "type": "index" },
    { "step": 6, "artifact": "associate-knowledge-base", "type": "index", "reason": "semantic_text — ELSER endpoint must exist" }
  ],
  "indices": [ ... ],
  "data_streams": [ ... ],
  "ingest_pipelines": [ ... ],
  "enrich_policies": [ ... ],
  "ilm_policies": [ ... ],
  "inference_endpoints": [ ... ],
  "data_views": [
    {
      "id": "{stable-uuid}",
      "title": "{index-pattern}",
      "timeFieldName": "{primary-date-field}",
      "semantic": "when this record was last scored/updated",
      "name": "{human-readable label}"
    },
    {
      "id": "{stable-uuid-2}",
      "title": "{index-pattern}",
      "timeFieldName": "target_completion",
      "semantic": "project deadline — use for deadline/burndown visualizations",
      "name": "{index-pattern}-deadline"
    }
  ],
  "sample_data": [ ... ]
}
```

### Output 2: `data/{slug}-data-model.md`

Human-readable build overview for the SE:

```
# Data Model — [Company / Demo Name]

## What Gets Built
[Table: artifact name | type | purpose | build step]

## Build Order
[Numbered list with dependency notes]

## Index Designs
[For each index: purpose, key fields with types, shard count, ILM, special notes]

## Data Views
[For each index: table of date fields with semantic meaning, which data view(s) are created,
 which visualizations use each, and what timeFieldName is configured. Flag any index where
 different visualization groups require different time fields — those need multiple data views.]

| Data view name | Index | timeFieldName | Semantic | Used by visualizations |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

## Ingest Pipeline Logic
[For each pipeline: what it does, processor chain summary, any tricky logic]

## Sample Data Requirements
[For each index: doc count, key entities, demo-critical documents.
 For each non-@timestamp index: confirm the timeFieldName field is populated at seed time.]

## Dependency Map
[Which artifacts block which — drawn in text if no diagram tool]
```

### Output 3: Individual artifact files in `data/mappings/` and `data/pipelines/`

For each index: a standalone JSON file with the complete mapping, settings, and aliases.
For each pipeline: a standalone JSON file with the complete processor chain.
These files should be directly passable to the Elasticsearch API:

```
# mapping file format
PUT /{index-name}
{
  "mappings": { ... },
  "settings": { "number_of_shards": 1, "number_of_replicas": 1 }
}
```

For data stream templates:
```
# component template + index template pattern
PUT /_component_template/{name}-mappings
{ "template": { "mappings": { ... } } }

PUT /_component_template/{name}-settings
{ "template": { "settings": { ... } } }

PUT /_index_template/{name}
{ "index_patterns": ["{name}-*"], "data_stream": {}, "composed_of": [...], "priority": 200 }
```

## Step 5b: Data Fidelity Assessment

Before finalizing the data specification, assess fidelity requirements by demo scenario.
**50 well-crafted records beat 10,000 poorly formed ones.**

**Reference:** `hive-mind/patterns/data/DATA_FIDELITY_GUIDE.md` — fidelity requirements
by scenario type with critical/important/nice-to-have breakdown.

| Dimension | What It Means | Example |
|---|---|---|
| **Visual** | Images load, realistic display | Product photos, chart data in correct ranges |
| **Structural** | Relationships make sense | Categories contain appropriate items, IDs are consistent |
| **Statistical** | Numbers are realistic | Prices in expected ranges, anomaly ratios match the story |
| **Semantic** | Content is meaningful for search | Descriptions keyword-rich, questions sound like real users |
| **Temporal** | Dates/times are plausible and ordered | Events in logical sequence, no future timestamps |

**Critical fidelity by scenario:**

| Scenario | Must Be Realistic | Can Approximate |
|---|---|---|
| AI Search / Agent Builder | Descriptions, attributes, relationships | Exact prices, dates |
| Operational/SIEM | Timestamps, event types, anomaly patterns | Exact IPs, metadata |
| Support / Knowledge Base | Content, questions, answers | Dates, view counts |
| Analytics / Observability | Queries, click patterns, sessions | Exact counts |
| Financial / Fraud | Transaction sequences, amounts in range | Non-demo-path records |
| **Observability Metrics** | **Path A integration-native or Path B managed-template naming, ECS fields populated on every document, temporal continuity** | Exact node counts, IP addresses |

**Common fidelity failures to avoid:**
- Broken image URLs — use `picsum.photos/seed/{id}/400/400` or validated placeholder pattern
- Generic content (`Product 1`, `Sample Description`) — all demo-visible text must be domain-realistic
- Inconsistent IDs — entity IDs used in demo-critical documents must appear in related indices
- Temporal incoherence — events that precede their prerequisite events (logout before login)
- Anomaly injection too early or too late — ML jobs need sufficient lead time before the anomaly
- **Data stream names outside the Path A/Path B contract** — arbitrary names break automatic ECS behavior and can make out-of-box UIs appear empty.
- **Mixed-case field names in indexed docs** — uppercase fields often bypass ECS conventions and break aggregations/rule/query assumptions; always normalize to lowercase at ingest.
- **Missing ECS identity fields** — absent `host.name`, `event.dataset`, `event.kind`, `event.type`, or `user.name` (as applicable) leaves Infrastructure/Security views without entities.

**For seed data with AI:** `hive-mind/patterns/data/LLM_DATA_GENERATION.md` provides
structured LLM prompts for generating domain-specific demo data. Use when custom data
is required (especially for Domain Expert Advisor and Documentation/Support archetypes).

## Step 5c: Token Visibility Index (conditional)

When the demo includes **Elastic Agent Builder**, include a `{prefix}agent-sessions` index
in the data model. This index powers the AI Cost + Usage dashboard (D-036).

Read `skills/token-visibility/SKILL.md` for the full mapping, seed data spec, and ES|QL
query patterns. Add the index to the `build_order` in `data/{slug}-data-model.json` as the
last standard index step (before ML config if present):

```json
{
  "step": N,
  "artifact": "{prefix}agent-sessions",
  "type": "index",
  "reason": "AI Cost + Usage dashboard — operational transparency for Agent Builder demos (D-036)"
}
```

Add `"include_token_visibility": true` to the data model JSON when this is included.
Set to `false` if the demo scope does not include Agent Builder or AI features.

## Step 5d: Embed Vulcan-Validated Queries (conditional)

When `data/{slug}-vulcan-queries.json` exists, embed the validated queries directly into the data
model JSON under each index spec. This ensures bootstrap.py has tested ES|QL without re-authoring:

```json
{
  "index": "fraud-claims",
  "validated_queries": [
    {
      "id": "q_1",
      "name": "Claims by status this week",
      "scene": "Scene 2 — Claims Overview",
      "esql": "FROM fraud-claims | WHERE @timestamp >= NOW() - 7 days | STATS count = COUNT(*) BY status",
      "query_type": "scripted",
      "validation_status": "passed"
    },
    {
      "id": "q_3",
      "name": "High-risk claims for account",
      "scene": "Scene 3 — AI Assistant deep dive",
      "esql": "FROM fraud-claims | WHERE account_id == ?account_id AND risk_score > ?threshold | SORT @timestamp DESC | LIMIT 10",
      "query_type": "parameterized",
      "parameters": [{"name": "account_id", "type": "keyword"}, {"name": "threshold", "type": "double"}],
      "validation_status": "passed"
    }
  ]
}
```

Parameterized queries (`query_type: "parameterized"`) are Agent Builder tool ES|QL bodies —
copy them into the agent-builder-spec tool definitions verbatim. Mark `validation_status: "failed"`
queries with a comment in the data model and exclude them from bootstrap.py step 13 tool creation.

---

## What Good Looks Like

**Lowe's pattern** — complex interdependent model: `store-transactions` data stream (events
upsert into `inventory-positions` via pipeline), `inventory-positions` (computed
`discrepancy_pct` field, geo_point for nearby-store queries), `associate-knowledge-base`
(semantic_text with ELSER), `associate-sessions` (nested conversation_history), `fulfillment-requests`
(written by Workflows). Build order has 17 steps because ELSER must precede KB mapping.

**Citizens Bank pattern** — simpler unified model: `fraud-claims` index (ingested from
three sources via connectors — no custom pipeline, connector handles the ETL), `fraud-escalations`
(written by agent tool calls), `sla-monitoring-telemetry` (agent observability). No data
stream needed — claims are mutable documents. No ELSER endpoint if semantic scene is
de-scoped.

**Migration pattern** — read-heavy, current-state mirroring: `current-state-mirror` index
mirrors the key structure of the customer's existing indices (inferred from diagnostic).
Demo shows before/after on the same data model. Primary artifact is the mapping that
mirrors their schema — not a new one.

## Reference: Elasticsearch Mapping Quick Reference

See `references/mapping-patterns.md` for:
- Complete field type reference with demo use cases
- `semantic_text` exact syntax for ELSER v2
- Data stream template boilerplate
- ILM policy boilerplate (hot-warm-delete pattern)
- Ingest pipeline patterns (enrich, script, upsert)
- Nested vs object vs flattened tradeoffs
