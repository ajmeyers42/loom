# Kibana API Registry

**Loaded by:** `skills/bolt-launch/SKILL.md`, `skills/wind-reset/SKILL.md`, `skills/bolt-spin/SKILL.md`, `skills/wind-pulse/SKILL.md`, `skills/weave-agent/SKILL.md`

This file is the **single source of truth** for Kibana API path patterns. Paths are version-sensitive but cluster-agnostic — they are appended to `KIBANA_URL` (or `KIBANA_URL + KIBANA_SPACE_PATH` for space-scoped calls).

**Authentication:** ALL Kibana API calls must use `KIBANA_API_KEY` (not `ES_API_KEY`). See `docs/decisions.md` D-016.

---

## Authentication Header

```python
KB_HEADERS = {
    "Authorization": f"ApiKey {KIBANA_API_KEY}",
    "Content-Type": "application/json",
    "kbn-xsrf": "loom",   # see pipeline-constants.md
}
```

---

## Feature Probe Endpoints

Run these immediately after provisioning or connecting to an existing cluster. Use `KIBANA_API_KEY`.

| Feature | Probe | 200 = enabled | 404 = not enabled |
|---------|-------|:---:|:---:|
| Agent Builder | `GET /api/agent_builder/agents` | ✅ | stop; do not build against this API |
| Agent Builder Skills catalog | `GET /api/agent_builder/skills` | ✅ | use tools-only config |
| Workflows | `GET /api/workflows` | ✅ | stop; do not build against this API |
| Kibana Streams | `GET /api/streams` | ✅ | not available on this version |

---

## Spaces

| Operation | Method | Path |
|-----------|--------|------|
| Create space | `POST` | `/api/spaces/space` |
| Get space | `GET` | `/api/spaces/space/{space_id}` |
| Update space | `PUT` | `/api/spaces/space/{space_id}` |
| Delete space | `DELETE` | `/api/spaces/space/{space_id}` |
| List spaces | `GET` | `/api/spaces/space` |

Space body must include `"solution"` and `"disabledFeatures": []` — see `docs/decisions.md` D-026.

---

## Dashboards API (versioned — use for all dashboard creation)

| Operation | Method | Path | Header |
|-----------|--------|------|--------|
| Create dashboard | `POST` | `{KIBANA_SPACE_PATH}/api/dashboards` | `Elastic-Api-Version: 2023-10-31` |
| Get dashboard | `GET` | `{KIBANA_SPACE_PATH}/api/dashboards/{id}` | `Elastic-Api-Version: 2023-10-31` |
| Update dashboard | `PUT` | `{KIBANA_SPACE_PATH}/api/dashboards/{id}` | `Elastic-Api-Version: 2023-10-31` |
| Delete dashboard | `DELETE` | `{KIBANA_SPACE_PATH}/api/dashboards/{id}` | `Elastic-Api-Version: 2023-10-31` |
| List dashboards | `GET` | `{KIBANA_SPACE_PATH}/api/dashboards` | `Elastic-Api-Version: 2023-10-31` |

**Always use this API — NOT the saved objects API — for dashboard creation.** The `Elastic-Api-Version: 2023-10-31` header is required; `"1"` or missing version returns 400.

**`PUT /api/dashboards/{id}` is a true upsert** — creates the dashboard if it doesn't exist, updates if it does. Use `PUT` (not `POST`) for all bootstrap deployments so you can control the stable ID. `POST` auto-generates an ID that cannot be specified.

**Create/update body (fields at the root level — NOT nested under `data`):**
```json
{
  "title": "Dashboard Title",
  "time_range": {"from": "now-2y", "to": "now"},
  "options": {
    "hide_panel_titles": false,
    "hide_panel_borders": false,
    "use_margins": true,
    "auto_apply_filters": true,
    "sync_colors": false,
    "sync_cursor": true,
    "sync_tooltips": false
  },
  "panels": [
    {
      "id": "<short-uuid>",
      "type": "vis",
      "grid": {"x": 0, "y": 0, "w": 24, "h": 8},
      "config": {"hide_title": false, "ref_id": "<lens-saved-object-id>"}
    },
    {
      "id": "<uuid>",
      "type": "slo_overview",
      "grid": {"x": 24, "y": 0, "w": 24, "h": 8},
      "config": {
        "overview_mode": "single",
        "slo_id": "<slo-id>",
        "slo_instance_id": "*",
        "remote_name": ""
      }
    }
  ],
  "pinned_panels": []
}
```

**Grid:** 48 columns wide. Common widths: full=48, half=24, third=16, quarter=12, small-metric=8.

**Panel types — Dashboards API support matrix (confirmed via cluster agent, 9.4 ECH):**
| `type` | Supported by Dashboards API | Purpose | Key `config` fields |
|---|---|---|---|
| `vis` | ✅ Yes | Lens saved object reference | `ref_id` (Lens saved object ID), `hide_title` |
| `slo_overview` | ✅ Yes | SLO embeddable | `overview_mode`, `slo_id`, `slo_instance_id`, `remote_name` |
| `markdown` | ✅ Yes | Text/markdown content panel | `content` (markdown string), `openLinksInNewTab` |
| `legacy_vis` | ❌ No — stripped on import | Old markdown/text viz framework | Use `markdown` type instead |
| `links` | ❌ No — stripped on import | Navigation link panels | Use `markdown` with URL instead |

**`ref_id` resolves to a `lens` saved object ID** — Kibana maps this to the `references` array internally. No `references` array needed in the PUT request.

**Markdown panel format (for section headers, callouts):**
```json
{
  "id": "<uuid>",
  "type": "markdown",
  "grid": {"x": 0, "y": 17, "w": 48, "h": 3},
  "config": {
    "content": "### Section Header",
    "openLinksInNewTab": false
  }
}
```

**When to use Dashboards API vs Saved Objects `_import`:**
| Scenario | Approach |
|---|---|
| Bootstrap: programmatic dashboard creation with Lens + SLO panels | `PUT /api/dashboards/{id}` (Dashboards API) |
| Terraform IaC: deploying dashboard NDJSON files | `elasticstack_kibana_import_saved_objects` resource |
| Dashboards with `legacy_vis`, `links`, or unknown panel types | Saved Objects `_export` → `_import` |
| Exact 1:1 copy preserving all panel types | Saved Objects `_export` / `_import` |

---

## Lens Visualizations (saved objects API)

| Operation | Method | Path |
|-----------|--------|------|
| Create/upsert Lens viz | `POST` | `{KIBANA_SPACE_PATH}/api/saved_objects/lens/{id}?overwrite=true` |
| Get Lens viz | `GET` | `{KIBANA_SPACE_PATH}/api/saved_objects/lens/{id}` |
| Delete Lens viz | `DELETE` | `{KIBANA_SPACE_PATH}/api/saved_objects/lens/{id}` |
| Find Lens vizzes | `GET` | `{KIBANA_SPACE_PATH}/api/saved_objects/_find?type=lens` |

**Create/upsert body (do NOT include `id`, `type`, `namespaces`, `migrationVersion`, `coreMigrationVersion`, `updated_at`, `version`, `managed`):**
```json
{
  "attributes": {
    "title": "My Metric",
    "description": "",
    "visualizationType": "lnsMetric",
    "state": {
      "datasourceStates": {
        "formBased": {
          "layers": {
            "main": {
              "indexPatternId": "<data-view-id>",
              "columns": {
                "col1": {
                  "label": "Count",
                  "dataType": "number",
                  "operationType": "count",
                  "isBucketed": false,
                  "sourceField": "Records",
                  "params": {}
                }
              },
              "columnOrder": ["col1"]
            }
          }
        }
      },
      "visualization": {
        "layers": [{"layerId": "main", "layerType": "data", "metricAccessor": "col1", "color": "#1EA593"}]
      },
      "query": {"query": "", "language": "kuery"},
      "filters": []
    }
  },
  "references": [
    {"type": "index-pattern", "id": "<data-view-id>", "name": "indexpattern-datasource-layer-main"}
  ]
}
```

**Reference `name` convention:** `"indexpattern-datasource-layer-{layerId}"` — must match the key in `datasourceStates.formBased.layers`.

**`formBased` aggregation compatibility on 9.4 ECH (confirmed via live cluster):**
| Operation | Status |
|---|---|
| `count` | ✅ Works |
| `sum`, `avg`, `min`, `max` | ❌ `TypeError: toExpression` crash at render — use `textBased` ES\|QL instead |

**ES\|QL (`textBased`) Lens layer shape (confirmed on 9.4 ECH live cluster):**
```json
{
  "attributes": {
    "visualizationType": "lnsMetric",
    "state": {
      "datasourceStates": {
        "textBased": {
          "layers": {
            "main": {
              "index": "<data-view-id>",
              "query": {"esql": "FROM tf-project-risk-scores | STATS val = SUM(cost_usd)"},
              "columns": [{"columnId": "col1", "fieldName": "val", "meta": {"type": "number"}}]
            }
          }
        }
      },
      "visualization": {
        "layers": [{"layerId": "main", "layerType": "data", "metricAccessor": "col1"}]
      },
      "query": {"query": "", "language": "kuery"},
      "filters": [],
      "adHocDataViews": {}
    }
  },
  "references": [{"type": "index-pattern", "id": "<data-view-id>", "name": "indexpattern-datasource-current-indexpattern"}]
}
```

**`textBased` ES\|QL rules (all confirmed via live cluster probe on 9.4 ECH):**
- `layer.index` **must** be the **data view ID** — NOT the raw index name. Missing/wrong ID = "no data view attached" error.
- `references[0].name` **must** be `"indexpattern-datasource-current-indexpattern"` (not the layer key). Confirmed by exporting working vizzes from cluster.
- Column `fieldName` must match the alias used in the ES\|QL `STATS` clause (e.g., `STATS val = SUM(x)` → `fieldName: "val"`).
- ES\|QL `WHERE` uses `==` not `:` — do NOT do `kuery.replace(":", "==")` (corrupts values like `loom_tf`). Only replace the operator ` : ` (with spaces) → ` == `.

**Dashboard time picker binding for ES\|QL vizzes (MANDATORY for non-`@timestamp` indices):**

Kibana applies the dashboard time filter to ES\|QL visualizations by substituting `?_tstart` and `?_tend` named parameters with ISO-8601 bounds. For indices that do **not** have `@timestamp`:
- The query MUST include `WHERE {time_field} >= ?_tstart AND {time_field} <= ?_tend` explicitly.
- Without this, Kibana silently tries `@timestamp`, finds nothing, returns zero rows — even though data exists.
- Kibana injects full ISO-8601 values (e.g., `"2024-05-05T00:00:00.000Z"`), so the date field must be a `date` type.

```esql
FROM tf-project-risk-scores
| WHERE updated_at >= ?_tstart AND updated_at <= ?_tend
| STATS val = AVG(risk_score) BY site_id
| SORT val DESC
| LIMIT 10
```

For indices **with** `@timestamp` (`tf-deliverables`, `tf-agent-sessions`, `tf-ml-anomaly-results`): Kibana uses the data view's configured time field automatically — no explicit `?_tstart`/`?_tend` needed in the query.

**Non-`@timestamp` indices in this engagement and their time fields:**
| Index | Time field | Data view time field |
|---|---|---|
| `tf-project-risk-scores` | `updated_at` | `updated_at` |
| `tf-entity-store` | `last_updated` | `last_updated` |
| `tf-portfolio-projects` | `updated_at` | `updated_at` |

**Seed data requirement (D-044):** Every index used by a time-filtered dashboard MUST have a populated date field at seed time. For project/entity indices: populate `updated_at` (or equivalent) to represent when the record was last scored/updated — NOT derived from the project start date. Use the seeding timestamp (`_NOW_ISO`) for active records so they always fall within the demo time range.

**Field population requirement (D-044):** Every field referenced in a `WHERE`, `STATS`, `BY`, `SUM`, `AVG`, `MAX`, or `MIN` clause across all visualization ES|QL queries MUST be non-null in every document. A null value is invisible to ES|QL and produces `Unknown column` errors. Derived fields (e.g., `risk_label` from `risk_score`) must be computed and stored at seed time — never left null. After seeding, verify with:

```python
# Validation pattern — run after every _bulk_index call
def assert_field_populated(index, field):
    total = es_count(index)
    populated = es_count(index, query={"exists": {"field": field}})
    assert populated == total, f"SEED VALIDATION FAIL: {index}.{field} null in {total-populated}/{total} docs"
```

---

## Saved Objects Import / Export

| Operation | Method | Path | Notes |
|-----------|--------|------|-------|
| Import NDJSON | `POST` | `{KIBANA_SPACE_PATH}/api/saved_objects/_import?overwrite=true` | Multipart form; `file` field; strip `migrationVersion` / `coreMigrationVersion` / `updated_at` / `version` / `managed` / `namespaces` before import |
| Export objects | `POST` | `{KIBANA_SPACE_PATH}/api/saved_objects/_export` | `{"objects":[...],"includeReferencesDeep":true,"excludeExportDetails":true}` |

**Export + clean for re-import:**
```python
strip_keys = {'migrationVersion','coreMigrationVersion','typeMigrationVersion',
              'updated_at','created_at','version','managed','namespaces'}
# Strip these from each line before storing as a deployable NDJSON artifact
```

**Terraform — NDJSON import resource** (`elasticstack_kibana_import_saved_objects`):
```hcl
resource "elasticstack_kibana_import_saved_objects" "dashboards" {
  space_id      = var.space_id
  overwrite     = true
  file_contents = file("${path.module}/kibana-objects/2026thermopm-dashboards-clean.ndjson")
}
```
This is the **recommended Terraform path** for dashboards, Lens vizzes, and data views. The NDJSON file should be exported from a validated cluster and stored in `deploy/kibana-objects/` as a deployment artifact. Strip migration/version metadata before storing.

---

## Data Views

| Operation | Method | Path |
|-----------|--------|------|
| Create data view | `POST` | `{KIBANA_SPACE_PATH}/api/data_views/data_view` |
| Get data view | `GET` | `{KIBANA_SPACE_PATH}/api/data_views/data_view/{id}` |
| Update data view | `PUT` | `{KIBANA_SPACE_PATH}/api/data_views/data_view/{id}` |
| Delete data view | `DELETE` | `{KIBANA_SPACE_PATH}/api/data_views/data_view/{id}` |
| List data views | `GET` | `{KIBANA_SPACE_PATH}/api/data_views` |

### Data View Time Semantics — Architectural Rule

**A data view is a time-axis declaration, not just an index alias.**

The `timeFieldName` on a data view determines which date field the dashboard time picker controls for any `formBased` (aggregation) layer that references it. Different visualizations over the same index can — and should — have different time semantics when the date fields carry different meanings:

| Date field | Semantic meaning | Example visualization |
|---|---|---|
| `updated_at` | When was this record last scored/refreshed? | "Current risk score by project" |
| `start_date` | When did the project begin? | "Projects opened this quarter" |
| `target_completion` | When is the work due? | "Deadlines in the next 90 days" |
| `@timestamp` | When did this event occur? | "Agent session volume over time" |

**Rule:** Create one data view per *(index, time-semantic)* pair, not one per index. Name secondary data views `{index-pattern}-{semantic}` to make intent explicit (e.g., `tf-portfolio-projects-deadline` with `timeFieldName: target_completion`).

**For ES|QL (`textBased`) layers:** The data view's `timeFieldName` does NOT inject a time filter automatically. You must include `WHERE {field} >= ?_tstart AND {field} <= ?_tend` explicitly in the query. Kibana substitutes `?_tstart`/`?_tend` with ISO-8601 bounds from the dashboard time picker at render time. This is MORE flexible than `formBased` — each query can use a different field regardless of what the data view declares.

**For `formBased` (aggregation) layers:** `timeFieldName` controls the automatic time filter. No `WHERE` clause needed.

**Consequence:** If you create a single data view for an index and point it at `updated_at`, then a `formBased` visualization that should filter by `start_date` will silently use the wrong field. The dashboard time picker will appear to work but will return the wrong slice of data. Always align the data view's `timeFieldName` to the **semantic intent of the visualizations that will use it**.

**Seed data rule:** Every index with a `formBased` or ES|QL visualization on a time-filtered dashboard MUST have a populated value in the relevant date field at seed time. A null `updated_at` means the document is invisible when the dashboard time picker is active.

### Create body

```json
{
  "data_view": {
    "id": "{stable-uuid}",
    "title": "{index-pattern}",
    "timeFieldName": "{date-field}",
    "name": "{human-readable-label}"
  }
}
```

### Existing data views for this engagement

| Data view ID (stable) | Index | `timeFieldName` | Semantic |
|---|---|---|---|
| `dv-tf-deliverables` | `tf-deliverables` | `@timestamp` | Event creation time |
| `dv-tf-portfolio-projects` | `tf-portfolio-projects` | `updated_at` | Last status update |
| `dv-tf-project-risk-scores` | `tf-project-risk-scores` | `updated_at` | Last scoring run |
| `dv-tf-entity-store` | `tf-entity-store` | `last_updated` | Entity last seen |
| `dv-tf-agent-sessions` | `tf-agent-sessions` | `@timestamp` | Session event time |
| `dv-tf-slo-metrics` | `tf-slo-metrics` | `@timestamp` | SLO sample time |
| `dv-tf-ml-anomaly-results` | `tf-ml-anomaly-results` | `@timestamp` | Anomaly detection time |
| `dv-tf-lessons-learned` | `tf-lessons-learned` | `date` | Lesson recorded date |
| `dv-tf-issue-log` | `tf-issue-log` | `raised_date` | Issue raised date |

**Additional data views to create when needed (not yet created):**

| Future data view ID | Index | `timeFieldName` | When to add |
|---|---|---|---|
| `dv-tf-portfolio-projects-deadline` | `tf-portfolio-projects` | `target_completion` | Any viz filtering by project deadline |
| `dv-tf-portfolio-projects-start` | `tf-portfolio-projects` | `start_date` | Any viz filtering by project open date |
| `dv-tf-deliverables-planned` | `tf-deliverables` | `planned_completion_date` | Any viz filtering by planned vs. actual delivery |

---

## Connectors (Actions)

| Operation | Method | Path |
|-----------|--------|------|
| Create connector | `POST` | `{KIBANA_SPACE_PATH}/api/actions/connector` |
| Get connector | `GET` | `{KIBANA_SPACE_PATH}/api/actions/connector/{id}` |
| Update connector | `PUT` | `{KIBANA_SPACE_PATH}/api/actions/connector/{id}` |
| Delete connector | `DELETE` | `{KIBANA_SPACE_PATH}/api/actions/connector/{id}` |
| List connectors | `GET` | `{KIBANA_SPACE_PATH}/api/actions/connectors` |
| Test connector | `POST` | `{KIBANA_SPACE_PATH}/api/actions/connector/{id}/_execute` |

**⚠ `.cases` connector is UI-only (confirmed 9.4):** The connector type `.cases` CANNOT be created via the REST API. It is auto-provisioned by Kibana when a solution space is created. Any `POST /api/actions/connector` with `connector_type_id: ".cases"` will return `400`. To wire Cases actions to alert rules: Kibana → Stack Management → Rules → [rule] → Edit → Add action → Kibana Cases.

**`.webhook` headers format:** The `config.headers` field must be a plain JSON object (`{"Content-Type": "application/json"}`), NOT an array of `{key, value}` pairs (which returns `400`). Confirmed via live API probe on 9.4 ECH.

---

## Alerting Rules

| Operation | Method | Path |
|-----------|--------|------|
| Create rule | `POST` | `{KIBANA_SPACE_PATH}/api/alerting/rule` |
| Get rule | `GET` | `{KIBANA_SPACE_PATH}/api/alerting/rule/{id}` |
| Update rule | `PUT` | `{KIBANA_SPACE_PATH}/api/alerting/rule/{id}` |
| Delete rule | `DELETE` | `{KIBANA_SPACE_PATH}/api/alerting/rule/{id}` |
| Enable rule | `POST` | `{KIBANA_SPACE_PATH}/api/alerting/rule/{id}/_enable` |
| Disable rule | `POST` | `{KIBANA_SPACE_PATH}/api/alerting/rule/{id}/_disable` |
| Find rules | `GET` | `{KIBANA_SPACE_PATH}/api/alerting/rules/_find` |

**⚠ Rule actions in 9.x require `group` + `frequency` (confirmed 9.4):** Every action object must include:
- `"group"`: the rule-type-specific action group name — NOT the generic `"default"`. Common values:
  - `.es-query` rules: `"query matched"` (fires on threshold breach), `"recovered"` (fires on recovery)
  - `slo.rules.burnRate` rules: `"slo.rules.burnRate.alert"`, `"slo.rules.burnRate.warning"`
  - Check `GET /api/alerting/rule_types` → `action_groups[].id` for any other rule type
- `"frequency"`: required object — `{"notifyWhen": "onActiveAlert", "throttle": null, "summary": false}`

A rule creation with `"group": "default"` or missing `"frequency"` returns `400: Invalid action groups: default / Actions missing frequency parameters`.

```json
{
  "id": "<connector_id>",
  "group": "query matched",
  "frequency": {
    "notifyWhen": "onActiveAlert",
    "throttle": null,
    "summary": false
  },
  "params": { "body": "..." }
}
```

---

## SLOs (Observability)

| Operation | Method | Path |
|-----------|--------|------|
| Create SLO | `POST` | `{KIBANA_SPACE_PATH}/api/observability/slos` |
| Get SLO | `GET` | `{KIBANA_SPACE_PATH}/api/observability/slos/{id}` |
| Update SLO | `PUT` | `{KIBANA_SPACE_PATH}/api/observability/slos/{id}` |
| Delete SLO | `DELETE` | `{KIBANA_SPACE_PATH}/api/observability/slos/{id}` |

---

## Agent Builder

| Operation | Method | Path |
|-----------|--------|------|
| Create agent | `POST` | `{KIBANA_SPACE_PATH}/api/agent_builder/agents` |
| Get agent | `GET` | `{KIBANA_SPACE_PATH}/api/agent_builder/agents/{id}` |
| Update agent | `PUT` | `{KIBANA_SPACE_PATH}/api/agent_builder/agents/{id}` |
| Delete agent | `DELETE` | `{KIBANA_SPACE_PATH}/api/agent_builder/agents/{id}` |
| List agents | `GET` | `{KIBANA_SPACE_PATH}/api/agent_builder/agents` |
| Create tool | `POST` | `{KIBANA_SPACE_PATH}/api/agent_builder/tools` |
| Get tool | `GET` | `{KIBANA_SPACE_PATH}/api/agent_builder/tools/{id}` |
| Update tool | `PUT` | `{KIBANA_SPACE_PATH}/api/agent_builder/tools/{id}` |
| Delete tool | `DELETE` | `{KIBANA_SPACE_PATH}/api/agent_builder/tools/{id}` |
| List skills catalog | `GET` | `{KIBANA_SPACE_PATH}/api/agent_builder/skills` |

**PUT update rule (D-025):** Send only `description`, `configuration`, and optional `labels`. Do NOT include `id`, `type`, `readonly`, or `created_by` (immutable/read-only).

**⚠ Tools are space-scoped (confirmed 9.4):** Agent Builder tools created in space A are NOT visible in space B. Always create both the tool and agent in the same target space.

**`configuration.tools` array format (confirmed 9.4):** Must be `[{"tool_ids": ["id1", "id2", ...]}]` — NOT a flat array of ID strings. A flat string array returns `400`. Confirmed via live API probe.

**Agent ID convention:** Agent IDs must be lowercase-with-hyphens (e.g. `demo-search-agent`). Mixed-case IDs are rejected by the API.

**`labels` vs Kibana tags:** Agent objects use a `labels` field (string array, e.g. `["loom", "thermo-fisher-pm"]`) — this is **NOT** the same as Kibana saved-object tags. Do not use the tags API for agents.

**`visibility`:** Always set `"visibility": "public"` on demo agents. Omitting it defaults to private/internal — agent will not appear in the chat UI.

**`enable_elastic_capabilities`:** Set `false` for custom demo agents (prevents the built-in Elastic capabilities from overriding the demo persona). The system `elastic-ai-agent` has it `true` by default.

**`avatar_symbol`:** Two-character string, e.g. `"fr"`. Optional but improves UI appearance.

**D-029 — `skill_ids` probe (MANDATORY before generating agent configuration):**
`skill_ids` = platform skills (capabilities like data-exploration); `tool_ids` = custom tools + `platform.core.*` built-ins. These are separate concerns and BOTH must be configured.

```python
# Step in bootstrap-data.py — run BEFORE creating agents
r = kb("GET", f"{space_path}/api/agent_builder/skills", ok=(200, 404))
if r is None or (isinstance(r, int) and r == 404):
    platform_skill_ids = []    # skills catalog not available; tools-only mode
else:
    available = {s["id"] for s in r.get("skills", [])}
    wanted    = {"data-exploration", "visualization-creation", "case-management",
                 "entity-analytics", "graph-creation", "workflow-authoring",
                 "search.keyword-search", "search.rag-chatbot", "search.vector-hybrid-search"}
    platform_skill_ids = list(available & wanted)

agent_body = {
    "id":          agent_id,
    "type":        "chat",
    "name":        agent_name,
    "description": agent_description,
    "labels":      ["loom", engagement_id],
    "avatar_symbol": "db",
    "visibility":  "public",
    "configuration": {
        "instructions":              system_prompt,
        "tools":                     [{"tool_ids": [custom_tool_id, "platform.core.execute_esql", "platform.core.search"]}],
        "skill_ids":                 platform_skill_ids,  # ALWAYS include; set [] if catalog unavailable
        "enable_elastic_capabilities": False,
        "workflow_ids":              [],
    }
}
kb("POST", f"{space_path}/api/agent_builder/agents", agent_body, ok=(200, 201))
```

**`configuration.skill_ids` omission causes silent capability gap:** Omitting `skill_ids` from the agent body does NOT return a 400 — it succeeds but silently disables platform skills. Always explicitly set it to `[]` or the probed list. Never omit it.

---

## Workflows

| Operation | Method | Path |
|-----------|--------|------|
| Create workflow | `POST` | `{KIBANA_SPACE_PATH}/api/workflows` |
| Get workflow | `GET` | `{KIBANA_SPACE_PATH}/api/workflows/{id}` |
| Update workflow | `PUT` | `{KIBANA_SPACE_PATH}/api/workflows/{id}` |
| Delete workflow | `DELETE` | `{KIBANA_SPACE_PATH}/api/workflows/{id}` |
| List all workflows | `GET` | `{KIBANA_SPACE_PATH}/api/workflows` |
| Execute workflow | `POST` | `{KIBANA_SPACE_PATH}/api/workflows/{id}/_run` |

**⚠ API endpoint (confirmed 9.4):** The correct endpoint is `/api/workflows`. The old endpoint `/api/workchat/workflows` returns 404 on 9.4 and should NOT be used.

**Create request body format:** `{"workflows": [{"yaml": "<yaml string>"}]}` — NOT a plain JSON object. The YAML string must use `triggers:` (plural array), NOT `trigger:` (singular). Response is `{"created": [...], "failed": [...]}`.

**YAML `valid: true` check:** Always check `created[0].valid == true` after creation. `valid: false` means the YAML was stored but could not be parsed — usually caused by `trigger:` (singular) instead of `triggers:` or wrong input format.

**Stale read warning:** Capture `id` from the POST response directly. Do not immediately GET after create — may return stale data or 404 for up to a few seconds.

---

## SIEM Detection Rules

| Operation | Method | Path |
|-----------|--------|------|
| Create rule | `POST` | `{KIBANA_SPACE_PATH}/api/detection_engine/rules` |
| Get rule | `GET` | `{KIBANA_SPACE_PATH}/api/detection_engine/rules?rule_id={rule_id}` |
| Update rule | `PATCH` | `{KIBANA_SPACE_PATH}/api/detection_engine/rules` |
| Delete rule | `DELETE` | `{KIBANA_SPACE_PATH}/api/detection_engine/rules?rule_id={rule_id}` |
| Install prebuilt rules | `PUT` | `{KIBANA_SPACE_PATH}/api/detection_engine/rules/prepackaged` |
| Find rules | `GET` | `{KIBANA_SPACE_PATH}/api/detection_engine/rules/_find` |

**D-032:** Never PUT/PATCH Elastic-managed rules with `immutable: true`. Clone them with a `demo-` prefixed `rule_id`.

---

## Cases

| Operation | Method | Path |
|-----------|--------|------|
| Configure cases | `POST` | `{KIBANA_SPACE_PATH}/api/cases/configure` |
| Get case config | `GET` | `{KIBANA_SPACE_PATH}/api/cases/configure` |
| Create case | `POST` | `{KIBANA_SPACE_PATH}/api/cases` |
| Update case | `PATCH` | `{KIBANA_SPACE_PATH}/api/cases` |
| Get case | `GET` | `{KIBANA_SPACE_PATH}/api/cases/{id}` |
| Find cases | `POST` | `{KIBANA_SPACE_PATH}/api/cases/_find` |
| Add comment | `POST` | `{KIBANA_SPACE_PATH}/api/cases/{id}/comments` |
| Delete cases | `DELETE` | `{KIBANA_SPACE_PATH}/api/cases?ids[]={id}` |

**⚠ `configure` prerequisite (confirmed 9.4):** `POST /api/cases` returns `400` unless `POST /api/cases/configure` has been called first for the target `owner`. Call it once per owner (`observability`, `securitySolution`, `cases`) before creating any cases. `GET /api/cases/configure` returns `[]` (empty array) if never configured — NOT a 404.

**Configure body:** `{"connector": {"id": "none", "name": "none", "type": ".none", "fields": null}, "closure_type": "close-by-user", "owner": "<owner>"}`. The `".none"` type is valid and means "no external connector attached".

**`owner` valid values:** `observability`, `securitySolution`, `cases`. Must match the solution area of the space where the case lives.

**⚠ `status` is read-only on POST (confirmed 9.4):** `POST /api/cases` does NOT accept a `status` field — returns `400: invalid keys "status"`. Cases are always created as `open`. To set `in-progress` or `closed`, PATCH immediately after creation using the `version` from the POST response:

```python
resp     = kb("POST", "/api/cases", {k: v for k, v in body.items() if k != "status"}, ok=(200, 201))
case_id  = resp.get("id", "")
case_ver = resp.get("version", "")
if desired_status != "open" and case_id and case_ver:
    kb("PATCH", "/api/cases", {
        "cases": [{"id": case_id, "version": case_ver, "status": desired_status}]
    }, ok=(200,))
```

**Delete cases API:** Uses query param `ids[]=<id>`, not a path param. `DELETE /api/cases?ids[]=abc123` (204 on success).

---

## Kibana Tags

| Operation | Method | Path |
|-----------|--------|------|
| Create tag | `POST` | `{KIBANA_SPACE_PATH}/api/saved_objects/tag` |
| Get tag | `GET` | `{KIBANA_SPACE_PATH}/api/saved_objects/tag/{id}` |
| Delete tag | `DELETE` | `{KIBANA_SPACE_PATH}/api/saved_objects/tag/{id}` |
| Find tags | `GET` | `{KIBANA_SPACE_PATH}/api/saved_objects/_find?type=tag` |

---

## Kibana Status / Version

| Operation | Method | Path |
|-----------|--------|------|
| Kibana status | `GET` | `/api/status` |
| Kibana version | `GET` | `/api/status` → `version.number` |

---

## Space-Scoping Notes

- `KIBANA_SPACE_PATH` is set to `/s/{DEMO_SLUG}` for per-engagement spaces, or empty string for the default space.
- Paths prefixed with `{KIBANA_SPACE_PATH}` must NOT include the prefix when `KIBANA_SPACE_PATH` is empty.
- All Agent Builder, Workflow, saved object, SLO, alerting, and connector operations are space-scoped.
- Space CREATE and DELETE operations are not space-scoped (use `/api/spaces/space` directly).

---

## `attempt_or_skip` — When to Skip vs. When to Halt

**Critical rule: `4xx` responses do NOT all mean "feature absent". HTTP status determines whether to skip or halt:**

| HTTP status | Meaning | Action |
|---|---|---|
| `404` on a feature **probe** (GET `/api/agent_builder/agents`, GET `/api/workflows`) | Feature not available on this cluster/version | **Skip gracefully** — log warning and continue |
| `403` on a feature **probe** | Feature exists but access denied | **Skip gracefully** — log warning, note permission gap |
| `400` on an **asset creation** (POST alerting rule, POST cases, POST Agent Builder) | Our payload is wrong | **HALT — fix the payload**, do NOT skip |
| `400` on a `.cases` connector create | `.cases` connector is UI-only by design | **Expected** — skip and log MANUAL step |

```python
def attempt_or_skip(label: str, fn) -> bool:
    """
    Use ONLY for optional tech-preview feature probes (GET 404/403).
    NEVER use to swallow 400 errors on in-scope asset creation.
    Returns True if succeeded, False if skipped.
    """
    try:
        fn()
        return True
    except APIError as e:
        if e.status in (404, 403):
            print(f"⚠ {label}: feature not available on this cluster — skipped")
            return False
        # 400 = bad payload — re-raise, do NOT silently skip
        raise

# Correct usage:
# attempt_or_skip("Workflows", lambda: create_workflow(...))  ← optional feature probe

# WRONG — never wrap in-scope asset creation:
# attempt_or_skip("Alerting rule", lambda: create_rule(...))  ← DO NOT DO THIS
# attempt_or_skip("Cases", lambda: create_case(...))          ← DO NOT DO THIS
```

**In-scope assets that must NEVER be wrapped in `attempt_or_skip`:**
- Alerting rules (if script includes alert scene)
- Cases (if script includes case scene)
- Agent Builder agents/tools (if script includes AI agent scene)
- SLOs (if script includes observability scene)
- Dashboards import (always in scope if dashboards exist)

If a `400` occurs on these, the bootstrap run must halt with a clear error message and the specific API response body, not silently log and continue.
