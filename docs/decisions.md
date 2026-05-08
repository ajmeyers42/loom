# loom — Architecture Decisions

*Rationale and enforcement contracts for every binding decision in the pipeline.*
*Updated as significant decisions are made.*

**Format:** Each entry has:
- **Status** — Active | Superseded (see D-NNN) | Informational
- **Enforced by** — the specific mechanism that implements this decision at runtime. "Prose in SKILL.md" is NOT acceptable here. If enforcement is pending, it is flagged as such.
- **Rationale** — why this decision was made
- **Date / Session** — provenance

> **Rule (D-042):** When a `references/` file and a `SKILL.md` prose rule conflict, the reference file wins. SKILL.md files describe process steps; `references/` files own constants, thresholds, and API shapes. This file owns *why* and *where*; `references/` files own *how* and *what*.

---

## D-001: Per-engagement `.env` file for credential isolation

**Status:** Active  
**Enforced by:** `bolt-spin` writes `.env` to `{engagement_dir}/` on create; `bolt-bootstrap` reads `.env` from `{engagement_dir}/` and halts if missing. Copy workflow for shared clusters: `cp {slug1}/.env {slug2}/.env` then update 3 fields.

**Rationale:** An SE running demos for multiple customers simultaneously needs clean credential and namespace separation. A global config risks cross-contamination.

**Concrete:** The `p(name)` helper in generated scripts applies `INDEX_PREFIX` to every index name, template name, and pipeline name so all resources carry the engagement namespace prefix.

**Date:** 2026-04-15 | **Session:** initial build

---

## D-002: Idempotent deployment with check-before-create

**Status:** Active  
**Enforced by:** `skills/bolt-launch/templates/bootstrap-template.py` — every step function checks existence before creating. `--step N` flag resumes from a specific step. Data load checks doc count before loading (90% threshold). These patterns are in the template and cannot be removed without breaking the template contract.

**Rationale:** A failed deploy at step 9 shouldn't require tearing down steps 1–8. Demo environments are time-pressured.

**Date:** 2026-04-15 | **Session:** initial build

---

## D-003: Separate provision and deploy skills

**Status:** Active  
**Enforced by:** Skill boundaries — `bolt-spin` ends at `.env` write. `bolt-bootstrap` (and its variants) begin at `.env` read. Neither skill calls the other.

**Rationale:** An SE might provision once and deploy many times (different `INDEX_PREFIX` per customer on the same cluster). Combining the two forces unnecessary reprovisioning.

**Date:** 2026-04-15 | **Session:** initial build

---

## D-004: `demo_critical_docs` as first-class concept in the data model

**Status:** Active  
**Enforced by:** `weave-model` Step 4 requires `demo_critical_docs` array in each index spec. `bootstrap-data.py` indexes demo_critical_docs individually (not in bulk) and verifies each by ID/field. `finish-check` Step 2 lists them explicitly in the data layer checks.

**Rationale:** Bulk doc count statistics don't catch missing scenario-critical documents. A demo that depends on merchant VND-0412 having 7 suspicious claims fails visibly if those docs aren't there.

**Date:** 2026-04-15 | **Session:** initial build

---

## D-005: Two-dimensional shard density metric

**Status:** Active  
**Enforced by:** `warp-scan` SKILL.md Step 3 output — both axes are required in the current-state report.

**Rationale:** Single-axis shard/GB rated DT SOC-T as healthy (0.027 shards/GB) while 211 shards/node with 30GB heap is a separate signal. One metric misleads in opposite directions depending on cluster topology.

**Thresholds:**
- Shards/GB: <0.1 (>10GB avg) → healthy, 0.1–1 → monitor, 1–20 → elevated, >20 → many tiny shards
- Shards/node/heap: <20 → healthy, 20–40 → elevated, >40 → high

**Date:** 2026-04-15 | **Session:** initial build (corrected via DT validation)

---

## D-006: Negative assertions in evals must specify scope

**Status:** Informational  
**Enforced by:** Eval authors must include `scope` qualifier on negative assertions ("not mentioned in talking points" not "not mentioned anywhere"). No runtime enforcement — code review check.

**Rationale:** A skill may correctly mention a competitor in an internal "do not mention" instruction block for SE awareness. A blunt full-document assertion falsely fails.

**Date:** 2026-04-15 | **Session:** post-mortem

---

## D-007: elastic/agent-skills as the execution layer for asset authoring

**Status:** Active — extended by D-045  
**Enforced by:** `finish-verify` SKILL.md Step 2 skill dispatch table — each asset class maps to a specific `elastic/agent-skills` skill call. Custom API code in generated scripts is only permitted for asset classes with no matching skill. The dispatch table in `finish-verify/SKILL.md` is the authoritative routing list.

**Rationale:** The Elastic-maintained skills handle auth, error handling, and API version differences for Cloud, Kibana, and Elasticsearch APIs. Duplicating this in custom code creates maintenance debt and version drift.

**Skill dispatch (non-exhaustive):**
| Asset class | Skill to call |
|---|---|
| Kibana dashboards, Lens panels | `kibana/kibana-dashboards` |
| Observability SLOs | `observability/manage-slos` |
| Alerting rules (inc. SLO burn-rate) | `kibana/kibana-alerting-rules` |
| Connectors (Slack, webhook, PD) | `kibana/kibana-connectors` |
| Agent Builder agents + tools | `kibana/agent-builder` |
| Vega / Vega-Lite visualizations | `kibana/kibana-vega` |
| Security / SIEM detection rules | `security/detection-rule-management` |
| Security sample data | `security/generate-security-sample-data` |
| Alert triage + cases | `security/alert-triage`, `security/case-management` |
| ES|QL query validation | `elasticsearch/elasticsearch-esql` |
| Bulk file ingestion | `elasticsearch/elasticsearch-file-ingest` |
| Workflow YAML authoring | `hive-workflows` skill + `hive-mind/patterns/workflows/` |

**Date:** 2026-04-15 | **Session:** post-mortem — extended 2026-05-05

---

## D-008: wind-pulse and wind-reset as lifecycle skills

**Status:** Active  
**Enforced by:** Skills exist and are registered in the orchestrator as post-deploy lifecycle operations. `wind-reset` reads D-039 manifest as primary delete source.

**Date:** 2026-04-15 | **Session:** post-mortem

---

## D-009: Orchestrator surfaces missing-plugin errors clearly

**Status:** Active  
**Enforced by:** Orchestrator Step 0 dependency check — if `elastic/agent-skills` is not installed, the orchestrator outputs a clear install message referencing `docs/todo.md` before any pipeline stage runs.

**Date:** 2026-04-15 | **Session:** post-mortem

---

## D-010: `docs/` directory for pipeline-level documentation

**Status:** Informational  
**Enforced by:** Convention — no runtime enforcement.

**Date:** 2026-04-15 | **Session:** post-mortem

---

## D-011: Feature flag verification applies to Serverless AND ECH

**Status:** Active  
**Enforced by:** `finish-verify` Step 1 probe sequence — Agent Builder and Workflows feature availability probed via `GET /api/agent_builder/agents` (404 = not enabled) and `GET /api/workflows` (404 = not enabled) before any asset authoring for those features begins.

**Rationale:** Agent Builder and Workflows are not enabled by default on new projects on either deployment type. Assuming they're available causes mid-demo failures.

**Date:** 2026-04-15 | **Session:** first-gen review; corrected 2026-04-15

---

## D-012: Serverless ML field names probed before any query or dashboard

**Status:** Active  
**Enforced by:** `weave-train` SKILL.md requires `GET .ml-anomalies-*/_mapping` before writing any query. `finish-verify` Step 1 includes ML mapping probe when ML scenes are in scope.

**Rationale:** `anomaly_score`/`@timestamp`/`store_id`/`sku` do not exist on Serverless. The actual fields are `record_score`/`timestamp`/`partition_field_value`/`by_field_value`. A 2-minute mapping check prevents hours of rework.

**Date:** 2026-04-15 | **Session:** first-gen review

---

## D-013: Workflow reference required before authoring any Workflow YAML

**Status:** Active  
**Enforced by:** `finish-verify` Step 2 — when Workflows are in scope, the `hive-workflows` skill is called with `hive-mind/patterns/workflows/WORKFLOWS_API_REFERENCE.md` and `WORKFLOW_YAML_STEP_TYPES.md` passed as context inputs. No Workflow YAML is authored without these references loaded.

**Rationale:** Workflow debugging took ~3h in first-gen because reference material was only found after problems were encountered. The `| first` Liquid filter, `_geo_distance` sort limitation, and stale-read warning are all documentable upfront.

**Date:** 2026-04-15 | **Session:** first-gen review

---

## D-014: ELSER service body differs between Serverless and ECH

**Status:** Active  
**Enforced by:** `references/inference-config.md` — canonical config for both deployment types. `bolt-ech` and `bolt-serverless` Terraform patterns read from this reference file. `bootstrap-data.py` template reads from this reference file.

**Concrete:** Serverless: `"service": "elser"` (no `model_id`). ECH 9.4+: `"service": "elastic"`, `model_id: ".elser-2"` (EIS, per D-028). `"service": "elasticsearch"` is never used for embeddings.

**Date:** 2026-04-15 | **Session:** first-gen review

---

## D-015: T-10min session cleanup is a required checklist item

**Status:** Active  
**Enforced by:** `finish-check` SKILL.md Step 4 output template includes the 10-minute `_delete_by_query` step as a mandatory non-removable checklist item.

**Rationale:** Pre-demo testing populates session history with test conversation turns that appear during the live demo.

**Date:** 2026-04-15 | **Session:** first-gen review

---

## D-016: `KIBANA_API_KEY` is a required `.env` field

**Status:** Active  
**Enforced by:** `bolt-bootstrap` Step 0 `.env` validation — halts if `KIBANA_API_KEY` is missing or empty, regardless of deployment type. `references/env-reference.md` marks it as required. `bolt-spin` writes it during provisioning.

**Rationale:** API key privilege requirements for Kibana vs Elasticsearch are under active product change. Separate keys are the safe default. First-gen hit 401 responses mid-build when this was not required upfront.

**Date:** 2026-04-15 | **Session:** first-gen review; elevated to required 2026-04-15

---

## D-017: Export-first dashboard pattern; never hand-write Lens NDJSON

**Status:** Active  
**Enforced by:** `finish-verify` Step 2 calls `kibana/kibana-dashboards` skill for all dashboard authoring. Hand-writing Lens JSON directly is not a valid path. If a dashboard must be authored from scratch without a live cluster, use `hive-mind/patterns/dashboards/DASHBOARD_NDJSON_FORMAT.md` as the format reference via the `kibana-dashboards` skill.

**Rationale:** Hand-written Lens panels took ~3h in first-gen due to format errors. The Serverless inline `embeddableConfig.attributes` format differs from all public examples and changes between versions. Export-first or skill-authored produces a valid template in minutes.

**Date:** 2026-04-15 | **Session:** first-gen review

---

## D-018: ML datafeed `geo_point` workaround via `runtime_mappings`

**Status:** Active  
**Enforced by:** `weave-train` SKILL.md datafeed config section — when the source index contains a `geo_point` field, a `runtime_mappings` shadow is added to the datafeed config.

**Rationale:** ML datafeeds cannot natively consume `geo_point` fields. The first-gen hit this with `store_location`. Runtime mapping shadows the field as a keyword emitting empty string.

**Date:** 2026-04-15 | **Session:** first-gen review

---

## D-019: Engagement collateral under `{slug}/` subfolder

**Status:** Active — see also D-023 and D-037  
**Enforced by:** Orchestrator Step 1 `mkdir -p` pattern creates audience-scoped subfolders. All skill output path specs use subfolder paths.

**Date:** 2026-04-20 | **Session:** workspace organization

---

## D-020: Default to latest GA for new stacks; validate version for existing

**Status:** Active  
**Enforced by:** `finish-verify` Step 0 — mandatory `GET /` and `GET {kibana}/api/status` on any existing cluster before any asset authoring begins. Result written to `asset-bundle/asset-schema.json` `platform.version`. `bootstrap-data.py` template Step 1 version gate warns if `.env ELASTIC_VERSION` disagrees with live cluster.

**Rationale:** ES|QL, APIs, ML, Kibana embeddables, Agent Builder, and Workflows all vary by version. Assuming "latest" on a customer's 8.x cluster causes failed demos.

**Date:** 2026-04-20 | **Session:** version policy

---

## D-021: Enterprise showcase; multi-input; all solution areas in scope

**Status:** Active  
**Enforced by:** `warp-listen` and `weave-script` scope extraction — neither defaults to search-only. Cross-solution demos are valid when inputs support them. No runtime gate; delivery risk flagged by `finish-check` if scope is narrower than inputs warrant.

**Date:** 2026-04-20 | **Session:** solution scope and inputs

---

## D-022: Solution-first narrative in scripts and plans

**Status:** Active  
**Enforced by:** `finish-check` Step 2 script narrative check — flags as delivery risk if script opens capability-first without an outcome hook for exec or mixed audiences.

**Date:** 2026-04-20 | **Session:** narrative arc

---

## D-023: `LOOM_ENGAGEMENTS_ROOT` — engagements outside the repo

**Status:** Active  
**Enforced by:** Orchestrator Step 1 path resolution — `{engagement_dir}` is always under `${LOOM_ENGAGEMENTS_ROOT:-$HOME/engagements}/{slug}/`. Never under the loom repo root. See `docs/engagements-path.md`.

**Date:** 2026-04-21 | **Session:** portable engagements root

---

## D-024: `asset-bundle/` as the review gate; single deployment executable

**Status:** Active — updated to reflect asset-bundle architecture  
**Enforced by:** `finish-verify` outputs to `{engagement_dir}/deploy/asset-bundle/`. SA reviews `asset-bundle/` contents before `bolt-bootstrap` runs. `bolt-bootstrap` reads `asset-bundle/` as its primary input — it does not re-derive assets from prose. Cluster deploy requires explicit SA approval after review of `main.tf` / `bootstrap-data.py` and platform audit outputs.

**Rationale:** Separating *planning complete* from *deploy authorized* prevents half-reviewed scripts from hitting clusters. The `asset-bundle/` directory replaces the prior `.ndjson`/`kibana-objects/` pattern with a single reviewed artifact set.

**Date:** 2026-04-16 | **Session:** artifact layout + deploy gate — updated 2026-05-05

---

## D-025: Every artifact must be deployable on a real Elastic stack

**Status:** Active  
**Enforced by:** `finish-verify` Step 1 schema probe gate (D-043 Rule 3) — no asset is authored against a field that wasn't confirmed by probe. `elasticsearch/elasticsearch-esql` skill validates every ES|QL query against the live cluster before it is stored in `asset-bundle/`. `finish-check` Step 2 version alignment check flags unverified mappings as conditional-go.

**Rationale:** Demos fail in front of customers when types or payloads are "almost" right. Binding definitions to Elastic's own contracts via live probes keeps scripts honest.

**Date:** 2026-04-16 | **Session:** datatype and deployability contract

---

## D-026: Engagement tag on all tagged deploy assets

**Status:** Active  
**Enforced by:** `bootstrap-data.py` template defines `loom_tags()` and `merge_tags()` helper functions at file top. These are called on every resource payload that accepts `tags`. Terraform resources use a `tags` local variable populated from the same formula. `references/loom-tagging.md` is the canonical tag format spec.

**Concrete:** Tag value = `loom:{engagement_id}` where `engagement_id` = `INDEX_PREFIX` normalized (hyphens/underscores/whitespace removed, lowercase), else `DEMO_SLUG` normalized. `DEMO_ASSET_TAG` in `.env` overrides.

**Date:** 2026-04-16 | **Session:** engagement tagging

---

## D-027: ILM defaults to hot-only; no `rollover` on plain indices

**Status:** Active  
**Enforced by:** `references/feature-compatibility.md` ILM section — Terraform ILM patterns and `bootstrap-data.py` template ILM step read from this reference. `weave-model` Step 2 ILM note cites this decision.

**Hard rules (non-negotiable):**
- Default: hot phase (`set_priority`) + `delete` phase only
- Never `rollover` on plain indices — requires `index.lifecycle.rollover_alias`; errors immediately without it
- `forcemerge` in hot also requires rollover; omit when rollover is absent
- Warm/cold/frozen phases: only when engagement explicitly requires tiered storage AND those node roles exist on the target cluster
- Data streams: `rollover` is valid and appropriate

**Date:** 2026-04-22 | **Session:** Citizens Bank 9.4 deployment

---

## D-028: Use EIS for embeddings and reranking; ML nodes for anomaly detection only

**Status:** Active  
**Enforced by:** `references/inference-config.md` — canonical service names and model IDs by deployment type. `bolt-ech` and `bolt-serverless` Terraform inference endpoint patterns read from this reference. `bootstrap-data.py` template ELSER step reads from this reference.

**Concrete:** EIS sparse embedding: `PUT /_inference/sparse_embedding/{id}` with `service: "elastic"`, `model_id: ".elser-2"` (ECH). Serverless: `service: "elser"`. Never `service: "elasticsearch"` for embeddings.

**Date:** 2026-04-22 | **Session:** Citizens Bank 9.4 deployment

---

## D-029: Agent Builder: `configuration.skill_ids` for platform skills

**Status:** Active  
**Enforced by:** `kibana/agent-builder` skill — it probes `GET /api/agent_builder/skills` before creating/updating agents. `references/kibana-api-registry.md` D-029 section contains the confirmed API shape. `finish-verify` Step 1 includes agent-builder skills probe when Agent Builder is in scope.

**Concrete:** Platform skills go in `configuration.skill_ids`. Individual tools (custom ES|QL, index_search, workflow, platform.core.*) go in `configuration.tools[0].tool_ids`.

**Date:** 2026-04-22 | **Session:** Citizens Bank 9.4 deployment

---

## D-030: `BOOTSTRAP_VERSION` as single source of truth across versioned assets

**Status:** Active  
**Enforced by:** `bootstrap-data.py` template has `BOOTSTRAP_VERSION = "X.Y.Z"` as the first constant. Terraform `locals.bootstrap_version`. Both are updated on any structural asset change. Version is embedded in asset descriptions as `[v{version}] ...` prefix.

**Date:** 2026-04-22 | **Session:** Citizens Bank 9.4 deployment

---

## D-031: Cluster-resident asset manifest

**Status:** Superseded — see D-039  
**Enforced by:** See D-039.

**Date:** 2026-04-22 | **Session:** post-mortem gap remediation

---

## D-032: Managed assets preferred; clone before modifying; never patch originals

**Status:** Active  
**Enforced by:** `finish-verify` Step 1 — `GET /api/fleet/epm/packages/{name}/assets` enumerates what each installed package already ships before any custom asset is authored for that domain. Package-shipped assets go into `asset-bundle/` as-is (referenced by ID). Custom assets are authored only for scenes or signals the package does not cover. `security/detection-rule-management` skill implements the D-032 clone pattern natively.

**Managed-first preference order:**
1. Use managed asset as-is — write its ID to `asset-bundle/asset-index.json`
2. Reference managed asset in a custom dashboard (embed by ID)
3. Clone with `[{SLUG}]` prefix — only when content modification is required

**Date:** 2026-04-22 | **Session:** post-mortem gap remediation

---

## D-033: API baseline is Elastic 9.4+; no pre-9.x shims

**Status:** Active  
**Enforced by:** `finish-verify` Step 0 version gate — probes `GET /` and halts if version < 9.4 unless `SKIP_VERSION_CHECK=true`. `bootstrap-data.py` template Step 1 contains the same gate as a second check at execution time.

**Concrete:** Bootstrap halts on clusters below 9.4. All Terraform resources and `bootstrap-data.py` patterns target 9.4 API shapes only. See `references/feature-compatibility.md` for version-specific behavior table.

**Date:** 2026-04-22 | **Session:** post-mortem gap remediation

---

## D-034: hive-mind as pattern reference library

**Status:** Superseded — see D-041 and D-045  
**Enforced by:** See D-041 (currency gate) and D-045 (asset authoring via skills that use hive-mind patterns).

**Date:** 2026-04-21 | **Session:** hive-mind comparison

---

## D-035: Demo ideation as Stage 0 in the pipeline

**Status:** Active  
**Enforced by:** Orchestrator Step 0b skip condition — ideation is skipped only when discovery notes, diagnostic, or prior pipeline outputs (`{slug}-discovery.json`, `{slug}-ideation.md`) already exist. No fallback to a "default demo" shape.

**Date:** 2026-04-21 | **Session:** hive-mind comparison and adoption

---

## D-036: Token visibility as standard feature for Agent Builder engagements

**Status:** Active  
**Enforced by:** `weave-model` Step 5c — `{prefix}agent-sessions` index included in `build_order` when Agent Builder is in scope. Opt-out via `INCLUDE_TOKEN_VISIBILITY=false` in `.env`.

**Date:** 2026-04-21 | **Session:** hive-mind comparison and adoption

---

## D-037: Audience-scoped subfolders within the engagement directory

**Status:** Active  
**Enforced by:** Orchestrator Step 1 `mkdir -p` pattern creates all four subdirectories. Every skill output path spec uses the appropriate subfolder. No skill writes files to the engagement root except `.env` and `.env.example`.

| Folder | Audience | Contents |
|---|---|---|
| `opportunity/` | AE, SDR, SA | Customer-facing docs, team alignment gate |
| `demo/` | SA | Discovery JSON, diagnostic, platform audit, script, agent spec |
| `data/` | SA, engineer | Data model, ML config, Vulcan outputs, mappings, pipelines, seed |
| `deploy/` | SA | `bootstrap-data.py`, `main.tf`, teardown, checklist, risks, `asset-bundle/` |

**Date:** 2026-05-01 | **Session:** Engagement folder reorganization

---

## D-038: Terraform deploy mode via `DEPLOY_MODE` env var; Terraform-first

**Status:** Active  
**Enforced by:** `bolt-bootstrap` SKILL.md routes to ECH or Serverless Terraform variant when `DEPLOY_MODE=terraform` (default). Python mode (`DEPLOY_MODE=python`) is the legacy fallback for toolchain issues only. New engagements use Terraform.

**Layer split:**
- **Terraform (`main.tf`):** ILM/DSL, ingest pipelines, component templates, index templates, indices, data streams, inference endpoints, ML jobs/datafeeds, enrich policies (create only), Kibana spaces, connectors, alerting rules, saved objects import, Agent Builder agents/tools, Workflows
- **Python (`bootstrap-data.py`):** Enrich policy execution + polling, bulk seed data ingestion, ELSER warm-up, anomaly injection, D-039 manifest write

**Date:** 2026-05-02 | **Session:** Bootstrap to Terraform investigation

---

## D-039: Dynamic asset manifest — trusted source for teardown

**Status:** Active — supersedes D-031  
**Enforced by:** `bootstrap-data.py` template defines `_manifest_add_es(type, id, **meta)` and `_manifest_add_kibana(space_id, type, id, **meta)` helpers. These are called after every resource creation. `wind-reset` reads the manifest at `GET /loom-manifests/_doc/{engagement_id}` as the primary delete source. The manifest index is never deleted.

**Date:** 2026-05-02 | **Session:** Bootstrap to Terraform investigation

---

## D-040: Agent Builder and Workflows supported in Terraform mode

**Status:** Active  
**Enforced by:** `bolt-ech` and `bolt-serverless` Terraform patterns include `elasticstack_kibana_agentbuilder_agent`, `elasticstack_kibana_agentbuilder_tool`, and `elasticstack_kibana_agentbuilder_workflow` resources. Complex conditional tool wiring that cannot be expressed declaratively uses Python in `bootstrap-data.py`.

**Date:** 2026-05-02 | **Session:** Bootstrap to Terraform investigation

---

## D-041: Pipeline-wide Reference Currency Gate

**Status:** Active — supersedes D-034  
**Enforced by:** Orchestrator Step 0 — runs currency checks for all repos in `references/reference-repos.md` before any pipeline stage. Only `elastic/loom` is blocking; all others warn-and-continue.

**Date:** 2026-05-02 | **Session:** Bootstrap to Terraform investigation

---

## D-042: Reference file authority — `references/` files win over SKILL.md prose

**Status:** Active  
**Enforced by:** SKILL.md files are stripped of inline constants, thresholds, and API shapes and replaced with `→ see references/{file}.md`. When a value in a reference file conflicts with text in a SKILL.md, the reference file wins. This is enforced by removing inline copies — a decision in prose is not an enforcement mechanism.

**Date:** 2026-05-02 | **Session:** Bootstrap to Terraform investigation

---

## D-043: Integration-first data sourcing; schema gate before any asset authoring

**Status:** Active  
**Enforced by:** `finish-verify` is a hard gate — Step 1 (probe) must complete and write `asset-bundle/asset-schema.json` before Step 2 (author assets) begins. No asset that queries an index may be authored until that index's field schema is confirmed in `asset-schema.json`. This is structural: `bolt-bootstrap` reads `asset-schema.json` as a required input and halts if it's absent or empty.

**Three binding rules:**

**Rule 1 — Agent-based integrations for Obs/Sec; use package assets first:**
- Observability/Security data comes from Fleet integrations (EPR packages), not Prometheus scrapers
- Package-shipped assets (dashboards, rules, ML jobs, data views) are used as-is unless inadequate for a required demo scene. Custom assets fill gaps only.
- Probe sequence: `GET /api/fleet/epm/packages/{name}` + `GET /api/fleet/epm/packages/{name}/assets` before authoring any custom asset for that domain

**Rule 2 — Custom search mappings may be iterative:**
- Custom indices for search use cases may evolve. No special gate beyond D-025 field-type compliance.

**Rule 3 — Schema must exist before assets that query it:**
```
GET /_index_template/*
GET /_component_template/{name}@package   # integration streams
GET /{index}/_mapping                      # custom indices
```
No dashboard panel, alerting rule, SLO query, workflow step, or Agent Builder tool that references an index may be authored until these probes confirm the field schema. Violating Rule 3 is the root cause of "Unknown column", "no such index", and "empty dashboard" failures.

**Date:** 2026-05-05 | **Session:** lenovo-gaiaas dashboard rebuild

---

## D-044: All mapped fields in custom indices must be populated at seed time

**Status:** Active  
**Enforced by:** `bootstrap-data.py` template — `assert_viz_fields_populated(index, viz_fields)` is called after every `_bulk_index` for a custom index. Raises `RuntimeError` if any viz-queried field has nulls, halting the bootstrap before any dashboard creation step runs. `weave-model` Step 4 requires the field population checklist table before the data model is finalized.

**Rules:**
1. Every viz-queried field must be non-null in 100% of seed documents
2. Every mapped field must have a non-null value (use sentinels: `"none"`, `"unknown"`, `0.0` for fields with no business value)
3. Derived fields (`risk_label`, `on_track`, etc.) computed and stored at seed time — never deferred to query time
4. `bootstrap-data.py` validation gate runs `POST /{index}/_count {"query": {"exists": {"field": "{field}"}}}` for every viz-queried field after seeding

**Anti-pattern:** `tf-entity-store` deployed with `risk_label` null in all seed docs → `Unknown column [risk_label]` from ES|QL → broken panel rendering propagated to neighboring panels in the same dashboard.

**Date:** 2026-05-05 | **Session:** ThermoFisher PM demo — null field audit

---

## D-043b: Data views are time-axis declarations — one per (index, time-semantic) pair

**Status:** Active  
**Enforced by:** `weave-model` Step 4b — required output is a `data_views` section inventorying every date field per index with its semantic meaning. Multiple time semantics on one index require multiple data views. This is checked by `finish-check` Step 2 data layer checks.

**Rules:**
1. One data view per (index, time-semantic) pair
2. `formBased` layers: `timeFieldName` controls automatic time filter — must match visualization intent
3. `textBased` (ES|QL) layers: `timeFieldName` does NOT inject a time filter automatically; query must include `WHERE {field} >= ?_tstart AND {field} <= ?_tend`
4. Seed data must populate every `timeFieldName` field with a non-null value

**Date:** 2026-05-05 | **Session:** ThermoFisher PM demo — dashboard time picker alignment

---

## D-045: finish-verify is the mandatory gate between planning and deployment

**Status:** Active  
**Enforced by:** `bolt-bootstrap` halts with a clear error if `deploy/asset-bundle/asset-schema.json` does not exist. The orchestrator routes Stage 5 (new) to `finish-verify` before Stage 6 (new) `bolt-bootstrap`. There is no path from planning artifacts directly to Terraform/Python generation.

**Rationale:** The prior `bolt-launch` skill tried to do everything: read prose, probe APIs (sometimes), design assets, and generate scripts in one pass. This allowed schema probe to be skipped silently and custom code to be written from memory instead of confirmed facts. Splitting into a verification gate and a generation step makes skipping the probe structurally impossible.

**Date:** 2026-05-05 | **Session:** loom postmortem and refactor

---

## D-046: `bootstrap-data.py` is for data operations only

**Status:** Active  
**Enforced by:** `bolt-ech` and `bolt-serverless` skill specs explicitly list what belongs in `main.tf` vs `bootstrap-data.py`. Any infrastructure API call (index create, template create, ILM, inference endpoint, ML job, Kibana space, dashboard, rule, SLO, agent, workflow) is a Terraform resource. Python is limited to: enrich policy execution+polling, bulk data indexing, ELSER warm-up, anomaly injection, D-039 manifest write.

**Rationale:** A 900-line bootstrap.py mixing infrastructure creation with data operations is the root cause of inconsistent deployments. Terraform manages infrastructure state; Python handles what Terraform structurally cannot.

**Date:** 2026-05-05 | **Session:** loom postmortem and refactor

---

## D-047: hive-mind patterns are template inputs to skill calls, not standalone reading tasks

**Status:** Active  
**Enforced by:** `finish-verify` Step 2 skill dispatch — when calling a skill for a given asset class, the relevant hive-mind pattern file is passed as a context input to that skill call. It is not a separate "read before proceeding" prose instruction. Example: calling `hive-workflows` skill includes `hive-mind/patterns/workflows/WORKFLOWS_API_REFERENCE.md` as an explicit input.

**Rationale:** "Read hive-mind X before doing Y" in a SKILL.md is a prose instruction that may or may not be followed depending on context window state. Passing the pattern as a direct input to the skill call makes it structurally present during authoring.

**Date:** 2026-05-05 | **Session:** loom postmortem and refactor

---

## D-048: AE/SDR discovery agent as a distinct pipeline entry point

**Status:** Active  
**Enforced by:** `warp-scout` skill boundary — the skill runs only Stages 1 (discovery-parser), 2 (diagnostic-analyzer, optional), and 2b (opportunity-review). It explicitly does not call weave-script, thread-audit, weave-model, finish-verify, or any build stage. Any orchestrator invocation that reaches a build stage must route through the SA entry point (loom), not warp-scout.

**Rationale:** Mixing AE/SDR discovery work with SA build work in a single pipeline run creates confusion about who drives what and when. The AE agent produces the intelligence package; the SA agent builds the demo. Clean separation prevents AEs from inadvertently triggering build stages and prevents SAs from skipping discovery structure.

**Date:** 2026-05-05 | **Session:** two-agent pipeline split

---

## D-049: Predefined vs. custom decision gate is mandatory before scripting

**Status:** Active  
**Enforced by:** Stage 3b (`thread-suggest`) in the loom orchestrator. This stage runs after platform-audit and before weave-script on every engagement. It is not optional — if `{slug}-ideation.md` exists, the recommender always evaluates predefined fit. The orchestrator does not route to Stage 4 (script-template) without a `custom_required: true` decision recorded in the pipeline state. Predefined path produces `{slug}-predefined-recommendation.md` and ends the pipeline.

**Rationale:** Building a full custom demo when a standard Elastic demo already serves the customer's needs wastes build time and increases the risk of deployment failures. The gate forces an explicit evaluation and decision before any technical build work begins.

**Date:** 2026-05-05 | **Session:** two-agent pipeline split

---

## D-050: Ideation always runs as SA commit step; post-ideation assets refreshed with technical-win framing

**Status:** Active  
**Enforced by:** `warp-spark` SKILL.md (expansion mode) and `loom` orchestrator Step 0b. Ideation runs in one of three modes depending on available inputs (Mode 1: pre-seeded from demo-goals.md; Mode 2: from discovery context; Mode 3: from scratch). In all modes, the skill does not exit until `{slug}-ideation.md` is frozen and the SA has approved the updated `opportunity/{slug}-confirmation.md`. The orchestrator does not proceed to platform-audit without this approval. `weave-script` requires `{slug}-ideation.md` as a required input (not optional).

**Post-ideation refresh rule:** After ideation freezes, `opportunity/{slug}-confirmation.md` is updated using technical-win framing — what problem, what they will see, what defines success. Internal pipeline terminology ("custom build", "predefined", "bootstrap", "standard demo") must not appear in the customer-facing confirmation document at any point.

**Rationale:** The prior ideation stage was "optional if no direction." This allowed build work to begin without an explicit SA commit, leading to scripts that diverged from what the SA intended to show. Making ideation mandatory and gating platform-audit on SA approval of the updated confirmation closes this gap. The technical-win framing rule ensures the customer always receives outcome-focused communication regardless of internal build strategy.

**Date:** 2026-05-05 | **Session:** two-agent pipeline split

---

## D-051: Vignette-based demo structure required for all custom demo scripts

**Status:** Active  
**Enforced by:** `weave-script` SKILL.md preamble — the skill reads `references/demo2win-conventions.md` before authoring any scene. `finish-check` compliance check C-11 (to be added): verifies that `{slug}-demo-script.md` contains an "Opening Punch" section, 3–5 scene blocks with "Can stand alone: yes" and "Skip signal" fields, and a "Value Confirmation Close" section. Scripts missing any of these three structural elements are flagged as non-conformant.

**Three required rules (per `references/demo2win-conventions.md`):**
1. **Opening punch** — business problem statement before any product is shown; names a role, states a consequence, grounded in discovery
2. **Vignette structure** — 3–5 self-contained scenes, each independently skippable/reorderable, each with its own setup/product moment/payoff
3. **Value confirmation close** — explicitly ties the ending back to the opening punch using outcome language; not a feature recap

The full Demo2Win methodology (Tell-Show-Tell, Limbic Opening, Visual Roadmaps) is optional depth for SAs. The three rules above are the minimum enforced by loom.

**Reference:** [Demo2Win®](https://www.2winglobal.com/programs/demo2win/) by 2Win! Global

**Rationale:** Demos that lack an opening punch and a value close leave the audience with feature impressions, not business conviction. Vignette independence allows SAs to adapt for time and audience without the whole script breaking. These structural rules are the minimum needed to produce a demo that advances a deal rather than just informing the buyer.

**Date:** 2026-05-05 | **Session:** two-agent pipeline split
