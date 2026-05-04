# Terraform Patterns Reference

**Loaded by:** `skills/demo-deploy/SKILL.md` (Terraform mode generation)

This file documents HCL patterns for generating `providers.tf`, `main.tf`, and `{slug}.tfvars` for demobuilder engagements. All patterns target the `elastic/elasticstack` + `elastic/ec` provider pair.

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
  demobuilder_tag = "demobuilder:${local.engagement_id}"

  common_tags = [local.demobuilder_tag]
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

```hcl
resource "elasticstack_kibana_space" "demo" {
  space_id  = var.slug
  name      = var.engagement
  solution  = var.kibana_solution    # "es" | "oblt" | "security"
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

  configuration = jsonencode({
    tools      = [{ tool_ids = [elasticstack_kibana_agentbuilder_tool.claims_search.id] }]
    skill_ids  = []
  })

  tags = local.common_tags

  depends_on = [
    elasticstack_kibana_agentbuilder_tool.claims_search,
    elasticstack_kibana_agentbuilder_workflow.open_case,
  ]
}
```

---

## Files Generated per Engagement (Terraform mode)

```
{slug}/
  deploy/
    providers.tf              # provider pins (version-validated before generation)
    variables.tf              # variable declarations
    main.tf                   # all resource definitions
    {slug}.tfvars             # engagement-specific values (no credentials)
    bootstrap-data.py         # enrich execute, bulk seed, ELSER warm, anomaly injection, manifest
    .terraform.lock.hcl       # committed (provider hash locks)
    terraform.tfstate          # gitignored — local state; move to S3/GCS for shared teams
    terraform.tfstate.backup   # gitignored
```

`.gitignore` additions for the engagement workspace:
```
.env
terraform.tfstate
terraform.tfstate.backup
.terraform/
```
