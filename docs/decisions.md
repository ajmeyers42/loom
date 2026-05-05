# demobuilder — Architecture Decisions

*Rationale for the choices baked into the pipeline. Updated as significant decisions are made.*
*See `docs/postmortem.md` for the full session post-mortem that prompted many of these.*

---

## D-020: Default to latest GA for new stacks; validate version for existing

**Decision:** When **creating** a new Elastic Cloud deployment or Serverless project for a
demo, use the **latest generally available** stack version for that product **unless** the
SA requests a specific version. When **using an existing** deployment, project, or cluster,
**resolve and record** Elasticsearch and Kibana versions (e.g. `GET /`, `/api/status`, or
diagnostic output) **before** producing scripts, data models, or plans. All guidance and
automation must be **scoped to that version** and deployment type.

**Rationale:** ES|QL, APIs, ML, Kibana embeddables, Agent Builder, and Workflows all vary
by version; assuming “latest” on a customer’s 8.x cluster causes failed demos.

**Applied to:** `skills/demobuilder/SKILL.md`, `skills/demo-cloud-provision/SKILL.md`,
`skills/demo-platform-audit/SKILL.md`, `skills/demo-script-template/SKILL.md`, `AGENTS.md`,
`.cursor/rules/demobuilder.mdc`, `README.md`.

**Date:** 2026-04-20 | **Session:** version policy

---

## D-021: Enterprise showcase; multi-input; search / Observability / Security / cross-solution

**Decision:** Demos should **assume enterprise-level Elastic features** are in play when they
address customer outcomes in the inputs — subject to platform audit, license, and version.
**Inputs** may include discovery notes, diagnostic files, supplemental notes from the
discovery team, and **architecture diagrams** illustrating current-state environments.
The primary use case may be **search / analytics**, **Observability**, **Elastic Security**,
or a **deliberate combination**; the pipeline must not default to “core search only” when
artifacts point elsewhere. **Cross-solution** demos (e.g. unified data, correlated
investigation) are acceptable when they match stated needs.

**Rationale:** Pre-sales stories follow the customer’s domain; many engagements are
Observability- or Security-led. Diagrams and team addenda are common and should be
first-class context.

**Applied to:** `skills/demobuilder/SKILL.md`, `skills/demo-discovery-parser/SKILL.md`,
`skills/demo-script-template/SKILL.md`, `AGENTS.md`, `.cursor/rules/demobuilder.mdc`, `README.md`.

**Date:** 2026-04-20 | **Session:** solution scope and inputs

---

## D-022: Solution-first narrative in scripts and plans

**Decision:** Unless the SA specifies otherwise, demo **scripts** and **plans** should
structure the storyline **solution first**: lead with **outcomes and business value**
linked to the customer’s **key asks** from discovery inputs, then describe **supporting
Elastic capabilities** (data, queries, ML, Security/Observability apps, agents, etc.) that
realize those outcomes. If primary goals or asks are **not clear** from artifacts, the agent
should **ask the SA for guidance** rather than guessing the headline narrative.

**Rationale:** Executives and business sponsors need the “why” before the “how”; technical
depth still follows, but order matters for retention and credibility.

**Applied to:** `skills/demo-script-template/SKILL.md`, `skills/demobuilder/SKILL.md`,
`skills/demo-validator/SKILL.md`, `AGENTS.md`, `.cursor/rules/demobuilder.mdc`, `README.md`.

**Date:** 2026-04-20 | **Session:** narrative arc

---

## D-023: `DEMOBUILDER_ENGAGEMENTS_ROOT` — engagements outside the repo

**Decision:** Per-customer engagement directories live under **`$DEMOBUILDER_ENGAGEMENTS_ROOT/{slug}/`**.
When **`DEMOBUILDER_ENGAGEMENTS_ROOT`** is unset, agents treat it as **`$HOME/engagements`**
(a normal directory under the user profile — not cloud symlinks by default). The demobuilder git
repository contains **no** customer workspaces under `engagements/` (only a tracked pointer
[`engagements/README.md`](../engagements/README.md)).

**Rationale:** Separates pipeline code from confidential demo assets; clones stay portable; the
default path avoids broken Google Drive symlink layouts on some hosts.

**Applied to:** `AGENTS.md`, `.cursor/rules/demobuilder.mdc`, `README.md`, `docs/engagements-path.md`,
`docs/todo.md`, `docs/runtimes/cursor.md`, `docs/runtimes/claude.md`, `skills/demobuilder/SKILL.md`,
`skills/demo-cloud-provision/SKILL.md`, `skills/demo-deploy/SKILL.md`, `skills/demo-deploy/references/env-reference.md`,
`skills/demo-status/SKILL.md`, `skills/demo-teardown/SKILL.md`, skill evals `files` paths, `.gitignore`,
`.cursor/plans/2026citizensai_engagement_setup_d360eb16.plan.md`.

**Date:** 2026-04-21 | **Session:** portable engagements root | **Updated:** 2026-04-21 — default `$HOME/engagements`

---

## D-024: Kibana assets as engagement files; single `bootstrap.py` import; review before deploy

**Decision:**

1. **Artifacts in the workspace** — Per engagement, treat Kibana-side deliverables as **files
   under the engagement folder**, e.g. `kibana-objects/{slug}-*.ndjson`, optional `kibana/workflows/*`,
   `kibana/agent/*.json`, alongside declarative `elasticsearch/**` JSON if the SA keeps ES defs
   as files (same pattern as reference demos). They are produced with **`elastic/agent-skills`**
   and **export-first** authoring (**D-017**), then **versioned** in the workspace (or a
   customer repo). **`bootstrap.py`** is the **only** deployment executable: it applies ES APIs,
   bulk data, ML, then **imports** those Kibana files via Kibana APIs (`saved_objects/_import`,
   Workflows, Agent Builder, etc.) — not a separate `deploy_kibana_*.py` beside it.

2. **No cluster deploy until review** — **`demo-cloud-provision`** and **`demo-deploy`**
   (including running `bootstrap.py` against a **live** cluster) run only after the SA has
   **both** (a) explicitly approved provision/deploy for this session **and** (b) **reviewed**
   the generated **`bootstrap.py`**, **`{slug}-platform-audit`**, **`{slug}-risks`**, demo
   checklist, and any other analysis outputs they rely on. **`bootstrap.py --dry-run`** and
   local inspection of committed assets do **not** require a cluster. Agents must not treat
   “artifacts complete” as permission to mutate production or shared demo clusters without
   that review step.

**Rationale:** Reference engagements (e.g. BigBox-style repos) already store NDJSON and agent
configs as files; the gap was automating import inside bootstrap. Separating **planning
complete** from **deploy authorized** prevents half-reviewed scripts from hitting clusters.
**`demo-kibana-builder`** (backlog) remains optional automation to **generate** NDJSON from
the data model; committed exports remain valid without it.

**Applied to:** `AGENTS.md`, `.cursor/rules/demobuilder.mdc`, `skills/demobuilder/SKILL.md`,
`skills/demo-deploy/SKILL.md`, `README.md`, `engagements/README.md`, `docs/todo.md`.

**Date:** 2026-04-16 | **Session:** artifact layout + deploy gate

---

## D-025: Deployable on Elastic; Elasticsearch datatypes and product conventions

**Decision:** Every artifact the pipeline defines (indices, mappings, ingest, ML, Kibana saved
objects, Agent Builder tools, Observability SLOs, Security rules, seed data shapes, ES|QL, and
API payloads) must be **deployable** on a real Elastic stack via **documented APIs** and must
**conform** to **Elastic datatypes and naming**, not generic or invented types.

**Concrete expectations:**

- **Mappings and documents:** Field types follow Elasticsearch mapping conventions (`keyword`,
  `text`, `long`, `date`, `semantic_text`, `geo_point`, etc.); demo seed data matches those
  mappings.
- **Agent Builder ES|QL tools:** Parameter `type` values use **Elasticsearch field-style types**
  accepted by the server (e.g. `keyword`, `text`, `integer`, `date`) — not abstract labels
  like `string` unless the target stack’s API explicitly allows them. Validate with
  `elastic/agent-skills` (`kibana/agent-builder`) and live `POST`/`PUT` when in doubt.
- **Kibana / APIs:** Request bodies match the stack version’s OpenAPI or reference repos
  (`elastic/workflows`, `elastic/kibana-agent-builder-sdk`); export-first for saved objects
  (**D-017**).
- **Platform audit:** If the customer cluster cannot support an artifact (version, license,
  feature flag), the artifact is **not** promised — scope adjusts in the script and audit.

**Rationale:** Demos fail in front of customers when types or payloads are “almost” right.
Binding definitions to Elastic’s own contracts keeps bootstrap and skills honest.

**Applied to:** `AGENTS.md`, `.cursor/rules/demobuilder.mdc`, `README.md`,
`docs/references-observability-slo.md`, `docs/references-kibana-apis.md`, `skills/demobuilder/SKILL.md`, `skills/demo-deploy/SKILL.md`,
`skills/demo-deploy/references/serverless-differences.md`, `demo-platform-audit` outputs,
`demo-data-modeler` / engagement `bootstrap.py` patterns.

**Date:** 2026-04-16 | **Session:** datatype and deployability contract

---

## D-026: Engagement tag on all tagged deploy assets

**Decision:** Every API-created asset that supports **tags** (or equivalent list metadata) must
include a **demobuilder** tag: `demobuilder:<engagement_id>`, where `<engagement_id>` is derived
from **`INDEX_PREFIX`** (normalized: hyphens, underscores, and whitespace removed; lowercase) when
the prefix is set, otherwise from **`DEMO_SLUG`** with the same normalization. Optional
**`DEMO_ASSET_TAG`** in `.env` overrides the normalized value when a different label is needed.

**Concrete expectations:**

- **bootstrap.py** defines `demobuilder_tags()` (or equivalent) and merges the tag into SLOs,
  alerting rules, ML jobs, Agent Builder entities, and any other payloads with a `tags` field
  in scope — not only NDJSON import.
- **Indices and templates** remain identified by **`p(name)`** / `INDEX_PREFIX` naming; tagging
  applies where the product API supports it (Kibana/Observability/ML/Security surfaces), not as a
  substitute for index naming.
- **Saved objects:** Prefer exports that include tags, or post-import tagging when required by the
  stack version.

**Rationale:** Operators need a consistent way to filter and audit demo resources across
solutions and to correlate assets with an engagement when cleaning up or handoff — without
replacing prefix-based Elasticsearch scoping.

**Applied to:** `AGENTS.md`, `.cursor/rules/demobuilder.mdc`, `README.md`,
`skills/demobuilder/SKILL.md`, `skills/demo-deploy/SKILL.md`,
`skills/demo-deploy/references/demobuilder-tagging.md`, `skills/demo-deploy/references/env-reference.md`,
`skills/demo-teardown/SKILL.md`, `skills/demo-status/SKILL.md`, `skills/demo-status/demo_status.py`,
`engagements/README.md`, engagement `bootstrap.py` patterns.

**Date:** 2026-04-16 | **Session:** engagement tagging for discovery and cleanup

---

## D-001: Per-engagement `.env` file for credential isolation

**Decision:** Each engagement workspace (`${DEMOBUILDER_ENGAGEMENTS_ROOT:-$HOME/engagements}/{slug}/`) holds its own `.env` file with cluster credentials. No global config.

**Rationale:** An SE running demos for Citizens Bank and IHG Club simultaneously — possibly on the same cluster — needs clean separation of credentials and namespace. A global config would require constant switching and risks cross-contamination.

**Implications:** The `p(name)` helper in `bootstrap.py` applies `INDEX_PREFIX` to every resource name, so indices, pipelines, templates, ML jobs, and Kibana index patterns all carry the engagement's namespace prefix. Copy workflow: `cp citizens-bank/.env ihg-club/.env` then update 3 fields (DEMO_SLUG, ENGAGEMENT, INDEX_PREFIX).

**Date:** 2026-04-15 | **Session:** initial build

---

## D-002: Idempotent bootstrap.py with check-before-create

**Decision:** Every resource creation in `bootstrap.py` checks for existence first. `--step N` flag resumes from a specific step. Data load checks doc count before loading (90% threshold).

**Rationale:** A failed deploy at step 9 shouldn't require tearing down steps 1–8. Demo environments are time-pressured — if something fails, you need to pick up where you left off, not start over.

**Implications:** Scripts are longer (each step has a check + create path), but they're safe to re-run. The check-before-create pattern also means running bootstrap on a half-deployed cluster is safe.

**Date:** 2026-04-15 | **Session:** initial build

---

## D-003: Separate provision and deploy skills

**Decision:** `demo-cloud-provision` and `demo-deploy` are distinct skills with a clean handoff via `.env`.

**Rationale:** An SE might provision once and deploy many times (adding a second customer on the same cluster with a different INDEX_PREFIX). Or they might bring their own existing cluster and skip provisioning entirely. Combining the two would force unnecessary reprovisioning or complex conditional logic.

**Implications:** `demo-cloud-provision` is optional. `demo-deploy` only needs a valid `.env` — it doesn't care how that `.env` was created.

**Date:** 2026-04-15 | **Session:** initial build

---

## D-004: `demo_critical_docs` as first-class concept in the data model

**Decision:** The data model spec includes a `demo_critical_docs` array for each index: specific documents that must exist, be individually verified by `_id` or unique field, and produce specific demo behavior.

**Rationale:** A demo where the script says "here's merchant VND-0412 with 7 suspicious claims" and the cluster has none of those documents fails visibly in front of the customer. Bulk doc count statistics don't catch this. Named, individually verified documents are the safety net.

**Implications:** `bootstrap.py` indexes demo_critical_docs individually (not in bulk), verifies each one, and reports specifically on their presence. `demo-status` spot-checks them as part of its readiness check. `demo-validator` lists them explicitly in the pre-demo checklist.

**Date:** 2026-04-15 | **Session:** initial build

---

## D-005: Two-dimensional shard density metric

**Decision:** `demo-diagnostic-analyzer` reports shard density on two axes: shards/GB of data AND (total shards / node count) / heap_GB_per_node.

**Rationale:** Discovered during real-data validation against Deutsche Telekom SOC-T (152-node, 1.18PB cluster). The first metric alone rated DT as healthy (0.027 shards/GB) — which it was from a data-sizing perspective. But 211 shards/node with 30GB heap is a different signal worth surfacing. One metric without the other is misleading in opposite directions depending on cluster topology.

**Thresholds:**
- Shards/GB: <0.1 (>10GB avg) → healthy, 0.1–1 → monitor, 1–20 → elevated, >20 → many tiny shards
- Shards/node/heap: <20 → healthy, 20–40 → elevated, >40 → high

**Date:** 2026-04-15 | **Session:** initial build (corrected via DT validation)

---

## D-006: Negative assertions in evals must specify scope

**Decision:** Eval assertions that check for the *absence* of content (e.g., "no competitor mentions") must specify which section of the output is being checked, not the full document.

**Rationale:** A skill may correctly mention a competitor in an internal "do not mention" instruction block for SE awareness — this is correct behavior. A blunt full-document assertion will falsely fail. Assertions like "not mentioned in talking points or scene narration" are precise; "not mentioned anywhere" is brittle.

**Applied to:** `demo-script-template` evals, and as a general rule for all future negative assertions.

**Date:** 2026-04-15 | **Session:** post-mortem

---

## D-007: elastic/agent-skills as the API integration layer

**Decision:** `demo-cloud-provision` and `demo-deploy` delegate cloud and Kibana API calls to skills from `elastic/agent-skills` (https://github.com/elastic/agent-skills) rather than implementing API clients from scratch.

**Rationale:** The Elastic-maintained skills handle auth, error handling, and API version differences for Cloud, Kibana, and Elasticsearch APIs. Duplicating this in demobuilder skills would create maintenance debt and diverge from the maintained implementations.

**Skills used:**
| elastic/agent-skill | Used by |
|---|---|
| `cloud-setup` | demo-cloud-provision (prerequisite) |
| `cloud-create-project` | demo-cloud-provision (serverless path) |
| `cloud-manage-project` | demo-cloud-provision (reuse path), demo-teardown (delete project) |
| `kibana-dashboards` | demo-deploy (if .ndjson doesn't exist), demo-kibana-builder (planned) |
| `kibana-agent-builder` | demo-deploy (agent config creation) |
| `kibana-connectors` | demo-deploy (Workflow email connectors) |
| `elasticsearch-esql` | demo-status (spot-check queries) |

**Gap:** No elastic/agent-skills exist yet for ML anomaly detection, Kibana Workflows (9.3), ingest pipelines, or index templates. These remain handled by `bootstrap.py` directly.

**Date:** 2026-04-15 | **Session:** post-mortem

---

## D-008: demo-status and demo-teardown as lifecycle skills

**Decision:** Add `demo-status` (pre-demo readiness pulse check) and `demo-teardown` (post-demo cleanup) to the skill set as first-class pipeline members.

**Rationale:** The pipeline was missing bookends: a way to quickly verify a deployed demo is healthy before going live, and a way to cleanly remove everything afterward. Without `demo-status`, SEs have to manually check 6 different things. Without `demo-teardown`, demo clusters accumulate resources and billing continues after demos end.

**Design principles:**
- `demo-status` runs in <60 seconds, produces ✅/❌ per resource, gives paste-ready fix commands
- `demo-teardown` is prefix-aware (only removes `{INDEX_PREFIX}*` resources on shared clusters), has `--dry-run`, generates a teardown log, offers to delete the cluster project if it was provisioned for this engagement only

**Date:** 2026-04-15 | **Session:** post-mortem

---

## D-009: Orchestrator references elastic/agent-skills explicitly and surfaces missing-plugin errors

**Decision:** The `demobuilder` orchestrator notes the elastic/agent-skills dependency upfront and tells the SE clearly if those skills aren't installed rather than failing silently at stage 8.

**Rationale:** An SE who completes stages 1–7 successfully and then hits a cryptic error at stage 8 because a dependency is missing will lose trust in the tool. A clear, actionable error message ("install elastic/agent-skills, see docs/todo.md") is better than a runtime failure.

**Date:** 2026-04-15 | **Session:** post-mortem

---

## D-010: docs/ directory for pipeline-level documentation

**Decision:** Add a `docs/` directory to the demobuilder repo for pipeline-wide documentation: postmortem, decisions log, and user-action todo list.

**Files:**
- `docs/postmortem.md` — full session post-mortem with lessons learned
- `docs/decisions.md` — this file; rationale for architectural choices
- `docs/todo.md` — items requiring user action (installs, credentials, validations)

**Rationale:** Pipeline-level knowledge was previously only in conversation history, which gets summarized and lost across context windows. These docs make it durable and accessible to any Claude session (or human) picking up the work cold.

**Date:** 2026-04-15 | **Session:** post-mortem

---

## D-011: Feature flag verification applies to Serverless AND ECH

**Decision:** `demo-cloud-provision` Step 4.5 verifies that Agent Builder and Kibana Workflows feature flags are enabled on **both Serverless and ECH deployments** before any build work begins.

**Rationale:** From the first-gen postmortem: Agent Builder and Workflows are not enabled by default on new projects. Initially documented as Serverless-only, but confirmed to apply equally to ECH until these features reach GA. Workflows is expected to GA with Elastic 9.4 — at that point the Workflows check can be relaxed for ECH, but Agent Builder may still require a flag. Always verify both.

**Applied to:** `demo-cloud-provision/SKILL.md` Step 4.5. `references/serverless-differences.md` Feature Flags section.

**Date:** 2026-04-15 | **Session:** first-gen review; corrected 2026-04-15

---

## D-012: Serverless ML field names documented as hard requirement

**Decision:** `demo-ml-designer` documents the Serverless `.ml-anomalies-*` field name differences and requires a `GET .ml-anomalies-*/_mapping` check before writing any query or dashboard panel.

**Rationale:** From the first-gen postmortem: all four ML dashboard panels had to be corrected after deployment because `anomaly_score`/`@timestamp`/`store_id`/`sku` do not exist on Serverless — the actual fields are `record_score`/`timestamp`/`partition_field_value`/`by_field_value`. A 2-minute mapping check prevents hours of rework.

**Applied to:** `demo-ml-designer/SKILL.md`. `references/serverless-differences.md`.

**Date:** 2026-04-15 | **Session:** first-gen review

---

## D-013: Workflow YAML reference required before writing any Workflow code

**Decision:** `demo-deploy` requires the `elastic/workflows` and `elastic/kibana-agent-builder-sdk` repos to be in context before any Workflow YAML or Agent Builder API call is written. 30-minute escalation rule: if progress stalls on an undocumented API, surface it as a blocker immediately.

**Rationale:** From the first-gen postmortem: Workflow debugging took ~3h and Agent Builder schema took ~2h because reference material was only found after problems were encountered. The `| first` Liquid filter, `_geo_distance` sort limitation, and `pattern` vs. `index` Agent Builder field were all documentable upfront.

**Applied to:** `demo-deploy/SKILL.md`. `references/workflow-patterns.md`. `references/serverless-differences.md`.

**Date:** 2026-04-15 | **Session:** first-gen review

---

## D-014: ELSER service body differs between Serverless and ECH

**Decision:** `bootstrap.py` uses `"service": "elser"` on Serverless (no `model_id`) and `"service": "elasticsearch"` with explicit `model_id` on ECH/self-managed.

**Rationale:** The actual working Serverless ELSER body uses `"service": "elser"` — the prior demobuilder implementation was using the wrong service name for Serverless, which would have caused step 8 to fail on every Serverless deploy.

**Applied to:** `demo-deploy/SKILL.md`. `demo-ml-designer/SKILL.md`.

**Date:** 2026-04-15 | **Session:** first-gen review

---

## D-015: Test session cleanup at T-10min is a required checklist item

**Decision:** The demo validator checklist includes a mandatory T-10min step to delete test agent sessions before going live.

**Rationale:** From the first-gen postmortem: pre-demo testing populates the session history index with test conversation turns that appear during the live demo. A single `_delete_by_query` on `@timestamp < now-10m` fixes it in seconds; not doing it risks surfacing test data during the demo.

**Applied to:** `demo-validator/SKILL.md`. `demo-deploy/SKILL.md` completion summary.

**Date:** 2026-04-15 | **Session:** first-gen review

---

## D-016: KIBANA_API_KEY is a required .env field for all Kibana asset operations

**Decision:** `KIBANA_API_KEY` is a required `.env` field used for **all** Kibana asset operations (Agent Builder, Workflows, Dashboards, Connectors, Saved Objects import) across all deployment types. It is not a fallback from `ES_API_KEY`. `bootstrap.py` uses `KB_KEY` (read from `KIBANA_API_KEY`) for all `kb()` calls.

**Rationale:** API key privilege requirements for Kibana vs. Elasticsearch are under active product change. Keeping separate keys is the safe default until product confirms a unified approach. The first-gen added this field after hitting 401 responses mid-build — it is now a provisioning-time requirement rather than a discovered fix.

**Applied to:** `references/env-reference.md`. `demo-cloud-provision/SKILL.md` `.env` and `.env.example` templates. `demo-deploy/SKILL.md` bootstrap.py credential block.

**Date:** 2026-04-15 | **Session:** first-gen review; elevated to required 2026-04-15

---

## D-017: Export-first dashboard pattern; never hand-write Lens JSON

**Decision:** Kibana dashboard saved objects must be exported from a working live panel. `migrationVersion` and `coreMigrationVersion` must be stripped before import or commit.

**Rationale:** From the first-gen postmortem: hand-written Lens panels took ~3h due to format errors. The Serverless inline `embeddableConfig.attributes` format differs from all public examples and changes between versions. Export-first produces a valid template in minutes.

**Applied to:** `demo-deploy/SKILL.md` Kibana step. `references/serverless-differences.md`.
Engagement layout and import path: **D-024**.

**Date:** 2026-04-15 | **Session:** first-gen review

---

## D-018: ML datafeed geo_point workaround via runtime_mappings

**Decision:** When the datafeed source index contains a `geo_point` field, `demo-ml-designer` adds a `runtime_mappings` shadow to prevent datafeed failure.

**Rationale:** ML datafeeds cannot natively consume geo_point fields. The first-gen hit this with `store_location` and fixed it with a runtime mapping that shadows the field as a keyword emitting an empty string.

**Applied to:** `demo-ml-designer/SKILL.md` datafeed config section.

**Date:** 2026-04-15 | **Session:** first-gen review

---

## D-019: Engagement collateral grouped under `engagements/` subfolder

**Decision:** All per-engagement workspaces live under **`$DEMOBUILDER_ENGAGEMENTS_ROOT/{slug}/`**
(see **D-023**). The repo may keep a **pointer** at `engagements/README.md` only — not full
engagement trees.

**Rationale:** `{slug}` is always one engagement (demo-specific). Pipeline code stays in the
clone; customer data and `.env` files stay outside git on a path the SA controls (often synced
“My Drive” or local disk).

**Applied to:** `demobuilder/SKILL.md`, `demo-cloud-provision/SKILL.md`, `demo-deploy/SKILL.md`, `demo-status/SKILL.md`, `demo-teardown/SKILL.md`, `demo-deploy/references/env-reference.md`, `README.md`. `docs/todo.md` item 11 closed.

**Date:** 2026-04-20 | **Session:** workspace organization | **Updated:** 2026-04-21 — engagements root via `DEMOBUILDER_ENGAGEMENTS_ROOT` (D-023)

---

## D-027: ILM defaults to hot-only; tiered phases only when explicitly required

**Decision:** The **default ILM posture for all generated scripts is hot-only** — a hot phase
with `set_priority` and a `delete` phase. Warm, cold, and frozen phases are **only added when
the engagement explicitly requires tiered storage** (e.g., the customer wants to demo
hot-warm-cold cost tiering). Tier detection via `GET /_nodes` is run at bootstrap time to guard
against applying unavailable phases, but it does not automatically opt-in to more phases.

Additional hard rules:
- **No `rollover` on plain indices.** Rollover requires `index.lifecycle.rollover_alias` and
  errors immediately on any index without a write alias
  (`IllegalArgumentException: setting [index.lifecycle.rollover_alias] … is empty or not defined`).
  Use age-based `delete` instead.
- **`forcemerge` in hot requires `rollover`.** If rollover is absent, omit forcemerge too.
- **Data streams:** rollover is always valid (the stream manages the write alias) and should be
  used when the engagement calls for it.

**Rationale:** Demo ECH clusters are almost always hot-only. Adding warm/cold/frozen phases by
default clutters the policy, wastes SA time debugging ERROR-state indices, and obscures whether
tiering is actually part of the demo story.

**Applied to:** `bootstrap.py` (`step1_connectivity` tier detection, `step2_ilm` policy builder),
`skills/demo-data-modeler/SKILL.md`.

**Date:** 2026-04-22 | **Session:** Citizens Bank 9.4 deployment

---

## D-028: Use EIS for embeddings and reranking; reserve ML nodes for anomaly detection and DFA

**Decision:** All **text embedding** (sparse and dense) and **reranking** inference in
demobuilder pipelines must use **Elastic Inference Service (EIS)** endpoints — i.e., inference
endpoints created with `service: "elastic"` via `PUT /_inference/{task_type}/{id}`. Do **not**
deploy embedding or reranking models directly on the deployment's ML nodes.

ML nodes are reserved for:
- **Anomaly detection** (ML jobs + datafeeds)
- **Data frame analytics** (classification, regression, outlier detection)
- Other tasks where local execution is architecturally necessary or explicitly requested

**Rationale:** EIS routes inference to Elastic's managed inference infrastructure, keeping ML
node resources free for jobs that cannot run externally. On demo ECH clusters, ML nodes are
typically undersized; loading ELSER or reranker weights alongside anomaly jobs causes resource
contention, slow model startup, and 408 timeouts during demos. EIS also scales independently of
the cluster and eliminates the ELSER adaptive-allocation warm-up delay during the demo itself.

**Implementation (9.x):**
```json
// Sparse embedding via EIS
PUT /_inference/sparse_embedding/elser-eis
{ "service": "elastic", "service_settings": { "model_id": ".elser-2" } }

// Reranking via EIS
PUT /_inference/rerank/rerank-eis
{ "service": "elastic", "service_settings": { "model_id": "elastic-reranker-v1" } }
```

**Applied to:** `skills/demo-data-modeler/SKILL.md`, `bootstrap.py` step 5 (ELSER endpoint —
migrate from `service: "elasticsearch"` to `service: "elastic"` when EIS is confirmed available
on the target deployment).

**Date:** 2026-04-22 | **Session:** Citizens Bank 9.4 deployment

---

## D-030 — Versioning convention: `BOOTSTRAP_VERSION` as single source of truth across all versioned assets

**Status:** Active | **Applies to:** `bootstrap.py`, `skills/demo-deploy/SKILL.md`

**Context:** Elastic assets have inconsistent version support — some have a formal `version` API
field, others only have `description` or `_meta`. Without a consistent convention, deployed assets
are indistinguishable in UIs that don't show API-assigned IDs (e.g. the Workflows UI).

**Decision:**
- A single `BOOTSTRAP_VERSION = "X.Y.Z"` constant at the top of `bootstrap.py` is the source of truth
- Bump it on any structural change to assets (new steps, changed queries, workflow edits, etc.)
- Apply by asset type:

| Asset type | Field | Format |
|---|---|---|
| Workflow YAML | `version` (string) | `"1.0.0"` |
| Workflow description | `description` | `[{slug} v1.0.0] ...` prefix |
| SIEM detection rules | `version` (integer) | `1` (matches major version) |
| SIEM rule description | `description` | `[v1.0.0] ...` prefix |
| All other assets (SLOs, ML jobs, tools, agents, dashboards) | `description` / `_meta` | `[v1.0.0] ...` prefix where practical |

- The `name`/`rule_id` fields stay stable — used for idempotent lookup and deduplication

**Date:** 2026-04-22 | **Session:** Citizens Bank 9.4 deployment

---

## D-031: Cluster-resident asset manifest — trusted source for teardown

**Decision:** `bootstrap.py` writes (and incrementally updates) a **manifest document** to the
target Elasticsearch cluster in a `demobuilder-manifests` index. The document ID is the
normalized engagement ID (same value as the `demobuilder:<id>` tag). The manifest captures
every resource ID created — by type — so `teardown.py` reads it as the **single trusted source**
of what to delete, rather than relying on hardcoded IDs that go stale across redeployments.

**Manifest index:** `demobuilder-manifests` (no prefix — shared across all engagements on the
cluster, never deleted by teardown). Document shape:

```json
{
  "engagement_id": "cbfraud",
  "slug": "2026citizens-ai",
  "bootstrap_version": "1.0.0",
  "deployed_at": "2026-04-22T...",
  "es_version": "9.4.0",
  "assets": {
    "ilm_policies": [...],
    "ingest_pipelines": [...],
    "component_templates": [...],
    "index_templates": [...],
    "indices": [...],
    "data_streams": [...],
    "inference_endpoints": [{"task_type": "sparse_embedding", "id": "cb-elser"}],
    "ml_jobs": [...],
    "ml_datafeeds": [...],
    "enrich_policies": [...],
    "kibana": {
      "space_id": "...",
      "data_views": [...],
      "slos": [{"id": "...", "name": "..."}],
      "alerting_rules": [{"id": "...", "name": "..."}],
      "dashboards": [{"id": "...", "title": "..."}],
      "connectors": [{"id": "...", "name": "..."}],
      "tags": [{"id": "...", "name": "..."}],
      "workflows": [{"id": "...", "name": "..."}],
      "agent_tools": [{"id": "...", "name": "..."}],
      "agents": [{"id": "...", "name": "..."}],
      "siem_rules": [{"rule_id": "...", "name": "..."}]
    }
  }
}
```

**Bootstrap** — upserts the manifest after each major step via
`POST /demobuilder-manifests/_doc/{engagement_id}`. A partial deploy can be cleaned up
because the manifest reflects what was actually created up to that point.

**Teardown** — reads the manifest at step 1 via
`GET /demobuilder-manifests/_doc/{engagement_id}`. Falls back to a hardcoded inventory
if the manifest is not found (with a warning). The `demobuilder-manifests` index itself
is **never** deleted — it is a durable audit log.

**Rationale:** IDs assigned by Kibana (alerting rules, SLOs, dashboards, connectors,
workflows, Agent Builder entities) are not deterministic. Hardcoding them in `teardown.py`
at generation time breaks the moment a re-deploy assigns new IDs. A cluster-resident
manifest stays fresh automatically because bootstrap writes it.

**Applied to:** `skills/demo-deploy/SKILL.md` (manifest write step),
`skills/demo-teardown/SKILL.md` (manifest read step),
`skills/demo-deploy/references/asset-manifest.md` (schema reference).

**Date:** 2026-04-22 | **Session:** post-mortem gap remediation

---

## D-032: Managed assets preferred; clone before modifying; never patch originals

**Decision:** Elastic-managed / prebuilt assets should be **used as-is wherever they serve the demo story** — they are the preferred deliverable over custom-authored equivalents. When a demo requires adapting a managed asset, the pipeline must **clone** it and modify the clone — **never** PUT/PATCH the original.

**Managed-first preference order:**
1. Use the managed asset as-is (no change needed)
2. Use the managed asset as-is AND reference it directly in a custom dashboard (embed by ID)
3. Clone it with a `[{SLUG}]` prefix, make targeted changes to the clone, delete nothing from the original

**Applies to all managed asset types:**

| Asset type | Managed indicator | Clone strategy |
|---|---|---|
| SIEM detection rules | `immutable: true` or `rule_source.type: "prebuilt-rule"` | `rule_id = f"demo-{source_rule_id}"` |
| ML anomaly detection jobs | `custom_settings.created_by: "ml-module-*"` | copy job JSON, rename `job_id` |
| Kibana ML results dashboards | Installed by ML module | reference by `ref_id` in custom dashboard; only clone if layout change needed |
| Integration package dashboards | Installed by Fleet EPR | reference or link from custom dashboard; clone only if content change needed |
| Data views installed by packages | `namespaces: ["*"]` or package-managed | use directly; never delete or overwrite |
| Ingest pipelines installed by packages | name matches `<pkg>-<version>.*` | add custom pipeline as a downstream processor; never overwrite the package pipeline |

**Pattern for SIEM prebuilt rules (unchanged):**

```python
# 1. GET the prebuilt rule to use as template
existing = kb("GET", f"/api/detection_engine/rules?rule_id={source_rule_id}", ok=(200,))
# 2. Strip read-only/managed fields (id, created_at, updated_at, immutable, etc.)
clone = {k: v for k, v in existing.items()
         if k not in ("id", "created_at", "updated_at", "updated_by", "created_by",
                      "immutable", "rule_source", "revision")}
# 3. Assign demo-specific identity and tagging
clone["rule_id"]     = f"demo-{source_rule_id}"       # stable ID for idempotency
clone["name"]        = f"[{SLUG}] {existing['name']}" # prefixed for UI clarity
clone["description"] = f"[v{BOOTSTRAP_VERSION}] Clone of '{existing['name']}' — {purpose}"
clone["tags"]        = merge_tags(clone.get("tags", []))
clone["version"]     = 1
# 4. POST as a new custom rule
kb("POST", "/api/detection_engine/rules", clone, ok=(200, 201))
```

**Custom rules we author from scratch:** upsert by `rule_id` —
- `GET /api/detection_engine/rules?rule_id={id}` → 200 means update (PUT with `version + 1`)
- 404 means create (POST with `version: 1`)

**Why:** Elastic-managed assets may be overwritten on the next package update, erasing any changes. Cloned and custom assets carry the engagement tag, survive updates, and are deleted cleanly by teardown.

**Applied to:** `skills/demo-deploy/SKILL.md` (step 13g), `skills/demo-data-modeler/SKILL.md` (Path A), engagement `bootstrap.py` patterns.

**Date:** 2026-04-22 | **Session:** post-mortem gap remediation

---

## D-033: API baseline is Elastic 9.4+; remove pre-9.x compatibility shims

**Decision:** The demobuilder pipeline targets **Elastic 9.4 ECH and Serverless** as the
minimum baseline. Pre-9.x compatibility shims, fallback API shapes, and 8.x-era workarounds
are **removed** from all generated scripts and skill guidance.

**Rationale:**
- Serverless auto-updates — it is always aligned with this baseline.
- ECH version is still validated at step 1 connectivity check (D-020); if the live version
  is below 9.4, bootstrap should **warn and halt** rather than attempt a degraded deploy.
- Accumulating compat shims adds complexity and is a source of silent failures when the
  shim is wrong for a new version.

**Baseline assumptions (9.4+):**
- **ELSER / embeddings:** EIS (`service: "elastic"`) on ECH; `service: "elser"` on Serverless
  (D-028). `service: "elasticsearch"` for local ML node inference is not used for embeddings.
- **ILM:** Full 9.x ILM API — no 8.x-era `include_type_name` or deprecated params.
- **Workflows:** Supported on both ECH 9.4+ and Serverless. Feature-flag check still required
  until GA (D-011).
- **Agent Builder:** v0.2.0 shape (D-029) — `configuration.skill_ids`, `index_search` tool
  type, `workflow` tool type. No legacy 9.0–9.3 payload shapes.
- **Alerting rules:** 9.x `windows` array schema for SLO burn-rate rules.
- **Data views API:** `POST /api/data_views/data_view` (9.x shape, no `index-pattern` type).
- **Inference GET response:** `{"endpoints": [...]}` wrapper (9.x shape).

**ECH version gate in bootstrap.py step 1:**
```python
major, minor = (int(x) for x in version.split(".")[:2])
if (major, minor) < (9, 4):
    print(f"  ⛔ Cluster version {version} is below 9.4 baseline (D-033).")
    print(f"     Update the cluster or set SKIP_VERSION_CHECK=true in .env to override.")
    sys.exit(1)
```

**Applied to:** `skills/demo-deploy/SKILL.md`, `skills/demo-teardown/SKILL.md`,
`skills/demo-data-modeler/SKILL.md`, engagement `bootstrap.py` patterns.

**Date:** 2026-04-22 | **Session:** post-mortem gap remediation

---

## D-034: hive-mind as pattern reference library; adopt where better with no gaps

**Decision:** The local `elastic/hive-mind` clone is a **reference library** for
demobuilder. When `hive-mind` provides a pattern, API reference, or skill that is
demonstrably better than demobuilder's current guidance **and** does not introduce a gap
in demobuilder's capabilities, the demobuilder skill should **reference or adopt** the
hive-mind pattern rather than maintaining a parallel implementation.

**Adoption boundaries:**
- hive-mind **patterns** (`patterns/workflows/`, `patterns/dashboards/`, `patterns/agent-builder/`,
  `patterns/deployment/`, `patterns/data/`) → Reference from demobuilder skills; do not copy verbatim.
- hive-mind **skills** (`skills/hive-sa-coaching/`, `skills/hive-token-optimization/`) → May be
  referenced or adapted; demobuilder-specific overlays in demobuilder skill files.
- hive-mind **does not replace** demobuilder's pipeline decisions (`docs/decisions.md`),
  engagement tagging (D-026), asset manifest (D-031), ILM defaults (D-027), or any ECH-specific
  patterns not present in hive-mind.

**Reference paths (default):**
- hive-mind root: `../hive-mind` relative to demobuilder root, or `HIVE_MIND_PATH` env var
- Currency checked at pipeline start (Step 0 in demobuilder/SKILL.md)

**Rationale:** hive-mind confirmed the Workflows DELETE endpoint, search-by-name pattern,
stale-read warning, dashboard stable UUIDs, probe-based feature detection, and agent-builder
A2A coordinator pattern — all of which demobuilder had discovered the hard way or missed
entirely. Maintaining alignment means future demobuilder builds benefit from hive-mind
improvements without manual re-discovery.

**Applied to:** `skills/demobuilder/SKILL.md`, `skills/demo-deploy/SKILL.md`,
`skills/demo-deploy/references/workflow-patterns.md`.

**Date:** 2026-04-21 | **Session:** hive-mind comparison and adoption

---

## D-035: Demo Ideation as Stage 0 in the demobuilder pipeline

**Decision:** A new **demo-ideation** stage (Stage 0) is added to the demobuilder pipeline,
running **before** `demo-discovery-parser` when the SA does not have a clear demo direction,
no discovery notes, or is at a hackathon / exploratory phase. It produces a frozen
`{slug}-ideation.md` contract that flows into `demo-script-template` as the primary
narrative source.

**The ideation stage implements the hive-mind SA coaching methodology** from
`hive-mind/skills/hive-sa-coaching/` and uses the **Demo Archetypes gallery** from
`hive-mind/skills/hive-sa-coaching/references/DEMO_ARCHETYPES.md`:
- AI Search + Assistant
- Operational Triage Console
- Customer Support Intelligence
- E-Commerce with Analytics
- Domain Expert Advisor

**Skip condition:** If discovery notes, a diagnostic file, or prior pipeline outputs
(`{slug}-discovery.json`, `{slug}-ideation.md`) already exist, ideation is skipped.

**Output contract** (`{slug}-ideation.md`) includes:
- Chosen archetype + rationale
- Top 3 wow moments
- Main demo paths (happy paths with user actions and expected outcomes)
- Elastic capability map (2-4 capabilities, outcome-first)
- Data strategy (starter vs custom, volume minimum)
- Operational transparency flag (token visibility — see D-036)
- Workflow automation proposals if applicable
- Build path (Quick / Customized / Custom Data / Full Custom) with time estimate

**Rationale:** The pipeline previously assumed discovery notes would always be provided
upfront. In practice, many engagements start with "I have a meeting next week — what
should I show?" This stage answers that before committing to a build direction.

**Applied to:** `skills/demobuilder/SKILL.md` (Step 0b and Stage 0),
`skills/demo-ideation/SKILL.md` (new skill), `skills/demo-script-template/SKILL.md` (Step 1b).

**Date:** 2026-04-21 | **Session:** hive-mind comparison and adoption

---

## D-036: Token visibility as a standard demo feature for Agent Builder engagements

**Decision:** Any demo that includes **Elastic Agent Builder** must include an **AI Cost +
Usage dashboard** as a standard deliverable, unless the SA explicitly opts out
(`INCLUDE_TOKEN_VISIBILITY=false` in `.env`).

**What is included:**
1. **`{prefix}agent-sessions` index** — engagement-scoped, schema compatible with hive-mind
   Group B token tracking. Hot-only ILM, delete after 90 days (D-027).
2. **30-60 synthetic session documents** — covering 7-14 days of realistic AI agent usage,
   realistic cost distribution ($0.02–$2.50/session), multiple models and agents.
3. **ES|QL dashboard panels** — daily spend, cost by model, sessions by agent, average cost
   per query, cache efficiency. Dashboard ID is stable (deterministic UUID from slug + "ai-usage").
4. **A demo scene** in `{slug}-demo-script.md` titled "AI Cost + Usage — Operational Transparency"
   with talking points for budget owners, IT governance, and CTO audiences.

**Rationale:** Enterprises buying AI-powered solutions increasingly ask: "What does it cost
to operate?" and "Who can see the usage?" The ability to show operational transparency and
AI cost governance is a differentiated capability that transforms a demo from a feature
showcase into a platform story. It lands especially well with finance and IT leadership.

**Index schema:** See `skills/token-visibility/SKILL.md` for the full mapping, cost formula,
and ES|QL queries. The schema is intentionally compatible with hive-mind Group B so SAs
can compare their own session patterns against the demo data.

**Applied to:** `skills/demo-data-modeler/SKILL.md` (Step 5c), `skills/demo-deploy/SKILL.md`
(Step 13j), `skills/demo-script-template/SKILL.md` (token visibility scene), `skills/token-visibility/SKILL.md`.

**Date:** 2026-04-21 | **Session:** hive-mind comparison and adoption

---

## D-029 — Agent Builder: skills vs. tools — use `configuration.skill_ids` for platform skills

**Status:** Active | **Applies to:** `skills/demo-deploy/SKILL.md`, `bootstrap.py` step 8f

**Context:** Agent Builder 9.4 introduced a Skills catalog (`GET /api/agent_builder/skills`) alongside
the existing custom tools API. Skills are platform capability bundles (system instructions + tool_ids)
that are linked to an agent via `configuration.skill_ids` — a sibling field to `configuration.tools`
in the agent PUT/POST body. This is distinct from `configuration.tools[].tool_ids` which lists
individual tool IDs (custom and platform.core.*).

**Decision:**
- Platform skills (`data-exploration`, `visualization-creation`, etc.) go in `configuration.skill_ids`
- Individual tools (custom ES|QL, index_search, workflow, platform.core.*) go in `configuration.tools[0].tool_ids`
- Agent instructions should reference both skills and tools explicitly by name
- Skills endpoint: `GET /api/agent_builder/skills` — always probe to confirm available skill IDs before deploying

**API shape confirmed on 9.4:**
```json
{
  "configuration": {
    "instructions": "...",
    "tools": [{"tool_ids": ["custom-tool-id", "platform.core.search"]}],
    "skill_ids": ["data-exploration", "visualization-creation"]
  }
}
```

**Date:** 2026-04-22 | **Session:** Citizens Bank 9.4 deployment

---

## D-037: Engagement folder reorganization — audience-scoped subfolders

**Status:** Active | **Applies to:** All pipeline skills, `scripts/inventory.py`, `docs/pipeline.md`

**Context:** As the demobuilder pipeline grew to 15+ output files per engagement, all artifacts
landed flat in `{slug}/`. AEs and SDRs had to navigate technical data model files to find the
team alignment doc. SEs looking for deployment scripts had to scroll past customer-facing docs.
Confusion about which files to share externally vs. keep internal was increasing.

**Decision:** Organize all engagement outputs into four audience-scoped subfolders under `{slug}/`:

| Folder | Audience | Contents |
|--------|----------|----------|
| `opportunity/` | AE, SDR, SA | Customer-facing docs + team alignment gate (confirmation, gaps, brief, MEDDPIC summary) |
| `demo/` | SA | Design intelligence: discovery JSON, diagnostic outputs, platform audit, demo script, agent spec |
| `data/` | SA, engineer | Data model, ML config, Vulcan outputs, `mappings/`, `pipelines/`, `seed/` |
| `deploy/` | SA | `bootstrap.py`, `teardown.py`, provision log, deploy log, checklists, risks, Kibana objects |

**Exception:** `.env` and `.env.example` remain at the **engagement root** (not in a subfolder).
They are sourced by scripts using `source {engagement_dir}/.env` which assumes the root convention.
Moving them into a subfolder would break all shell-level sourcing patterns.

**Rationale:**
- AEs and SDRs open `opportunity/` and find exactly what they need for the team call — no scrolling past ML config files.
- When sharing a confirmation doc externally, the SA sends `opportunity/{slug}-confirmation.md` without needing to filter.
- `deploy/` is the boundary for scripts that touch live clusters — clearly separated from the planning artifacts.
- `data/` groups everything an engineer needs to build or debug the data layer, including sub-directories for mappings and pipelines.

**Migration for existing engagements:** Move files manually or re-run the relevant pipeline stages.
The orchestrator will create subfolders automatically on any new engagement. `scripts/inventory.py`
searches `{subfolder}/{filename}` patterns when falling back to file scan.

**Applied to:** All 15 skill `SKILL.md` files, `skills/demobuilder/SKILL.md` (orchestrator),
`scripts/inventory.py` `STAGE_OUTPUTS`, `docs/pipeline.md` workspace layout section.

**Date:** 2026-05-01 | **Session:** Engagement folder reorganization

---

## D-038: Terraform deploy mode via `DEPLOY_MODE` env var

**Status:** Active | **Applies to:** `skills/demo-deploy/SKILL.md`, `skills/demo-teardown/SKILL.md`, `skills/demo-cloud-provision/SKILL.md`

**Decision:** `bootstrap.py` generation is augmented with a **Terraform path** selected by `DEPLOY_MODE=terraform` in `.env`. When active:

- **Layer 1 (cloud provisioning):** `ec_deployment` / `ec_elasticsearch_project` via `terraform-provider-ec` replaces the Elastic Cloud API calls in `demo-cloud-provision`.
- **Layer 2 (stack resources):** Generated `deploy/main.tf` + `deploy/{slug}.tfvars` + `deploy/providers.tf` cover all Terraform-manageable resources: ILM/DSL, ingest pipelines, component templates, index templates, indices, data streams, enrich policies (create only), ML jobs/datafeeds, inference endpoints, Kibana spaces, connectors, alerting rules, NDJSON saved objects import, Agent Builder agents/tools, Workflows (`kibana_agentbuilder_agent`, `kibana_agentbuilder_tool`, `kibana_agentbuilder_workflow` are confirmed resources in `elasticstack` provider as of 2026-05).
- **Layer 3 (data + ops):** `deploy/bootstrap-data.py` (Python) handles what Terraform cannot: enrich policy execution + polling, bulk seed data ingestion, ELSER warm-up, anomaly injection, and D-039 manifest write.
- `terraform plan` serves as the reviewable deployment artifact at the D-024 approval gate.
- `terraform destroy` is the primary teardown mechanism; `teardown.py` handles data indices + manifest cleanup.
- Terraform state stored in `deploy/terraform.tfstate` (local default; configurable to S3/GCS). State file is gitignored.
- `DEPLOY_MODE=python` (default) keeps existing `bootstrap.py` behavior unchanged. New engagements should use `terraform` once the path is validated end-to-end.

**Provider currency:** Before generating HCL, validate `elasticstack` and `ec` provider versions against latest GitHub releases (D-041).

**Reference:** `skills/demo-deploy/references/terraform-patterns.md`

**Date:** 2026-05-02 | **Session:** Bootstrap to Terraform investigation

---

## D-039: Dynamic asset manifest replaces D-031 static schema

**Status:** Active — supersedes D-031 | **Applies to:** `skills/demo-deploy/SKILL.md`, `skills/demo-teardown/SKILL.md`, `skills/demo-fleet-integrations/SKILL.md`

**Decision:** The D-031 manifest schema used fixed category keys (`ilm_policies`, `ingest_pipelines`, etc.). This schema is replaced with an **open-list format**:

- **`assets.elasticsearch`**: flat list of `{"type": "...", "id": "..."}` records; any new asset type is a new entry, no schema migration needed.
- **`assets.kibana.by_space`**: dict keyed by `space_id`, each value a list of `{"type": "...", "id": "..."}` records. Multi-space engagements work naturally; teardown iterates spaces to scope deletes.
- Extra fields (`name`, `task_type`, `version`, etc.) are carried as additional keys on the same record object.

New Python helpers: `_manifest_add_es(type, id, **meta)` and `_manifest_add_kibana(space_id, type, id, **meta)` replace the old `_manifest_add()`.

Teardown uses a **dispatch table** keyed on `type` (see `skills/demo-deploy/references/teardown-dispatch.md`) rather than iterating hardcoded inventory lists. New asset types require only a handler entry in the dispatch table.

**Reference:** `skills/demo-deploy/references/asset-manifest.md`, `skills/demo-deploy/references/teardown-dispatch.md`

**Date:** 2026-05-02 | **Session:** Bootstrap to Terraform investigation

---

## D-040: Agent Builder and Workflows are supported in Terraform mode

**Status:** Active | **Applies to:** `skills/demo-deploy/SKILL.md`

**Decision:** As of 2026-05, `elastic/terraform-provider-elasticstack` includes confirmed resources for Agent Builder and Workflows:
- `elasticstack_kibana_agentbuilder_agent`
- `elasticstack_kibana_agentbuilder_tool`
- `elasticstack_kibana_agentbuilder_workflow`

When `DEPLOY_MODE=terraform`, Agent Builder agents/tools and Workflows are generated as Terraform resources in `main.tf`. This supersedes the earlier assumption that these would require Python. Skills still use Python for complex agent configuration that cannot be expressed declaratively (e.g. probe-based skip logic, conditional tool wiring based on runtime feature detection).

**Date:** 2026-05-02 | **Session:** Bootstrap to Terraform investigation

---

## D-041: Pipeline-wide Reference Currency Gate replaces D-034

**Status:** Active — supersedes D-034 | **Applies to:** `skills/demobuilder/SKILL.md` Step 0

**Decision:** The narrow D-034 currency check (demobuilder + hive-mind only) is replaced by a **pipeline-wide Reference Currency Gate** covering all 8 external repositories used by the pipeline. The gate runs at **Step 0 of the orchestrator** before any pipeline stage starts.

**Registry:** `skills/demo-deploy/references/reference-repos.md` is the authoritative list of all repos, their default paths, env var overrides, check methods, scope conditions, and blocking rules.

**Rules:**
- **Blocking**: Only `elastic/demobuilder` itself causes a pipeline halt if stale (ask SA before continuing).
- **Warn-and-continue**: All other repos (hive-mind, agent-skills, workflows, kibana-agent-builder-sdk, vulcan, Terraform providers). Note stale state, recommend pull/update, proceed unless SA objects.
- **Scope-conditional**: Terraform providers only checked when `DEPLOY_MODE=terraform`; `workflows` and `kibana-agent-builder-sdk` repos only when those features are in demo scope; vulcan only when demo-vulcan-generate is in scope.
- **Missing optional repo**: Log `⏭ not installed — skipping`. Never error.

Individual skills invoked directly (not via orchestrator) run a scoped subset covering their specific repo dependencies at minimum.

**Date:** 2026-05-02 | **Session:** Bootstrap to Terraform investigation

---

## D-043: Integration-first data sourcing and asset-after-schema ordering

**Status:** Active | **Applies to:** `skills/demo-data-modeler/SKILL.md`, `skills/demo-deploy/SKILL.md`, `skills/demo-script-template/SKILL.md`

**Decision:** Three binding rules for all engagements:

### Rule 1 — Agent-based integrations for Observability and Security; use package assets first

For any scenario with an Observability or Security primary domain, data sources **must** come from Elastic Agent Fleet integrations (EPR packages), not Prometheus scrapers, custom DCGM/kube-state-metrics streams, or any other custom-named data stream that duplicates a shipped integration.

- Correct: `metrics-kubernetes.pod-*`, `metrics-nginx.stubstatus-*`, `metrics-nvidia_gpu.stats-*`, `logs-system.syslog-*`
- Incorrect: `metrics-k8s.state.prometheus-*`, `metrics-gpu.dcgm.prometheus-*`, any ad-hoc stream named after a Prometheus exporter

**Package assets take precedence over custom-authored assets.** When a Fleet integration package is installed, it ships dashboards, detection rules, ML jobs, data views, alerts, and ingest pipelines. These must be used as the primary demo assets unless the SA explicitly specifies otherwise:

- **Dashboards**: use the package's shipped dashboards; extend or supplement with custom panels only if the package dashboard does not cover a required demo scene
- **Detection rules / ML jobs**: use the package's prebuilt rules and jobs (following D-032 clone-don't-modify for rules); do not author parallel custom rules for the same signal
- **Data views**: use the package's installed data view; do not create a duplicate data view for the same index pattern
- **Ingest pipelines**: use the package's pipeline; add a custom pipeline only as a downstream processor if engagement-specific enrichment is needed

**Embeddable visualizations in custom dashboards:** When building a custom dashboard, scan for already-deployed Kibana assets that tell part of the story and embed them directly rather than re-creating equivalent visualizations from scratch:

- **SLOs**: embed via `"type": "slo_overview"`, `"slo_alerts"`, `"slo_burn_rate"`, or `"slo_error_budget"` panel types with `"config": { "sloId": "<id>", "instanceId": "*" }`
- **ML anomaly results**: embed the ML job's swimlane or heatmap via `"type": "vis"` with `"config": { "ref_id": "<ml-results-vis-id>" }` — retrieve the saved object ID with `GET /api/ml/results/anomaly_charts`
- **Discover sessions / saved searches**: embed via `"type": "discover_session"` with `"config": { "ref_id": "<saved-search-id>" }`
- **Other Lens / aggregation-based visualizations**: embed via `"type": "vis"` with `"config": { "ref_id": "<vis-id>" }` — look up IDs with `GET /api/saved_objects/_find?type=visualization`

The probe sequence must include `GET /api/fleet/epm/packages/<name>` and `GET /api/fleet/epm/packages/<name>/assets` to discover what the installed package provides before any custom asset is authored for that domain.

Exceptions: SA explicitly confirms (a) no Fleet integration exists for the technology, (b) the customer's actual architecture is Prometheus-native and the demo must mirror it, or (c) a specific package asset is inadequate for a required demo scene. Document the exception in the engagement's `{slug}-risks.md`.

Custom search indices (e.g. `lg-clinical-corpus`, `cb-fraud-claims`) are always Path B and are not subject to Rule 1.

### Rule 2 — Custom search mappings may be iterative

Custom indices for search use cases (`strategy: "custom"`, Path B) are expected to evolve: author mapping → deploy → test query → refine. This is normal. No special gate applies beyond standard D-025 field-type compliance.

### Rule 3 — Asset ordering: schema must exist before assets that query it

**No dashboard panel, alerting rule, SLO query, workflow step, or Agent Builder tool that references an index may be authored or deployed until:**

1. `GET /_index_template/<name>` confirms the template exists, **AND**
2. `GET /_component_template/<name>@package` (for integration streams) or `GET /<index>/_mapping` (for custom indices) confirms the field schema, **AND**
3. For integration streams with no live agent data yet: the component template field list serves as the schema source. For custom indices: at least one document must exist before dashboard authoring begins.

**The mandatory probe sequence** (run at Step 2b of demo-deploy, before authoring any asset):
```
GET /_index_template/*                          # discover available templates
GET /_component_template/<name>@package         # read integration field schema
GET /_data_stream/<name>                        # confirm data stream exists
GET /<index>/_mapping                           # for custom indices, confirm actual fields
```

Violating Rule 3 is the root cause of "Unknown column", "no such index", and "empty dashboard" failures. It is never acceptable to write a query against a field name that was not confirmed to exist via the above probes.

**Date:** 2026-05-05 | **Session:** lenovo-gaiaas dashboard rebuild

---

## D-042: Reference file authority — canonical sources for pipeline constants and configuration

**Status:** Active | **Applies to:** All skills and generated scripts

**Decision:** The following files under `skills/demo-deploy/references/` are the **canonical sources** for their respective domains. Skills and generated scripts cite them rather than hardcoding values. Updates to these files propagate automatically to all downstream consumers.

| File | Domain |
|------|--------|
| `reference-repos.md` | External repo registry (paths, check methods, scope conditions) |
| `pipeline-constants.md` | Numeric thresholds, special index names, UUID5 namespace, header values, token visibility defaults |
| `feature-compatibility.md` | Version gates, feature availability by deployment type, ILM vs DSL rules |
| `inference-config.md` | ELSER/reranker service names, model IDs, task types by deployment type |
| `kibana-api-registry.md` | Kibana API paths, feature probe endpoints, auth requirements |
| `teardown-dispatch.md` | Deletion ordering, asset-type → API path dispatch table |
| `terraform-patterns.md` | HCL patterns for Terraform mode generation |
| `env-reference.md` | All `.env` variable definitions and the `.env-sample` template |
| `asset-manifest.md` | Manifest schema, Python helpers, and teardown inventory pattern |

When a value in these files conflicts with text in a `SKILL.md` or `docs/decisions.md`, the reference file wins. Update the SKILL or decision text to point to the reference file.

**Date:** 2026-05-02 | **Session:** Bootstrap to Terraform investigation
