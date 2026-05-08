---
name: weave-query
description: >
  Bridges loom's pipeline with elastic/vulcan to generate validated, parameterized
  ES|QL queries, LLM-produced synthetic datasets, EPR-grounded integration data, and
  tested RAG pipelines. Vulcan handles the bottom-up data + query layer; loom
  consumes its outputs in weave-model to replace hand-authored seed data and ES|QL.

  ALWAYS use this skill when the demo script contains ES|QL-heavy scenes with parameterized
  queries, semantic/RAG search, integration-grounded data (Fleet, Beats, integrations),
  or when the SA asks to "generate synthetic data", "use Vulcan", "run Vulcan first", or
  "generate validated queries". Run BEFORE weave-model — Vulcan outputs are inputs
  to the data modeling step.
---

# Demo Vulcan Generate

You are wiring elastic/vulcan into the loom pipeline to produce cluster-validated
ES|QL queries, synthetic datasets, and optionally integration-grounded or RAG pipelines.

Vulcan assumes a **running Elastic cluster** for indexing and validation. If no cluster is
available, generate Vulcan's config context only (skip indexing + query testing).

Vulcan is a sibling clone at `../vulcan` (same parent as loom). If it is absent,
tell the SA to clone it:

```bash
git clone https://github.com/elastic/vulcan ../vulcan
cd ../vulcan && pip install -r requirements.txt
cp .env.example .env  # fill in ELASTICSEARCH credentials + LLM keys
```

---

## Step 0: Decide Whether Vulcan Applies

Run this skill when **at least one** of the following is true for the current engagement:

| Signal | Source |
|--------|--------|
| ES|QL queries are parameterized (date ranges, account IDs, thresholds) | `{slug}-demo-script.md` mentions `?param`, variable filters, or "parameterized query" |
| Semantic / RAG search is a key demo scene | Script mentions ELSER, `semantic_text`, RERANK, COMPLETION, RAG pipeline |
| Integration-grounded data needed (logs-*, metrics-*) | Script or discovery mentions Fleet, Beats, or specific integrations (APM, system, nginx…) |
| Synthetic data quality is critical (realistic field values, distributions) | SA requests "realistic data" or script demos anomaly detection, ML, or statistical analysis |
| More than 5 distinct ES|QL queries in scope | Script scenes list 5+ unique queries |

**Skip this skill if:**
- The demo has no ES|QL scenes and no semantic search
- The data model is already complete (`{slug}-data-model.json` exists and script hasn't changed)
- `data/{slug}-vulcan-queries.json` already exists and the script hasn't changed
- Vulcan is not installed at `../vulcan` and the SA does not want to install it now

If skipping, note it in the Stage inventory and proceed to weave-model directly.

---

## Step 1: Build the Vulcan Context

From `{slug}-demo-script.md` and `{slug}-discovery.json`, extract the inputs Vulcan needs.
You will pass these to Vulcan either via its Streamlit UI or by constructing the config dict
for programmatic invocation.

```json
{
  "company": "<company name from discovery>",
  "department": "<primary business unit from script>",
  "pain_points": ["<pain_1>", "<pain_2>", "..."],
  "demo_type": "analytics",         // "analytics" (observability/fraud/ops) or "search"
  "use_integrations": false,        // true when logs-* / metrics-* integration grounding needed
  "confirmed_integrations": [],     // e.g. ["elastic_agent", "system", "apm"]
  "include_rag": false,             // true when ELSER / semantic search is in scope
  "skip_indexing": false,           // true if no live cluster available
  "skip_query_testing": false,
  "datasets": [
    {
      "name": "<dataset_name>",     // must match index names in script (e.g. "fraud-claims")
      "description": "<what this data represents>",
      "approximate_rows": 500
    }
  ]
}
```

**demo_type heuristics:**
- `"search"` → script centers on keyword/semantic search, product catalog, document retrieval
- `"analytics"` → script centers on ES|QL aggregations, anomaly scores, operational metrics, fraud detection

**integration grounding:** Set `use_integrations: true` and populate `confirmed_integrations`
when index names in the script match Elastic integration conventions (`logs-system.*`,
`metrics-apm.*`, etc.). Vulcan will fetch EPR schemas and align field names to the integration,
making generated data compatible with shipped integration dashboards.

---

## Step 2: Run Vulcan

### Option A — Streamlit UI (interactive)

```bash
cd ../vulcan
set -a && source .env && set +a
streamlit run app.py
```

In the **Create** tab:
1. Enter the context from Step 1 (company, pain points, department)
2. Select demo type (Analytics or Search)
3. Enable Integration Grounding if applicable (Step 1 `use_integrations`)
4. Type `generate` to start

Vulcan will run through its pipeline phases and produce the demo module under
`../vulcan/demos/<module_name>/`.

### Option B — Programmatic (headless, for scripted pipelines)

```python
import sys, os
sys.path.insert(0, "../vulcan")
from src.framework.orchestrator import ModularDemoOrchestrator

config = {
    # ... context from Step 1 ...
    "demo_output_dir": os.path.expanduser("../vulcan/demos"),
}
orchestrator = ModularDemoOrchestrator(config)
results = orchestrator.generate_new_demo_with_strategy(config)
print(results.get("module_path"))
```

---

## Step 3: Collect Vulcan Outputs

After Vulcan completes, locate the generated module directory:

```
../vulcan/demos/<module_name>/
├── config.json               ← demo metadata, timing, index name map
├── query_strategy.json       ← query plan (concepts, strategy)
├── data_profile.json         ← actual field distributions from indexed data
├── all_queries.json          ← validated, parameterized ES|QL queries
├── query_testing_results.json← pass/fail per query (Layer 1 deterministic results)
├── data_generator.py         ← LLM-authored synthetic data generator
├── query_generator.py        ← ES|QL query module (parameterized)
├── demo_guide.py             ← narrative guide
└── data/
    └── *.csv                 ← generated datasets (one CSV per logical dataset)
```

**Copy the key artifacts into the engagement directory:**

```bash
VULCAN_MODULE="../vulcan/demos/<module_name>"
ENGAGEMENT_DIR="${LOOM_ENGAGEMENTS_ROOT:-$HOME/engagements}/{slug}"

cp "$VULCAN_MODULE/all_queries.json"           "$ENGAGEMENT_DIR/data/{slug}-vulcan-queries.json"
cp "$VULCAN_MODULE/query_testing_results.json" "$ENGAGEMENT_DIR/data/{slug}-vulcan-query-results.json"
cp "$VULCAN_MODULE/data_profile.json"          "$ENGAGEMENT_DIR/data/{slug}-vulcan-data-profile.json"
cp "$VULCAN_MODULE/config.json"                "$ENGAGEMENT_DIR/data/{slug}-vulcan-config.json"
mkdir -p "$ENGAGEMENT_DIR/data/seed"
cp "$VULCAN_MODULE/data/"*.csv                 "$ENGAGEMENT_DIR/data/seed/"
```

---

## Step 4: Review Query Test Results

Read `data/{slug}-vulcan-query-results.json`. For each query:

- **PASS** — query ran against the cluster and returned results. Safe to include in `bootstrap.py`.
- **FAIL** — query did not return results or had syntax errors. Document the failure and either
  fix the ES|QL manually or exclude from the data model.
- **SKIPPED** — `skip_query_testing` was true or cluster was unavailable. Flag as unvalidated.

Produce a summary:

```
Vulcan query validation — {slug}
  Total queries: N
  Passed: N   Failed: N   Skipped: N
  Failed queries: [list names + error snippets]
```

Surface any FAIL/SKIP counts as a risk item in `deploy/{slug}-risks.md` (finish-check will pick this up).

---

## Step 5: Write `data/{slug}-vulcan-queries.json`

This file is the contract passed to weave-model. Structure:

```json
{
  "generated_by": "vulcan",
  "vulcan_module": "<module_name>",
  "demo_type": "analytics|search",
  "integration_grounded": false,
  "integrations": [],
  "include_rag": false,
  "queries": [
    {
      "id": "q_<n>",
      "name": "<human-readable name>",
      "scene": "<demo script scene this query serves>",
      "esql": "FROM <index> | WHERE <condition> | STATS ...",
      "parameters": [
        {"name": "account_id", "type": "keyword", "sample_values": ["ACC-001", "ACC-042"]}
      ],
      "query_type": "scripted|parameterized|rag",
      "validation_status": "passed|failed|skipped",
      "validation_note": ""
    }
  ],
  "rag_pipeline": null,
  "index_name_map": {},
  "data_profile_summary": {
    "<dataset_name>": {
      "row_count": 500,
      "key_fields": ["field_a", "field_b"],
      "date_range": "2025-01-01 / 2026-01-01"
    }
  }
}
```

Map each Vulcan query back to the demo script scene it serves (use scene headings from
`{slug}-demo-script.md` as the `scene` value).

---

## Step 6: Announce and Hand Off

```
✅ weave-query complete

Queries generated: N (N passed, N failed, N skipped)
Integration grounded: yes/no (integrations: ...)
RAG pipeline: yes/no
CSVs under: {engagement_dir}/data/seed/

→ data/{slug}-vulcan-queries.json     (feed to weave-model)
→ data/{slug}-vulcan-data-profile.json
→ data/{slug}-vulcan-query-results.json
→ data/seed/*.csv                       (seed data for bootstrap.py)
```

Proceed to **weave-model** — the next stage will consume these outputs.

---

## Reference: Vulcan's Query Types

| Type | ES|QL pattern | When to use |
|------|------------|-------------|
| `scripted` | Static FROM / WHERE / STATS | Dashboard panels, fixed aggregations |
| `parameterized` | Uses `?param` placeholders resolved from real field values | Agent Builder tools — parameters bound at runtime |
| `rag` | MATCH → RERANK → COMPLETION chain | Semantic search scenes, LLM-augmented answers |

For parameterized queries, Vulcan samples actual field values from the indexed data to produce
meaningful `sample_values` — these feed directly into Agent Builder tool parameter definitions
(see `{slug}-agent-builder-spec.md`).

---

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| `ModuleNotFoundError` | `pip install -r ../vulcan/requirements.txt` |
| `401 Unauthorized` from cluster | Check `ELASTICSEARCH_API_KEY` in `../vulcan/.env` |
| Queries fail with `Unknown column` | Field name mismatch — reconcile with `{slug}-data-model.json` fields once that is generated, then re-run query testing |
| EPR fetch times out | `VULCAN_EPR_CACHE=1` to use cached packages, or set `use_integrations: false` and align field names manually |
| LLM not available | Set `LLM_PROVIDER=mock` in `../vulcan/.env` to skip LLM codegen and use cached modules |
