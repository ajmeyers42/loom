# loom — Open Items Requiring User Action

*Generated from the post-mortem and current skill review. Updated as items are resolved.*
*Last updated: 2026-10-30 — baseline commit. Deploy path is finish-verify, then bolt-bootstrap.*

For **agent behavior** (orchestrator path, `$LOOM_ENGAGEMENTS_ROOT` outputs, deploy approvals), see
[`AGENTS.md`](../AGENTS.md), [`docs/engagements-path.md`](../docs/engagements-path.md), and [`docs/runtimes/`](../docs/runtimes/).

---

## 🔴 Before the first provision

### 1. Run `cloud-setup` once to configure EC_API_KEY
Before `bolt-spin` can create any serverless project, the `cloud-setup` skill needs to run to configure and validate your Elastic Cloud API key. This is a one-time setup.

**How:** In a Claude session with the elastic/agent-skills installed, say: "set up my Elastic Cloud credentials" and follow the prompts. **Never paste the API key directly into chat** — the skill handles secure entry.

---

## 🟡 Required Before First Live Demo Deploy

### 3. Validate the deploy pair against a real cluster
`finish-verify` writes `deploy/asset-bundle/`. `bolt-bootstrap` writes `deploy/main.tf` and `deploy/bootstrap-data.py`. That pair has not yet been executed against a real cluster. Edge cases (network timeouts, ELSER model load time, Terraform provider pins, Kibana ndjson import formatting) may surface only on a live run.

**Action:** Pick one engagement. Root defaults to **`~/engagements`** (see [`docs/engagements-path.md`](../docs/engagements-path.md)):
```bash
cd /path/to/loom
ROOT="${LOOM_ENGAGEMENTS_ROOT:-$HOME/engagements}"
SLUG="{slug}"
set -a && source "$ROOT/$SLUG/.env" && set +a
python3 "$ROOT/$SLUG/deploy/bootstrap-data.py" --dry-run
terraform -chdir="$ROOT/$SLUG/deploy" plan
# Review output, then apply only after the D-024 review gate.
```
Note any failures and report back — the templates in `bolt-bootstrap`, `bolt-ech`, and `bolt-serverless` may need adjustments.

### 4. Kibana saved objects — files in the engagement workspace
Terraform saved-object import reads paths such as `deploy/kibana-objects/{slug}-*.ndjson` and optional
`deploy/kibana/workflows/*`, `deploy/kibana/agent/*.json` (see `docs/decisions.md` **D-024**). Those files
are **authored** using **`elastic/agent-skills`** (e.g. `kibana-dashboards`) and **export-first**
from Kibana when needed (**D-017**), then **saved under `{engagement_dir}/deploy/`**.

**Action:** Keep dashboards/agent exports under `deploy/`. `bolt-bootstrap` imports them from Terraform, not by hand in the UI.

**Review gate:** Do **not** `terraform apply` or run `deploy/bootstrap-data.py` against a cluster until the SA has reviewed
`deploy/main.tf`, `deploy/bootstrap-data.py`, `demo/{slug}-platform-audit`, `deploy/{slug}-risks`, and `deploy/{slug}-demo-checklist.md` (**D-024**, `AGENTS.md`).

### 5. Configure an email connector for Workflows demos
Any demo whose Workflow sends email needs a Kibana email connector. The `kibana-connectors` skill creates it. SMTP or an equivalent provider still has to be supplied per engagement.

**Action:** Configure the connector in the demo cluster before `terraform apply` when a Workflow scene sends mail.

---

## 🟢 SDR / AE Discovery Tool

### warp-discovery + Gemini Gem — shipped

The `warp-discovery` skill and Gemini Gem deployment are complete and merged to main.
SDRs and AEs can use the Gem at [gemini.google.com](https://gemini.google.com) — no Cursor,
CLI, or `.env` setup required.

**What shipped:**
- `skills/warp-discovery/` — distilled bundle of `warp-listen` + `thread-qualify` logic
- `deployments/gem/` — Gemini Gem system prompt, config, and setup guide
- `docs/runtimes/gem.md` — setup and usage documentation for SDRs/AEs
- Canonical SA pipeline skills (`warp-listen`, `thread-qualify`, `warp-scout`) updated to
  match the same two-score format and document posture guardrails

**Ongoing — Gem maintenance:**
When `warp-listen` or `thread-qualify` are updated, re-sync `skills/warp-discovery/SKILL.md`
and `deployments/gem/system-prompt.md`. Check sync dates in `skills/warp-discovery/components.md`.
Update the live Gem by replacing the Instructions field with the updated `system-prompt.md`.

### Slack bot — deferred (pending IT approval)

A Slack bot deployment of `warp-discovery` is designed but not implemented.
See `deployments/slack/README.md` for the planned architecture.

**Action:** Submit Slack app approval request to Elastic IT. If approved, implement per the
spec in `deployments/slack/README.md` on a new `feature/sdr-slack` branch.

---

## 🔵 Backlog — Skills to Build Next

### 6. `demo-kibana-builder` *(optional accelerator)*
Generates baseline Kibana saved objects (dashboards, Lens, ES|QL panels) from `data/{slug}-data-model.json`
+ `demo/{slug}-demo-script.md`. **Not required** if the SA commits exports under `deploy/kibana-objects/`
as in **D-024**; this skill would automate first-time **generation** only.

**Priority:** Medium — improves repeatability; file-based imports remain the contract.
**Inputs:** `data/{slug}-data-model.json`, `demo/{slug}-demo-script.md`
**Outputs:** `deploy/kibana-objects/{slug}-dashboards.ndjson`, etc.
**Depends on:** `kibana-dashboards` skill from elastic/agent-skills

### 7. `demo-data-generator`
Generates seed data as reviewable flat JSON files from the data model's sample data spec, before `deploy/bootstrap-data.py` runs. Makes seed data version-controllable and re-loadable independently.

**Priority:** Medium — seed documents are still produced inside the data model and loaded by `bootstrap-data.py`. They are not a separate reviewable file yet.
**Inputs:** `data/{slug}-data-model.json`
**Outputs:** `data/{slug}-{index-name}-seed.json` (one file per index)

### 8. `demo-refresh`
Re-injects anomaly data T-2h before a demo. Separate from the initial `bootstrap-data.py` run because timing, verification, and failure modes differ. SEs will run this the morning of every ML demo.

**Priority:** Medium — until built, re-run `python3 deploy/bootstrap-data.py` (it includes anomaly injection) the morning of the demo.
**Inputs:** `{engagement_dir}/.env`, `data/{slug}-ml-config.json`
**Outputs:** confirmation that injection docs are indexed and ML score ≥ 75 on target

### 9. `weave-fleet`
Installs and configures Elastic Fleet integration packages (EPM) for demo environments. Provides managed assets — ingest pipelines, index templates, ILM policies, dashboards — from the Integrations catalog rather than hand-rolled equivalents. Supports both agent-based collection and synthetic bulk ingest into integration-managed indices.

**Status: Spec complete and implemented** — see `skills/weave-fleet/SKILL.md`.
Wired into the pipeline as Stage 5.5 (after data-modeler, before ml-designer).
Includes asset catalog review with shared `use_as_is` / `clone_and_modify` / `storyline_enhancement` taxonomy.

**Remaining:** Validate against a live cluster (part of item #3 first-deploy gate).

### 10. `weave-pipe`
Designs and generates Elasticsearch ingest pipeline definitions from a field mapping specification. Outputs would be consumed by `wind-streams` or by `finish-verify` as Terraform resources. Not a `bootstrap-data.py` step.

**Priority:** Medium — originated from 2026lenovoGAIaaS engagement.
**Status:** Backlog. `skills/weave-pipe/SKILL.md` halts if selected. Do not treat it as a deploy step. Pipelines that are in scope are infrastructure for `finish-verify` / `bolt-bootstrap`.
**Inputs:** `data/{slug}-data-model.json`, field samples or log examples
**Outputs:** `data/pipelines/{slug}-{name}-pipeline.json`

### 11. `wind-streams`
Creates, configures, and wires Kibana Streams with ingest pipelines for demo environments. Extends the read-only `kibana-streams` skill with write-side operations (create stream, set routing, attach pipeline, configure retention).

**Priority:** Medium — originated from 2026lenovoGAIaaS engagement. Required when the demo story is Streams-native ingest.
**Status:** Backlog. `skills/wind-streams/SKILL.md` halts if selected. Inspect existing streams with `kibana-streams`.
**Depends on:** `weave-pipe` (pipelines must exist before wiring)

### 12. `thread-audit` — Asset Discovery pass

Add a cluster-resident asset discovery pass to `thread-audit` (Stage 3) that catalogs
existing Agent Builder agents (including RCA), deployed ML jobs, pre-built dashboards,
detection rules, SLOs, and workflows already on the cluster. Classifies each using the
shared asset taxonomy (`use_as_is` / `clone_and_modify` / `storyline_enhancement`) defined
in `skills/weave-fleet/SKILL.md`.

**Why:** `weave-fleet` (Stage 5.5) handles package-install-time assets after the
script is written. The platform audit handles cluster-resident assets *before* the script —
so the SA can script around what already exists rather than building from scratch.

**Priority:** Medium — high value for engagements where the customer's cluster has existing
Agent Builder agents (e.g. Elastic's own RCA agent) or pre-deployed integrations that could
be cloned into the demo.
**Status:** Design complete — see generalization note in `skills/weave-fleet/SKILL.md`.
**Inputs:** `demo/{slug}-current-state.json`, optional live cluster queries (`GET /api/saved_objects/_find`, etc.)
**Outputs:** `demo/{slug}-platform-assets.md` (shared entry format — same taxonomy as fleet-integrations)
**Feeds into:** `weave-script` as optional context before script is finalized

---

## ⚪ Process / Infrastructure

### 13. Add `read:org` scope to GitHub token
The current keychain token has `repo` scope but not `read:org`, which blocks `gh auth login` and the gh CLI. Not blocking for loom usage, but limits automation.

**Action:** Regenerate the GitHub PAT at `github.com/settings/tokens` and include `read:org`.

### 14. Run evals for bolt-spin, finish-verify, and bolt-bootstrap
`bolt-spin` and the retired `bolt-launch` have `evals/evals.json`. `finish-verify` and `bolt-bootstrap` are the live deploy pair. The eval loop (run → grade → benchmark) has not been executed. These evals need a real cluster to mean anything.

**Action:** After the first live deploy (item 3), run evals for `bolt-spin`, `finish-verify`, and `bolt-bootstrap`. Do not spend an eval cycle on `bolt-launch`.

### 15. Validate `.ml-anomalies-*` field names on first Serverless ML build

On first use of ML anomaly detection on Serverless, run this before writing any query or dashboard:
```
GET .ml-anomalies-*/_mapping
```
The Serverless field names differ from documentation: use `record_score`, `timestamp`, `partition_field_value`, `by_field_value`. See `skills/references/serverless-differences.md`.

---

## ✅ Resolved

- **2026-10-30 baseline** — Local dependency clones fast-forwarded. Deploy instructions, handoffs, and indexes name `finish-verify` then `bolt-bootstrap` (`main.tf` + `bootstrap-data.py`). `bolt-launch` is a redirect only. Duplicate `skills/bolt-launch/references/` removed. `wind_pulse.py` reads `deploy/kibana-objects/`. `weave-query` targets Vulcan 2.1 (`OPENROUTER_*`). `validate_ext_deps.py` finds the agent-skills plugin. `elastic-demo-starter` is an optional registry entry. D-035 is superseded by D-050.
- **elastic/agent-skills installed (checked 2026-10-26)** — Cursor plugin cache, `~/.claude/skills`, and `~/Documents/GitHub/agent-skills` (`baa5111`). Re-run `npx skills update elastic/agent-skills` when the Cursor plugin should move past that cache.
- **wind-pulse D-037 paths (2026-10-26)** — `wind_pulse.py` searches `deploy/kibana-objects/` and `deploy/kibana/` first, and still falls back to the pre-D-037 root paths.

- **Workspace root convention** — Engagement workspaces live under **`~/engagements/{slug}/`** by default (or **`$LOOM_ENGAGEMENTS_ROOT/{slug}/`** if set) outside the repo. See `docs/decisions.md` D-019, D-023 and [`docs/engagements-path.md`](../docs/engagements-path.md).
- **Engagement folder reorganization (D-037)** — All pipeline outputs are now organized into audience-scoped subfolders: `opportunity/` (AE/SDR), `demo/` (SA design), `data/` (data model / ML / seed), `deploy/` (bootstrap, teardown, Kibana objects). `.env` remains at the engagement root. All skill SKILL.md files, `scripts/inventory.py`, `docs/pipeline.md`, and `docs/decisions.md` updated accordingly. Merged to main via PR #5.
- **Cloud-synced engagement root** — Google Drive (and OneDrive) documented as a valid `LOOM_ENGAGEMENTS_ROOT` with pathing, sync latency, and credential security guidance. See `docs/engagements-path.md`.
- **Pipeline efficiency layer** — Pipeline state file, context pruning strategy, model routing guidance, subagent parallelization map, and `scripts/inventory.py` zero-AI CLI added. See `docs/efficiency.md`.
- **Reference repos for Workflow and Agent Builder builds** — `elastic/workflows` and `elastic/kibana-agent-builder-sdk` cloned at `~/Documents/GitHub/workflows` and `~/Documents/GitHub/kibana-agent-builder-sdk`. Local paths embedded in `weave-agent/SKILL.md` and `skills/references/serverless-differences.md`. Agent surfaces a blocker if context is missing before any Workflow/Agent Builder build.
