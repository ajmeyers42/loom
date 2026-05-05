---
name: demo-bootstrap-serverless
description: >
  Serverless deployment variant for demo-bootstrap-generator. Generates Terraform HCL
  targeting the elasticstack provider for Serverless projects and bootstrap-data.py for
  data operations only. Key differences from ECH: no ILM (use Data Stream Lifecycle in
  index template), ELSER uses managed service endpoint, ML job state management differs.
  Targets Elastic Serverless projects.
---

# Demo Bootstrap — Serverless Variant

You are generating Terraform HCL and bootstrap-data.py for a Serverless deployment.
Read `references/terraform-patterns.md`, `references/serverless-differences.md`, and
`references/inference-config.md` now before writing any resource. Every pattern comes
from those reference files — not memory.

**Serverless-specific rules (all sourced from `references/` files):**
- **No ILM:** Serverless uses Data Stream Lifecycle (DSL). Set `lifecycle` in the index template, not a separate ILM policy resource.
- **ELSER:** `service: "elser"` (managed endpoint, no `model_id`) — see `references/inference-config.md`
- **ML field names:** Serverless uses `record_score`, `timestamp`, `partition_field_value`, `by_field_value` — NOT `anomaly_score`, `@timestamp`, `store_id`, `sku`. Confirmed by Step 1f in demo-asset-verifier.
- **Dashboards:** Same `elasticstack_kibana_dashboard` resource as ECH — 9.4 declarative API
- **Agent Builder + Workflows:** Same `elasticstack_kibana_agentbuilder_*` resources as ECH (D-040)
- **Serverless quirks:** See `references/serverless-differences.md` for Liquid syntax differences, stale-read warnings, and saved object format variations

## Step 1: Read Reference Files

Before writing any HCL, read:
```
skills/demo-deploy/references/terraform-patterns.md       ← Serverless HCL patterns
skills/demo-deploy/references/serverless-differences.md   ← Serverless behavioral quirks
skills/demo-deploy/references/inference-config.md         ← ELSER config for Serverless
skills/demo-deploy/references/feature-compatibility.md    ← ILM vs DSL rules
skills/demo-deploy/references/kibana-api-registry.md      ← API shapes
skills/demo-deploy/references/pipeline-constants.md       ← thresholds, UUID5 namespace
skills/demo-deploy/references/asset-manifest.md           ← D-039 manifest helpers
```

## Step 2: Generate `deploy/providers.tf`

Same structure as ECH variant. `ec` provider is used for Serverless project management when
`demo-cloud-provision` created a Serverless project (otherwise omit the `ec` provider block).

## Step 3: Generate `deploy/{slug}.tfvars`

Same as ECH variant. Additionally:
```hcl
deployment_type = "serverless"
```

## Step 4: Generate `deploy/main-serverless.tf`

Serverless resource differences:

### No ILM — use DSL in index template
```hcl
resource "elasticstack_elasticsearch_index_template" "main" {
  name           = "${var.index_prefix}main"
  index_patterns = ["${var.index_prefix}main-*"]
  data_stream {}
  template {
    lifecycle {
      data_retention = "90d"   # DSL — no separate ILM resource
    }
    settings = jsonencode({ ... })
    mappings = jsonencode({ ... })
  }
}
```

### ELSER inference endpoint (Serverless)
```hcl
resource "elasticstack_elasticsearch_inference" "elser" {
  inference_id = "${var.index_prefix}elser"
  task_type    = "sparse_embedding"
  service      = "elser"            # managed endpoint — no model_id
  service_settings = jsonencode({
    num_allocations = 1
    num_threads     = 1
  })
}
```

### ML jobs on Serverless
ML jobs use the same `elasticstack_elasticsearch_ml_job` resource but query field names
differ. Use confirmed field names from `asset-bundle/asset-schema.json` `serverless_ml_fields`
(written by demo-asset-verifier Step 1f). Never use `anomaly_score`, `@timestamp`, `store_id`,
or `sku` as Serverless ML field names.

### Kibana space
Same `elasticstack_kibana_space` resource as ECH with `solution` and `disabled_features = []`.

### Everything else (dashboards, rules, agents, workflows, SLOs)
Same resources as ECH variant. Serverless behavioral differences are in the *content* of
YAML/JSON (already handled by demo-asset-verifier using `asset-schema.json`), not in the
Terraform resource types.

## Step 5: Generate `deploy/bootstrap-data.py`

Use the same template as the ECH variant with these Serverless-specific changes:

### ELSER warmup (Serverless — cold start can take 30+ seconds)
```python
def step5_elser_warmup():
    endpoint_id = p("elser")
    print(f"  Warming Serverless managed ELSER endpoint '{endpoint_id}'...")
    max_attempts = 10
    for i in range(max_attempts):
        try:
            result = es("POST", f"/_inference/sparse_embedding/{endpoint_id}",
                       {"input": "test query for warmup"})
            if result.get("sparse_embedding"):
                print(f"  ✅ ELSER warm (attempt {i+1})")
                return
        except Exception as e:
            if i < max_attempts - 1:
                print(f"  ⏳ Not ready yet ({i+1}/{max_attempts}), waiting 5s...")
                time.sleep(5)
            else:
                raise RuntimeError(f"ELSER endpoint failed to warm after {max_attempts} attempts: {e}")
```

### Step ordering
Same 7-step structure as ECH. No ILM step needed (DSL is in Terraform index template).

## Serverless Checklist (before finalizing output)

| # | Check | Reference |
|---|---|---|
| 1 | No `elasticstack_elasticsearch_index_lifecycle` resources in main-serverless.tf | D-027 + serverless-differences.md |
| 2 | All ELSER endpoints use `service = "elser"` (no model_id) | references/inference-config.md |
| 3 | All ML query field names sourced from `asset-schema.json serverless_ml_fields` | D-012 |
| 4 | Dashboard NDJSON does not contain migrationVersion or coreMigrationVersion | D-017 + serverless-differences.md |
| 5 | Liquid Workflow YAML uses `| first` filter correctly | references/workflow-patterns.md |
| 6 | ELSER warmup uses retry loop (cold start latency) | This file Step 5 |
