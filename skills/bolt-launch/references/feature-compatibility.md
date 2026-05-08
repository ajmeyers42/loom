# Feature Compatibility Reference

**Loaded by:** `skills/bolt-launch/SKILL.md`, `skills/thread-audit/SKILL.md`, `skills/weave-agent/SKILL.md`, `skills/weave-fleet/SKILL.md`, `skills/weave-model/SKILL.md`

This file is the **single source of truth** for Elastic version gates and feature availability by deployment type. When a feature's minimum version or availability changes, update here. Skills read from here rather than hardcoding version numbers.

---

## Pipeline Baseline (D-033)

| Constant | Value |
|----------|-------|
| Minimum Elastic version for generated scripts | **9.4** |
| `SKIP_VERSION_CHECK` env var | Set to `true` to bypass the version gate (use only for pre-GA testing) |
| Bootstrap halt message | `"Cluster version {v} < 9.4 — set SKIP_VERSION_CHECK=true to override"` |

All `bootstrap.py` / `bootstrap-data.py` generated scripts validate `version.number >= (9, 4)` at Step 1 unless `SKIP_VERSION_CHECK=true`.

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

---

## Feature Probe Endpoints

These probes must be run after provisioning or connecting to an existing cluster. A `404` response means the feature is not enabled on this deployment — do not write build code against it until it returns `200`.

| Feature | Probe | Interpretation |
|---------|-------|---------------|
| Agent Builder | `GET /api/agent_builder/agents` | 404 = not enabled |
| Agent Builder Skills catalog | `GET /api/agent_builder/skills` | 404 = skills not available (use tools only) |
| Workflows | `GET /api/workflows` | 404 = not enabled |
| Kibana Streams | `GET /api/streams` | 404 = not available on this version |

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
