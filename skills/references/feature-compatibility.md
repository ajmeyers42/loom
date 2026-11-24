# Feature Compatibility Reference

**Loaded by:** `skills/bolt-launch/SKILL.md`, `skills/thread-audit/SKILL.md`, `skills/weave-agent/SKILL.md`, `skills/weave-fleet/SKILL.md`, `skills/weave-model/SKILL.md`

This file is the **single source of truth** for Elastic version gates and feature availability by deployment type. When a feature's minimum version or availability changes, update here. Skills read from here rather than hardcoding version numbers.

---

## Pipeline Baseline (D-033)

| Constant | Value |
|----------|-------|
| Default Elastic version for new demos | **9.6** |
| Minimum Elastic version for generated scripts | **9.6** |
| `SKIP_VERSION_CHECK` env var | Set to `true` to bypass the version gate (use only for pre-GA testing) |
| Bootstrap halt message | `"Cluster version {v} < 9.6 — set SKIP_VERSION_CHECK=true to override"` |

New demos default to Elastic 9.6 unless the SA specifies a different version. Serverless
9.6 capabilities are available now; ECH and self-managed 9.6 availability should be
confirmed at provisioning time and pinned when the create API exposes it. Existing
deployments still use the live version from `GET /` and Kibana `/api/status`.

All `bootstrap.py` / `bootstrap-data.py` generated scripts validate `version.number >= (9, 6)` at Step 1 unless `SKIP_VERSION_CHECK=true`.

---

## Feature Availability Matrix

| Feature | Min Version | Min License | Serverless ES | Serverless Oblt | Serverless Security | ECH | Self-managed / ECK |
|---------|------------|-------------|:---:|:---:|:---:|:---:|:---:|
| ES\|QL | 8.11 | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| ELSER v2 / `semantic_text` | 8.11 | Basic | ✅ (managed) | ✅ | ✅ | ✅ | ✅ (EIS/local) |
| BM25 / standard search | Any | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| RRF hybrid retrieval | 8.14 | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| ML anomaly detection (API) | 7.3 | Gold (ECH/self-managed); included Serverless | ✅ auto-scaled | ✅ | ✅ | ✅ | ✅ (ML nodes req'd) |
| ML Anomaly Explorer UI | 7.3 | Gold | ❌ not available | ❌ | ❌ | ✅ | ✅ |
| ML NLP / trained models | 8.7 | Platinum (ECH/self-managed); included Serverless | ✅ | ✅ | ✅ | ✅ | ✅ (≥16GB ML node) |
| **Agent Builder** | **9.3** | Any | ✅ | ✅ | ✅ | ✅ | ✅ (Cloud Connect req'd) |
| **Elastic Workflows** | **9.3** | Any | ✅ | ✅ | ✅ | ✅ | ✅ |
| Elastic Inference Service (EIS) | 9.0 | Basic | ✅ built-in | ✅ | ✅ | ✅ (Cloud Connect) | ✅ (Cloud Connect) |
| AI Assistant (Security/Oblt) | 8.14 | Any (connector req'd) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Kibana Playground | 8.14 | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| ILM | 7.0 | Basic | ❌ use DSL | ❌ | ❌ | ✅ | ✅ |
| Data Stream Lifecycle (DSL) | 8.11 | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| Kibana Streams | 9.x | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| Fleet / Elastic Agent | 7.13 | Basic | ❌ | ✅ | ✅ | ✅ (Fleet Server) | ✅ |
| Transforms | 7.2 | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| Security / SIEM detection rules | 7.11 | Basic (limited) / Gold (full) | ❌ | ❌ | ✅ | ✅ | ✅ |
| SLOs | 8.12 | Any | ❌ | ✅ | ❌ | ✅ | ✅ |
| Searchable Snapshots | 7.12 | Enterprise | ❌ | ❌ | ❌ | ✅ | ✅ |
| Frozen tier | 7.12 | Enterprise | ❌ | ❌ | ❌ | ✅ | ✅ |
| Watcher | 5.0 | Gold | ❌ | ❌ | ❌ | ✅ | ✅ |
| Cross-cluster search | 6.7 | Gold | ❌ | ❌ | ❌ | ✅ | ✅ |
| Connector framework (ingestion) | 8.8 | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| Data streams | 7.9 | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| Geo / spatial search | 7.x | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| ES\|QL Logical Views | 9.6 | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| ES\|QL `IN` / `NOT IN` subqueries | 9.6 | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| ES\|QL coordinator-mode `LOOKUP JOIN` | 9.6 | Enterprise | ✅ | ✅ | ✅ | ✅ | ✅ |
| ES\|QL Data Federation for Amazon S3 | 9.6 | Enterprise | ⏳ coming soon | ⏳ coming soon | ⏳ coming soon | TP | TP |
| Columnar Mode high-cardinality analytics / codec | 9.6 | Check license | TP | TP | TP | TP | TP |
| PromQL against Elasticsearch | 9.6 | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cross-project search (CPS) | Serverless GA | Check license | ✅ | ✅ | ✅ | ❌ | ❌ |
| Universal Alerting (ES\|QL alerts) | 9.6 | Basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| Elastic Service Accounts for Workflows | 9.6 | Any (`manage_security` to bind) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Non-streaming chat completion | 9.6 | Any | ✅ | ✅ | ✅ | ✅ | ✅ |
| EIS `document_extraction` task | 9.6 | EIS entitlement | TP | TP | TP | TP | TP |
| Opt-in prompt caching | 9.6 | Provider-dependent | TP | TP | TP | TP | TP |
| Multiuser Kibana chat | 9.6 | Any | TP | TP | TP | TP | TP |
| Prompt-generated custom Kibana panels | 9.6 | Any | TP | TP | TP | TP | TP |
| Elastic Security AlertZero | 9.6 | Enterprise or trial | ❌ | ❌ | TP | ❌ until 9.6 ECH | ❌ until 9.6 self-managed |
| Elastic Security Entity Analytics attention signals/resolution | 9.6 | Enterprise | ❌ | ❌ | ✅ | ✅ | ✅ |
| Elastic Defend Linux ransomware protection | 9.6 | Security license | ❌ | ❌ | ✅ | ✅ | ✅ |
| Elastic Defend custom YARA memory signatures | 9.6 | Security license | ❌ | ❌ | ✅ | ✅ | ✅ |
| Security for AI integration package | 9.6 | Platinum or trial | ❌ | ❌ | TP | TP | TP |
| Elastic Agent FIPS 140-3 support | 9.6 | Deployment-dependent | ❌ | ✅ | ✅ | ✅ | ✅ |

---

Status legend: ✅ = generally available for that deployment type, TP = technical preview,
⏳ = announced but not yet available for that deployment type, ❌ = not available / not
applicable. Treat TP and private-preview features as storyline options only after the
SA confirms preview risk and `finish-verify` probes the backing APIs or package assets.

---

## 9.6 Demo Guidance

Use 9.6 GA capabilities first when they fit the customer outcome:

- **Search / AI:** Logical Views for reusable ES|QL, `IN` / `NOT IN` subqueries for
  dynamic allow/deny lists, coordinator-mode `LOOKUP JOIN` for distributed lookup
  patterns, PromQL for migration-friendly metrics dashboards, non-streaming chat
  completion for regulated proxy environments, and Elastic Service Accounts for
  durable scheduled Workflows.
- **Observability:** Universal Alerting for ES|QL-authored alerts, contextual APM
  investigations, service-map drilldowns, GenAI trace visibility (technical preview),
  Vercel/Supabase/Temporal integrations where the Fleet package exists, and automatic
  Synthetics private-location scaling.
- **Security:** Entity Analytics attention signals and entity resolution, Linux
  ransomware protection, custom YARA memory signatures, MITRE ATLAS / AI detection
  rule coverage, and Security for AI only when the package and license are confirmed.
- **Platform governance:** budget alerts, serverless log delivery, Cloud audit trails,
  service accounts, FIPS 140-3 Agent support, and cross-project search for Serverless
  consolidation stories.

Technical-preview or private-preview features must be framed as optional "preview wow"
moments, not required demo dependencies, unless the customer explicitly accepts preview
risk and the target deployment proves support:

- ES|QL Data Federation for Amazon S3 (TP; Enterprise; ECH/self-managed first,
  Serverless announced as coming soon).
- Columnar Mode high-cardinality aggregations and columnar codec (TP).
- EIS `document_extraction`, prompt caching, multiuser Kibana chat, prompt-generated
  custom panels, AlertZero, Security for AI, GenAI traces, and nightshift AI SRE
  (nightshift is private preview).

9.6 known-risk notes for demo authors:

- Kibana Workflows execution-read APIs require both `workflow_execution_read` and
  `workflow_read`; custom roles with execution-only access receive `403`.
- ES|QL `KNN` followed by `STATS` requires an explicit `LIMIT` immediately after `KNN`.
- Inline `TO_DENSE_VECTOR` inside `KNN` can fail; convert with `EVAL` first and pass
  the derived dense-vector column.
- Avoid 9.x upgrades of indices with complex `simple_pattern` tokenizer expressions
  until the Lucene tokenizer issue is fixed.

## Feature Probe Endpoints

These probes must be run after provisioning or connecting to an existing cluster. A `404` response means the feature is not enabled on this deployment — do not write build code against it until it returns `200`.

| Feature | Probe | Interpretation |
|---------|-------|---------------|
| Agent Builder | `GET /api/agent_builder/agents` | 404 = not enabled |
| Agent Builder Skills catalog | `GET /api/agent_builder/skills` | 404 = skills not available (use tools only) |
| Workflows | `GET /api/workflows` | 404 = not enabled |
| Kibana Streams | `GET /api/streams` | 404 = not available on this version |
| Fleet package inventory | `GET /api/fleet/epm/packages/{package}/assets` | Confirm package dashboards, rules, ML jobs, and templates before custom assets |
| Security for AI package | Search EPM, then `GET /api/fleet/epm/packages/{confirmed_package}/assets` | 404 = package unavailable; do not assume package IDs before probing |
| ES\|QL S3 Data Federation | Probe the documented 9.6 data-source APIs and run a dry ES\|QL query | 404/403 = do not use as a required demo path |
| Elastic Service Accounts | Probe Kibana service-account / Workflows binding APIs | 404/403 = keep scheduled Workflows user/API-key based |
| Universal Alerting | Probe rule type inventory for ES\|QL alert support | 404/403 = use classic alerting patterns |

Always use `KIBANA_API_KEY` for these probes. Surface the result before writing any code that depends on these features.

---

## Deployment-Type Capability Notes

### Serverless Elasticsearch
- No ILM — use DSL (`lifecycle` block in index template)
- No ML Anomaly Explorer UI — use `.ml-anomalies-*` index directly via ES|QL dashboards
- ELSER is managed: `service: "elser"`, no `model_id` required
- Agent Builder + Workflows available (feature flag may be required — always probe)
- No Watcher, no frozen tier, no Fleet

### Serverless Observability
- All Serverless ES constraints apply
- Fleet + Elastic Agent available
- APM server + Managed OTLP endpoint available
- SLOs available

### Serverless Security
- All Serverless ES constraints apply
- Fleet + Elastic Agent available
- SIEM detection rules available
- SLOs not available

### ECH (Elastic Cloud Hosted)
- Full feature set; standard licensing applies
- Agent Builder available 9.3+; EIS via Cloud Connect (one-time setup)
- ILM available; DSL also available 8.11+
- ML Anomaly Explorer UI available
- ELSER: `service: "elastic"`, `model_id: ".elser-2"` (see `inference-config.md`)

### Self-managed / ECK
- Full feature set from 9.3+
- Agent Builder + EIS require Cloud Connect config
- Explicit node roles required for ML/frozen/transform
- Local ML nodes for anomaly detection and models that cannot leave the environment

---

## ILM vs DSL Selection

Generated bootstrap scripts detect deployment type from `DEPLOYMENT_TYPE` env var and branch accordingly:

```python
USE_DSL = DEPLOYMENT_TYPE == "serverless"
# ECH, self_managed, docker → ILM
# serverless → DSL (lifecycle block in index template; skip ILM PUT)
```

Teardown also branches: ILM DELETE is skipped on serverless; DSL is embedded in templates and removed with them.
