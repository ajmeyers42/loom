---
name: thread-audit
description: >
  Cross-references the selected demo scope (the frozen capability map from warp-spark) against the
  customer's actual Elastic deployment (from warp-scan output, if available)
  to produce a feature feasibility matrix. Flags version gaps, license tier mismatches,
  infrastructure requirements, and setup work needed before the demo can be built or run.
  Outputs a machine-readable audit JSON and a human-readable SE briefing in markdown.

  ALWAYS use this skill when the user has discovery JSON and wants to know if the planned
  demo is feasible, asks "can we demo X on their cluster", "what do we need to set up before
  the demo", "are there any blockers", "what license do they need for this", or provides
  both a discovery profile and a diagnostic current-state file. Also trigger when
  warp-listen output includes gaps referencing version or license unknowns.
  Run this before weave-script — the audit output shapes what can be scoped.
---

# Demo Platform Audit

You are evaluating whether the demo scenarios identified in discovery are feasible on the
customer's actual Elastic platform. This is a blocking step before demo build — it's far
cheaper to catch a version gap here than after data is loaded and scripts are written.

The audit has two modes:

**Full audit** — both discovery JSON and diagnostic current-state JSON are available.
Cross-reference planned features against confirmed platform capabilities.

**Partial audit (discovery only)** — no diagnostic available. Assess feasibility based on
what was stated in the discovery notes (version, license, deployment type). Flag all
assumptions and mark them as unverified. Recommend getting a diagnostic before building.

## Step 1: Read the Inputs

**Scope = the selected capability map.** In the loom pipeline the audit runs after the
vision is frozen and confirmed. Run `python3 scripts/loom_state.py path plan <slug>` — it
refuses until vision is confirmed and returns the audit scope: every in-scope
`capability_id` with its origin, catalog `audit_feature` (the row to use in the Feature
Requirements table below), default `remediation_owner`, and the **capability map hash** to
stamp into `meta.capability_map_hash`. Audit exactly those capabilities — one
`feature_audit` row each — including SA-added and implied ones (e.g. `ai-cost-dashboard`).
Do not add capabilities the map does not select; do not drop selected ones.

Read for platform context:

- `demo/{slug}-capability-map.json` — the scope (above).
- `demo/{slug}-discovery.json` — from warp-listen. Focus on `elastic_relationship`,
  `deal_context`, and any version/license statements.
- `demo/{slug}-current-state.json` — from warp-scan (if available). Focus on
  `cluster.version`, `cluster.license_type`, `cluster.deployment_type`, `features_in_use`,
  `resource_signals`, and `findings_summary`.
- `opportunity/{slug}-opportunity-profile.json` — from thread-qualify (if available). Read
  `demo_scope_signals` to pre-scope the feature audit to only the capabilities actually in
  play for this engagement:

  ```json
  "demo_scope_signals": {
    "primary_solution_area": "search | observability | security | cross_solution",
    "agent_builder_in_scope": false,
    "ml_in_scope": false,
    "siem_in_scope": false,
    "slo_in_scope": false,
    "noted_wow_moments": []
  }
  ```

  Use `demo_scope_signals` only as context (e.g. to explain why a capability matters) —
  the capability map, not the signals, decides scope.

  **Standalone use (no capability map — ad-hoc "can we demo X on their cluster"):** audit the
  features the SA names, or `demo_scope.recommended_features` from discovery, and set
  `meta.scope_source` to `discovery` (or `ad_hoc`). Such an audit cannot be used for the
  loom demo-path commit.

If `demo/{slug}-discovery.json` is missing and no capability map exists, ask the user to run
`warp-listen` first.

**Version anchoring:** When the target is an **existing** cluster (diagnostic present or
the SA supplied endpoints/credentials), the audit **must** use the **observed**
Elasticsearch/Kibana versions from `{slug}-current-state.json` or from `GET /` and
Kibana `/api/status` — never assume “latest” for an existing deployment. If only
discovery is available, flag version as **unverified** until a diagnostic or live
version check is performed.

## Step 2: Build the Feature Compatibility Matrix

For each feature in the planned demo scope, evaluate it against the platform requirements
table below. Mark each feature as:

- ✅ **Ready** — platform meets all requirements, feature can be demoed as-is
- ⚠️ **Setup required** — platform supports it but needs pre-demo configuration (endpoint
  deployment, mapping changes, connector setup, etc.)
- 🔶 **Upgrade required** — feature needs a newer Elastic version than what's deployed
- 🔴 **Blocked** — hard blocker: wrong license tier, feature not available on deployment type,
  or infrastructure requirement not met
- ❓ **Unverified** — insufficient platform data to confirm; assumption stated

### Feature Requirements Reference

Use this table to assess each planned feature. Always check the customer's actual version
and license against the minimum required. When the diagnostic is unavailable, flag the
requirement and mark as unverified.

| Feature | Min Version | Min License | Deployment Notes | Infrastructure Notes |
|---|---|---|---|---|
| ES\|QL | 8.11 | Basic | All deployment types | None |
| ELSER v2 (semantic_text) | 8.11 | Basic | All types; serverless uses managed endpoint | Inference endpoint must be deployed and warmed |
| BM25 / standard search | Any | Basic | All | None |
| RRF hybrid retrieval | 8.14 | Basic | All | ELSER endpoint if semantic leg included |
| ML anomaly detection (UI + API) | 7.3 | Gold (self-managed/cloud); included on serverless | Self-managed needs dedicated ML node(s) | ML nodes with adequate heap |
| ML NLP / trained models | 8.7 | Platinum (self-managed); included on serverless | ML nodes required on self-managed | 1+ ML node with ≥ 16GB heap |
| AI Assistant (Security / Observability) | 8.14 | All (connector required) | Kibana connector to OpenAI/Bedrock/etc. must be configured | None beyond connector config |
| Agent Builder | 9.3 | Any | ECK/self-managed 9.3+, ECH, Serverless Elasticsearch — available on all deployment types from 9.3; requires Cloud Connect for Elastic Managed LLMs | Cloud Connect to EIS if using Elastic Managed LLMs |
| Elastic Inference Service (EIS) via Cloud Connect | 9.0 | Basic | ECK/self-managed and ECH connect to EIS via Cloud Connect (one-time setup); built-in on Serverless. Default for semantic_text embedding (ELSER, jina-embeddings-v3), reranking (jina-reranker-v3), and Elastic Managed LLMs for Agent Builder | ECK/self-managed: Cloud Connect config required; Serverless: auto-provisioned |
| Elastic Workflows | 9.3 | Any (serverless or cloud) | Serverless only at initial release | None |
| Kibana Playground | 8.14 | Basic | All | ELSER or other inference endpoint for semantic |
| ILM | 7.0 | Basic | Serverless uses DSL (data stream lifecycle) instead | None |
| Searchable Snapshots | 7.12 | Enterprise | Snapshot repo required | Object storage or HDFS repo |
| Frozen tier | 7.12 | Enterprise | Requires searchable snapshots | Object storage repo + frozen nodes or serverless |
| Cross-cluster search | 6.7 | Gold | Both clusters must be accessible | Network connectivity between clusters |
| Fleet / Elastic Agent | 7.13 | Basic | All | Fleet Server required |
| Transforms | 7.2 | Basic | All | Dedicated transform nodes recommended at scale |
| Security / SIEM detection rules | 7.11 | Basic (limited) / Gold (full) | All | None |
| Entity risk scoring / entity analytics | 9.0 (privilege model changed in 9.4) | Platinum (Stack); Security Analytics Complete tier (Serverless) | All; risk scoring is enabled per Kibana space | Risk engine uses transforms + ingest pipelines; ~2 GB JVM heap per ~44M risk documents |
| Kibana alerting rules + connectors | Any 9.x | Rules: Basic. Connectors: some free (Index, Server log), most third-party (Slack, email, webhook, PagerDuty, ITSM) are paid — confirm the tier on elastic.co/subscriptions | All; rules and connectors are space-isolated; self-managed needs `xpack.encryptedSavedObjects.encryptionKey` | A connector per destination, created in the demo space |
| SLOs (+ burn-rate rules) | 8.12 (GA) | Paid tier on Stack (docs: "appropriate license" — confirm on elastic.co/subscriptions); included in Serverless Observability | Stack: SLO access configured; Serverless: SLO Editor role | Stack: node(s) with both ingest and transform roles (ECH hot nodes cover this); default burn-rate rule has no connector |
| Elasticsearch Graph API | 5.0 | Platinum | All | None |
| Watcher | 5.0 | Gold | Self-managed / cloud (not serverless) | None |
| Data streams | 7.9 | Basic | All | None |
| Connector framework (ingestion) | 8.8 | Basic | All | Connector service or managed connectors |
| Geo / spatial search | 7.x | Basic | All | None |

**Deployment type caveats:**
- **Serverless Elasticsearch:** No ILM (use Data Stream Lifecycle), no self-managed ML nodes
  (ML is auto-scaled), Agent Builder (9.3+) and Workflows available, EIS built-in, no Watcher
- **ECH (Elastic Cloud Hosted):** Full feature set, standard licensing applies; Agent Builder
  available 9.3+; EIS via Cloud Connect
- **Self-managed / ECK:** Full feature set from 9.3+, explicit node roles required for
  ML/frozen/transform; Agent Builder available on ECK 9.3+ (requires Cloud Connect for Elastic
  Managed LLMs); EIS accessible via Cloud Connect (quick one-time config); local ML nodes for
  anomaly detection and specialized models that cannot leave the customer environment

## Step 3: Identify Gaps and Remediation

For each non-Ready feature, determine the remediation path and its cost/effort:

| Effort Level | Definition | Examples |
|---|---|---|
| **Quick** (< 1 hour) | Config change or API call | Deploy ELSER endpoint, enable a setting, register snapshot repo |
| **Half-day** (2–4 hours) | Index creation + data load + warmup | New index with semantic_text, load corpus, warm ELSER |
| **Upgrade** (1+ days, schedule required) | Version or license change | 8.x → 9.x rolling upgrade, license tier change |
| **Infra change** (days–weeks) | New nodes or cluster reconfiguration | Add ML nodes to self-managed cluster, provision frozen tier |
| **Descope** | Feature cannot be made available in demo timeframe | Use narrative + screenshot, or replace with available alternative |

For upgrade-required and blocked features, always suggest an alternative that works on the
current platform if one exists. The demo should not fail because of a version gap — it
should be re-scoped. In the loom pipeline, re-scoping means the SA edits the capability map
(`vision map exclude` / `add`), re-freezes, and the audit re-runs — red rows block the
demo-path commit.

**Remediation owner (required on every non-ready row):** who closes the gap —
- `pipeline` — loom's build stages automate it (deploy an inference endpoint, create an
  Agent Builder agent, seed an index).
- `manual_once` — a one-time manual step in the target environment (configure an LLM
  connector, enable a Kibana feature, accept a license prompt).
- `customer` — needs customer- or SA-supplied evidence or action (license upgrade, network
  access, a version confirmation, sample data).

Start from the catalog default reported by `path plan`; override it when the platform
facts say otherwise.

## Step 4: Write the Two Output Files

### Output 1: `demo/{slug}-platform-audit.json`

```json
{
  "meta": {
    "slug": "",
    "audit_date": "",
    "audit_mode": "full | partial",
    "discovery_version": "",
    "diagnostic_version": "",
    "opportunity_profile_version": "",
    "scope_source": "capability_map | discovery | ad_hoc",
    "capability_map_hash": "sha256:… (from loom_state path plan)",
    "scope_pre_filtered": true,
    "platform_summary": ""
  },
  "platform": {
    "version": "",
    "license_type": "",
    "deployment_type": "",
    "version_verified": true,
    "license_verified": true
  },
  "feature_audit": [
    {
      "capability_id": "agent-builder",
      "origin": "vision | sa_added | sa_requested | implied",
      "feature": "",
      "planned": true,
      "status": "ready | setup_required | upgrade_required | blocked | unverified",
      "remediation_owner": "pipeline | manual_once | customer (required unless ready)",
      "requirement_met": {
        "version": true,
        "license": true,
        "infrastructure": true,
        "configuration": true
      },
      "gap": "",
      "remediation": "",
      "effort": "quick | half_day | upgrade | infra_change | descope",
      "demo_impact": "blocks_scene | reduces_realism | talking_point | none",
      "alternative": ""
    }
  ],
  "overall_status": "green | amber | red",
  "blocking_count": 0,
  "setup_required_count": 0,
  "ready_count": 0,
  "pre_demo_tasks": [
    {
      "task": "",
      "effort": "",
      "owner": "SE | customer | joint",
      "blocks": []
    }
  ],
  "descoped_features": [],
  "recommended_alternatives": []
}
```

**Overall status logic:**
- 🟢 **green** — all planned features are ready or require quick setup (< 1 hour each)
- 🟡 **amber** — one or more features need half-day setup or have unverified requirements;
  demo is buildable but needs prep work
- 🔴 **red** — one or more features are blocked or require upgrade/infra change; demo scope
  must be revised or timeline extended

`descoped_features` / `recommended_alternatives` items may be strings or objects
(`{capability_id, reason}` / `{capability_id, alternative}`). Validate against
`schemas/platform-audit.schema.json`.

### Output 2: `demo/{slug}-platform-audit.md`

A concise SE briefing — not sent to the customer. Written so an SE who hasn't read the
discovery notes can pick this up and know exactly what to do before building.

Structure:
```
# Platform Audit — [Public Display Name] ([slug])
**Status:** 🟢 Green / 🟡 Amber / 🔴 Red
**Platform:** [version] · [license] · [deployment type]
**Audit date:** [date] · **Scope:** capability map `sha256:…` (first 12 chars)

## Feature Feasibility

| Capability | Status | Gap | Remediation | Owner | Effort |
|---|---|---|---|---|---|
[One row per in-scope capability in the map]

## Pre-Demo Task List
[Ordered by dependency — tasks that unblock other tasks come first]

## Descoped / Alternatives
[If anything was descoped, say what was dropped and what replaces it]

## Bottom Line
[2–3 sentences: is the demo buildable as scoped? What's the critical path?
What conversation needs to happen with the customer before build starts?]
```

### Register

Run `python3 scripts/loom_state.py path check <slug>`. It validates the JSON, requires the
markdown, `scope_source: capability_map`, a `capability_map_hash` matching the current map,
one row per in-scope capability, and a `remediation_owner` on every non-ready row, then
reports amber rows grouped by owner and any red rows. Fix and re-run until it passes; the
SA then commits the Demo path (thread-suggest → `loom_state path commit`).

## What Good Looks Like

**Green — Serverless, modern demo:** Discovery asks for ELSER, ES|QL, Agent Builder,
Workflows. Customer is on Serverless Elasticsearch (9.x). All features ready or quick-setup.
Pre-demo tasks: deploy ELSER endpoint, load corpus. Overall green.

**Amber — ECH 8.17, semantic scene in scope:** ELSER available but not deployed (half-day
setup). ML anomaly detection available and Gold license confirmed. Agent Builder not available
(8.x). Recommendation: keep ML and ES|QL scenes, replace Agent Builder with Playground/AI
Assistant which works on 8.14+. Overall amber — buildable with prep.

**Red — Self-managed 7.17, modern demo scope:** ELSER requires 8.11 (upgrade required).
ML available but on basic license (Gold required). Agent Builder requires 9.3+ (not available
on 7.x or 8.x). Recommendation: re-scope to ES|QL + BM25 + basic ML, or flag that an upgrade
conversation needs to happen before the demo can be built. Overall red — scope must change.

**Amber — ECK 9.4, Agent Builder in scope:** Greenfield deployment, ECK 9.4 with Enterprise
Trial. Agent Builder is available (9.3+ on ECK). EIS access requires Cloud Connect
configuration (quick, one-time). Inference endpoints (ELSER on EIS, jina-embeddings-v3,
jina-reranker-v3) not yet deployed — setup required. Overall amber — buildable, critical path
is Cloud Connect → inference endpoints → corpus load.

**Partial audit — no diagnostic:** Discovery says "on-prem Elastic, version unknown." Mark
all ML and semantic features as unverified. Pre-demo task: get diagnostic before scoping
demo. Recommend warp-scan be run first.
