# Elasticsearch Mapping Patterns — Demo Reference

## Field Type Quick Reference

| Use case | Field type | Notes |
|---|---|---|
| IDs, codes, tags | `keyword` | Never `text` for things you filter or aggregate on |
| Free-text search | `text` | Always add `.keyword` sub-field if you might aggregate |
| ELSER semantic search | `semantic_text` | Requires `inference_id` pointing to deployed endpoint |
| Timestamps | `date` | Use `"format": "strict_date_optional_time||epoch_millis"` |
| Counts, quantities | `integer` or `long` | Prefer `integer` unless values exceed 2^31 |
| Rates, percentages | `float` or `double` | Prefer `float` for demo data |
| Lat/lon coordinates | `geo_point` | Format: `{"lat": 35.22, "lon": -80.84}` or `"lat,lon"` string |
| Boolean flags | `boolean` | |
| Multi-value with subfields | `nested` | Use for conversation history, line items; costs more at query time |
| Computed at ingest | regular field | Populated by script processor; type matches the value |
| IP addresses | `ip` | Native range queries; don't use keyword for IPs |

## semantic_text with ELSER v2

```json
PUT /associate-knowledge-base
{
  "mappings": {
    "properties": {
      "title":        { "type": "text" },
      "body":         { "type": "text" },
      "body_semantic": {
        "type": "semantic_text",
        "inference_id": "elser-v2-endpoint"
      },
      "sku_tags":     { "type": "keyword" },
      "category":     { "type": "keyword" },
      "doc_type":     { "type": "keyword" }
    }
  },
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1
  }
}
```

Deploy the inference endpoint BEFORE creating this mapping:
```json
PUT /_inference/sparse_embedding/elser-v2-endpoint
{
  "service": "elasticsearch",
  "service_settings": {
    "model_id": ".elser_model_2_linux-x86_64",
    "num_allocations": 1,
    "num_threads": 1
  }
}
```

## Data Stream Template (hot-warm-delete ILM)

```json
PUT /_ilm/policy/store-transactions-policy
{
  "policy": {
    "phases": {
      "hot":    { "min_age": "0ms", "actions": { "rollover": { "max_age": "7d", "max_primary_shard_size": "50gb" }, "set_priority": { "priority": 100 } } },
      "warm":   { "min_age": "7d",  "actions": { "shrink": { "number_of_shards": 1 }, "forcemerge": { "max_num_segments": 1 }, "set_priority": { "priority": 50 } } },
      "delete": { "min_age": "30d", "actions": { "delete": {} } }
    }
  }
}

PUT /_component_template/store-transactions-mappings
{
  "template": {
    "mappings": {
      "properties": {
        "@timestamp":    { "type": "date" },
        "store_id":      { "type": "keyword" },
        "event_type":    { "type": "keyword" },
        "sku":           { "type": "keyword" },
        "quantity":      { "type": "integer" },
        "associate_id":  { "type": "keyword" },
        "register_id":   { "type": "keyword" }
      }
    }
  }
}

PUT /_component_template/store-transactions-settings
{
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 1,
      "index.lifecycle.name": "store-transactions-policy"
    }
  }
}

PUT /_index_template/store-transactions-template
{
  "index_patterns": ["store-transactions-*"],
  "data_stream": {},
  "composed_of": ["store-transactions-mappings", "store-transactions-settings"],
  "priority": 200
}
```

## Ingest Pipeline Patterns

### Enrich processor (lookup join)
```json
PUT /_ingest/pipeline/store-transactions-pipeline
{
  "processors": [
    {
      "enrich": {
        "policy_name": "store-location-enrich",
        "field": "store_id",
        "target_field": "store_meta",
        "max_matches": 1
      }
    },
    {
      "set": {
        "field": "store_location",
        "copy_from": "store_meta.store_location",
        "ignore_empty_value": true
      }
    },
    { "remove": { "field": "store_meta", "ignore_missing": true } }
  ]
}
```

Enrich policy must be created AND executed before the pipeline is used:
```
PUT /_enrich/policy/store-location-enrich/_execute
```

### Script processor (computed field)
```json
{
  "script": {
    "lang": "painless",
    "source": """
      if (ctx.system_on_hand != null && ctx.system_on_hand > 0) {
        double diff = ctx.system_on_hand - ctx.stock_on_hand;
        ctx.discrepancy_pct = Math.round((diff / ctx.system_on_hand) * 1000.0) / 10.0;
      } else {
        ctx.discrepancy_pct = 0.0;
      }
    """
  }
}
```

### Upsert pattern (update-or-create in a separate index)
When a pipeline event needs to upsert into a mutable index (e.g., transaction event
updates inventory-positions), use the bulk API with `update` + `scripted_upsert`:

```json
POST /inventory-positions/_update/{{store_id}}_{{sku}}
{
  "script": {
    "lang": "painless",
    "source": """
      if (ctx._source.stock_on_hand == null) { ctx._source.stock_on_hand = 0; }
      if (params.event_type == 'sale') {
        ctx._source.stock_on_hand -= params.quantity;
      } else if (params.event_type == 'receive' || params.event_type == 'stock') {
        ctx._source.stock_on_hand += params.quantity;
      }
      ctx._source.last_transaction_at = params.timestamp;
      if (ctx._source.system_on_hand != null && ctx._source.system_on_hand > 0) {
        double diff = ctx._source.system_on_hand - ctx._source.stock_on_hand;
        ctx._source.discrepancy_pct = Math.round((diff / ctx._source.system_on_hand) * 1000.0) / 10.0;
      }
    """,
    "params": { "event_type": "{{event_type}}", "quantity": "{{quantity}}", "timestamp": "{{@timestamp}}" }
  },
  "upsert": {
    "store_id": "{{store_id}}",
    "sku": "{{sku}}",
    "stock_on_hand": 0,
    "system_on_hand": 0,
    "discrepancy_pct": 0.0
  }
}
```

For ingest pipeline → secondary index upserts, the most reliable pattern at demo scale
is to have the live-data-simulator script call the update API directly after indexing
the event, rather than relying on pipeline-level cross-index writes (which require
additional privileges and have edge cases).

## Nested vs Object vs Flattened

| Situation | Use |
|---|---|
| Array of objects you query independently | `nested` |
| Single sub-object, queried as a unit | `object` (default) |
| High-cardinality dynamic keys (e.g., labels map) | `flattened` |

Nested example (conversation history):
```json
"conversation_history": {
  "type": "nested",
  "properties": {
    "role":      { "type": "keyword" },
    "content":   { "type": "text" },
    "timestamp": { "type": "date" },
    "tool_calls": { "type": "keyword" }
  }
}
```

## Hybrid OOTB Data Stream Contract (Path A / Path B)

This repo uses a two-path strategy to keep logs/metrics/security data ECS-compliant and visible
in out-of-box UIs without hand-built schema drift.

### Path A — Fleet integration packages (preferred)

Use integration-native naming and install the package through `weave-fleet`.

- Naming: `logs-<integration>.<dataset>-<namespace>` or
  `metrics-<integration>.<dataset>-<namespace>`
- Examples:
  - `metrics-nvidia_gpu.dcgm-tenant-a`
  - `logs-kubernetes.container_logs-default`
  - `logs-system.auth-default`
- Benefits:
  - ECS-correct mappings and ingest pipelines
  - Prebuilt dashboards, ML modules, and (for security packages) detection assets
  - Minimal custom mapping logic in loom

### Path B — Managed templates fallback (custom demo data)

For datasets that do not map to a real package, keep data stream names in the `demo` namespace
and compose from Elastic-managed templates.

- Naming: `logs-demo.<dataset>-<namespace>` or `metrics-demo.<dataset>-<namespace>`
- Mapping model:
  - Do not redefine ECS fields in a custom component template
  - Define only non-ECS fields in `<dataset>@custom`
  - Compose with managed templates:
    - Logs: `["logs@mappings", "logs@settings", "ecs@mappings", "<dataset>@custom"]`
    - Metrics: `["metrics@mappings", "metrics@settings", "ecs@mappings", "<dataset>@custom"]`

### Lowercase field rule (mandatory)

Final indexed fields must be lowercase ECS style. If sources emit uppercase/mixed-case names,
rename them in ingest before indexing.

Example (GPU source normalization):

```json
PUT /_ingest/pipeline/demo-gpu-lowercase-normalize
{
  "processors": [
    { "rename": { "field": "DCGM_FI_DEV_GPU_UTIL", "target_field": "nvidia_gpu.activity.gpu.pct", "ignore_missing": true } },
    { "rename": { "field": "DCGM_FI_DEV_POWER_USAGE", "target_field": "nvidia_gpu.power.draw.watts", "ignore_missing": true } },
    { "set": { "field": "host.name", "copy_from": "instance", "ignore_empty_value": true } },
    { "set": { "field": "event.dataset", "value": "nvidia_gpu.dcgm" } },
    { "set": { "field": "service.type", "value": "nvidia_gpu" } }
  ]
}
```

### Base visibility checks to design for

The data model must satisfy these baseline UI assumptions before any custom use-case logic:

| Surface | Minimum fields/pattern |
|---|---|
| Infrastructure UI / Hosts | `metrics-*` stream + `host.name` + `event.dataset` |
| Metrics Explorer | `metrics-*` stream + `@timestamp` + numeric metric fields |
| Logs UI | `logs-*` stream + `@timestamp` + `message`/event content |
| Security detections / Entity Analytics | `logs-*` stream + `event.kind` + `event.category` + `event.type` + `host.name`/`user.name` |

If a stream fails these baseline checks, the model is incomplete even if custom dashboards work.

## IDs and Document Routing

For mutable documents that are updated by ingest events, use a deterministic `_id`:
- Inventory positions: `{store_id}_{sku}` — ensures updates hit the same document
- Sessions: `session_{associate_id}_{date}_{store_id}`
- Metadata/lookup: natural key from the source system

For data streams (append-only), let Elasticsearch auto-generate the `_id`.
