# Asset Manifest Reference

Per **`docs/decisions.md` D-039** — `bootstrap.py` / `bootstrap-data.py` writes a manifest document to the target cluster so `teardown.py` has a fresh, authoritative inventory of every created resource. The manifest is **cluster-resident** and survives local file loss or re-generation.

**Teardown ordering and dispatch:** See `teardown-dispatch.md` for the canonical deletion order and asset-type → API path table.

---

## Manifest index

| Field | Value |
|-------|-------|
| Index name | `loom-manifests` (never prefixed — see `pipeline-constants.md`) |
| Document ID | normalized engagement ID (same as `demobuilder:<id>` tag value) |
| Prefix applied? | No — shared registry index; never prefixed, never deleted by teardown |

---

## Document Schema (D-039 — dynamic open-list format)

The schema uses **open lists** of typed asset records rather than hardcoded category keys. New asset types are added as `{"type": "...", "id": "..."}` entries — no schema migration required. Kibana assets are grouped by `space_id` so teardown can scope deletes correctly.

```json
{
  "engagement_id":      "cbfraud",
  "slug":               "2026citizens-ai",
  "bootstrap_version":  "1.0.0",
  "deployed_at":        "2026-04-22T14:30:00Z",
  "es_version":         "9.4.0",
  "es_url":             "https://demo-447f06.es.us-west2.gcp.elastic-cloud.com",
  "assets": {
    "elasticsearch": [
      {"type": "ilm_policy",          "id": "cb-fraud-claims-ilm"},
      {"type": "ingest_pipeline",     "id": "cb-fraud-enrich"},
      {"type": "component_template",  "id": "cb-fraud-claims-mappings"},
      {"type": "component_template",  "id": "cb-fraud-claims-settings"},
      {"type": "index_template",      "id": "cb-fraud-claims-template"},
      {"type": "index",               "id": "cb-fraud-claims"},
      {"type": "index",               "id": "cb-fraud-escalations"},
      {"type": "data_stream",         "id": "cb-fraud-transactions"},
      {"type": "enrich_policy",       "id": "cb-fraud-enrich-policy"},
      {"type": "inference_endpoint",  "id": "cb-elser", "task_type": "sparse_embedding"},
      {"type": "ml_job",              "id": "cb-fraud-volume-anomaly"},
      {"type": "ml_datafeed",         "id": "datafeed-cb-fraud-volume-anomaly"},
      {"type": "fleet_package",       "id": "kubernetes", "version": "1.62.0"},
      {"type": "fleet_agent_policy",  "id": "abc123-policy-id"}
    ],
    "kibana": {
      "by_space": {
        "2026citizens-ai": [
          {"type": "data_view",      "id": "cb-fraud-claims-*"},
          {"type": "dashboard",      "id": "a1b2c3d4-...", "name": "Citizens Fraud Operations"},
          {"type": "slo",            "id": "e5f6a7b8-...", "name": "cb-slo-debit-ack-rate"},
          {"type": "alerting_rule",  "id": "f9g0h1i2-...", "name": "Citizens — Debit SLO Burn Rate"},
          {"type": "connector",      "id": "j3k4l5m6-...", "name": "cb-fraud-index-connector"},
          {"type": "workflow",       "id": "n7o8p9q0-...", "name": "citizens-open-fraud-case"},
          {"type": "agent_tool",     "id": "citizens-claims-search",        "name": "citizens-claims-search"},
          {"type": "agent_tool",     "id": "citizens-esql-debit-at-risk",   "name": "citizens-esql-debit-at-risk"},
          {"type": "agent",          "id": "citizens-fraud-assistant-poc",  "name": "Fraud Assistant"},
          {"type": "siem_rule",      "id": "demo-citizens-wire-transfer-ml-anomaly", "name": "Citizens POC — Wire Transfer Volume Anomaly"}
        ],
        "default": [
          {"type": "tag", "id": "r1s2t3u4-...", "name": "demobuilder:cbfraud"}
        ]
      }
    }
  }
}
```

**Key properties:**
- **Open by design** — any new asset type is just a new `{"type": "...", "id": "..."}` entry with optional extra fields; no schema migration needed
- **Space-grouped Kibana assets** — `by_space` key makes multi-space engagements first-class; teardown iterates spaces and scopes each delete correctly
- **Extra metadata optional** — `name`, `task_type`, `version` etc. are carried as extra keys; no required envelope changes
- **Elasticsearch assets** — flat list (not space-grouped); ordered by creation sequence in bootstrap

---

## Python Helpers

```python
MANIFEST_INDEX = "loom-manifests"   # see pipeline-constants.md
_manifest: dict = {}   # in-memory accumulator — written to cluster after each step

def _manifest_init():
    global _manifest
    _manifest = {
        "engagement_id":    _engagement_id_for_tag(),
        "slug":             SLUG,
        "bootstrap_version": BOOTSTRAP_VERSION,
        "deployed_at":      __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "es_version":       "",    # filled in step 1
        "es_url":           ES_URL,
        "assets": {
            "elasticsearch": [],
            "kibana": {"by_space": {}}
        }
    }

def _manifest_add_es(asset_type: str, asset_id: str, **meta):
    """Append an Elasticsearch asset record. Extra kwargs become extra fields."""
    entry = {"type": asset_type, "id": asset_id, **meta}
    lst = _manifest["assets"]["elasticsearch"]
    if entry not in lst:
        lst.append(entry)
    _manifest_push()

def _manifest_add_kibana(space_id: str, asset_type: str, asset_id: str, **meta):
    """Append a Kibana asset record under its space."""
    entry = {"type": asset_type, "id": asset_id, **meta}
    by_space = _manifest["assets"]["kibana"]["by_space"]
    if space_id not in by_space:
        by_space[space_id] = []
    if entry not in by_space[space_id]:
        by_space[space_id].append(entry)
    _manifest_push()

def _manifest_push():
    """Upsert the current in-memory manifest to the cluster."""
    eng_id = _engagement_id_for_tag()
    try:
        es("POST", f"/{MANIFEST_INDEX}/_doc/{eng_id}", _manifest, ok=(200, 201))
    except Exception as exc:
        print(f"  ⚠  manifest write failed (non-fatal): {exc}")
```

### Usage — call after each successful resource creation

```python
# Elasticsearch assets
_manifest_add_es("ilm_policy",         p("fraud-claims-ilm"))
_manifest_add_es("ingest_pipeline",    p("fraud-enrich"))
_manifest_add_es("inference_endpoint", p("elser"), task_type="sparse_embedding")
_manifest_add_es("ml_job",             p("fraud-volume-anomaly"))
_manifest_add_es("ml_datafeed",        f"datafeed-{p('fraud-volume-anomaly')}")

# Kibana assets (always pass space_id)
_manifest_add_kibana(SPACE_ID, "dashboard",   dashboard_id, name="Citizens Fraud Operations")
_manifest_add_kibana(SPACE_ID, "slo",         slo_id,       name="cb-slo-debit-ack-rate")
_manifest_add_kibana(SPACE_ID, "agent",       agent_id,     name="Fraud Assistant")
_manifest_add_kibana(SPACE_ID, "workflow",    workflow_id,  name="citizens-open-fraud-case")
_manifest_add_kibana("default", "tag",        tag_id,       name=f"demobuilder:{_engagement_id_for_tag()}")
```

---

## Ensure Manifest Index Exists (call in step 1)

```python
def _ensure_manifest_index():
    try:
        es("HEAD", f"/{MANIFEST_INDEX}", ok=(200,))
    except RuntimeError:
        es("PUT", f"/{MANIFEST_INDEX}", {
            "settings": {"number_of_shards": 1, "number_of_replicas": 1},
            "mappings": {
                "dynamic": "true",
                "_meta": {"description": "Loom engagement asset manifests. Not a demo index — do not delete."}
            }
        }, ok=(200,))
```

---

## Teardown — Reading the Manifest

```python
def _load_manifest() -> dict | None:
    eng_id = _engagement_id_for_tag()
    try:
        resp = es("GET", f"/{MANIFEST_INDEX}/_doc/{eng_id}", ok=(200,))
        manifest = resp.get("_source", {})
        if manifest:
            print(f"  Manifest found (deployed {manifest.get('deployed_at','?')}, "
                  f"bootstrap v{manifest.get('bootstrap_version','?')})")
        return manifest
    except RuntimeError as e:
        if "404" in str(e):
            print("  ⚠  No manifest found — falling back to hardcoded inventory")
        else:
            print(f"  ⚠  Manifest read error ({e}) — falling back to hardcoded inventory")
        return None

def _build_inventory(manifest: dict | None) -> dict:
    """Build the teardown inventory from the manifest, or fall back to hardcoded."""
    if not manifest:
        return _hardcoded_inventory()
    assets = manifest.get("assets", {})
    return {
        "elasticsearch": assets.get("elasticsearch", []),
        "kibana": assets.get("kibana", {"by_space": {}}),
    }
```

See `teardown-dispatch.md` for the dispatch loop that consumes this inventory.

---

## Notes

- The `loom-manifests` index is excluded from ILM, snapshot policies, and teardown.
- Multiple engagements on the same cluster each have their own document (document ID = engagement_id).
- If bootstrap is re-run (idempotent re-deploy), the manifest is overwritten with the latest state. Old IDs from a previous partial run are replaced cleanly.
- **What the manifest does NOT replace:** `INDEX_PREFIX` safety gate, `DEMO_SLUG` and `.env` credential fields, `demobuilder:<id>` tags (the manifest complements tag-based discovery by providing IDs directly).
