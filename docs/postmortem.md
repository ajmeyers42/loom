# Session Post-Mortem: loom Pipeline Build

**Date:** 2026-04-15
**Scope:** Two-context-window session building 9 skills from scratch (warp-listen through bolt-launch) plus the loom orchestrator. Real-data validated against a Deutsche Telekom 152-node production cluster.

---

## What the session was

Nine skills built across two context windows, running from raw discovery notes all the way through cluster deployment. Real-data validation against a 152-node Deutsche Telekom cluster. One live audience change (Citizens Bank DM added mid-build) that tested the pipeline's ability to re-scope without rebuilding from scratch. Deploy skills added late when the scoping question arose organically.

---

## What worked well

**The pipeline architecture held.** The data flow — each skill consuming the prior stage's JSON output — proved sound. The Citizens Bank re-scope (champion → DM-present) needed only two stages to re-run (`weave-script` + `finish-check`). The data model didn't change, the discovery didn't change. That's the right behavior, and the orchestrator's skip logic correctly captures it.

**Real validation caught a real bug.** The DT SOC-T diagnostic test was the most valuable thing done this session. The shard density metric was initially one-dimensional (shards/GB of data), which rated DT as healthy at 0.027 shards/GB. But 211 shards across 7 nodes is actually a signal worth surfacing when normalized against heap. The bug would never have appeared on synthetic evals — it required a real cluster with real topology.

> **Lesson: synthetic evals should be a floor, not a ceiling. Real-data validation should happen on at least one skill before shipping.**

**The "keep rolling forward" instruction worked.** Across 7 back-to-back skills, confirmation was only needed three times total. Each skill was self-contained enough to execute without a confirmation loop.

**The `p(name)` prefix pattern is clean.** The INDEX_PREFIX design — a single helper applied everywhere — is the right abstraction. It made both the deploy skill and the env-reference documentation easy to write without case-by-case exceptions.

---

## Where friction happened

### 1. Scope wasn't defined upfront

The deploy skills came in as a late question mid-pipeline. The orchestrator was written to 7 stages, then extended to 9 after the architecture was committed. The resulting edit was clean, but the orchestrator's stage inventory table (Step 2) was written statically and had to be updated separately.

**Fix:** The orchestrator should describe its stage table as extensible, not enumerate every stage by number in static prose. New stages should just be addable to the Step 4 list without touching Step 2 formatting.

### 2. Context window exhausted before work was committed

The session ran long because each skill build included its own eval loop (run prompts → draft assertions → grade → review viewer → iterate). The last ~30 minutes of the session (deploy skills + orchestrator edits + README + commit) happened in a resumed context from a cold summary — extra cognitive load, re-reading files to verify state.

**Root cause:** A session building 7+ skills with full eval cycles will reliably hit context limits.

**Fix options:**
- One session = one skill, draft to committed
- Write a `{skill}-session-notes.md` checkpoint after each skill is committed, so a resumed session can orient without a full summary read

### 3. The `gh auth login` failure

The GitHub CLI had a `repo` scope token but not `read:org`. The workaround (curl with the raw REST API) worked, but the wrong tool was tried first.

**Fix:** Before touching GitHub in any session, check scope with `gh auth status`. Note that elastic/agent-skills and the Elastic Cloud APIs may have similar auth requirements — document what token scopes are needed upfront.

### 4. Assertion calibration problem

One eval assertion — "No Bain/AWS Bedrock mention" — failed because the skill correctly named competitors in its internal "do not mention" block for SE awareness. The assertion searched the whole document rather than just the customer-facing talking points.

**General rule:** Negative assertions must specify scope — "not mentioned in the talking points" rather than "not mentioned anywhere." Internal context sections may legitimately name the things you don't want externally surfaced.

**Fix:** Add an optional `scope` field to assertion schema: `"talking_points"`, `"customer_facing"`, `"full_document"`.

### 5. The Write tool requiring a prior Read

Hit twice — once writing a file that existed but hadn't been read in the session, once writing to a path where a script had auto-created an empty file. The workaround (`cat > file << 'EOF'` via bash) worked, but it's a switching cost.

**Internalized pattern:** Before writing any file that might already exist, issue a Read first. Even `Read` with limit=1 satisfies the constraint.

---

## Decisions that look good in retrospect

**Per-engagement `.env` isolation.** Credentials per-workspace, with `INDEX_PREFIX` as the shared-cluster namespace separator. The copy workflow (`cp citizens-bank/.env ihg-club/.env` + edit 3 fields) is simple and correct.

**Idempotent bootstrap design.** Check-before-create for every resource, `--step N` resume, doc count threshold before data reload — a failed deploy at step 9 doesn't require tearing down steps 1–8. Critical for live demo environments.

**Separating provision from deploy.** Provision once, deploy many times (with different INDEX_PREFIX for a second customer). Skill boundary maps cleanly to user intent.

**The `demo_critical_docs` concept.** Naming specific documents in the data model that must exist, must be individually verified, and must produce the right demo behavior — rather than relying on bulk doc count statistics.

---

## Skill gaps identified

### `demo-kibana-builder`
The pipeline stops at `bootstrap.py`. Kibana objects (dashboards, visualizations, index patterns, saved searches) are imported from an `.ndjson` file that must come from somewhere. A `demo-kibana-builder` skill would generate baseline dashboards from the data model JSON — Lens visualizations for key fields, ES|QL panels, index patterns. Currently the missing step between "cluster bootstrapped" and "demo visually ready."

### `demo-data-generator`
Seed data generation is buried inside `bootstrap.py`. A standalone `demo-data-generator` skill would produce flat JSON seed files from the data model's sample data spec before bootstrap runs — reviewable, version-controllable, re-loadable independently.

### `demo-refresh`
Anomaly injection timing (T-2h) and the things that can go wrong with it (ML job not trained, bucket span error, injection doesn't score) are different enough from initial deployment to warrant a dedicated skill. SEs run this the morning of every demo, not just on initial deploy.

### `wind-pulse` *(added this session)*
A quick pre-demo pulse check: connectivity, index doc counts, demo_critical_docs spot-check, ML job state, ELSER latency, Kibana object reachability. Should run in under 60 seconds and output paste-ready fix commands for anything failing.

### `wind-reset` *(added this session)*
Cleanup after a demo: stops ML jobs, deletes Kibana objects, removes indices and all supporting infrastructure — prefix-aware, dry-run support, verification step confirming resources are gone.

---

## elastic/agent-skills dependency

The pipeline implicitly depends on skills from `https://github.com/elastic/agent-skills` that were not referenced explicitly in skill instructions. These provide the actual API integration layer for:

| Skill | Used by loom for |
|---|---|
| `cloud-setup` | Configure EC_API_KEY before provisioning |
| `cloud-create-project` | Create serverless projects (bolt-spin) |
| `cloud-manage-project` | Day-2 ops: connect to existing project, delete project (wind-reset) |
| `kibana-agent-builder` | Create/update agent configs during bootstrap (bolt-launch) |
| `kibana-dashboards` | Create/deploy dashboards and Lens visualizations (bolt-launch, demo-kibana-builder) |
| `kibana-connectors` | Set up email/webhook connectors for Workflows (bolt-launch) |
| `kibana-alerting-rules` | Configure alerting if demo includes alerting scenes |
| `elasticsearch-esql` | Run spot-check queries in wind-pulse, finish-check |

**Gap:** No elastic/agent-skills exist yet for ML anomaly detection jobs, Kibana Workflows (9.3), ingest pipelines, or index template management. These are handled entirely within `bootstrap.py` today.

---

## Process improvements for next time

1. **Scope conversation first** — before writing the first skill, map the full pipeline: start, end, optional branches, external dependencies
2. **One skill per session** — or at most two; eval cycle + commit fits cleanly in one context window
3. **Commit after each skill** — not in batches; individual commits keep history readable
4. **Write evals before writing the skill** — forces articulation of "good" before design is committed
5. **Real-data validation on at least one skill per category** before shipping

---

## Tool observations

- `gh auth login` requires `read:org` scope; `repo` scope alone supports repo creation via curl but not the gh CLI
- The `Write` tool requires a prior `Read` on any file that may already exist
- Negative assertions in evals need explicit scope qualifiers to avoid false failures
