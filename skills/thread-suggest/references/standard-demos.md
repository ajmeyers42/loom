# Elastic Standard Demo Catalog

This file is the lookup table used by `thread-suggest` to evaluate whether
an existing Elastic demo environment covers a customer's needs. It is SA-maintained —
add new entries as standard demos are published or updated.

**Format:** Each entry includes the demo name, primary use cases covered, industries it
lands well in, known limitations/gaps, and a note on any associated hive-mind recipe.

---

## How to Use This File

`thread-suggest` reads this file in Step 1 and maps each entry against the
customer's technical win criteria from `{slug}-ideation.md`. A demo is a candidate if its
covered use cases overlap with the top 2–3 customer pains. Limitations are gaps to evaluate
against the three predefined-fit criteria.

---

## Standard Demo Entries

---

### Elastic Enterprise Search — Site Search

**Use cases covered:**
- Full-text search over document corpus (knowledge base, policy library, product catalog)
- Hybrid search (BM25 + semantic via ELSER)
- Faceted filtering and aggregations
- AI chat assistant grounded in indexed documents (RAG via Agent Builder)
- Search relevance tuning

**Industries:** Any — strongest signal in retail, financial services, healthcare, government,
insurance, professional services

**Elastic capabilities demonstrated:**
- Elasticsearch full-text + semantic search
- ELSER sparse embedding
- Agent Builder (RAG assistant persona)
- Kibana dashboards (search analytics)

**Known limitations / gaps:**
- No Observability or Security scenes — pure search/AI narrative
- Data is generic; customer-specific terminology requires talk track bridging
- Agent Builder scenes require Enterprise license on ECH or Serverless project
- No workflow automation scenes

**Predefined fit signals:** Customer's primary pain is "we can't find information" or
"our users can't self-serve answers" — knowledge management, policy lookup, product search,
RAG over internal documents

**Not a fit when:** Customer needs operational telemetry, SIEM, APM, or any real-time
streaming data story

**hive-mind recipe:** Check `../hive-mind/patterns/` for AI Search pattern if available

---

### Elastic Observability — Full-Stack

**Use cases covered:**
- APM / distributed tracing (service maps, transaction analysis)
- Log management and search (Discover, ES|QL log queries)
- Infrastructure monitoring (host metrics, Kubernetes, containers)
- SLO definition and burn rate tracking
- ML-based anomaly detection on metrics and logs
- Alert management and incident correlation

**Industries:** Technology, financial services, retail, healthcare — any organization
running modern application infrastructure

**Elastic capabilities demonstrated:**
- APM with service map
- Logs explorer / Streams
- Infrastructure inventory
- SLO management
- ML anomaly detection
- Alerting and cases

**Known limitations / gaps:**
- No Security / SIEM scenes
- No custom agent or RAG scenes
- Data is synthetic APM/infra — customer service names not reflected
- Requires Observability license tier (Enterprise or Platinum for ML/SLO features)
- Fleet agent integration assumed — no Prometheus-scraper stream demos

**Predefined fit signals:** Customer pain is operational visibility, MTTR, alert fatigue,
service reliability, infrastructure cost, or "we can't find root cause fast enough"

**Not a fit when:** Customer needs search, SIEM, or AI assistant capabilities

**hive-mind recipe:** Check `../hive-mind/patterns/` for Observability patterns

---

### Elastic Security — SIEM and Threat Detection

**Use cases covered:**
- Detection rule management (custom and prebuilt SIEM rules)
- Alert triage and investigation workflow
- ES|QL threat hunting queries
- ML-based anomaly detection (behavioral, user/entity)
- Cases and incident management
- AI Security Assistant (SOC analyst assistant)

**Industries:** Financial services, healthcare, government, retail, technology —
any organization with a SOC or security function

**Elastic capabilities demonstrated:**
- SIEM detection rules
- Alert triage UI
- ES|QL threat hunting
- ML anomaly detection (users, hosts, network)
- Cases API
- AI Security Assistant

**Known limitations / gaps:**
- No Observability or APM scenes
- No custom search or AI assistant scenes outside security context
- AI Security Assistant requires Enterprise license + connector configuration
- Sample data is synthetic — no customer-specific threat scenarios without custom data
- Detection rules are generic SIEM scenarios; MITRE ATT&CK mapping is general

**Predefined fit signals:** Customer pain is detection coverage, SOC efficiency, threat
hunting, compliance monitoring, or "our analysts are overwhelmed with alerts"

**Not a fit when:** Customer needs application observability, search, or a cross-solution story

**hive-mind recipe:** Check `../hive-mind/patterns/` for Security patterns

---

### Elastic Search — E-Commerce with Analytics

**Use cases covered:**
- Product search with relevance tuning
- Faceted navigation and filtering
- AI-powered product recommendations and shopping assistant
- Search analytics (zero-result rates, top queries, conversion funnel)
- A/B testing for search relevance

**Industries:** Retail, marketplace, grocery, electronics, fashion

**Elastic capabilities demonstrated:**
- Full-text + semantic search over product catalog
- Agent Builder (shopping assistant)
- ES|QL analytics dashboards (query performance, conversion)
- Behavioral analytics (click-through, cart events)

**Known limitations / gaps:**
- Data is synthetic retail product catalog — requires talk track bridging for non-retail
- No operational or security scenes
- Behavioral analytics requires custom OTel/APM instrumentation or synthetic events
- Agent Builder requires Enterprise license

**Predefined fit signals:** Customer is in retail/e-commerce and pain is search quality,
customer self-service, cart abandonment, or "customers can't find what they want"

**Not a fit when:** Customer is not in retail/commerce, or primary pain is operational/security

---

### Elastic Observability — Kubernetes and Cloud Native

**Use cases covered:**
- Kubernetes cluster monitoring (pod health, resource utilization, HPA events)
- Container log search and correlation
- Service dependency mapping
- Cost visibility (resource waste, right-sizing signals)
- Incident correlation across nodes, pods, and services

**Industries:** Technology, financial services, any organization running Kubernetes at scale

**Elastic capabilities demonstrated:**
- Kubernetes integration (Fleet agent / EDOT)
- Infrastructure inventory with K8s views
- APM service map
- ES|QL cost and utilization queries
- ML anomaly detection on resource metrics

**Known limitations / gaps:**
- No SIEM or search scenes
- Highly specific to Kubernetes — less relevant for VM-only or serverless infrastructure
- Fleet agent / EDOT integration assumed; Prometheus-scraper patterns not shown
- Requires Observability license

**Predefined fit signals:** Customer is running Kubernetes, pain is cluster visibility,
reliability, or cost optimization

**Not a fit when:** Customer is not Kubernetes-native or primary pain is non-observability

---

## Adding New Entries

To add a new standard demo, use the template below. SA-curated entries are trusted.

```markdown
### [Demo Name]

**Use cases covered:**
- {use case}

**Industries:** {industries}

**Elastic capabilities demonstrated:**
- {capability}

**Known limitations / gaps:**
- {limitation}

**Predefined fit signals:** {when this is the right call}

**Not a fit when:** {explicit disqualifiers}

**hive-mind recipe:** {path or "none"}
```

---

## Maintenance Notes

- Review this file at the start of each quarter or when Elastic releases a new standard demo
- Mark deprecated demos with `**[DEPRECATED]**` and a date — do not delete entries
- If a standard demo has been updated with new capabilities, update the entry and add a
  `**Last updated:**` line at the bottom of the entry
