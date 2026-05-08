# Kibana — Saved Objects, rules, and connectors (reference links)

**How this relates to `docs/references-observability-slo.md`:** The Observability SLO doc covers
**SLOs** (`/api/observability/slos`) and **SLO burn-rate rules** as one use of `POST
/api/alerting/rule/{id}` (`rule_type_id: slo.rules.burnRate`). It does **not** replace the
**Saved Objects** or **Alerting** references below — those are what you need for **dashboards,
Lens, tags, generic alert rules, connectors**, and **bulk import/export** of saved objects
(**D-025**, bolt-launch Step **13c–13d**).

## Saved Objects API

**Primary (automation):** [Saved objects — API reference](https://www.elastic.co/docs/api/doc/kibana/group/endpoint-saved-objects)
— groups every `/api/saved_objects/...` operation (import, export, bulk get, find, resolve,
etc.). Use this with **Kibana OpenAPI** / your stack’s **`ELASTIC_VERSION`** for exact request
bodies.

**Narrative (optional):** [Saved Objects API](https://www.elastic.co/guide/en/kibana/current/saved-objects-api.html)
in the Kibana Guide (`current`) — often redirects to the same Elastic Docs material.

## Rules and connectors (Alerting)

**Primary (automation):** [Alerting — API reference](https://www.elastic.co/docs/api/doc/kibana/group/endpoint-alerting)
— rules, connectors, and related endpoints.

**Narrative (optional):** [Alerting APIs](https://www.elastic.co/guide/en/kibana/current/alerting-apis.html)
in the Kibana Guide (`current`).

## Skills

- **`kibana-alerting-rules`** — create/tune rules; includes connector-related workflows where
  applicable.
- **`kibana-connectors`** — manage connectors.
- **`kibana-dashboards`** — dashboards and Lens as code; often paired with **Saved Objects**
  import/export.

## Maintenance

- When the stack version changes, **re-validate** request bodies against the **Kibana OpenAPI**
  for that version, not only the `current` Guide.
