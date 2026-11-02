# Capability catalog (D9)

One vocabulary for the **Elastic Capability Map** (warp-spark / Vision), **platform audit rows**
(thread-audit), and the **Build list** (P3). Machine-readable source:
[`capability-catalog.json`](capability-catalog.json) — ids there are canonical; this page explains
how to use them.

## How each stage uses the catalog

| Stage | Use |
|-------|-----|
| `warp-spark` | Propose 2–4 capabilities by `id` (origin `vision`). SA adds chips by `id` (origin `sa_added`) or free-text requests (origin `sa_requested`, slugified id, `catalog: false`). Warn above ~4 in scope. |
| `loom_state vision map …` | Edits `demo/{slug}-capability-map.json`; adding `agent-builder` auto-includes `ai-cost-dashboard` (origin `implied`, D-036) unless `--no-token-visibility`. |
| `thread-audit` | One `feature_audit` row per **in-scope** capability, `capability_id` = map id. Use `audit_feature` to find the requirement row in the Feature Requirements Reference. Set `remediation_owner` on every non-ready row (default from `default_remediation_owner`). |
| Build (P3) | `build_skills` hints which weave/finish stage owns the asset. |

## Ids

| id | Capability | Solutions | Default remediation owner |
|----|------------|-----------|---------------------------|
| `esql` | ES\|QL investigations and analytics | search, observability, security | pipeline |
| `full-text-search` | Full-text search (BM25) | search | pipeline |
| `semantic-search` | Semantic search (semantic_text via EIS) | search, security, observability | pipeline |
| `hybrid-search` | Hybrid retrieval (RRF) | search | pipeline |
| `reranking` | Reranking (EIS) | search | pipeline |
| `agent-builder` | Agent Builder (agents + tools) — implies `ai-cost-dashboard` | all | pipeline |
| `ai-cost-dashboard` | AI Cost + Usage dashboard (D-036) | all | pipeline |
| `workflows` | Elastic Workflows | all | pipeline |
| `ai-assistant` | Elastic AI Assistant (Security / Observability) | observability, security | manual_once |
| `detection-rules` | Detection rules + alerts | security | pipeline |
| `cases` | Cases | security, observability | pipeline |
| `attack-discovery` | Attack Discovery | security | manual_once |
| `entity-analytics` | Entity analytics / risk scoring | security | pipeline |
| `ml-anomaly` | ML anomaly detection | observability, security, search | pipeline |
| `fleet-integrations` | Fleet integrations (EPR packages) | observability, security | pipeline |
| `apm` | APM / distributed tracing | observability | pipeline |
| `logs` | Log analytics (Discover / Streams) | observability, security | pipeline |
| `slos` | SLOs and burn-rate alerting | observability | pipeline |
| `alerting` | Kibana alerting rules + connectors | all | pipeline |
| `dashboards` | Kibana dashboards (ES\|QL panels) | all | pipeline |

## Remediation owner (amber subtypes)

| Value | Meaning | UX action |
|-------|---------|-----------|
| `pipeline` | Platform can run it; Loom authors the asset in Build (agents, tools, workflows, data, dashboards). | Accept into Build — never a discovery restart. |
| `manual_once` | One non-automatable step (tech-preview toggle, LLM connector pick). | Surface on Readiness; does not block Design. |
| `customer` | Needs customer/SA evidence or action (unverified version, license, diagnostic). | Optional Inputs update → re-audit. |

`blocked` / `upgrade_required` rows are **red**, not amber: descope (move to Out of Scope and
re-freeze) or pick an alternative before committing the demo path.

Adding an entry: append to the JSON, add a row here, keep ids kebab-case and stable.
