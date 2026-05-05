# Kibana API Registry

**Loaded by:** `skills/demo-deploy/SKILL.md`, `skills/demo-teardown/SKILL.md`, `skills/demo-cloud-provision/SKILL.md`, `skills/demo-status/SKILL.md`, `skills/demo-kibana-agent-design/SKILL.md`

This file is the **single source of truth** for Kibana API path patterns. Paths are version-sensitive but cluster-agnostic — they are appended to `KIBANA_URL` (or `KIBANA_URL + KIBANA_SPACE_PATH` for space-scoped calls).

**Authentication:** ALL Kibana API calls must use `KIBANA_API_KEY` (not `ES_API_KEY`). See `docs/decisions.md` D-016.

---

## Authentication Header

```python
KB_HEADERS = {
    "Authorization": f"ApiKey {KIBANA_API_KEY}",
    "Content-Type": "application/json",
    "kbn-xsrf": "demobuilder",   # see pipeline-constants.md
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

## Saved Objects Import

| Operation | Method | Path | Notes |
|-----------|--------|------|-------|
| Import NDJSON | `POST` | `{KIBANA_SPACE_PATH}/api/saved_objects/_import?overwrite=true` | Multipart form; `file` field; strip `migrationVersion` / `coreMigrationVersion` before import |
| Export objects | `POST` | `{KIBANA_SPACE_PATH}/api/saved_objects/_export` | |

---

## Data Views

| Operation | Method | Path |
|-----------|--------|------|
| Create data view | `POST` | `{KIBANA_SPACE_PATH}/api/data_views/data_view` |
| Get data view | `GET` | `{KIBANA_SPACE_PATH}/api/data_views/data_view/{id}` |
| Update data view | `PUT` | `{KIBANA_SPACE_PATH}/api/data_views/data_view/{id}` |
| Delete data view | `DELETE` | `{KIBANA_SPACE_PATH}/api/data_views/data_view/{id}` |
| List data views | `GET` | `{KIBANA_SPACE_PATH}/api/data_views` |

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

**PUT update rule (D-025):** Send only `description`, `configuration`, and optional `tags`. Do NOT include `id` or `type` (immutable).

**⚠ Tools are space-scoped (confirmed 9.4):** Agent Builder tools created in space A are NOT visible in space B. Always create both the tool and agent in the same target space.

**`configuration.tools` array format (confirmed 9.4):** Must be `[{"tool_ids": ["id1", "id2", ...]}]` — NOT a flat array of ID strings. A flat string array returns `400`. Confirmed via live API probe.

**Agent ID convention:** Agent IDs must be lowercase-with-hyphens (e.g. `demo-search-agent`). Mixed-case IDs are rejected by the API.

**D-029 — `skill_ids` probe (MANDATORY before generating agent configuration):**
`skill_ids` = platform skills (capabilities like data-exploration); `tool_ids` = custom tools + `platform.core.*` built-ins. These are separate concerns and BOTH must be configured.

```python
# Step in bootstrap-data.py — run BEFORE creating agents
r = kb("GET", f"{space_path}/api/agent_builder/skills", ok=(200, 404))
if r is None or (isinstance(r, int) and r == 404):
    platform_skill_ids = []    # skills catalog not available; tools-only mode
else:
    available = {s["id"] for s in r.get("skills", [])}
    wanted    = {"data-exploration", "visualization-creation", "case-management"}
    platform_skill_ids = list(available & wanted)

agent_body = {
    "id":   agent_id,
    "name": agent_name,
    "configuration": {
        "instructions": system_prompt,
        "tools": [{"tool_ids": [custom_tool_id, "platform.core.execute_esql", "platform.core.search"]}],
        "skill_ids": platform_skill_ids,    # ALWAYS include; set [] if catalog unavailable
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
