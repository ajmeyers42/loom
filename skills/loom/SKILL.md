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

**Deploy approval:** Before running **Stage 8 (bolt-spin)**, **Stage 8b (finish-verify)**, or **Stage 9 (bolt-bootstrap)**
against a **live** cluster, confirm the SA wants to provision or deploy **and** has **reviewed**
`bootstrap.py`, `{slug}-platform-audit`, `{slug}-risks`, `{slug}-demo-checklist.md`, and any
Kibana/ES files the script will apply — unless they state review is complete. **`bootstrap.py --dry-run`**
does not require this gate. See `docs/decisions.md` **D-024** and `AGENTS.md`. Planning stages
(1–7) may proceed when the SA asks to build or refresh artifacts.

**Elastic version scope:**
- **New deployment or Serverless project** — Assume the **latest generally available**
  stack version for that offering **unless the SA specifies otherwise**. Record the
  actual version in `.env` (`ELASTIC_VERSION`) and in any provision log after create.
- **Existing deployment / project / cluster** — **Do not** assume latest. Obtain
  `version` from `GET /` (Elasticsearch) and Kibana `/api/status` (or from diagnostic /
  `warp-scan` output) **before** writing demo scripts, data models, or
  execution plans, and thread that version into **thread-audit** and downstream
  artifacts.
- **All scripts, plans, and guidance** — Must match the target stack: ES|QL syntax,
  API shapes, Kibana features, ML APIs, and Agent Builder / Workflows availability all
  depend on version and deployment type. When in doubt, cite the version the guidance
  applies to.

**Deployability on Elastic (`docs/decisions.md` D-025):** Data models, bootstrap payloads,
Agent Builder tools, ML configs, and Kibana imports must be **deployable** on a real cluster
and use **Elastic datatypes and API conventions** — not hand-wavy JSON. When skills or
OpenAPI disagree with a first guess, trust the stack and **`elastic/agent-skills`**
reference behavior.

**Engagement tagging (`docs/decisions.md` D-026):** Generated **`bootstrap.py`** and API payloads
must merge **`loom:<engagement_id>`** into every resource that supports **`tags`**
(SLOs, alerting rules, ML jobs, Agent Builder entities, etc.). Derive `<engagement_id>` per
**`skills/bolt-launch/references/loom-tagging.md`** (`INDEX_PREFIX` normalized, else
`DEMO_SLUG`; optional **`DEMO_ASSET_TAG`** override).

**Demo scope — enterprise capabilities and solution areas:**
- **Assume enterprise-appropriate features** when shaping the demo: prefer capabilities that
  match the **customer outcomes** and pain points in the inputs (discovery, diagnostic,
  supplemental notes), subject to **thread-audit** and license/version reality.
  Do not default to “minimal” or core-search-only unless the customer story is search-only.
- **Inputs** may include: discovery notes, **Elastic diagnostic** exports, **additional
  notes** from the AE/SE/discovery team, and **architecture diagrams** (current-state
  systems, data flows). Treat diagrams as first-class context — extract what they imply
  for integrations, data paths, and operational pain.
- **Use case domains:** Demos apply equally to **Elasticsearch (search / analytics)**,
  **Observability**, and **Elastic Security** — pick the primary domain from the artifacts.
  Past examples often emphasized search; **do not** force search framing when the
  discovery points to logs, APM, SIEM, or detection workflows.
- **Cross-solution demos:** When the customer’s needs span domains, it is **acceptable and
  often desirable** to combine capabilities across **search, Observability, and Security**
  in one storyline (e.g. unified data platform, correlated investigation, shared ES|QL).
  Call this out in the script and platform audit so scope stays honest.

**Narrative — solution first:** Unless the SA says otherwise, demo **scripts and plans**
should lead with **business value and the customer’s key asks** from discovery, then
detail **supporting Elastic capabilities** (how to get there). If primary goals are unclear
in the inputs, the agent should **ask for guidance** before finalizing storyline — see
`weave-script`.

**Scenario adaptability (any demo, not one template):** The pipeline is **analytic**, not
prescriptive. Each engagement may emphasize different Elastic surfaces — relevance and
semantic search, log analytics, APM, Synthetics, Security detection and SIEM, Observability
SLOs, ML anomalies, Agent Builder, cross-cluster search, etc. **Nothing** in the stage
list assumes a particular vertical (financial services, retail, public sector, etc.) or a
fixed feature bundle. **thread-audit** and **weave-script** narrow what is
feasible and what the story needs; **weave-model** and **bolt-launch** materialize
only that. Do not retrofit every engagement into a “standard” shape that happened to work
for a prior customer; **read the inputs** and produce artifacts that match **this** demo.

**Additional skills (planning / Kibana / Security):**
- `warp-spark` — consultative SA coaching to choose demo direction, archetype, and wow moments before discovery. Produces `{slug}-ideation.md` (see Stage 0 above).
- `thread-qualify` — consolidates all discovery and diagnostic outputs into a living Opportunity Summary for SDR/AE/SA team alignment. MEDDPIC qualification assessment + technical landscape. Acts as the gate between intelligence gathering and demo planning. Produces `{slug}-opportunity-summary.md` and `{slug}-opportunity-profile.json`. Re-run after any follow-up call. See Stage 2b.
- `weave-agent` — when the demo script includes **Elastic Agent Builder** (custom agent, tools, workflows), produce `{slug}-agent-builder-spec.md` per `skills/weave-agent/SKILL.md`.
- `weave-cost` — two-dimensional: (A) SA tooling for tracking own Claude Code / Cursor spend; (B) demo feature that adds an **AI Cost + Usage dashboard** to any Agent Builder demo. Included by default when Agent Builder is in scope (D-036). Read `skills/weave-cost/SKILL.md`.
- **Elastic Security** — when the story includes detection, alerts, cases, or sample security data, read and follow the relevant `security-*` skills from `elastic/agent-skills` (same install as Search/Obs); **platform-audit** must reflect Sec license/tier and feature availability.

**Reference libraries (hive-mind):**
The `hive-mind` local clone (see currency check, Step 0) provides validated patterns for:
- Kibana dashboards: `hive-mind/patterns/dashboards/DASHBOARD_NDJSON_FORMAT.md`
- Workflows API: `hive-mind/patterns/workflows/WORKFLOWS_API_REFERENCE.md`
- Agent Builder API: `hive-mind/patterns/agent-builder/AGENT_BUILDER_API_MANAGEMENT.md`
- Probe-based feature detection: `hive-mind/patterns/deployment/SERVERLESS_FEATURE_DETECTION.md`
- Data fidelity: `hive-mind/patterns/data/DATA_FIDELITY_GUIDE.md`
- Demo archetypes + coaching: `hive-mind/skills/hive-sa-coaching/`
Always prefer loom's `docs/decisions.md` and `skills/bolt-launch/references/` for
loom-specific decisions; use hive-mind for upstream pattern reference.

**Additional post-deploy skills** available once a cluster is deployed:
- `wind-pulse` — quick pre-demo readiness pulse check (connectivity, doc counts, ML state, ELSER latency)
- `wind-reset` — post-demo cleanup; removes all demo resources prefix-aware

## Entry Points

Two distinct starting points exist for the loom pipeline. Choose based on who is running it:

### AE/SDR Entry Point — 

**Who uses this:** AE or SDR who has discovery notes and wants to structure them and hand
off a brief to the SA. This is the early-funnel pipeline.

Read  and execute it. This skill runs three stages:
discovery parsing, optional diagnostic analysis, and opportunity review. It produces the
full discovery package plus  as the SA handoff brief.

The AE/SDR pipeline ends at . The SA picks up from there.

Trigger phrases: "parse these notes", "qualify this deal", "structure the discovery",
"hand off to SA", "what do we know about [company]".

### SA Entry Point —  (this skill)

**Who uses this:** SA who is building or planning the demo. Can start from AE outputs
( and ) or from scratch.

This is the primary pipeline — proceed through the stages below.

---

## Step 0: Reference Currency Gate (D-041 — before any pipeline work)

Before starting or continuing any pipeline for an engagement, verify that all external
reference repositories are current. The full repo registry and check methods live in
**`skills/bolt-launch/references/reference-repos.md`** — read it for paths, env var
overrides, scope conditions, and blocking rules. Summary below.

### Repos to check

| Repo | Check | Scope | Blocking? |
|------|-------|-------|-----------|
| `elastic/loom` (this repo) | `git fetch origin && git status` | Always | **Yes** |
| `elastic/hive-mind` | `git fetch origin && git status` on `../hive-mind` or `HIVE_MIND_PATH` | Always | Warn only |
| `elastic/agent-skills` | Plugin version vs latest GitHub release | Always | Warn only |
| `elastic/workflows` | `git fetch origin && git status` on `WORKFLOWS_REPO_PATH` | Agent Builder / Workflows in scope | Warn only |
| `elastic/kibana-agent-builder-sdk` | `git fetch origin && git status` on `AGENT_BUILDER_SDK_PATH` | Agent Builder in scope | Warn only |
| `elastic/vulcan` | `git fetch origin && git status` on `VULCAN_PATH` | weave-query in scope | Skip if not installed |
| `terraform-provider-elasticstack` | GitHub Releases API vs `providers.tf` pin | `DEPLOY_MODE=terraform` | Warn only |
| `terraform-provider-ec` | GitHub Releases API vs `providers.tf` pin | `DEPLOY_MODE=terraform` | Warn only |

### Report format

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

### Rules

- **loom stale:** ask the SA before continuing. If they proceed, record the rev.
- **All other repos stale/missing:** note stale state, recommend pull/update, continue unless SA objects.
- **Missing optional repo (vulcan):** log `⏭ not installed — skipping`; never error.
- **Scope-conditional:** only check Terraform providers when `DEPLOY_MODE=terraform`; only check `workflows` / `kibana-agent-builder-sdk` when those features are in demo scope.

**Why:** New pattern adoptions (workflow DELETE, search-by-name, probe-based detection,
dashboard stable UUIDs, inference config changes) are documented in reference repos.
Running against a stale clone means the agent works from outdated guidance. This check
adds ~10 seconds and prevents hours of debugging.

## Step 0b: Ideation (always runs — SA commit gate)

Ideation **always runs** before platform-audit. It is the SA’s explicit commit to demo direction.
No technical build work (script-template, data-modeler, asset-verifier) begins until
`{slug}-ideation.md` is frozen and the post-ideation confirmation refresh is approved (D-050).

**Operating mode selection:**

| Condition | Mode |
|---|---|
| `opportunity/{slug}-demo-goals.md` exists | **Mode 1 — SA Expansion:** pre-seeded from AE/SDR outputs |
| Discovery notes or `{slug}-discovery.json` exist but no goals brief | **Mode 2 — Customer context** |
| No prior context | **Mode 3 — From scratch** |

- Read: `skills/warp-spark/SKILL.md`
- Outputs: `demo/{slug}-ideation.md` (frozen) + updated `opportunity/{slug}-confirmation.md`
- **Gate:** SA must approve the updated confirmation before pipeline continues to Step 3

**Skip condition:** Only skip if `demo/{slug}-ideation.md` already exists in `{engagement_dir}`
**and** the SA explicitly confirms the existing contract is still current. Do not skip silently.

## Step 1: Identify the Engagement and Set the Engagement Directory

**Determine `{engagement_dir}` first, then derive the slug from it.**

**Path-first resolution (preferred):** If the user provides a path to discovery
documents or files that are already inside a folder under `LOOM_ENGAGEMENTS_ROOT`
(e.g., `~/engagements/2026acmecorp/discovery/notes.md`), the **parent of that
discovery folder is `{engagement_dir}`**:

```
user provides: ~/engagements/2026acmecorp/discovery/
                               ^^^^^^^^^^^
engagement_dir = ~/engagements/2026acmecorp/   ← use exactly as-is
slug           = 2026acmecorp                  ← taken from folder name, not re-normalized
```

Use the **folder name exactly as it exists on disk** for the slug in this case.
Do not normalize or lowercase it when an existing folder was provided.

**Name-first resolution (fallback):** If no path is provided and you only have a
customer name, derive slug and engagement_dir from the user's prompt:

```
slug           = lowercase-hyphenated form of customer name
                 "Citizens Bank" → citizens-bank
                 "Deutsche Telekom SOC-T" → dt-soct
engagement_dir = "${LOOM_ENGAGEMENTS_ROOT:-$HOME/engagements}/{slug}/"
```

> **Important:** `{engagement_dir}` is always a folder under `~/engagements/` (or the
> configured root). **Never** name it `workspace`, `workspace-{slug}`, or any path
> relative to the loom repo root. The repo holds skills only; all customer
> artifacts live outside it under `{engagement_dir}`.

Create the directory and its four audience-scoped subfolders if they don’t exist:

```bash
mkdir -p "{engagement_dir}/opportunity"   # AE / SDR / SA — sales alignment, customer-facing docs
mkdir -p "{engagement_dir}/demo"          # SA — discovery intel, platform audit, scripts
mkdir -p "{engagement_dir}/data"          # SA / engineer — data model, ML config, Vulcan, seed data
mkdir -p "{engagement_dir}/deploy"        # SA — bootstrap, teardown, Kibana objects, readiness
```

Only per-demo artifacts belong in `{engagement_dir}/`; pipeline code stays in the
loom clone (`skills/`, `docs/`).

**Folder → audience mapping:**
| Folder | Primary audience | What lives here |
|--------|----------------|----------------|
| `opportunity/` | AE, SDR, SA | Opportunity summary, qualification profile, customer confirmation, gaps, demo brief |
| `demo/` | SA | Ideation contract, discovery JSON, diagnostic outputs, platform audit, demo script, agent spec |
| `data/` | SA, engineer | Data model, ML config, Vulcan outputs, `mappings/`, `pipelines/`, `seed/` |
| `deploy/` | SA | `bootstrap.py`, `teardown.py`, provision log, deploy log, checklist, risks, Kibana objects |

`.env` and `.env.example` remain at the **engagement root** (not inside any subfolder) — they
are sourced directly by scripts and shell workflows using the root path convention.

All output files for this engagement live under the appropriate subfolder. Each skill writes
to the correct folder; the slug prefix is still used on each file so files remain identifiable
when shared individually (e.g. `opportunity/{slug}-confirmation.md` sent to the customer).

## Step 2: Take Inventory

**Token-efficient inventory — read pipeline-state first.**

Check for `{engagement_dir}/{slug}-pipeline-state.json`. If it exists, read it instead of
scanning all output files individually — it is the authoritative record of what has run and
what inputs each stage last saw. If it does not exist yet, fall back to the file scan below
and write the state file once inventory is complete.

Pipeline-state schema (write and update this after every stage completes):

```json
{
  "slug": "{slug}",
  "engagement_dir": "{engagement_dir}",
  "last_updated": "ISO-8601 timestamp",
  "stages": {
    "ideation":            { "status": "complete|skipped|pending", "output": "demo/{slug}-ideation.md",           "input_hash": "…" },
    "discovery-parser":    { "status": "complete|skipped|pending", "output": "demo/{slug}-discovery.json",        "input_hash": "…" },
    "diagnostic-analyzer": { "status": "complete|skipped|pending", "output": "demo/{slug}-current-state.json",    "input_hash": "…" },
    "opportunity-review":  { "status": "complete|skipped|pending", "output": "opportunity/{slug}-opportunity-summary.md","input_hash": "…" },
    "platform-audit":      { "status": "complete|skipped|pending", "output": "demo/{slug}-platform-audit.json",   "input_hash": "…" },
    "script-template":     { "status": "complete|skipped|pending", "output": "demo/{slug}-demo-script.md",        "input_hash": "…" },
    "agent-design":        { "status": "complete|skipped|pending", "output": "demo/{slug}-agent-builder-spec.md", "input_hash": "…" },
    "vulcan-generate":     { "status": "complete|skipped|pending", "output": "data/{slug}-vulcan-queries.json",        "input_hash": "…" },
    "data-modeler":        { "status": "complete|skipped|pending", "output": "data/{slug}-data-model.json",             "input_hash": "…" },
    "fleet-integrations":  { "status": "complete|skipped|pending", "output": "deploy/{slug}-integrations-manifest.json","input_hash": "…" },
    "ml-designer":         { "status": "complete|skipped|pending", "output": "data/{slug}-ml-config.json",              "input_hash": "…" },
    "validator":           { "status": "complete|skipped|pending", "output": "deploy/{slug}-demo-checklist.md",     "input_hash": "…" },
    "cloud-provision":     { "status": "complete|skipped|pending", "output": ".env",                         "input_hash": "…" },
    "deploy":              { "status": "complete|skipped|pending", "output": "deploy/bootstrap.py",                 "input_hash": "…" }
  }
}
```

`input_hash` is a short fingerprint (first 8 chars of the last-modified timestamp of the
primary input file, or `"none"` if no input). Use it to detect when re-runs are needed —
if the hash on disk differs from the hash recorded here, mark the stage pending.

If `{slug}-pipeline-state.json` is missing (first run), scan for individual output files to
populate it, then write it.

**File scan fallback** (only when no state file exists):

```
Stage                    | Output file                     | Re-run if...
-------------------------|----------------------------------|---------------------------
warp-spark            | demo/{slug}-ideation.md                    | No discovery notes; SA needs direction
warp-listen    | demo/{slug}-discovery.json                 | New/changed discovery notes
warp-scan | demo/{slug}-current-state.json             | New/changed diagnostic file
thread-qualify  | opportunity/{slug}-opportunity-summary.md  | discovery or diagnostic changed; follow-up notes added
thread-audit      | demo/{slug}-platform-audit.json            | opportunity-profile or current-state changed
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
`{slug}-data-model.json`, `{slug}-demo-checklist.md`, or `bootstrap.py`).

Report the inventory to the user before executing:
```
📋 Engagement: [Company] ([slug])
📁 Engagement dir: {engagement_dir}

Stage                    Status
─────────────────────────────────────────
Currency check           ✅ Up to date (loom rev abc1234, hive-mind rev def5678)
Ideation                 ⏭  Skipped  (discovery notes provided)
Discovery parser         ✅ Complete  ({slug}-discovery.json)
Diagnostic analyzer      ⏭  Skipped  (no diagnostic provided)
Opportunity review       🔲 Pending
Platform audit           🔲 Pending  (runs after opportunity review)
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

For each stage that needs to run, in order:

1. **Announce the stage:** `🔄 Running: warp-listen...`
2. **Read the sub-skill SKILL.md** from the sibling directory:
   `../warp-listen/SKILL.md` (relative to this file's location)
   This loads the specialist's instructions. Follow them exactly.
   If the relative path does not resolve in the current agent runtime, read
   `{loom_repo}/skills/<skill>/SKILL.md` from the repo root instead.
3. **Execute the stage** using the loaded instructions and available inputs.
4. **Write outputs** to `{engagement_dir}` with the slug prefix.
5. **Update `{slug}-pipeline-state.json`** — mark the stage `complete`, record the output filename and input hash. This keeps the next session's inventory instant.
6. **Announce completion:** `✅ warp-listen complete → {slug}-discovery.json`
6. **Surface any blockers:** If a stage produces a RED platform audit or critical gaps, pause
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

**Stage 0 — warp-spark** *(optional — run when no discovery notes or diagnostic exist)*
- Skip if: `{slug}-discovery.json` OR `{slug}-ideation.md` exists, OR discovery notes provided
- Read: `../warp-spark/SKILL.md`
- Inputs: SA description, customer vertical, or "I have a meeting with X" context
- Outputs: `{slug}-ideation.md` (frozen contract: archetype, wow moments, capability map, data strategy)

**Stage 1 — warp-listen**
- Skip if: `demo/{slug}-discovery.json` exists AND no new discovery notes provided
- Read: `../warp-listen/SKILL.md`
- Inputs: discovery notes (PDF/text/markdown); optionally `{slug}-ideation.md` for narrative validation
- Outputs: `{slug}-discovery.json`, `{slug}-confirmation.md`, `{slug}-gaps.md`

**Stage 2 — warp-scan** *(optional)*
- Skip if: no diagnostic file provided OR `demo/{slug}-current-state.json` already exists
- Read: `../warp-scan/SKILL.md`
- Inputs: diagnostic ZIP or API exports
- Outputs: `{slug}-current-state.json`, `{slug}-architecture.md`, `{slug}-findings.md`

**Stage 2b — thread-qualify**
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
- Inputs: `{slug}-discovery.json` (required), `{slug}-gaps.md`, `{slug}-current-state.json`,
  `{slug}-findings.md`, `{slug}-architecture.md` (all optional but used when present),
  plus any raw follow-up notes or supplemental files provided in the current session
- Outputs: `{slug}-opportunity-summary.md`, `{slug}-opportunity-profile.json`
- **Team alignment gate:** After writing outputs, surface the qualification recommendation
  and prompt the SA to share `{slug}-opportunity-summary.md` with the SDR and AE for review
  before continuing. Do not proceed to platform audit until the SA confirms alignment
  (or explicitly says "proceed anyway").
- **Qualification gate:** If `qualification_status` is `not_qualified`, **stop the pipeline**
  and report clearly. Do not run platform audit or demo build for unqualified opportunities.
  If `continue_discovery`, surface the open questions and ask the SA whether to continue
  building or wait for answers.

**Stage 3 — thread-audit**
- Skip if: `demo/{slug}-platform-audit.json` exists AND neither discovery, current-state, nor
  opportunity-profile have changed
- Read: `../thread-audit/SKILL.md`
- Inputs: `{slug}-discovery.json`, `{slug}-current-state.json` (if available),
  `{slug}-opportunity-profile.json` (use `demo_scope_signals` to pre-scope the audit)
- Outputs: `{slug}-platform-audit.json`, `{slug}-platform-audit.md`
- **Blocker check:** If overall_status is RED, surface the blocking features before
  proceeding. Auto-adjust scope: remove blocked features from the script brief, continue.

**Stage 3b — thread-suggest** *(required — D-049)*
- **Decision gate: predefined vs. custom build.** Every engagement must make this decision
  explicitly before scripting begins.
- Read: `../thread-suggest/SKILL.md`
- Inputs: `demo/{slug}-ideation.md` (required), `opportunity/{slug}-opportunity-profile.json`,
  `demo/{slug}-platform-audit.json`, `skills/thread-suggest/references/standard-demos.md`
- **PREDEFINED path:** Produces `opportunity/{slug}-predefined-recommendation.md` and
  updates `opportunity/{slug}-confirmation.md`. **Pipeline ends here.** Do not run Stage 4+.
- **CUSTOM path:** Sets `custom_required: true`, proceeds to Stage 4.
- Skip if: `{slug}-ideation.md` is missing — halt and run Stage 0b first.

**Stage 4 — weave-script** *(custom path only — skip if predefined was recommended)*
- Skip if: `demo/{slug}-demo-script.md` exists AND platform-audit hasn't changed AND ideation hasn't changed
- Read: `../weave-script/SKILL.md`
- **Before authoring:** read `skills/weave-script/references/demo2win-conventions.md` (D-051)
- Inputs: `{slug}-discovery.json`, `{slug}-platform-audit.json`, `{slug}-ideation.md` (required — takes priority for wow moments and archetype)
- Outputs: `{slug}-demo-script.md`, `{slug}-demo-brief.md`, `{slug}-live-script.md`
- Script must include: opening punch, 3–5 self-contained vignettes, value confirmation close

**Stage 4b — weave-agent** *(conditional — Agent Builder only)*
- Skip if: `demo/{slug}-demo-script.md` does not include Agent Builder / custom agents / tools /
  workflows, OR `demo/{slug}-agent-builder-spec.md` exists AND the script and audit have not changed
- Read: `../weave-agent/SKILL.md`
- Inputs: `{slug}-demo-script.md`, `{slug}-discovery.json`, `{slug}-platform-audit.json`
- Outputs: `{slug}-agent-builder-spec.md`
- If the platform audit marks Agent Builder blocked, do not write a runnable full spec; surface
  the blocker and fallback.

**Stage 4c — weave-cost** *(conditional — AI / Agent Builder only)*
- Skip if: no Agent Builder or AI-powered component is in scope, OR `INCLUDE_TOKEN_VISIBILITY=false`
- Read: `../weave-cost/SKILL.md`
- Inputs: `{slug}-demo-script.md`, `{slug}-data-model.json` if it exists, `.env` if available
- Outputs: guidance and schema content that downstream stages must materialize in
  `{slug}-data-model.json`, `{slug}-demo-checklist.md`, dashboards, and `bootstrap.py`
- Include by default for Agent Builder demos per D-036.

**Stage 4.5 — weave-query** *(conditional — ES|QL / RAG / integration-grounded data)*
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

**Stage 5 — weave-model**
- Skip if: `data/{slug}-data-model.json` exists AND script hasn't changed AND Vulcan outputs unchanged
- Read: `../weave-model/SKILL.md` and `../weave-model/references/mapping-patterns.md`
- Inputs: `{slug}-demo-script.md`, `{slug}-discovery.json`, `{slug}-agent-builder-spec.md`
  (if present), `{slug}-vulcan-queries.json` (if present — fast path for ES|QL + seed data),
  and weave-cost guidance if Agent Builder / AI is in scope
- Outputs: `{slug}-data-model.json`, `{slug}-data-model.md`, individual mapping files

**Stage 5.5 — weave-fleet** *(required when logs/metrics streams exist)*
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

**Stage 6 — weave-train** *(conditional)*
- Skip if: no ML scenes detected in `demo/{slug}-demo-script.md`, OR `data/{slug}-ml-config.json`
  exists AND data model hasn't changed
- Detect ML scenes: look for terms like "ML anomaly", "anomaly detection", "swimlane",
  "anomaly_score" in the script
- Read: `../weave-train/SKILL.md`
- Inputs: `{slug}-demo-script.md`, `{slug}-data-model.json`
- Outputs: `{slug}-ml-config.json`, `{slug}-ml-setup.md`

**Stage 7 — finish-check**
- Always run last before deploy — regenerate even if it exists
- Read: `../finish-check/SKILL.md`
- Inputs: all available `{slug}-*.json` and `{slug}-*.md` files in `{engagement_dir}`
- Outputs: `{slug}-demo-checklist.md`, `{slug}-risks.md`

**Stage 8 — bolt-spin** *(optional — new cluster path only)*
- **Requires explicit SA approval** to spend resources / create infrastructure (unless
  the user already clearly requested provisioning this session)
- Skip if: `{engagement_dir}/.env` already exists at the engagement root and credentials are valid
- Run if: user requests "create a new cluster", "spin up a serverless project", or no `.env`
  exists and deployment was requested
- Read: `../bolt-spin/SKILL.md`
- Inputs: deployment type preference, region, engagement slug
- Outputs: `{engagement_dir}/.env`, `{engagement_dir}/.env.example`, `{slug}-provision-log.md`
- Note: if user wants to reuse an existing cluster for a new engagement, copy the `.env`
  from the prior engagement's workspace and update `DEMO_SLUG`, `ENGAGEMENT`, and `INDEX_PREFIX` —
  no re-provisioning needed

**Stage 8b — finish-verify** *(required before deployment — D-045)*
- **Mandatory gate between planning and deployment.** No Terraform or Python deployment
  artifacts are generated until this stage writes `deploy/asset-bundle/asset-schema.json`.
- Skip if: `deploy/asset-bundle/asset-schema.json` exists AND data model, script, and platform audit are all unchanged since last run
- Run if: `.env` exists AND Stage 7 returned go or conditional-go AND asset bundle is absent or stale
- Read: `../finish-verify/SKILL.md`
- Inputs: `{engagement_dir}/.env`, `data/{slug}-data-model.json`, `demo/{slug}-demo-script.md`, `demo/{slug}-platform-audit.json`
- Outputs: `deploy/asset-bundle/asset-schema.json`, `deploy/asset-bundle/asset-index.json`, and all authored asset files per skill dispatch table in finish-verify
- **Blockers (halt Stage 9):** Failed ES|QL validation, null viz-queried fields, version gate fail, disabled required feature. SA must resolve before continuing.

**Stage 9 — bolt-bootstrap** *(optional — runs after asset verifier)*
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
 DEMOBUILDER COMPLETE — [Company]
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
  ✅  demo/{slug}-ideation.md          — frozen demo direction contract (if run)
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
  ✅  deploy/bootstrap.py              — generated deployment (15 steps; step 13 = scoped Kibana/platform APIs)
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
  1. Run bolt-spin or copy an existing .env
  2. Run bolt-launch → python3 bootstrap.py --dry-run first
  3. Run end-to-end checks from {slug}-demo-checklist.md (scenes vary by demo)

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
Run stages 1, 2b, 3, 4, 4b/4c if in scope, 5, 6 (if ML), 7. Skip stage 2. Platform audit runs in partial mode after opportunity review.

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
Run stage 8 (bolt-spin) to provision and write `.env`, then stage 9 (bolt-launch)
to generate and execute `bootstrap.py`. Stages 1–7 already complete — skip them.

**User wants to deploy to an existing cluster:**
"I already have a cluster — here are my credentials." Or they copy a `.env` from another
engagement. Skip stage 8. Run stage 9 only. Verify the `.env` has all required fields before
generating `bootstrap.py`.

**User running a second engagement on the same cluster:**
"Reuse this cluster for another customer." Copy `.env`, update `DEMO_SLUG`, `ENGAGEMENT`,
and `INDEX_PREFIX` (e.g. `cb-` → `acme-`). Run stage 9 with the new slug’s artifacts.
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
set, provisions the cluster, generates and executes `bootstrap.py`. Delivers a deploy log
confirming 4 indices created, seed data loaded, ELSER endpoint warmed.

**Multi-customer on shared cluster:** First engagement deployed with `INDEX_PREFIX=cb-`.
User adds a second engagement with `INDEX_PREFIX=acme-`. Orchestrator copies `.env`,
updates slug fields, skips provisioning, runs stage 9 for the new artifacts. Both demos
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
