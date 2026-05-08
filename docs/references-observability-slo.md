# Observability SLOs — programmatic creation (reference links)

Use these alongside **`elastic/agent-skills`** (`observability-manage-slos`, `kibana-alerting-rules`) and the **Kibana OpenAPI** for request bodies. Scope all API payloads to **`ELASTIC_VERSION`** / `thread-audit` (**D-020**, **D-025**).

## Which Guide branch to open

- **Elastic Stack 8.x:** Use your stack **minor** in the path (e.g. `8.19`, `8.18`). Pages are published per minor.
- **Elastic Stack 9.0+:** The **Observability Guide** under `/guide/en/observability/` is published on the **`9.0`** branch for the 9.x line (verified: `9.1` / `9.2` book URLs are not present as separate branches; use **`9.0`** or follow **[current](https://www.elastic.co/guide/en/observability/current/slo.html)**, which redirects to the latest **Elastic Docs**).
- **Staying current:** When you bump the engagement’s target stack, re-open the **same topic** for the new branch (8.x minor or `9.0`) and skim for product changes — e.g. **9.0** [Create an SLO](https://www.elastic.co/guide/en/observability/9.0/slo-create.html) adds **Observability serverless** role requirements and restates that **UI-created SLOs** get a **default burn-rate rule** (configure a connector to notify). **OpenAPI** remains the contract for automation.

## Elastic Guide — Observability (stack-aligned)

| Topic | Stack 8.x (example `8.19`) | Stack 9.x (`9.0` book for 9.0+) |
| --- | --- | --- |
| SLO concepts | [Service-level objectives (SLOs)](https://www.elastic.co/guide/en/observability/8.19/slo.html) | [Service-level objectives (SLOs)](https://www.elastic.co/guide/en/observability/9.0/slo.html) |
| Create an SLO (UI + context for APIs) | [Create an SLO](https://www.elastic.co/guide/en/observability/8.19/slo-create.html) | [Create an SLO](https://www.elastic.co/guide/en/observability/9.0/slo-create.html) |
| SLO burn rate **alert** rules | [Create an SLO burn rate rule](https://www.elastic.co/guide/en/observability/8.19/slo-burn-rate-alert.html) | [Create an SLO burn rate rule](https://www.elastic.co/guide/en/observability/9.0/slo-burn-rate-alert.html) |
| Troubleshoot SLOs (includes **reset** usage) | [Troubleshoot SLOs](https://www.elastic.co/guide/en/observability/8.19/slo-troubleshoot-slos.html) | [Troubleshoot SLOs](https://www.elastic.co/guide/en/observability/9.0/slo-troubleshoot-slos.html) |

## API hub

| Resource | Stack 8.x (example `8.19`) | Stack 9.x (`9.0`) |
| --- | --- | --- |
| Kibana & Observability API entry | [API reference](https://www.elastic.co/guide/en/starting-with-the-elasticsearch-platform-and-its-solutions/8.19/api-reference.html) | [API reference](https://www.elastic.co/guide/en/starting-with-the-elasticsearch-platform-and-its-solutions/9.0/api-reference.html) |

From there, use the **Kibana** OpenAPI for:

- `POST /api/observability/slos` — [Create an SLO](https://www.elastic.co/docs/api/doc/kibana/operation/operation-createsloop)
- `POST /api/alerting/rule/{id}` with `rule_type_id: slo.rules.burnRate` — burn rate rules (validate `params` per version)

## Programmatic path in loom

- **`skills/bolt-launch/SKILL.md`** — Step 13 (SLOs + burn-rate rules when in scope).
- Engagement example: `kibana/deploy_kibana_gaps.py` (Citizens) — creates SLOs via API; burn-rate rules still require Alerting API payloads validated for the target stack (see Guide + OpenAPI).

## Why both Guide and OpenAPI

- **Guide** explains behavior, defaults (e.g. UI-created SLOs may get default burn rules), and operations like **reset**.
- **OpenAPI** is the source of truth for **JSON bodies** on a given Kibana version.

## Related: rules, connectors, and other saved objects

For **general** Alerting rules (not only SLO burn rate), **connectors**, and **Saved Objects**
(import, export, dashboards, tags), use **`docs/references-kibana-apis.md`** — Kibana Guide
`current` + Elastic Docs API groups.
