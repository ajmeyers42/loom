---
name: thread-audit
description: >
  Cross-references the planned demo scope (from warp-listen output) against the
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

Read all available files:

- `demo/{slug}-discovery.json` — from warp-listen. Focus on `demo_scope.recommended_features`,
  `demo_scope.recommended_type`, `elastic_relationship`, and `deal_context`.
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

  **When opportunity-profile is present:** use `demo_scope_signals` to narrow the feature
  compatibility matrix in Step 2 — only evaluate features flagged as in-scope. Do not audit
  the full feature table for capabilities the qualification review has already determined are
  out of scope. This keeps the audit focused and actionable.

  **When opportunity-profile is absent:** run a full audit against all features in
  `demo_scope.recommended_features` from the discovery JSON, as before.

If `demo/{slug}-discovery.json` is missing, ask the user to run `warp-listen` first.

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
should be re-scoped.

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
    "scope_pre_filtered": false,
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
      "feature": "",
      "planned": true,
      "status": "ready | setup_required | upgrade_required | blocked | unverified",
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

### Output 2: `demo/{slug}-platform-audit.md`

A concise SE briefing — not sent to the customer. Written so an SE who hasn't read the
discovery notes can pick this up and know exactly what to do before building.

Structure:
```
# Platform Audit — [Company Name]
**Status:** 🟢 Green / 🟡 Amber / 🔴 Red
**Platform:** [version] · [license] · [deployment type]
**Audit date:** [date]

## Feature Feasibility

| Feature | Status | Gap | Remediation | Effort |
|---|---|---|---|---|
[One row per planned feature]

## Pre-Demo Task List
[Ordered by dependency — tasks that unblock other tasks come first]

## Descoped / Alternatives
[If anything was descoped, say what was dropped and what replaces it]

## Bottom Line
[2–3 sentences: is the demo buildable as scoped? What's the critical path?
What conversation needs to happen with the customer before build starts?]
```

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
