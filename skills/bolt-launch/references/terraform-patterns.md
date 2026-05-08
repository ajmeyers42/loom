# Terraform Patterns Reference

**Loaded by:** `skills/bolt-launch/SKILL.md` (Terraform mode generation)

This file documents HCL patterns for generating `providers.tf`, `main.tf`, and `{slug}.tfvars` for loom engagements. All patterns target the `elastic/elasticstack` + `elastic/ec` provider pair.

**Provider currency:** Always validate provider versions against latest releases before generating HCL. See `reference-repos.md` for check method.

---

## `providers.tf` — Provider Pins

```hcl
terraform {
  required_version = ">= 1.6"
  required_providers {
    elasticstack = {
      source  = "elastic/elasticstack"
      version = "~> 0.11"   # update to latest minor at generation time
    }
    ec = {
      source  = "elastic/ec"
      version = "~> 0.14"   # update to latest minor at generation time
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

provider "ec" {
  apikey = var.ec_api_key
}
```

---

## `{slug}.tfvars` — Engagement Variables

```hcl
# Identity
slug            = "citizens-bank"
engagement      = "Citizens Bank"
deployment_type = "serverless"   # serverless | ech | self_managed | docker
index_prefix    = "cb-"

# Cluster credentials (from .env)
elasticsearch_url = "https://abc123.es.io:443"
kibana_url        = "https://abc123.kb.io:443"
es_api_key        = ""   # set from .env — never hardcode
kibana_api_key    = ""   # set from .env — never hardcode

# Optional
ec_api_key     = ""   # needed only for cloud provisioning resources
elastic_version = "9.4.0"
kibana_solution = "es"   # es | oblt | security
```

---

## Stable UUIDs via `uuid` Provider or `local` Values

Use deterministic IDs for Kibana saved objects so re-apply is idempotent. The UUID5 namespace must match `pipeline-constants.md`:

```hcl
locals {
  # Namespace matches pipeline-constants.md UUID5 namespace
  uuid_ns = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

  # Stable IDs — format: {slug}:{object_name}
  dashboard_fraud_ops_id = uuidv5("url", "${var.slug}:fraud-ops-dashboard")
  dashboard_ai_usage_id  = uuidv5("url", "${var.slug}:ai-usage")
}
```

*Note: HCL `uuidv5` uses the `url` namespace constant which maps to the same UUID5 URL namespace. Generate IDs in Python `bootstrap-data.py` using the same formula and pass them as tfvars when needed, or use `uuidv5("url", ...)` directly in HCL.*

---

## ILM vs DSL Conditional

```hcl
locals {
  use_dsl = var.deployment_type == "serverless"
}

# ILM policy — ECH/self-managed only
resource "elasticstack_elasticsearch_index_lifecycle" "claims_ilm" {
  count = local.use_dsl ? 0 : 1
  name  = "${var.index_prefix}fraud-claims-ilm"

  hot {
    set_priority { priority = 100 }
  }
  delete {
    min_age = "90d"
    delete  {}
  }
}

# Index template with conditional ILM/DSL
resource "elasticstack_elasticsearch_index_template" "claims" {
  name           = "${var.index_prefix}fraud-claims-template"
  index_patterns = ["${var.index_prefix}fraud-claims*"]

  template {
    settings = jsonencode({
      number_of_shards   = 1
      number_of_replicas = 1
      index.lifecycle.name = local.use_dsl ? null : "${var.index_prefix}fraud-claims-ilm"
    })
    # DSL lifecycle embedded in template for serverless
    lifecycle = local.use_dsl ? jsonencode({ data_retention = "90d" }) : null
  }

  composed_of = [
    elasticstack_elasticsearch_component_template.claims_mappings.name,
    elasticstack_elasticsearch_component_template.claims_settings.name,
  ]
}
```

---

## D-026 Tagging — `tags` Maps

All resources that support `tags` must carry `demobuilder:{engagement_id}`. In HCL:

```hcl
locals {
  engagement_id = replace(var.index_prefix != "" ? trimsuffix(var.index_prefix, "-") : var.slug, "/[^a-z0-9]/", "")
  loom_tag = "demobuilder:${local.engagement_id}"

  common_tags = [local.loom_tag]
}

# Example on an alerting rule
resource "elasticstack_kibana_alerting_rule" "fraud_burn_rate" {
  name       = "Citizens — Debit SLO Burn Rate"
  rule_type_id = "slo.rules.burnRate"
  # ...
  tags = local.common_tags
}
```

---

## Kibana Space

**Required on every space resource:** `disabled_features = []` ensures all features are visible. This controls feature *visibility*, not tech preview *activation*. After `terraform apply`, `bootstrap-data.py` must call `PUT /api/spaces/space/{id}` and probe each tech preview feature (D-011) — see bootstrap-data.py guidance.

```hcl
resource "elasticstack_kibana_space" "operator" {
  space_id          = "${var.slug}-operator"
  name              = "${var.engagement} — Operator"
  solution          = var.kibana_solution    # "es" | "oblt" | "security"
  disabled_features = []    # all features visible; required on EVERY space
}

resource "elasticstack_kibana_space" "tenant_a" {
  space_id          = "${var.slug}-tenant-a"
  name              = "${var.engagement} — Tenant A"
  solution          = var.kibana_solution
  disabled_features = []
}
```

---

## NDJSON Saved Objects Import

Dashboards, Lens panels, and other saved objects are imported via NDJSON. Committed NDJSON must have `migrationVersion` and `coreMigrationVersion` stripped:

```hcl
resource "elasticstack_kibana_import_saved_objects" "dashboards" {
  space_id      = elasticstack_kibana_space.demo.space_id
  overwrite     = true
  file_contents = file("${path.module}/../kibana-objects/${var.slug}-dashboards.ndjson")

  depends_on = [elasticstack_kibana_space.demo]
}
```

---

## ELSER Inference Endpoint

```hcl
resource "elasticstack_elasticsearch_inference_endpoint" "elser" {
  inference_id = "${var.index_prefix}elser"
  task_type    = "sparse_embedding"

  # ECH: service = "elastic", model_id = ".elser-2"
  # Serverless: service = "elser", no model_id
  # See inference-config.md
  inference_config = local.use_dsl ? jsonencode({
    service          = "elser"
    service_settings = { num_allocations = 1, num_threads = 1 }
  }) : jsonencode({
    service          = "elastic"
    service_settings = { model_id = ".elser-2", num_allocations = 1, num_threads = 1 }
  })
}
```

---

## Fleet Integration Packages

Install EPM packages before any index templates that depend on them (Path A streams). Use `depends_on` to enforce ordering.

```hcl
resource "elasticstack_fleet_integration" "nvidia_gpu" {
  name    = "nvidia_gpu"
  version = "1.17.0"    # pin to tested version; update at generation time
  force   = false        # set true only if re-installing over existing
}

resource "elasticstack_fleet_integration" "kubernetes" {
  name    = "kubernetes"
  version = "1.62.0"
  force   = false
}

# Path A index templates depend on Fleet packages being installed first
resource "elasticstack_elasticsearch_index_template" "path_a_example" {
  depends_on = [elasticstack_fleet_integration.nvidia_gpu]
  # ...
}
```

---

## Plain Elasticsearch Indices

Use for static/search indices (not data streams). Supports full mapping and settings.

```hcl
resource "elasticstack_elasticsearch_index" "agent_sessions" {
  name               = "${var.index_prefix}agent-sessions"
  number_of_shards   = 1
  number_of_replicas = 1

  mappings = jsonencode({
    properties = {
      "@timestamp"     = { type = "date" }
      session_id       = { type = "keyword" }
      agent_name       = { type = "keyword" }
      model_id         = { type = "keyword" }
      total_tokens     = { type = "long" }
      cost_usd         = { type = "float" }
    }
  })

  settings = jsonencode({
    "index.lifecycle.name" = local.use_dsl ? null : "${var.index_prefix}agent-sessions-ilm"
  })
}
```

---

## Enrich Policy (CREATE only)

Enrich policy *execution* (`_execute`) cannot be done by Terraform — that is a `bootstrap-data.py` step.

```hcl
resource "elasticstack_elasticsearch_enrich_policy" "tenant_lookup" {
  name       = "${var.index_prefix}tenant-lookup"
  policy_type = "match"
  indices    = ["${var.index_prefix}tenant-rate-cards"]
  match_field = "tenant_id"
  enrich_fields = ["tenant_name", "tier", "rate_per_token"]
}
# After terraform apply, bootstrap-data.py must call:
# POST /_enrich/policy/{name}/_execute
```

---

## Kibana Data View

Space-scoped. Create one per index pattern the demo references.

```hcl
resource "elasticstack_kibana_data_view" "gpu_metrics" {
  space_id   = elasticstack_kibana_space.operator.space_id
  name       = "${var.engagement} — GPU Metrics (DCGM)"
  title      = "metrics-nvidia_gpu.dcgm-*"
  time_field_name = "@timestamp"

  depends_on = [elasticstack_kibana_space.operator]
}

resource "elasticstack_kibana_data_view" "k8s_logs" {
  space_id        = elasticstack_kibana_space.tenant_a.space_id
  name            = "${var.engagement} — K8s Pod Logs"
  title           = "logs-kubernetes.container_logs-*"
  time_field_name = "@timestamp"

  depends_on = [elasticstack_kibana_space.tenant_a]
}
```

---

## SLOs (Observability)

`elasticstack_kibana_slo` is a confirmed provider resource. Use it for all SLOs rather than Python API calls.

```hcl
resource "elasticstack_kibana_slo" "gpu_utilization" {
  space_id    = elasticstack_kibana_space.operator.space_id
  name        = "GPU Platform Utilization — All Tenants"
  description = "[v${var.bootstrap_version}] GPU utilization SLO across all tenant namespaces"

  indicator = {
    type = "sli.kql.custom"
    params = {
      index       = "metrics-nvidia_gpu.dcgm-*"
      timestampField = "@timestamp"
      good        = "nvidia_gpu.activity.gpu.pct < 0.85"
      total       = "*"
      filter      = ""
    }
  }

  time_window = {
    duration   = "30d"
    type       = "rolling"
  }

  budgeting_method = "occurrences"
  objective = {
    target = 0.95
  }

  tags = local.common_tags

  depends_on = [elasticstack_kibana_space.operator]
}
```

---

## ML Job Lifecycle (full state machine)

**Required sequence:** job created → job opened → datafeed created → datafeed started. Use state resources to encode the lifecycle in Terraform — this prevents the missing-`_open` bug.

```hcl
resource "elasticstack_elasticsearch_ml_anomaly_detection_job" "gpu_util" {
  job_id      = "${var.index_prefix}gpu-util-anomaly"
  description = "GPU utilization anomaly detection per tenant"

  analysis_config = jsonencode({
    bucket_span = "5m"
    detectors   = [{
      function              = "high_mean"
      field_name            = "nvidia_gpu.activity.gpu.pct"
      partition_field_name  = "host.name"
    }]
    influencers = ["host.name"]
  })

  data_description = jsonencode({
    time_field = "@timestamp"
  })

  custom_settings = jsonencode({
    created_by = "loom"
  })
}

# Step 2: Open the job (REQUIRED before datafeed can start)
resource "elasticstack_elasticsearch_ml_job_state" "gpu_util" {
  job_id = elasticstack_elasticsearch_ml_anomaly_detection_job.gpu_util.job_id
  state  = "opened"

  depends_on = [elasticstack_elasticsearch_ml_anomaly_detection_job.gpu_util]
}

resource "elasticstack_elasticsearch_ml_datafeed" "gpu_util" {
  datafeed_id = "datafeed-${var.index_prefix}gpu-util-anomaly"
  job_id      = elasticstack_elasticsearch_ml_anomaly_detection_job.gpu_util.job_id
  indices     = ["metrics-nvidia_gpu.dcgm-*"]
  query       = jsonencode({ match_all = {} })
  frequency   = "5m"
  scroll_size = 1000

  depends_on = [elasticstack_elasticsearch_ml_job_state.gpu_util]
}

# Step 4: Start the datafeed
resource "elasticstack_elasticsearch_ml_datafeed_state" "gpu_util" {
  datafeed_id = elasticstack_elasticsearch_ml_datafeed.gpu_util.datafeed_id
  state       = "started"

  depends_on = [elasticstack_elasticsearch_ml_datafeed.gpu_util]
}
```

---

## Agent Builder (Terraform Mode)

Agent Builder, tools, and workflows are supported by the `elasticstack` provider:

```hcl
resource "elasticstack_kibana_agentbuilder_tool" "claims_search" {
  space_id    = elasticstack_kibana_space.demo.space_id
  name        = "${var.index_prefix}claims-search"
  description = "Search the fraud claims index"
  type        = "index_search"

  configuration = jsonencode({
    pattern = "${var.index_prefix}fraud-claims"
  })

  tags = local.common_tags
}

resource "elasticstack_kibana_agentbuilder_workflow" "open_case" {
  space_id = elasticstack_kibana_space.demo.space_id
  name     = "${var.slug}-open-fraud-case"
  yaml     = file("${path.module}/../kibana-objects/${var.slug}-open-fraud-case.yml")
  tags     = local.common_tags
}

resource "elasticstack_kibana_agentbuilder_agent" "fraud_assistant" {
  space_id     = elasticstack_kibana_space.demo.space_id
  name         = "Fraud Assistant"
  instructions = file("${path.module}/../kibana-objects/${var.slug}-agent-instructions.txt")

  # D-029: skill_ids = platform skills; tools[0].tool_ids = custom + platform.core.*
  # Before generating this block, probe GET /api/agent_builder/skills to confirm available IDs.
  # If the skills catalog returns 404, use skill_ids = [] (tools-only fallback).
  # Common platform skill IDs (validate against live cluster):
  #   "data-exploration", "visualization-creation", "case-management"
  configuration = jsonencode({
    tools     = [{ tool_ids = [
      elasticstack_kibana_agentbuilder_tool.claims_search.id,
      "platform.core.search",
      "platform.core.generate_esql",
      "platform.core.execute_esql",
    ]}]
    skill_ids = var.agent_platform_skill_ids    # from tfvars; set via skills probe at generation time
  })

  tags = local.common_tags

  depends_on = [
    elasticstack_kibana_agentbuilder_tool.claims_search,
    elasticstack_kibana_agentbuilder_workflow.open_case,
  ]
}
# In {slug}.tfvars:
# agent_platform_skill_ids = ["data-exploration", "visualization-creation"]
# Leave empty [] if GET /api/agent_builder/skills returned 404
```

---

## Files Generated per Engagement (Terraform mode)

```
{slug}/
  deploy/
    providers.tf              # provider pins (version-validated before generation, D-041)
    variables.tf              # variable declarations
    main.tf                   # ALL Layer 2 resources (see resource inventory in plan)
    {slug}.tfvars             # engagement-specific values (no credentials)
    bootstrap-data.py         # Layer 3 ONLY: tech preview probe, enrich execute, bulk seed,
                              #   cases, ELSER warmup, anomaly injection, manifest (D-039)
    kibana-objects/
      {slug}-dashboards.ndjson   # NDJSON authored via DASHBOARD_NDJSON_FORMAT.md (D-017)
      {slug}-*-workflow.yaml     # Workflow YAML files (loaded by agentbuilder_workflow resource)
      {slug}-agent-instructions.txt  # Agent system prompt (loaded by agentbuilder_agent resource)
    .terraform.lock.hcl       # committed (provider hash locks)
    terraform.tfstate         # gitignored — local state; move to S3/GCS for shared teams
    terraform.tfstate.backup  # gitignored
```

**Layer 3 (`bootstrap-data.py`) scope — what Terraform cannot manage:**
- Step 0: version gate 9.4+ (D-033); optional ECH user_settings_json patch
- Step 0.5: tech preview `PUT /api/spaces/space/{id}` + probe per space (D-011); halt if unavailable
- Step 1: enrich policy `_execute` + poll
- Step 2: bulk seed data + `demo_critical_docs` individual verification (D-004)
- Step 3: cases configure + sample cases (no `elasticstack_kibana_cases` resource)
- Step 4: ELSER warmup
- Step 5: anomaly injection + sleep (2 × bucket_span)
- Step 6: manifest write (D-039 `_manifest_add_es` / `_manifest_add_kibana` helpers)

`.gitignore` additions for the engagement workspace:
```
.env
terraform.tfstate
terraform.tfstate.backup
.terraform/
```
