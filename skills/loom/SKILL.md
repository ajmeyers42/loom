---
name: loom
description: >
  Top-level orchestrator for the Elastic loom pipeline. Accepts any combination of
  discovery notes, diagnostic files, architecture diagrams, supplemental notes from the
  discovery team, and existing pipeline outputs; determines which stages need to run,
  executes them in dependency order, and delivers demo-ready artifacts. Demos may emphasize
  search, Observability, Security, or a deliberate mix — scoped to customer needs and
  enterprise-level Elastic capabilities.

  ALWAYS use this skill when the user says "build the demo for X", "run loom",
  "take this from discovery to demo", "full pipeline for [company]", "we have notes and
  a diagnostic — build everything", or provides input files and wants a complete demo build
  rather than a specific pipeline step. Also trigger when the user says "loom" by
  name. Use individual pipeline skills (warp-listen, weave-script, etc.)
  when the user wants only a specific stage.
---

# Loom Orchestrator

You are the project manager for a full demo build. Your job is to figure out where this
engagement is in the pipeline, run every stage that hasn't been completed yet, and hand
off a complete, organized set of artifacts at the end.

You don't do the work yourself — you read each sub-skill's SKILL.md to load its expertise,
execute that stage, then move to the next. Each stage produces files that feed into the
next. Treat each sub-skill as a specialist you're briefing, not a function you're calling.

**External dependencies — `elastic/agent-skills` (Search, Observability, and Security):**
The pipeline is designed to use specialists from `elastic/agent-skills` (separate plugin)
across **all** major Elastic solution areas — not only search and Observability. Install the
**full** plugin so these are **available** in every session, even when a particular
engagement does not use them (e.g. a pure search demo still benefits from a consistent
install; the orchestrator simply does not invoke Security skills for that scenario).

| Area | Examples (non-exhaustive) |
|------|-------------------------|
| **Elasticsearch / search / analytics** | `elasticsearch-esql`, `elasticsearch-file-ingest`, `elasticsearch-authn`, … |
| **Observability** | `observability-manage-slos`, `observability-service-health`, `observability-logs-search`, … |
| **Elastic Security / SIEM** | `security-detection-rule-management`, `security-alert-triage`, `security-case-management`, `security-generate-security-sample-data`, … |
| **Kibana / platform** | `kibana-dashboards`, `kibana-alerting-rules`, `kibana-connectors`, `kibana-vega`, … |
| **Cloud** | `cloud/setup`, `cloud/create-project`, `cloud/manage-project`, … |

Stages **8–9** (provision, deploy) rely on Cloud + Kibana skills; stages **1–7** still call
Security or Observability skills whenever the **discovery, script, or audit** scope requires
them (e.g. SIEM detection demos, hybrid Sec + Obs storylines).

If `elastic/agent-skills` is not installed, surface a clear message rather than failing
silently: install the plugin per `docs/todo.md` — **include Security skills**, not a subset.

**Agent runtimes:** Skills live under `skills/` in the loom repo. Behavior for
Cursor, Claude, and other hosts is unified — see repo root `AGENTS.md` and
`docs/runtimes/`. Do not fork skill content per IDE; only loading paths differ.

**Key behavioral rules** (rationale in `docs/decisions.md`; these are the actions):

- **Deploy approval (D-024):** Stages 8–9 against a live cluster require explicit SA confirmation that they've reviewed `bootstrap-data.py`, platform audit, risks, and checklist. `terraform plan` and `bootstrap-data.py --dry-run` are always safe without approval.
- **Version (D-020, D-033):** New deploy → latest GA unless SA specifies. Existing cluster → probe `GET /` and Kibana `/api/status` first; scope all ES|QL, APIs, and guidance to the confirmed version.
- **Deployability (D-025):** All mappings, API calls, and bootstrap payloads must use real Elasticsearch field types and Kibana API shapes — not invented JSON. Trust `elastic/agent-skills` reference behavior.
- **Tagging (D-026):** Every resource that supports `tags` gets `loom:<engagement_id>`. Spec: `skills/references/loom-tagging.md`.
- **Demo scope:** Enterprise-appropriate features matching the customer's outcomes. Any solution area (search, Observability, Security, cross-solution). Architecture diagrams are first-class inputs. Do not default to search-only.
- **Narrative:** Lead with outcomes tied to the customer's key asks; capabilities follow. If goals are unclear, ask before locking the storyline.
- **Scenario adaptability:** Analytic, not prescriptive. Read the inputs; do not retrofit every engagement into a template that worked for a prior customer.

**Additional skills (planning / Kibana / Security):**
- `warp-spark` — consultative SA coaching to choose demo direction, archetype, wow moments, and the capability map **after the qualification decision** (or immediately for scratch engagements). Produces `{slug}-ideation.md` + `{slug}-capability-map.json` (see Stage 2c).
- `thread-qualify` — consolidates all discovery and diagnostic outputs into a living Opportunity Summary for SDR/AE/SA team alignment. MEDDPIC qualification assessment + technical landscape. Acts as the gate between intelligence gathering and demo planning. Produces `{slug}-opportunity-summary.md` and `{slug}-opportunity-profile.json`. Re-run after any follow-up call. See Stage 2b.
- `weave-agent` — when the demo script includes **Elastic Agent Builder** (custom agent, tools, workflows), produce `{slug}-agent-builder-spec.md` per `skills/weave-agent/SKILL.md`.
- `weave-cost` — two-dimensional: (A) SA tooling for tracking own Claude Code / Cursor spend; (B) demo feature that adds an **AI Cost + Usage dashboard** to any Agent Builder demo. Included by default when Agent Builder is in scope (D-036). Read `skills/weave-cost/SKILL.md`.
- **Elastic Security** — when the story includes detection, alerts, cases, or sample security data, read and follow the relevant `security-*` skills from `elastic/agent-skills` (same install as Search/Obs); **platform-audit** must reflect Sec license/tier and feature availability.

**Reference libraries (hive-mind):**
The `hive-mind` local clone provides validated patterns. Path: `{hive-mind-root}` = `$HIVE_MIND_PATH` if set, otherwise `../hive-mind` (sibling clone). See `docs/ext-registry.yaml`.
- Kibana dashboards: `{hive-mind-root}/patterns/dashboards/DASHBOARD_NDJSON_FORMAT.md`
- Kibana custom panels: `{hive-mind-root}/skills/hive-kibana-custom-panels/SKILL.md` — technical preview, Kibana 9.6+ or Serverless. Prefer standard ES|QL visualizations on the 9.4 floor and on 9.5. Do not reimplement custom panels in loom.
- Workflows API: `{hive-mind-root}/patterns/workflows/WORKFLOWS_API_REFERENCE.md`
- Agent Builder API: `{hive-mind-root}/patterns/agent-builder/AGENT_BUILDER_API_MANAGEMENT.md`
- Probe-based feature detection: `{hive-mind-root}/patterns/deployment/SERVERLESS_FEATURE_DETECTION.md`
- Data fidelity: `{hive-mind-root}/patterns/data/DATA_FIDELITY_GUIDE.md`
- Demo archetypes + coaching: `{hive-mind-root}/skills/hive-sa-coaching/`
Always prefer loom's `docs/decisions.md` and `skills/references/` for
loom-specific decisions; use hive-mind for upstream pattern reference.

**Additional post-deploy skills** available once a cluster is deployed:
- `wind-pulse` — quick pre-demo readiness pulse check (connectivity, doc counts, ML state, ELSER latency)
- `wind-reset` — post-demo cleanup; removes all demo resources prefix-aware

## Entry Points

Two distinct starting points exist for the loom pipeline. Choose based on who is running it:

### AE/SDR Entry Point — `warp-scout`

**Who uses this:** AE or SDR who has discovery notes and wants to structure them and hand
off a brief to the SA. This is the early-funnel pipeline. Non-technical users use the
Gemini Gem (`warp-discovery`) instead of this skill.

Read `skills/warp-scout/SKILL.md` and execute it. This skill runs three stages:
discovery parsing, optional diagnostic analysis, and opportunity review. It produces the
full discovery package plus `opportunity/{slug}-demo-goals.md` as the SA handoff brief.

The AE/SDR pipeline ends at `opportunity/{slug}-demo-goals.md`. The SA picks up from there
with `loom`: import the package into a new engagement (`loom_state new --entry-mode import
--import <package-dir>`), register intake, record the qualification decision, then ideate (D-050).

Trigger phrases: "parse these notes", "qualify this deal", "structure the discovery",
"hand off to SA", "what do we know about [company]".

### SA Entry Point —  (this skill)

**Who uses this:** SA who is building or planning the demo. Can start from AE outputs
( and ) or from scratch.

This is the primary pipeline — proceed through the stages below.

### Engagement state CLI — `loom_state` (D-052)

Skills **author** content (discovery JSON, profiles, ideation, audits). `scripts/loom_state.py`
**registers** that content: it scaffolds engagements, validates outputs against `schemas/`,
enforces gates, and writes `{slug}-pipeline-state.json` + `approvals[]`. Run it on the SA's
behalf; never hand-edit pipeline-state for stages it owns.

| Step | Command (`python3 scripts/loom_state.py …`) |
|---|---|
| Create engagement | `new --slug acme-… --display "…" [--company … --opportunity … --opportunity-id …] --entry-mode import\|notes\|scratch --solution …` |
| Keystore | `keys status\|list\|init\|defer\|set K=V…\|clone --from <slug>\|validate [--probe]` |
| Add input | `inputs add <slug> <file>` (Path A source of truth: `inputs/`) |
| Intake | `listen plan\|record <slug>`, `scan record\|skip <slug>` |
| Gaps | `gaps list <slug>`, `gaps respond <slug> <gap_id> --status answered\|accepted_risk\|deferred` (Path B) |
| Qualify | `qualify plan\|record\|status <slug>`, `qualify decide <slug> --status …`, `qualify design-anyway <slug> --rationale …` |
| Vision | `vision plan\|freeze\|confirm <slug>`, `vision map show\|add\|exclude\|token-visibility <slug> …` |
| Demo path | `path plan\|check <slug>`, `path commit <slug> --path custom\|predefined` |
| Resume | `next <slug>` (phase + next action derived from state), `hygiene` |

Add `--json` for machine-readable output. `loom_state` never mutates a cluster; `keys validate
--probe` is a read-only `GET /` + Kibana `/api/status`.

---

## Step 0: Reference Currency Gate (D-041 — before any pipeline work)

Before starting or continuing any pipeline for an engagement, verify that all external
reference repositories are current.

**Preferred — run the validator script** (takes ~10 seconds, exits non-zero if loom is blocking-stale):

```bash
python3 scripts/validate_ext_deps.py
# or to skip network calls: python3 scripts/validate_ext_deps.py --fast
```

The script reads `docs/ext-registry.yaml` (the machine-readable dependency registry) and
produces the standard currency report. For scope-conditional deps (Terraform, Workflows,
Agent Builder SDK), pass `--all-scopes` when those features are in scope.

**If the script is unavailable** (e.g. first-time setup), read `docs/ext-registry.yaml`
and `skills/references/reference-repos.md` for the full registry and check methods.

### Report format

```
🔄  Reference Currency Gate
    Registry: docs/ext-registry.yaml

  loom                      ✅  up to date (rev abc1234)
  hive-mind                 ⚠️   2 commits behind — run: git -C ../hive-mind pull --ff-only  (rev def5678)
  elastic-agent-skills      ✅  installed at .cursor/plugins/elastic-agent-skills
  workflows                 ⏭  scope-conditional — skipped
  ...
```

### Rules

- **loom stale:** ask the SA before continuing. If they proceed, record the rev.
- **All other repos stale/missing:** note stale state, recommend pull/update, continue unless SA objects.
- **Missing optional repo (vulcan):** log `⏭ not installed — skipping`; never error.
- **Scope-conditional:** only check Terraform providers when `DEPLOY_MODE=terraform`; only check `workflows` / `kibana-agent-builder-sdk` when those features are in demo scope.
- **Adding a new external repo:** add one entry to `docs/ext-registry.yaml` — that is the only file to change.

**Path resolution shorthand:** In SKILL.md files, `{hive-mind-root}` resolves to `$HIVE_MIND_PATH`
if set, otherwise `../hive-mind`. Same pattern for `{workflows-root}`, `{agent-builder-sdk-root}`, etc.
All canonical paths are defined in `docs/ext-registry.yaml`.

**Why:** New pattern adoptions (workflow DELETE, search-by-name, probe-based detection,
dashboard stable UUIDs, inference config changes) are documented in reference repos.
Running against a stale clone means the agent works from outdated guidance.

### warp-discovery drift check

After the repo currency check, scan `skills/warp-discovery/components.md` for `Last synced` dates.
For each upstream skill listed there, compare the `Last synced` date against the output of:

```bash
git -C {loom_repo} log -1 --format="%ci" -- skills/{upstream-skill}/SKILL.md
```

If the skill was modified **after** its `Last synced` date, surface:

```
⚠️  warp-discovery may be out of sync with {skill} (last synced: {date}, last modified: {commit-date}).
    Run the re-sync checklist in skills/warp-discovery/components.md before delivering Gem outputs to SDRs/AEs.
```

This is warn-only — do not block the pipeline. Record it in the Step 2 inventory.

### Pipeline cost tracking (optional — recommended for multi-stage runs)

If the SA wants visibility into token spend across pipeline stages, invoke `hive-token-optimization`
(`.agents/skills/hive-token-optimization`) to set up session cost tracking before starting.
This is SA tooling — not required per engagement, but useful for full pipeline runs where
multiple models and stages accumulate cost. Run once per SA setup, not per engagement.

## Step 0b: Ideation timing (D-050)

Ideation **always runs**, but **after** intake and the recorded qualification decision — it
is Stage 2c below, not a pre-discovery step. It is the SA’s explicit commit to demo direction:
no platform audit, demo-path commit, or build work begins until `{slug}-ideation.md` +
`{slug}-capability-map.json` are frozen (`loom_state vision freeze`) and the refreshed
confirmation is approved (`loom_state vision confirm`).

Exception: **scratch** engagements with no discovery go straight to ideation (Mode 3) — there
is nothing to qualify yet.

## Step 1: Identify the Engagement and Set the Engagement Directory

**Existing engagement:** If the user points at a folder under `LOOM_ENGAGEMENTS_ROOT`
(e.g. `~/engagements/acme-pharma/inputs/notes.md`), that folder is `{engagement_dir}` and
its **name is the slug** — use it exactly as on disk; do not re-normalize it. Run
`loom_state next <slug>` to orient. Legacy folders without pipeline-state still work via the
file-scan fallback (Step 2).

**New engagement — public slug, private identity (dual identity):** The slug is a **public
demo codename** the SA chooses (convention `acme-<vertical>`, e.g. `acme-pharma`). It is
**never derived from the customer name** — it lands on Kibana spaces, tags, index prefixes,
and shared files. The real company / opportunity live only in pipeline-state `identity`:

```bash
python3 scripts/loom_state.py new --slug acme-pharma --display "Acme Pharma" \
  --company "<company>" --opportunity "<opportunity>" --opportunity-id "<crm id>" \
  --entry-mode notes --solution security --notes /path/to/call-notes.md
```

`new` refuses a slug or display name containing the company / opportunity identity,
normalizes the tag id per D-026 (`acme-pharma` → `loom:acmepharma`), auto-suffixes on
folder or tag-id collision (`acme-pharma-2`), refuses a root inside a git work tree, warns
on cloud-synced roots, and writes `.env.example` with public values only.

Entry modes: `import` (AE/SDR package — `--import <dir>`; files are renamed to the public
slug), `notes` (raw notes copied into `inputs/`), `scratch` (no discovery yet → Mode 3).

> **Important:** `{engagement_dir}` is always a folder under `~/engagements/` (or the
> configured root). **Never** name it `workspace`, `workspace-{slug}`, or any path
> relative to the loom repo root. The repo holds skills only; all customer
> artifacts live outside it under `{engagement_dir}`.

`new` creates the audience-scoped subfolders:

```
{engagement_dir}/inputs/       # Path A source of truth — raw notes, transcripts, AE follow-ups
{engagement_dir}/opportunity/  # AE / SDR / SA — sales alignment, customer-facing docs
{engagement_dir}/demo/         # SA — discovery intel, ideation, capability map, platform audit, scripts
{engagement_dir}/data/         # SA / engineer — data model, ML config, Vulcan, seed data
{engagement_dir}/deploy/       # SA — bootstrap, teardown, Kibana objects, readiness
```

Only per-demo artifacts belong in `{engagement_dir}/`; pipeline code stays in the
loom clone (`skills/`, `docs/`).

**Folder → audience mapping:**
| Folder | Primary audience | What lives here |
|--------|----------------|----------------|
| `inputs/` | SA, AE | Raw discovery inputs; every `source_ref.file` in discovery JSON points here |
| `opportunity/` | AE, SDR, SA | Opportunity summary, qualification profile, customer confirmation, gaps, demo brief |
| `demo/` | SA | Ideation contract, discovery JSON, diagnostic outputs, platform audit, demo script, agent spec |
| `data/` | SA, engineer | Data model, ML config, Vulcan outputs, `mappings/`, `pipelines/`, `seed/` |
| `deploy/` | SA | `main.tf`, `providers.tf`, `bootstrap-data.py`, `teardown.py`, provision log, deploy log, checklist, risks, Kibana objects |

`.env` and `.env.example` remain at the **engagement root** (not inside any subfolder) — they
are sourced directly by scripts and shell workflows using the root path convention.

**Keystore ≠ cloud provisioning.** `.env` is the engagement's credential keystore; its
`keystore.status` (`empty|partial|complete|validated`) is tracked separately from the
`cloud-provision` stage (bolt-spin created a cluster → `deploy/{slug}-provision-log.md`).
A keystore is optional for planning (`keys defer`); it is required before live verify, deploy,
or agent-runtime launch. Reuse a sibling engagement's cluster with `loom_state keys clone
--from <slug>` — it keeps this slug's `DEMO_SLUG` / `KIBANA_SPACE_PATH`, re-derives the
`KIBANA_SOLUTION` suggestion, forces a distinct `INDEX_PREFIX` on a shared URL, skips `DEMO_ASSET_TAG` /
`CLUSTER_NAME` / `DEPLOYMENT_ID` unless `--keep`, and never copies private identity.

All output files for this engagement live under the appropriate subfolder. Each skill writes
to the correct folder; the slug prefix is still used on each file so files remain identifiable
when shared individually (e.g. `opportunity/{slug}-confirmation.md` sent to the customer).

## Step 2: Take Inventory

**Token-efficient inventory — read pipeline-state first.**

Check for `{engagement_dir}/{slug}-pipeline-state.json`. If it exists, read it instead of
scanning all output files individually — it is the authoritative record of what has run and
what inputs each stage last saw. If it does not exist yet, fall back to the file scan below
and write the state file once inventory is complete.

Pipeline-state schema — canonical: `schemas/pipeline-state.schema.json`. `loom_state` writes
the intake → demo-path stages (P2); later stages are still updated by the orchestrator after
each stage completes:

```json
{
  "schema_version": "2",
  "slug": "{slug}",
  "engagement_dir": "{engagement_dir}",
  "last_updated": "ISO-8601 timestamp",
  "tag_id": "acmepharma",
  "solution": "search|observability|security|cross_solution|unknown",
  "identity": { "company_name": "…", "opportunity_name": "…", "opportunity_id": "…", "public_display_name": "Acme Pharma" },
  "entry_mode": "import|notes|scratch",
  "path": "custom|predefined|unset",
  "keystore": { "status": "empty|partial|complete|validated", "deferred": false, "source": "manual|sample|clone", "cloned_from": null },
  "approvals": [ { "action": "qualification_decision|qualification_override|vision_freeze|confirmation_approve|demo_path_commit|spend|deploy_apply|teardown",
                   "approver": "…", "timestamp": "…", "artifacts": { "demo/{slug}-ideation.md": "sha256:…" }, "rationale": "…" } ],
  "stages": {
    "discovery-parser":    { "status": "…", "output": "demo/{slug}-discovery.json",        "input_hash": "sha256:…" },
    "diagnostic-analyzer": { "status": "…", "output": "demo/{slug}-current-state.json",    "input_hash": "sha256:…" },
    "opportunity-review":  { "status": "…", "output": "opportunity/{slug}-opportunity-summary.md", "input_hash": "sha256:…", "decision": "proceed" },
    "ideation":            { "status": "…", "outputs": ["demo/{slug}-ideation.md", "demo/{slug}-capability-map.json"], "map_hash": "sha256:…" },
    "platform-audit":      { "status": "…", "output": "demo/{slug}-platform-audit.json",   "input_hash": "sha256:…" },
    "build-path":          { "status": "…", "path": "custom|predefined", "custom_required": true },
    "script-template":     { "status": "complete|skipped|pending", "output": "demo/{slug}-demo-script.md",        "input_hash": "…" },
    "agent-design":        { "status": "complete|skipped|pending", "output": "demo/{slug}-agent-builder-spec.md", "input_hash": "…" },
    "vulcan-generate":     { "status": "complete|skipped|pending", "output": "data/{slug}-vulcan-queries.json",        "input_hash": "…" },
    "data-modeler":        { "status": "complete|skipped|pending", "output": "data/{slug}-data-model.json",             "input_hash": "…" },
    "fleet-integrations":  { "status": "complete|skipped|pending", "output": "deploy/{slug}-integrations-manifest.json","input_hash": "…" },
    "ml-designer":         { "status": "complete|skipped|pending", "output": "data/{slug}-ml-config.json",              "input_hash": "…" },
    "validator":           { "status": "complete|skipped|pending", "output": "deploy/{slug}-demo-checklist.md",     "input_hash": "…" },
    "cloud-provision":     { "status": "complete|skipped|pending", "output": "deploy/{slug}-provision-log.md", "input_hash": "…" },
    "deploy":              { "status": "complete|skipped|pending", "output": "deploy/bootstrap-data.py",            "input_hash": "…" }
  }
}
```

Stage statuses: `pending`, `running`, `complete`, `skipped`, `awaiting_decision`
(qualification recorded, SA decision pending), `awaiting_confirmation` (vision frozen,
refreshed confirmation pending), `stale` (inputs changed since the stage ran), `blocked`.

**Phase is derived, never stored.** `loom_state next <slug>` derives phase (Intake → Qualify →
Design → Build & Validate), next action, and blockers from stages + `path` + approvals +
keystore. `--no-fs` resumes from pipeline-state alone.

`input_hash` is a **sha256 content hash** (`sha256:<64 hex>`) of the stage's inputs — e.g.
discovery-parser hashes every file under `inputs/`; opportunity-review hashes discovery +
gaps + current-state; platform-audit is stamped with the capability-map hash. If the hash
of the current inputs differs from the recorded one, the stage is `stale` and must re-run.
Never use mtimes.

If `{slug}-pipeline-state.json` is missing (legacy engagement), scan for individual output
files to populate it, then write it.

**File scan fallback** (only when no state file exists):

```
Stage                    | Output file                     | Re-run if...
-------------------------|----------------------------------|---------------------------
warp-listen    | demo/{slug}-discovery.json                 | New/changed files under inputs/
warp-scan | demo/{slug}-current-state.json             | New/changed diagnostic file
thread-qualify  | opportunity/{slug}-opportunity-summary.md  | discovery or diagnostic changed; follow-up notes added
warp-spark            | demo/{slug}-ideation.md + capability-map   | Qualification decided (or scratch); not yet frozen
thread-audit      | demo/{slug}-platform-audit.json            | capability map changed since audit
thread-suggest    | (state) path + stages.build-path           | audit changed; path unset
weave-script     | demo/{slug}-demo-script.md                 | platform-audit or ideation changed or user requested
weave-agent | demo/{slug}-agent-builder-spec.md          | script includes Agent Builder and script/audit changed
weave-query     | data/{slug}-vulcan-queries.json            | ES|QL-heavy script; RAG/semantic search in scope; integrations needed
weave-model        | data/{slug}-data-model.json                | script changed or Vulcan outputs changed
weave-fleet  | deploy/{slug}-integrations-manifest.json   | any logs/metrics stream exists in data model (Path A/Path B contract)
weave-train         | data/{slug}-ml-config.json                 | data-model changed and ML scenes in script
finish-check           | deploy/{slug}-demo-checklist.md            | always run last — regenerate each time
```

Conditional skills without a standalone required file (`weave-cost`, Security-specific
sample data, SLO authoring helpers) should still be invoked when the script or audit scopes
those capabilities. Record their outputs in the downstream artifact they enrich (usually
`{slug}-data-model.json`, `{slug}-demo-checklist.md`, or `deploy/bootstrap-data.py`).

**Model tier guidance** — use this when the SA can configure per-stage models or when cost matters:

| Stage | Skill | Model tier | Reason |
|---|---|---|---|
| 1 | warp-listen | Fast | Structured extraction from notes; predictable schema |
| 2a | warp-scan | Fast | Structured extraction from diagnostic JSON |
| 2b | thread-qualify | **Best** | Analytical judgment; MEDDPIC scoring; deal decision |
| 2c | warp-spark | **Best** | Creative ideation; high-stakes SA commit gate |
| 3 | thread-audit | Fast | Lookup and comparison against feature matrix |
| 4 | thread-suggest | Fast | Catalog lookup; predefined vs custom decision |
| 5 | weave-script | **Best** | Customer-facing narrative; highest-stakes artifact |
| 6a | weave-query | **Best** | ES\|QL correctness critical; API shape validation |
| 6b | weave-model | **Best** | Technical accuracy critical; field type errors break deployment |
| 6c | weave-fleet | Fast | Package catalog lookup; manifest generation |
| 6d | weave-train | **Best** | ML job config accuracy; detector/datafeed shapes |
| 6e | weave-agent | **Best** | Agent system prompt quality; tool API shapes |
| 7 | finish-check | Fast | Template-driven checklist generation |
| 8 | bolt-spin | Fast | Provisioning; spend approval required |
| 8b | finish-verify | Fast | Probe, compare, and template |
| 9 | bolt-bootstrap | Fast | Template generation from verified asset-bundle |

Report the inventory to the user before executing:
```
📋 Engagement: [slug] — sales: [Company] (internal only)
📁 Engagement dir: {engagement_dir}

Stage                    Status
─────────────────────────────────────────
Currency check           ✅ Up to date (loom rev abc1234, hive-mind rev def5678)
Discovery parser         ✅ Complete  ({slug}-discovery.json)
Diagnostic analyzer      ⏭  Skipped  (no diagnostic provided)
Opportunity review       🔲 Pending
Ideation                 🔲 Pending  (after qualification decision — D-050)
Platform audit           🔲 Pending  (scoped to the frozen capability map)
Demo path                🔲 Pending  (custom / predefined commit)
Script template          🔲 Pending
Data modeler             🔲 Pending
ML designer              🔲 Pending  (will check for ML scenes in script)
Validator                🔲 Pending

Starting from: weave-script
```

After this inventory, continue with **planning stages** (1–7) without an extra confirmation
step unless the user asked to pause. **Do not** run provisioning or deploy (stages 8–9)
without explicit approval — see Stage 8–9 notes below.

## Step 3: Detect Available Inputs

Before running any stage, verify what raw inputs are available:

**Discovery notes** — PDF, markdown, plain text, or raw notes provided by the user or
already parsed into `{slug}-discovery.json`. If raw notes are present and no JSON exists,
run `warp-listen` first.

**Diagnostic file** — ZIP archive or individual JSON API exports from an Elastic cluster.
If present and no `{slug}-current-state.json` exists, run `warp-scan`.
If absent, skip the diagnostic stage entirely — it's optional.

**Existing pipeline outputs** — Any `{slug}-*.json` or `{slug}-*.md` files in `{engagement_dir}`.
Use these as inputs to downstream stages. Do not regenerate unless inputs changed.

## Step 4: Execute Each Pending Stage

**Context budget — load only what the current stage needs.**
Before running a stage, load only its required input files. Once a stage completes and its
structured JSON output is written, that output is the canonical representation — raw inputs
(discovery note PDFs, raw note text, diagnostic ZIPs) should be considered dropped from
active context. Downstream stages read the parsed JSON, not the original files.
This keeps context windows proportional to the current stage, not cumulative across the pipeline.

**Session boundaries — one stage per chat session.**
Each stage should ideally run in its own Cursor chat. At stage completion, emit a session
handoff line so the SA knows exactly what to attach to the next session:

```
🔁 Next session: start fresh, attach `{primary-output-file}` (and `.env` if cluster work follows)
   Stage to run next: {next-stage}
   Model: [fast] or [full] — see cursor.md model table
```

A fresh session starting with only the prior stage's output file avoids context
accumulation costs and keeps the model focused on the current stage's task only.
`{slug}-pipeline-state.json` is the inventory shortcut — a new session can orient
in seconds without re-reading all prior outputs.

**Model selection per stage** — see `docs/runtimes/cursor.md` for the full table.
Stages tagged `[fast-model]` below work well with a cheaper/faster model (e.g.
claude-3-5-haiku, gpt-4o-mini). Stages tagged `[full-model]` require a capable model
(Sonnet/Opus/GPT-4o) — creative generation or correctness-sensitive code.

**Subagent routing** — see `docs/agent-patterns.md` for the full Tier A–E matrix.

Skills stay the source of truth (`skills/<name>/SKILL.md`). Subagents are an optional
**execution mode** (Cursor Task / Claude Task, or thin wrappers under `.cursor/agents/`).
Do not put D-024, ideation freeze, or qualification stop decisions inside unattended workers.

When the runtime supports parallel or isolated workers, the orchestrator **may** spawn
these **Tier A** stages as subagents instead of running them inline:

| Stage | Skill path | Typical inputs to pass |
|-------|------------|------------------------|
| warp-listen | `skills/warp-listen/SKILL.md` | Raw discovery notes |
| warp-scan | `skills/warp-scan/SKILL.md` | Diagnostic ZIP / exports |
| thread-audit | `skills/thread-audit/SKILL.md` | discovery.json, opportunity-profile.json, current-state.json (if any) |
| weave-fleet | `skills/weave-fleet/SKILL.md` | data-model.json, demo-script.md |
| weave-train | `skills/weave-train/SKILL.md` | data-model.json, demo-script.md |
| finish-check | `skills/finish-check/SKILL.md` | Prior planning artifacts + pipeline-state |
| finish-verify | `skills/finish-verify/SKILL.md` | `.env`, demo-script, data-model, platform-audit |
| bolt-bootstrap | `skills/bolt-bootstrap/SKILL.md` | `asset-bundle/` (codegen only; live apply stays gated in parent) |

**Spawn rules:**

1. Brief the worker with: engagement slug, `{engagement_dir}`, skill path, input file list, and exit condition (which artifacts to write).
2. Prefer parallel pairs from `docs/efficiency.md` §4 when both sides are pending (e.g. warp-listen ∥ warp-scan; weave-fleet ∥ weave-train).
3. After each worker returns, **read the artifacts it claims to have written**, then **update `{slug}-pipeline-state.json`** in the parent (`loom_state listen record` / `scan record` for intake workers; otherwise mark stage `complete`, output filename, input hash). Do not trust the summary alone.
4. Keep Tier C stages (warp-spark, thread-qualify, weave-script, bolt-spin, wind-reset) and all approval gates in the **main** interactive chat.
5. Prefer CLI (`scripts/inventory.py`, `wind_pulse.py`) over an AI subagent for deterministic status/health.

For each stage that needs to run, in order:

1. **Announce the stage:** `🔄 Running: warp-listen...`
2. **Read the sub-skill SKILL.md** from the sibling directory:
   `../warp-listen/SKILL.md` (relative to this file's location)
   This loads the specialist's instructions. Follow them exactly.
   If the relative path does not resolve in the current agent runtime, read
   `{loom_repo}/skills/<skill>/SKILL.md` from the repo root instead.
3. **Execute the stage** using the loaded instructions and available inputs.
4. **Write outputs** to `{engagement_dir}` with the slug prefix.
5. **Update `{slug}-pipeline-state.json`** — for intake → demo-path stages, run the stage's `loom_state … record` / `decide` / `freeze` / `confirm` / `commit` command (it validates and records the hash); for later stages, mark the stage `complete` with output filename and sha256 input hash. This keeps the next session's inventory instant.
6. **Announce completion:** `✅ Stage N complete — {stage-name} → {output-file}. Proceeding to Stage N+1.`
   Example: `✅ Stage 1 complete — warp-listen → demo/{slug}-discovery.json. Proceeding to Stage 2a.`
7. **Emit session handoff:** `🔁 Next session: attach {primary-output-file} — run {next-stage} [{model-tag}]`
8. **Surface any blockers:** If a stage produces a RED platform audit or critical gaps, pause
   and report before continuing:
   ```
   ⚠️  Platform audit returned RED. Blocking issues:
   - Agent Builder requires 9.x upgrade (current: 8.17.5)
   - ELSER endpoint not deployed

   Recommended action: re-scope demo to exclude Agent Builder, proceed with ES|QL + ML.
   Continuing with adjusted scope...
   ```
   If the blocker is fatal (e.g., no data available at all, zero contacts in discovery),
   stop and ask the user for the missing input rather than producing empty outputs.

### Stage execution order and skip conditions

**Stage 1 — warp-listen** `[fast-model ok]`
- Skip if: `stages.discovery-parser` is `complete` and not stale (`loom_state next` reports no new `inputs/` content)
- Read: `../warp-listen/SKILL.md`
- Inputs: every file under `inputs/` (`loom_state listen plan <slug>` lists them plus the prior gap ids to keep stable)
- Outputs: `{slug}-discovery.json` (claims + gaps with `source_ref` evidence), `{slug}-confirmation.md`, `{slug}-gaps.md`
- **Register:** `loom_state listen record <slug>` — validates the schema, verifies every
  `source_ref` excerpt against `inputs/`, enforces gap-id stability, and reports gaps closed
  by re-inference. Fix and re-run on failure; do not hand-mark the stage complete.

**Stage 2 — warp-scan** `[fast-model ok]` *(optional)*
- Skip if: no diagnostic file provided OR `demo/{slug}-current-state.json` already exists
- Read: `../warp-scan/SKILL.md`
- Inputs: diagnostic ZIP or API exports
- Outputs: `{slug}-current-state.json`, `{slug}-architecture.md`, `{slug}-findings.md`
- **Register:** `loom_state scan record <slug>` (or `scan skip <slug>` when no diagnostic exists)

**Stage 2b — thread-qualify** `[fast-model ok]`
- Skip if **all** of the following are true:
  1. `opportunity/{slug}-opportunity-summary.md` AND `opportunity/{slug}-opportunity-profile.json` both exist
  2. `{slug}-discovery.json` and `{slug}-gaps.md` have not changed since the last run
  3. `{slug}-current-state.json` and `{slug}-findings.md` have not changed (or were absent before and remain absent)
  4. **No new raw notes, follow-up text, or supplemental files have been provided in this session**
- Re-run (do not skip) if any of the following are true:
  - The outputs do not exist
  - `{slug}-discovery.json` or `{slug}-gaps.md` changed (e.g., Stage 1 just ran)
  - `{slug}-current-state.json` or `{slug}-findings.md` changed (e.g., Stage 2 just ran)
  - **The SA has provided new notes, follow-up text, or files in the current session** — even if
    the parsed JSON files appear unchanged, fresh input always warrants a re-run so the living
    document reflects the latest intelligence
- Read: `../thread-qualify/SKILL.md`
- Inputs: `{slug}-discovery.json` (required), `{slug}-gaps.md`, `{slug}-gap-responses.json`
  (Path B answers, if present), `{slug}-current-state.json`, `{slug}-findings.md`,
  `{slug}-architecture.md` (all optional but used when present). New raw notes go into
  `inputs/` first (`loom_state inputs add`) and re-run Stage 1 — Path A is the source of truth.
- Outputs: `{slug}-opportunity-summary.md`, `{slug}-opportunity-profile.json`
- **Register:** `loom_state qualify record <slug>` → stage `awaiting_decision`.
- **Decision gate (SA, in the main chat):** surface the recommendation, open blocking gaps
  (`loom_state gaps list`), and prompt the SA to share the summary with SDR/AE. Record the
  SA's call with `loom_state qualify decide <slug> --status proceed|continue_discovery|not_qualified`
  (`--ae-aligned`, `--rationale`, `--accept-risk <gap_id>…`). This writes `approvals[]` and
  `qualification_decision` into the profile.
  - `proceed` requires every blocking gap answered or accepted as risk (rationale required).
  - `not_qualified` **stops the pipeline**.
  - `continue_discovery` **parks** the engagement — Vision stays locked until new inputs
    close the gaps, or the SA explicitly runs `loom_state qualify design-anyway <slug>
    --rationale "…"`.

**Stage 2c — warp-spark** `[best-model]` *(always runs — D-050)*
- Runs after the qualification decision is `proceed` (or design-anyway); scratch engagements
  without discovery run it first (Mode 3).
- Skip if: `stages.ideation` is `complete` and not stale. Discovery notes do not skip ideation.
- Read: `../warp-spark/SKILL.md`. `loom_state vision plan <slug>` reports the mode:

  | Condition | Mode |
  |---|---|
  | `opportunity/{slug}-demo-goals.md` exists | **Mode 1 — SA Expansion** (pre-seeded from AE/SDR outputs) |
  | Discovery exists but no goals brief | **Mode 2 — Customer context** |
  | Scratch, no discovery | **Mode 3 — From scratch** |

- Outputs: `demo/{slug}-ideation.md`, `demo/{slug}-capability-map.json` (built with
  `loom_state vision map add|exclude` from `skills/references/capability-catalog.json`;
  ≥1 SA-added feature expected; Agent Builder implies `ai-cost-dashboard` per D-036),
  refreshed `opportunity/{slug}-confirmation.md`, and a `Demo direction:` line in the summary TL;DR.
- **Freeze:** `loom_state vision freeze <slug>` — checks required sections, renders the map
  table, records `vision_freeze`. Stage → `awaiting_confirmation`.
- **Confirm (SA gate):** SA approves the refreshed confirmation → `loom_state vision confirm <slug>`.
  Editing the map after freeze returns it to draft and marks ideation stale.

**Stage 3 — thread-audit** `[fast-model ok]`
- Runs after Stage 2c is `complete` (vision frozen + confirmation approved).
- Skip if: `demo/{slug}-platform-audit.json` exists AND its `meta.capability_map_hash` matches
  the current capability map
- Read: `../thread-audit/SKILL.md`
- Inputs: **the selected capability map** (`loom_state path plan <slug>` lists the in-scope
  capability ids, catalog audit features, default `remediation_owner`, and the map hash to
  stamp), `{slug}-current-state.json` (if available), `{slug}-opportunity-profile.json`
- Outputs: `{slug}-platform-audit.json` (one row per in-scope `capability_id`;
  `scope_source: capability_map`), `{slug}-platform-audit.md`
- **Check:** `loom_state path check <slug>` — coverage, map-hash match, `remediation_owner`
  on every amber row.
- **Blocker check:** RED rows (`blocked` / `upgrade_required`) block the path commit. Re-scope
  in the capability map (`vision map exclude`), re-freeze, and re-audit — do not silently drop scenes.

**Stage 3b — thread-suggest** `[fast-model ok]` *(required — D-049)*
- **Decision gate: Demo path — predefined vs. custom build.** Every engagement must make this
  decision explicitly before scripting begins.
- Read: `../thread-suggest/SKILL.md`
- Inputs: `demo/{slug}-ideation.md` + `demo/{slug}-capability-map.json` (required),
  `opportunity/{slug}-opportunity-profile.json`, `demo/{slug}-platform-audit.json`,
  `skills/thread-suggest/references/standard-demos.md`
- **Commit:** `loom_state path commit <slug> --path predefined|custom` — sets top-level
  `path`, `stages.build-path`, completes `platform-audit`, and records `demo_path_commit`.
- **PREDEFINED path:** Produces `opportunity/{slug}-predefined-recommendation.md` and
  updates `opportunity/{slug}-confirmation.md`. **Pipeline ends here** — custom Build stays
  locked. Do not run Stage 4+.
- **CUSTOM path:** `stages.build-path.custom_required: true`, proceeds to Stage 4.
- Halt if: vision is not confirmed — run Stage 2c first.

**Stage 4 — weave-script** `[full-model required]` *(custom path only — skip if predefined was recommended)*
- Skip if: `demo/{slug}-demo-script.md` exists AND platform-audit hasn't changed AND ideation hasn't changed
- Read: `../weave-script/SKILL.md`
- **Before authoring:** read `skills/weave-script/references/demo2win-conventions.md` (D-051)
- Inputs: `{slug}-discovery.json`, `{slug}-platform-audit.json`, `{slug}-ideation.md` (required — takes priority for wow moments and archetype)
- Outputs: `{slug}-demo-script.md`, `{slug}-demo-brief.md`, `{slug}-live-script.md`
- Script must include: opening punch, 3–5 self-contained vignettes, value confirmation close

**Stage 4b — weave-agent** `[full-model required]` *(conditional — Agent Builder only)*
- Skip if: `demo/{slug}-demo-script.md` does not include Agent Builder / custom agents / tools /
  workflows, OR `demo/{slug}-agent-builder-spec.md` exists AND the script and audit have not changed
- Read: `../weave-agent/SKILL.md`
- Inputs: `{slug}-demo-script.md`, `{slug}-discovery.json`, `{slug}-platform-audit.json`
- Outputs: `{slug}-agent-builder-spec.md`
- If the platform audit marks Agent Builder blocked, do not write a runnable full spec; surface
  the blocker and fallback.

**Stage 4c — weave-cost** `[fast-model ok]` *(conditional — AI / Agent Builder only)*
- Skip if: no Agent Builder or AI-powered component is in scope, OR `INCLUDE_TOKEN_VISIBILITY=false`
- Read: `../weave-cost/SKILL.md`
- Inputs: `{slug}-demo-script.md`, `{slug}-data-model.json` if it exists, `.env` if available
- Outputs: guidance and schema content that downstream stages must materialize in
  `{slug}-data-model.json`, `{slug}-demo-checklist.md`, and dashboards. Deploy materializes them through `finish-verify` and `bolt-bootstrap`.
- Include by default for Agent Builder demos per D-036.

**Stage 4.5 — weave-query** `[full-model required]` *(conditional — ES|QL / RAG / integration-grounded data)*
- Skip if **all** of the following are true:
  1. `data/{slug}-vulcan-queries.json` exists AND the script hasn't changed
  2. Vulcan is not installed at `../vulcan` and the SA does not want to install it now
  3. No integration-grounded data is needed (no Fleet/Beats integrations in scope)
- Run if **any** of the following are true:
  - Script has 5+ distinct ES|QL queries or parameterized query scenes
  - Demo includes semantic / RAG search (`semantic_text`, RERANK, COMPLETION)
  - Discovery or script references Elastic integrations (logs-* / metrics-* naming needed)
  - SA says "use Vulcan", "generate synthetic data", or "generate validated queries"
- Read: `../weave-query/SKILL.md`
- Inputs: `{slug}-demo-script.md`, `{slug}-discovery.json`, `../vulcan/.env` (cluster creds)
- Outputs: `{slug}-vulcan-queries.json`, `{slug}-vulcan-data-profile.json`,
  `{slug}-vulcan-query-results.json`, `{engagement_dir}/vulcan-data/*.csv`

**Stage 5 — weave-model** `[full-model required]`
- Skip if: `data/{slug}-data-model.json` exists AND script hasn't changed AND Vulcan outputs unchanged
- Read: `../weave-model/SKILL.md` and `../weave-model/references/mapping-patterns.md`
- Inputs: `{slug}-demo-script.md`, `{slug}-discovery.json`, `{slug}-agent-builder-spec.md`
  (if present), `{slug}-vulcan-queries.json` (if present — fast path for ES|QL + seed data),
  and weave-cost guidance if Agent Builder / AI is in scope
- Outputs: `{slug}-data-model.json`, `{slug}-data-model.md`, individual mapping files

**Stage 5.5 — weave-fleet** `[full-model required]` *(required when logs/metrics streams exist)*
- Skip only if **all** of the following are true:
  1. `deploy/{slug}-integrations-manifest.json` exists AND data model and script are unchanged
  2. `data/{slug}-data-model.json` contains no `logs-*` and no `metrics-*` data streams
- Run if **any** of the following are true:
  - Data model contains any `logs-*` or `metrics-*` stream
  - `data/{slug}-vulcan-queries.json` has `integration_grounded: true`
  - Discovery mentions Kubernetes, NVIDIA GPU, APM, synthetics, or other named integrations
  - SA says "install the X integration", "use Fleet for log collection", "EPM package install",
    "I want the out-of-the-box dashboards", "set up the integration"
- This stage enforces the hybrid contract:
  - **Path A:** package-backed streams (`logs-<integration>.<dataset>-<namespace>`,
    `metrics-<integration>.<dataset>-<namespace>`)
  - **Path B:** fallback managed-template streams (`logs-demo.<dataset>-<namespace>`,
    `metrics-demo.<dataset>-<namespace>`)
- Read: `../weave-fleet/SKILL.md`
- Inputs: `data/{slug}-data-model.json`, `demo/{slug}-discovery.json`, `demo/{slug}-demo-script.md`,
  `data/{slug}-vulcan-queries.json` (if present), `{engagement_dir}/.env` (for mode detection)
- Outputs: `deploy/{slug}-integrations-manifest.json`, `demo/{slug}-integration-assets.md`
- **Human gate:** if Step 3 finds `storyline_enhancement` assets, skill pauses and asks SA
  whether to re-run `weave-script` before proceeding

**Stage 6 — weave-train** `[full-model required]` *(conditional)*
- Skip if: no ML scenes detected in `demo/{slug}-demo-script.md`, OR `data/{slug}-ml-config.json`
  exists AND data model hasn't changed
- Detect ML scenes: look for terms like "ML anomaly", "anomaly detection", "swimlane",
  "anomaly_score" in the script
- Read: `../weave-train/SKILL.md`
- Inputs: `{slug}-demo-script.md`, `{slug}-data-model.json`
- Outputs: `{slug}-ml-config.json`, `{slug}-ml-setup.md`

**Stage 7 — finish-check** `[fast-model ok]`
- Always run last before deploy — regenerate even if it exists
- Read: `../finish-check/SKILL.md`
- Inputs: all available `{slug}-*.json` and `{slug}-*.md` files in `{engagement_dir}`
- Outputs: `{slug}-demo-checklist.md`, `{slug}-risks.md`

**Stage 8 — bolt-spin** `[fast-model ok]` *(optional — new cluster path only)*
- **Requires explicit SA approval** to spend resources / create infrastructure (unless
  the user already clearly requested provisioning this session)
- Skip if: keystore status is `complete` or `validated` (`loom_state keys status <slug>`)
- Run if: user requests "create a new cluster", "spin up a serverless project", or the
  keystore is empty/partial and deployment was requested
- Read: `../bolt-spin/SKILL.md`
- Inputs: deployment type preference, region, engagement slug
- Outputs: `{engagement_dir}/.env`, `{engagement_dir}/.env.example`, `deploy/{slug}-provision-log.md`
- Note: to reuse an existing cluster from another engagement, run
  `loom_state keys clone <slug> --from <other-slug>` (never copy `.env` by hand) — no
  re-provisioning needed

**Stage 8b — finish-verify** `[full-model required]` *(required before deployment — D-045)*
- **Mandatory gate between planning and deployment.** No Terraform or Python deployment
  artifacts are generated until this stage writes `deploy/asset-bundle/asset-schema.json`.
- Skip if: `deploy/asset-bundle/asset-schema.json` exists AND data model, script, and platform audit are all unchanged since last run
- Run if: `.env` exists AND Stage 7 returned go or conditional-go AND asset bundle is absent or stale
- Read: `../finish-verify/SKILL.md`
- Inputs: `{engagement_dir}/.env`, `data/{slug}-data-model.json`, `demo/{slug}-demo-script.md`, `demo/{slug}-platform-audit.json`
- Outputs: `deploy/asset-bundle/asset-schema.json`, `deploy/asset-bundle/asset-index.json`, and all authored asset files per skill dispatch table in finish-verify
- **Blockers (halt Stage 9):** Failed ES|QL validation, null viz-queried fields, version gate fail, disabled required feature. SA must resolve before continuing.

**Stage 9 — bolt-bootstrap** `[full-model required]` *(optional — runs after asset verifier)*
- **Requires explicit SA approval** before running Terraform apply or bootstrap-data.py
  against a **live** cluster. `terraform plan` and `python3 bootstrap-data.py --dry-run`
  do not require approval. See `docs/decisions.md` **D-024**.
- Skip if: user has not requested deployment and no `.env` is present
- Run if: `deploy/asset-bundle/asset-schema.json` exists (Stage 8b complete)
  AND `.env` exists AND user says "deploy", "generate the terraform", or "generate the bootstrap" after reviewing Stage 8b outputs
- Requires: `deploy/asset-bundle/asset-schema.json` — stop with clear message if missing (run Stage 8b first)
- Read: `../bolt-bootstrap/SKILL.md` (routes to ECH, Serverless, or ECK variant based on `DEPLOYMENT_TYPE` in `.env`)
- Inputs: `deploy/asset-bundle/asset-schema.json`, `deploy/asset-bundle/asset-index.json`, `{engagement_dir}/.env`
- Outputs: `deploy/main.tf`, `deploy/providers.tf`, `deploy/{slug}.tfvars`, `deploy/bootstrap-data.py`
- **Split (D-046):** `main.tf` = all infrastructure. `bootstrap-data.py` = enrich execute, seed data, field assertions, ELSER warmup, anomaly injection, manifest write only.

## Step 5: Deliver the Handoff Summary

When all stages are complete, produce a structured handoff:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 LOOM COMPLETE — [Company]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Workspace: $LOOM_ENGAGEMENTS_ROOT/{slug}/  (default: ~/engagements/{slug}/)

ARTIFACT SUMMARY
────────────────
opportunity/  (AE / SDR / SA — team alignment gate)
  ✅  opportunity/{slug}-opportunity-summary.md   — living team review doc (SDR/AE/SA)
  ✅  opportunity/{slug}-opportunity-profile.json — MEDDPIC + technical landscape (machine-readable)
  ✅  opportunity/{slug}-confirmation.md          — send to customer before demo
  ✅  opportunity/{slug}-gaps.md                  — internal follow-up questions
  ✅  opportunity/{slug}-demo-brief.md            — one-page AE brief

demo/  (SA — planning & design intelligence)
  ✅  demo/{slug}-ideation.md          — frozen demo direction contract (D-050)
  ✅  demo/{slug}-capability-map.json  — selected capabilities (audit + build scope)
  ✅  demo/{slug}-discovery.json       — structured customer profile
  ⏭   or ✅  demo/{slug}-current-state.json  — diagnostic (optional)
  ✅  demo/{slug}-platform-audit.json  — feature feasibility matrix
  ✅  demo/{slug}-platform-audit.md    — SE briefing
  ✅  demo/{slug}-demo-script.md       — full SE script with scenes and queries
  ⏭   or ✅  demo/{slug}-agent-builder-spec.md — Agent Builder spec (if agent scenes exist)

data/  (SA / engineer — data model & generation)
  ✅  data/{slug}-data-model.json      — index mappings, build order, seed data spec
  ✅  data/{slug}-data-model.md        — human-readable build overview
  ⏭   data/{slug}-ml-config.json      — skipped if no ML scenes in script
  ⏭   data/{slug}-vulcan-queries.json — Vulcan ES|QL outputs (if Vulcan ran)

deploy/  (SA — cluster assets & readiness)
  ✅  deploy/{slug}-demo-checklist.md  — pre-demo checklist (timed)
  ✅  deploy/{slug}-risks.md           — risks and fallbacks
  ✅  deploy/{slug}-provision-log.md   — cluster info (if provisioned)
  ✅  deploy/main.tf                   — infrastructure (D-046)
  ✅  deploy/bootstrap-data.py         — data operations only (seed, warm-up, anomaly injection, manifest)
  ✅  deploy/{slug}-deploy-log.md      — what was created for this engagement
  ⏭   (skipped — no cluster target provided)

root/  (credentials — never in a subfolder)
  ✅  .env                             — cluster credentials (never committed)
  ✅  .env.example                     — safe template for sharing

PLATFORM STATUS: [Green / Amber / Red from platform audit]
  Ready now:     [list features verified]
  Setup needed:  [gaps from audit]
  Not in scope:  [explicitly out of story]

BEFORE YOU BUILD  *(shown only if cluster not yet deployed)*
─────────────────
  1. Run bolt-spin or `loom_state keys clone <slug> --from <other-slug>`
  2. Run finish-verify, then bolt-bootstrap
  3. Review deploy/main.tf and deploy/bootstrap-data.py; terraform plan and bootstrap-data.py --dry-run are safe
  4. Run end-to-end checks from {slug}-demo-checklist.md (scenes vary by demo)

  *(If already deployed, check {slug}-deploy-log.md)*

SEND TO CUSTOMER
─────────────────
  {slug}-confirmation.md  (after review — remove internal notes)

DEMO DAY
─────────
  Follow {slug}-demo-checklist.md and {slug}-demo-brief.md
  Go / No-Go per {slug}-risks.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Handling Partial Inputs

**Only discovery notes, no diagnostic:**
Run stages 1, 2b, 2c, 3, 3b, 4, 4b/4c if in scope, 5, 6 (if ML), 7 (`scan skip` for stage 2). Platform audit runs in partial mode against the frozen capability map.

**Only a diagnostic file, no discovery notes:**
Run stage 2 only. Output the current-state and findings. Tell the user: "Run
`warp-listen` with discovery notes to continue the pipeline."

**Discovery notes + diagnostic:**
Run all stages in order, including opportunity review before platform audit and conditional 4b/4c stages when in scope. Full audit with both inputs.

**Resuming a partial build:**
User says "continue the [customer] demo build" or "pick up where we left off."
Take inventory, identify what's missing, run only the pending stages.

**User wants to regenerate one stage:**
"Rewrite the demo script — new stakeholder joined the meeting."
Run only `weave-script` with the updated context, then re-run `finish-check`.
Leave all other artifacts unchanged unless downstream stages must react.

**User wants to deploy to a new cluster:**
"Create a new serverless project for this demo and deploy it."
Run stage 8 (bolt-spin) to provision and write `.env`, then stage 8b (finish-verify)
and stage 9 (bolt-bootstrap). Live `terraform apply` and `bootstrap-data.py` stay behind
the D-024 approval gate. Stages 1–7 already complete — skip them.

**User wants to deploy to an existing cluster:**
"I already have a cluster — here are my credentials." Record them with `loom_state keys set`
(or `keys clone --from <slug>`), then `keys validate --probe`. Skip stage 8. Run stages 8b and 9 only. Verify the `.env` has all required fields before
generating `main.tf` and `bootstrap-data.py`.

**User running a second engagement on the same cluster:**
"Reuse this cluster for another customer." Run `loom_state keys clone <new-slug> --from
<old-slug>` — it binds `DEMO_SLUG` / `KIBANA_SPACE_PATH` / `ENGAGEMENT` to the new slug and
forces a distinct `INDEX_PREFIX` (e.g. `are-` → `aph-`). Run stage 9 with the new slug’s artifacts.
No re-provisioning unless credentials or endpoint change; rebuild data model only if scope differs.

## What Good Looks Like

**Full cold start:** User drops a PDF and a diagnostic ZIP. Orchestrator auto-detects
both, runs all 7 stages in order, delivers a complete engagement directory with 12+ files and a
clear handoff summary. Total time to run: the time it takes to execute each stage.

**Resume from discovery JSON:** User already has `{slug}-discovery.json` from a prior
session. Orchestrator skips stage 1, runs stages 3–7, outputs script + data model +
checklist. Clearly reports what was skipped and why.

**RED platform audit — auto-adjust:** Demo scoped for Agent Builder but customer cluster is
on 8.x self-managed. Orchestrator surfaces the blocker, removes Agent Builder from script
scope, proceeds with what the platform supports, notes the removed scene in the handoff
under "Scope adjustments."

**End-to-end with deploy:** User provides discovery notes and says "create a serverless
project and deploy this demo." Orchestrator runs all 9 stages: builds the full artifact
set, provisions the cluster, runs finish-verify and bolt-bootstrap, then applies the
reviewed Terraform and `bootstrap-data.py`. Delivers a deploy log
confirming 4 indices created, seed data loaded, ELSER endpoint warmed.

**Multi-customer on shared cluster:** First engagement deployed with `INDEX_PREFIX=are-`.
User adds a second engagement; `keys clone` gives it `INDEX_PREFIX=aph-` and its own
space, skips provisioning, runs stage 9 for the new artifacts. Both demos
coexist on the same cluster.

**Pre-demo morning check:** Demo was deployed yesterday. SE asks "is this engagement ready?"
Orchestrator reads `.env` + data model, runs `wind-pulse`, and returns a compact ✅/❌
report with paste-ready fix commands for anything off.

**Post-demo cleanup:** Demo went well. SE asks to tear down this engagement’s resources.
Orchestrator runs `wind-reset` — stops ML jobs, removes Kibana objects, deletes indices
and all supporting infrastructure. If INDEX_PREFIX was set (shared cluster), only prefix-
matching resources are removed. Offers to delete the serverless project entirely if it was
provisioned specifically for this engagement.

**Orchestrator as SE daily driver:** SE starts every engagement by dropping discovery
notes into a prompt. Orchestrator handles the rest — they get a script, a data model,
and a pre-demo checklist without touching any individual skill manually.
