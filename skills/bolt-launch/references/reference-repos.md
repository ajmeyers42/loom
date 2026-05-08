# Reference Repos Registry

**Loaded by:** `skills/loom/SKILL.md` Step 0 (currency gate), and any skill that accesses an external repo.

This file is the **single source of truth** for all external repositories referenced anywhere in the loom pipeline. Add new repos here; remove or deprecate here. Skills read paths and check methods from this file rather than hardcoding them.

---

## Registry

### 1. `elastic/demobuilder` — this repo

| Field | Value |
|-------|-------|
| Default path | Workspace root (the repo you're in) |
| Env override | — |
| Check method | `git fetch origin && git status` |
| Scope | Always |
| Blocking? | **Yes** — stale skills drive wrong outputs |
| Notes | If HEAD is behind origin and SA wants to proceed, record the rev and continue with a warning |

---

### 2. `elastic/hive-mind`

| Field | Value |
|-------|-------|
| Default path | `../hive-mind` relative to loom root |
| Env override | `HIVE_MIND_PATH` |
| Check method | `git fetch origin && git status` |
| Scope | Always |
| Blocking? | Warn only |
| Notes | Provides validated patterns: dashboards, workflows, agent-builder, probe detection, data fidelity, SA coaching. Not a hard dependency — pipeline continues if missing. |

---

### 3. `elastic/agent-skills`

| Field | Value |
|-------|-------|
| Default path | Cursor/Claude plugin install (not a local clone) |
| Env override | — |
| Check method | Compare installed plugin version against latest GitHub release tag via `https://api.github.com/repos/elastic/agent-skills/releases/latest` |
| Scope | Always (cloud provisioning, Kibana APIs, Security skills) |
| Blocking? | Warn only — surface install/update command |
| Notes | Full install required (Search + Observability + Security). If not installed, surface: "Install the full elastic/agent-skills plugin per docs/todo.md — include Security skills." |

---

### 4. `elastic/workflows`

| Field | Value |
|-------|-------|
| Default path | `~/Documents/GitHub/workflows` |
| Env override | `WORKFLOWS_REPO_PATH` |
| Check method | `git fetch origin && git status` |
| Scope | When Agent Builder or Workflow YAML is in demo scope |
| Blocking? | Warn only |
| Notes | Authoritative Elastic Workflow Library — YAML examples, Liquid syntax, step type reference. Read before authoring any workflow YAML. |

---

### 5. `elastic/kibana-agent-builder-sdk`

| Field | Value |
|-------|-------|
| Default path | `~/Documents/GitHub/kibana-agent-builder-sdk` |
| Env override | `AGENT_BUILDER_SDK_PATH` |
| Check method | `git fetch origin && git status` |
| Scope | When Agent Builder is in demo scope |
| Blocking? | Warn only |
| Notes | Agent Builder tool/agent API schema. Read before writing any Agent Builder API call. |

---

### 6. `elastic/vulcan`

| Field | Value |
|-------|-------|
| Default path | `../vulcan` relative to loom root |
| Env override | `VULCAN_PATH` |
| Check method | `git fetch origin && git status` |
| Scope | When `weave-query` has run or is in scope |
| Blocking? | Skip silently if not installed |
| Install | `git clone https://github.com/elastic/vulcan ../vulcan && cd ../vulcan && pip install -r requirements.txt` |
| Notes | Optional. Never error if absent; log `⏭ not installed — skipping`. |

---

### 7. `elastic/terraform-provider-elasticstack`

| Field | Value |
|-------|-------|
| Default path | Terraform provider registry (not a local clone) |
| Env override | — |
| Check method | `https://api.github.com/repos/elastic/terraform-provider-elasticstack/releases/latest` → compare `tag_name` against pin in `deploy/providers.tf` |
| Scope | When `DEPLOY_MODE=terraform` |
| Blocking? | Warn only — surface changelog URL, ask SA to confirm pin before HCL generation |
| Current known resources | `elasticsearch_index`, `elasticsearch_index_template`, `elasticsearch_component_template`, `elasticsearch_data_stream`, `elasticsearch_data_stream_lifecycle`, `elasticsearch_index_lifecycle`, `elasticsearch_ingest_pipeline`, `elasticsearch_enrich_policy`, `elasticsearch_ml_anomaly_detection_job`, `elasticsearch_ml_datafeed`, `elasticsearch_ml_job_state`, `elasticsearch_inference_endpoint`, `kibana_space`, `kibana_action_connector`, `kibana_alerting_rule`, `kibana_data_view`, `kibana_import_saved_objects`, `kibana_slo`, `kibana_agentbuilder_agent`, `kibana_agentbuilder_tool`, `kibana_agentbuilder_workflow`, `kibana_security_detection_rule`, `kibana_install_prebuilt_rules`, `fleet_*` |
| Notes | Re-check resource list on each major version bump. |

---

### 8. `elastic/terraform-provider-ec`

| Field | Value |
|-------|-------|
| Default path | Terraform provider registry (not a local clone) |
| Env override | — |
| Check method | `https://api.github.com/repos/elastic/terraform-provider-ec/releases/latest` → compare `tag_name` against pin in `deploy/providers.tf` |
| Scope | When `DEPLOY_MODE=terraform` |
| Blocking? | Warn only — same as elasticstack |
| Current known resources | `ec_deployment`, `ec_elasticsearch_project`, `ec_observability_project`, `ec_security_project`, `ec_deployment_traffic_filter`, `ec_serverless_traffic_filter`, `ec_organization`, `ec_snapshot_repository` |
| Notes | Scope: cloud provisioning only. Stack config belongs in `elasticstack` provider. |

---

## Currency Check Report Format

```
🔄  Reference Currency Gate (Step 0)
  loom                      ✅  up to date (main, rev abc1234)
  hive-mind                        ⚠️   2 commits behind — run: git pull --ff-only
  agent-skills                     ✅  v2.4.1 (latest)
  elastic/workflows                ✅  up to date (main, rev 9f3a21c)
  elastic/kibana-agent-builder-sdk ✅  up to date (main, rev c77d802)
  elastic/vulcan                   ⏭   not installed — skipping
  terraform-provider-elasticstack  ⚠️   pinned v0.11.4 → latest v0.11.9 (changelog: https://github.com/elastic/terraform-provider-elasticstack/releases/tag/v0.11.9)
  terraform-provider-ec            ✅  pinned v0.14.1 = latest
```

---

## Rules

- **Blocking**: Only `elastic/demobuilder` itself causes a pipeline halt if stale. Ask SA before continuing.
- **Warn-and-continue**: All other repos. Note stale state, recommend pull/update, proceed unless SA objects.
- **Scope-conditional**: Check Terraform providers only when `DEPLOY_MODE=terraform` is set or TF work is being initiated. Check `workflows` and `kibana-agent-builder-sdk` only when those features are in demo scope.
- **Missing optional repo**: Log `⏭ not installed — skipping`. Never error.

---

## Adding or Retiring a Repo

To add a new reference repo:
1. Add a numbered entry to this file with all fields populated.
2. Update the currency gate in `skills/loom/SKILL.md` Step 0 to include it.
3. Record the decision in `docs/decisions.md`.

To retire a repo:
1. Mark the entry `**DEPRECATED**` with a note on what replaced it.
2. Update skills that referenced it.
3. The currency gate skips deprecated entries.
