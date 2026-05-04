# Teardown Dispatch Reference

**Loaded by:** `skills/demo-teardown/SKILL.md`

This file defines the canonical deletion ordering and the asset-type → API path dispatch table for `teardown.py`. The same table is used whether running in Python mode (direct API calls) or after `terraform destroy` (for any residual assets not managed by Terraform state).

---

## Macro Deletion Order

Delete resources in this order to respect dependency chains:

1. **Stop ML datafeeds** — must stop before deleting ML jobs
2. **Delete ML jobs** — after datafeeds stopped
3. **Delete Kibana objects** (see sub-order below) — before inference endpoints (agents may reference them)
4. **Delete inference endpoints** — after agents that reference them
5. **Delete data streams** — after pipelines/templates
6. **Delete indices** — after templates
7. **Delete index templates** — after component templates
8. **Delete component templates**
9. **Delete ingest pipelines** — after indices that reference them
10. **Delete enrich policies** — after pipelines
11. **Delete ILM policies** — ECH/self-managed only; skip on Serverless
12. **Verify** — confirm all expected resources are gone; report any residual

---

## Kibana Object Sub-Order

Within step 3, delete Kibana objects in this order (dependency-aware):

1. **Workflows** — agents may reference workflows; delete workflows first
2. **Agents** (Agent Builder agents)
3. **Agent Tools** (Agent Builder tools)
4. **Dashboards** — may reference data views; delete before data views
5. **Connectors**
6. **SLOs** — may reference alerting rules; delete before rules
7. **Alerting rules**
8. **SIEM detection rules**
9. **Cases** — delete before spaces (cases belong to a space)
10. **Data views**
11. **Tags**
12. **Space** — delete last, after all objects within it

---

## ES Asset Dispatch Table

```python
ES_TEARDOWN: dict[str, callable] = {
    "ilm_policy":         lambda a: es("DELETE", f"/_ilm/policy/{a['id']}"),
    "ingest_pipeline":    lambda a: es("DELETE", f"/_ingest/pipeline/{a['id']}"),
    "enrich_policy":      lambda a: es("DELETE", f"/_enrich/policy/{a['id']}"),
    "component_template": lambda a: es("DELETE", f"/_component_template/{a['id']}"),
    "index_template":     lambda a: es("DELETE", f"/_index_template/{a['id']}"),
    "index":              lambda a: es("DELETE", f"/{a['id']}"),
    "data_stream":        lambda a: es("DELETE", f"/_data_stream/{a['id']}"),
    "inference_endpoint": lambda a: es("DELETE", f"/_inference/{a['task_type']}/{a['id']}"),
    "ml_datafeed":        lambda a: (
                              es("POST",   f"/_ml/datafeeds/{a['id']}/_stop", ok=(200,)),
                              es("DELETE", f"/_ml/datafeeds/{a['id']}")),
    "ml_job":             lambda a: es("DELETE", f"/_ml/anomaly_detectors/{a['id']}"),
    "transform":          lambda a: (
                              es("POST",   f"/_transform/{a['id']}/_stop", ok=(200,)),
                              es("DELETE", f"/_transform/{a['id']}")),
    # New ES asset types: add handler here — no other changes required
}
```

---

## Kibana Asset Dispatch Table

```python
KB_TEARDOWN: dict[str, callable] = {
    "workflow":       lambda sp, a: kb(sp, "DELETE", f"/api/workflows/{a['id']}"),
    "agent":          lambda sp, a: kb(sp, "DELETE", f"/api/agent_builder/agents/{a['id']}"),
    "agent_tool":     lambda sp, a: kb(sp, "DELETE", f"/api/agent_builder/tools/{a['id']}"),
    "dashboard":      lambda sp, a: kb(sp, "DELETE", f"/api/saved_objects/dashboard/{a['id']}"),
    "connector":      lambda sp, a: kb(sp, "DELETE", f"/api/actions/connector/{a['id']}"),
    "slo":            lambda sp, a: kb(sp, "DELETE", f"/api/observability/slos/{a['id']}"),
    "alerting_rule":  lambda sp, a: kb(sp, "DELETE", f"/api/alerting/rule/{a['id']}"),
    "siem_rule":      lambda sp, a: kb(sp, "DELETE", f"/api/detection_engine/rules?rule_id={a['id']}"),
    "data_view":      lambda sp, a: kb(sp, "DELETE", f"/api/data_views/data_view/{a['id']}"),
    "tag":            lambda sp, a: kb(sp, "DELETE", f"/api/saved_objects/tag/{a['id']}"),
    # Cases: DELETE /api/cases?ids[]=<id> (query param, not path param; returns 204)
    "case":           lambda sp, a: kb(sp, "DELETE", f"/api/cases?ids[]={a['id']}", ok=(200, 204)),
    # kibana_space: space objects are in manifest["assets"]["kibana"]["kibana_spaces"]
    # Space is deleted last via a separate call — not in this dispatch table
    # New Kibana asset types: add handler here — no other changes required
}
```

**Notes on `case` handler:**
- The Cases delete API uses `DELETE /api/cases?ids[]=<id>` (query string, not path)
- Accepts multiple IDs: `DELETE /api/cases?ids[]=id1&ids[]=id2`
- Returns `200` with a list of deleted IDs on success, or `204` if none found
- The manifest key for cases is `kibana.cases` (added in bootstrap D-031 update)

---

## Teardown Loop Pattern

```python
# ── Elasticsearch assets ────────────────────────────────────────────────────
# Run in macro order: stop datafeeds first, then delete in dependency order
_ES_DELETE_ORDER = [
    "ml_datafeed", "ml_job",
    "inference_endpoint",
    "data_stream", "index",
    "index_template", "component_template",
    "ingest_pipeline", "enrich_policy",
    "ilm_policy",    # skip on serverless
    "transform",
]

for asset_type in _ES_DELETE_ORDER:
    handler = ES_TEARDOWN.get(asset_type)
    if not handler:
        continue
    for asset in [a for a in inventory["elasticsearch"] if a["type"] == asset_type]:
        if asset_type == "ilm_policy" and DEPLOYMENT_TYPE == "serverless":
            continue  # ILM not supported on serverless
        attempt_or_skip(
            f"delete {asset_type} {asset['id']}",
            lambda a=asset: handler(a)
        )

# ── Kibana assets ───────────────────────────────────────────────────────────
_KB_DELETE_ORDER = [
    "workflow", "agent", "agent_tool",
    "dashboard", "connector",
    "slo", "alerting_rule", "siem_rule",
    "data_view", "tag",
]

for space_id, assets in inventory["kibana"]["by_space"].items():
    for asset_type in _KB_DELETE_ORDER:
        handler = KB_TEARDOWN.get(asset_type)
        if not handler:
            continue
        for asset in [a for a in assets if a["type"] == asset_type]:
            attempt_or_skip(
                f"delete {asset_type} {asset['id']} (space: {space_id})",
                lambda sp=space_id, a=asset: handler(sp, a)
            )
    # Delete the space itself after all objects are gone
    if space_id != "default":
        attempt_or_skip(
            f"delete space {space_id}",
            lambda sp=space_id: kb("", "DELETE", f"/api/spaces/space/{sp}")
        )
```

---

## Terraform Mode

When `DEPLOY_MODE=terraform`, `terraform destroy` handles deletion of all Terraform-managed resources (indices, templates, pipelines, ML jobs, Kibana spaces, connectors, alerting rules, Agent Builder, Workflows, etc.).

`teardown.py` in Terraform mode only needs to:
1. Delete **data indices** with actual documents (not managed by Terraform — they were loaded by `bootstrap-data.py`)
2. Delete the **cluster manifest document** from `demobuilder-manifests/{engagement_id}`
3. Optionally offer to delete the entire Serverless project / ECH deployment via `cloud-manage-project`

The dispatch tables above are used in Python mode and as a fallback if Terraform state is lost.

---

## Safety Gates

- **`INDEX_PREFIX` blank on shared clusters** (`ech`, `self_managed`): warn and require `--confirm` flag before any wildcard-style index delete
- **Never delete** `.kibana*`, `.fleet*`, `.security*`, `demobuilder-manifests`, or any system index
- **`--dry-run`** mode: print all planned deletes without executing; always safe to run
- **`--keep-data`**: skip all index/data-stream deletion (useful when re-deploying over the same data)
