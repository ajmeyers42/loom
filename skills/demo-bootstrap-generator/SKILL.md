---
name: demo-bootstrap-generator
description: >
  Agent B of the two-stage deployment pipeline. Reads the asset-bundle/ produced by
  demo-asset-verifier and generates the deployment artifacts for the target deployment
  type. Terraform-first (D-038): generates main.tf + providers.tf + {slug}.tfvars for
  infrastructure, and bootstrap-data.py for data operations only. Routes to the correct
  deployment-type variant (ECH, Serverless, ECK) based on DEPLOYMENT_TYPE in .env.

  ALWAYS use this skill when the user says "generate the bootstrap", "create the
  deployment scripts", "generate main.tf", or when demo-asset-verifier has completed
  and the SA wants to proceed to deployment artifacts. Requires asset-bundle/
  from demo-asset-verifier — will not run without it (D-045).
---

# Demo Bootstrap Generator

You are generating the deployment artifacts from a verified asset bundle. You do not
design assets, probe APIs, or make judgment calls about what to deploy — that was
`demo-asset-verifier`'s job. You translate the `asset-bundle/asset-index.json` and
`asset-bundle/asset-schema.json` into executable deployment artifacts.

**This skill enforces D-038, D-045, D-046.** Infrastructure goes in Terraform.
Data operations go in `bootstrap-data.py`. Nothing else.

---

## Step 0: Validate Inputs

### Required files
```
{engagement_dir}/deploy/asset-bundle/asset-schema.json   ← written by demo-asset-verifier
{engagement_dir}/deploy/asset-bundle/asset-index.json    ← written by demo-asset-verifier
{engagement_dir}/.env                                     ← credentials + DEPLOYMENT_TYPE
```

**If `asset-schema.json` or `asset-index.json` is missing, halt:**
```
⛔ asset-bundle/ not found or incomplete.
   Run demo-asset-verifier first. demo-bootstrap-generator requires verified
   asset outputs — generating scripts from unverified inputs is not permitted (D-045).
```

### Read `.env` fields
```
DEPLOYMENT_TYPE   → one of: ech, serverless, eck
DEPLOY_MODE       → terraform (default) | python (legacy fallback)
INDEX_PREFIX      → engagement namespace prefix
DEMO_SLUG         → engagement slug
KIBANA_SOLUTION   → es | oblt | security
ELASTIC_VERSION   → informational; must match asset-schema.json platform.es_version
```

### Route to deployment-type variant

Based on `DEPLOYMENT_TYPE`:

| Value | Skill to call |
|---|---|
| `ech` | Read `../demo-bootstrap-ech/SKILL.md` |
| `serverless` | Read `../demo-bootstrap-serverless/SKILL.md` |
| `eck` | Read `../demo-bootstrap-eck/SKILL.md` |

Read the variant skill's SKILL.md now and follow its instructions for the remainder of this skill execution.

---

## What Both Variants Produce

Regardless of variant, the output always follows this split (D-046):

### `deploy/main.tf` (or `deploy/main-serverless.tf`)
Contains all infrastructure resources:
- ILM policies / Data Stream Lifecycle
- Ingest pipelines
- Component templates
- Index templates
- Indices and data streams
- Inference endpoints (ELSER via EIS)
- ML jobs and datafeeds
- Enrich policies (create only — execution is in bootstrap-data.py)
- Kibana space
- Kibana connectors
- Alerting rules
- Saved object imports (dashboards, data views)
- SLOs
- Agent Builder agents and tools
- Workflows
- SIEM detection rules

### `deploy/bootstrap-data.py`
Contains only what Terraform cannot do:
```python
OPERATIONS = [
    "step1_connectivity",        # version gate D-033; manifest init D-039
    "step2_enrich_execute",      # POST /_enrich/policy/{name}/_execute + poll
    "step3_seed_data",           # bulk index all indices from asset-bundle/elasticsearch/seed/
    "step4_assert_viz_fields",   # D-044: assert_viz_fields_populated() for each custom index
    "step5_elser_warmup",        # warm EIS inference endpoint with one test query
    "step6_anomaly_injection",   # inject ML anomaly documents (if ML in scope)
    "step7_manifest_write",      # D-039: write/update demobuilder-manifests/{engagement_id}
]
```

Nothing outside this list belongs in `bootstrap-data.py`. If an operation is in Terraform,
it is not in `bootstrap-data.py`.

### `deploy/providers.tf`
Provider version pins sourced from `references/reference-repos.md` current versions.

### `deploy/{slug}.tfvars`
All engagement-specific values: URLs, API keys (via variable references), index prefix,
slug, space ID, solution type, asset IDs from `asset-index.json`.

---

## Generation Checklist (run before writing any file)

| # | Check | Fail action |
|---|---|---|
| 1 | `asset-schema.json` `platform.version_gate_passed == true` | Halt — version gate must pass |
| 2 | `asset-index.json` has no entries with `validation_status: "failed"` | Halt — fix failed ES|QL queries first |
| 3 | `asset-index.json` has no entries with `all_non_null_confirmed: false` | Halt — fix null fields first |
| 4 | All `deployment_method: "terraform_resource"` assets have a known Terraform resource type | Surface unknown types as blockers |
| 5 | Provider versions checked against `references/reference-repos.md` (D-041) | Update pins before writing providers.tf |
| 6 | `BOOTSTRAP_VERSION` constant set at top of `bootstrap-data.py` (D-030) | Set before writing any other content |
| 7 | `demobuilder_tags()` and `merge_tags()` defined in `bootstrap-data.py` (D-026) | Include in template credential block |
| 8 | All Terraform resources have `tags` or labels from `demobuilder_tags()` where the resource type supports it (D-026) | Add tag block to each resource |

---

## Handoff Summary

```
✅ demo-bootstrap-generator complete

GENERATED FILES
───────────────
  deploy/main.tf              → {N} Terraform resources
  deploy/providers.tf         → elasticstack {version}, ec {version}
  deploy/{slug}.tfvars        → {N} variables
  deploy/bootstrap-data.py    → {N} data operations

DEPLOYMENT INSTRUCTIONS
────────────────────────
  1. Review deploy/main.tf and deploy/bootstrap-data.py (D-024 approval gate)
  2. terraform -chdir=deploy init
  3. terraform -chdir=deploy plan -var-file={slug}.tfvars   ← reviewable plan
  4. (SA approval) terraform -chdir=deploy apply -var-file={slug}.tfvars
  5. python3 deploy/bootstrap-data.py

  For --dry-run: python3 deploy/bootstrap-data.py --dry-run
  (Does not require SA approval — no cluster mutations)
```
