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

## Elastic Security — ECS Required Fields and Index Conventions

Security demos have the same category of failure as Observability metrics: data ingests
successfully but the Security UIs (Alerts view, Entity Analytics, Timeline, Detection rules)
see nothing because the required ECS fields or data stream naming conventions are missing.

---

### 1. Data Stream Naming — Detection Rules Only See `logs-*`

SIEM detection rules run against a default index pattern that includes `logs-*`, `filebeat-*`,
`winlogbeat-*`, `endgame-*`, `auditbeat-*`, and `.siem-signals-*` — but **not** arbitrary
custom index names. If you put security event data into an index named `security-events-*`
or `custom-threats-default`, the built-in detection rules will never fire against it.

**Rule:** All security event data streams for demos must follow:
```
logs-{integration}.{dataset}-{namespace}
```
Examples:
- `logs-system.auth-default` — authentication events
- `logs-windows.security-default` — Windows Security log events
- `logs-network.traffic-default` — network traffic events
- `logs-endpoint.events.process-default` — process events (Endpoint)
- `logs-demo.security-{namespace}` — custom demo security events (still visible to rules)

Custom demo events in `logs-demo.*-*` will be picked up by any rule whose index pattern
includes `logs-*`. This is the correct pattern for synthetic demo data.

---

### 2. Required ECS Fields for Raw Security Events

For a detection rule (EQL, KQL, threshold, ML) to match a document, the fields the rule
queries on must be present. These are the fields **every** security event document must have:

| Field | Type | Required | Notes |
|---|---|---|---|
| `@timestamp` | `date` | **Mandatory** | Event time — not ingest time |
| `event.kind` | `keyword` | **Mandatory** | Must be `"event"` on raw events rules run against |
| `event.category` | `keyword` | **Mandatory** | `authentication`, `network`, `process`, `file`, `registry`, `intrusion_detection`, `malware`, `web` |
| `event.type` | `keyword` | **Mandatory** | `start`, `end`, `allowed`, `denied`, `info`, `error`, `access`, `creation`, `deletion`, `change` |
| `event.action` | `keyword` | Recommended | Specific action e.g. `logged-in`, `logon-failed`, `process-started` |
| `event.outcome` | `keyword` | Recommended | `success`, `failure`, `unknown` |
| `event.dataset` | `keyword` | **Mandatory** | e.g. `system.auth`, `windows.security` |
| `event.module` | `keyword` | Recommended | e.g. `system`, `windows`, `endpoint` |
| `host.name` | `keyword` | **Mandatory** | Required for host-based rules and Entity Analytics |
| `host.hostname` | `keyword` | Recommended | |
| `host.os.type` | `keyword` | Recommended | `linux`, `windows`, `macos` |
| `user.name` | `keyword` | **Mandatory** | Required for user-based rules and Entity Analytics |
| `user.domain` | `keyword` | Recommended | |
| `agent.type` | `keyword` | Recommended | e.g. `filebeat`, `elastic_agent`, `endpoint` |

**Event-category-specific required fields:**

| Category | Additional required fields |
|---|---|
| `authentication` | `user.name`, `source.ip`, `event.outcome` |
| `network` | `source.ip`, `source.port`, `destination.ip`, `destination.port`, `network.protocol` |
| `process` | `process.name`, `process.pid`, `process.executable`, `process.parent.name` |
| `file` | `file.name`, `file.path` |
| `registry` | `registry.key`, `registry.value.name` |
| `dns` | `dns.question.name`, `dns.question.type`, `network.protocol: dns` |

---

### 3. Entity Analytics — Risk Scoring Requirements

The Entity Risk Score engine consumes Security alerts (from `.alerts-security.alerts-*`) to
compute per-entity scores. For risk scores to appear in Entity Analytics:

- Alerts must have been generated by detection rules (or written as synthetic alerts with
  correct `kibana.alert.*` fields — see section 4 below)
- **`user.name`** must be present on alerts for User risk scores
- **`host.name`** must be present on alerts for Host risk scores
- Without these fields, Entity Analytics shows a blank risk table even when alerts exist

---

### 4. Synthetic Demo Alerts (writing directly to `.alerts-security.alerts-*`)

When the demo requires pre-seeded alerts visible in the Security Alerts view (rather than
waiting for detection rules to fire), write synthetic documents directly to the alerts index.
This requires the `manage` privilege on `.alerts-security.alerts-default`.

**Required fields for synthetic alerts:**

```json
{
  "@timestamp": "<ISO8601>",
  "event.kind": "signal",
  "event.action": "open",
  "kibana.alert.rule.name": "Demo - Credential Stuffing Attempt",
  "kibana.alert.rule.rule_id": "demo-credential-stuffing-001",
  "kibana.alert.rule.category": "Custom Query Rule",
  "kibana.alert.rule.uuid": "<uuid5 stable ID>",
  "kibana.alert.severity": "high",
  "kibana.alert.risk_score": 73,
  "kibana.alert.workflow_status": "open",
  "kibana.alert.status": "active",
  "kibana.alert.uuid": "<unique per alert>",
  "kibana.space_ids": ["<space_id>"],
  "host.name": "<hostname>",
  "user.name": "<username>",
  "event.dataset": "demo.security"
}
```

**Key rules for synthetic alerts:**
- `event.kind` must be `"signal"` (not `"event"`) — the Alerts view filters on this
- `kibana.space_ids` must contain the Kibana space ID where the alert should appear
- `kibana.alert.workflow_status` must be `"open"`, `"acknowledged"`, or `"closed"`
- `kibana.alert.severity` must be one of: `"critical"`, `"high"`, `"medium"`, `"low"`
- Use `uuid.uuid5(NS, f"{SLUG}:alert:{n}")` for `kibana.alert.uuid` to keep them idempotent
- Write to `.alerts-security.alerts-default` (or the namespace-specific variant) via the
  bulk API — **not** to a custom index

**Preferred alternative for demos:** Generate synthetic raw events (section 2 fields) + create
matching detection rules (section 6). Let the rules fire and generate real alerts. This is
more reliable and avoids privilege requirements on the `.alerts-*` system index.

---

### 5. Component Template: Security Events Data Stream

```json
PUT /_component_template/demo-security-events-mappings
{
  "template": {
    "mappings": {
      "properties": {
        "@timestamp":           { "type": "date" },
        "event": {
          "properties": {
            "kind":             { "type": "keyword" },
            "category":         { "type": "keyword" },
            "type":             { "type": "keyword" },
            "action":           { "type": "keyword" },
            "outcome":          { "type": "keyword" },
            "dataset":          { "type": "keyword" },
            "module":           { "type": "keyword" },
            "severity":         { "type": "long" }
          }
        },
        "host": {
          "properties": {
            "name":             { "type": "keyword" },
            "hostname":         { "type": "keyword" },
            "ip":               { "type": "ip" },
            "os": {
              "properties": {
                "type":         { "type": "keyword" }
              }
            }
          }
        },
        "user": {
          "properties": {
            "name":             { "type": "keyword" },
            "domain":           { "type": "keyword" },
            "id":               { "type": "keyword" }
          }
        },
        "source": {
          "properties": {
            "ip":               { "type": "ip" },
            "port":             { "type": "integer" },
            "geo": {
              "properties": {
                "country_name": { "type": "keyword" },
                "city_name":    { "type": "keyword" }
              }
            }
          }
        },
        "destination": {
          "properties": {
            "ip":               { "type": "ip" },
            "port":             { "type": "integer" }
          }
        },
        "process": {
          "properties": {
            "name":             { "type": "keyword" },
            "pid":              { "type": "long" },
            "executable":       { "type": "keyword" },
            "parent": {
              "properties": {
                "name":         { "type": "keyword" },
                "pid":          { "type": "long" }
              }
            },
            "command_line":     { "type": "wildcard" }
          }
        },
        "network": {
          "properties": {
            "protocol":         { "type": "keyword" },
            "direction":        { "type": "keyword" },
            "bytes":            { "type": "long" }
          }
        },
        "file": {
          "properties": {
            "name":             { "type": "keyword" },
            "path":             { "type": "keyword" },
            "hash": {
              "properties": {
                "sha256":       { "type": "keyword" }
              }
            }
          }
        },
        "agent": {
          "properties": {
            "type":             { "type": "keyword" },
            "version":          { "type": "keyword" }
          }
        },
        "message":              { "type": "text" },
        "tags":                 { "type": "keyword" }
      }
    }
  }
}

PUT /_component_template/demo-security-events-settings
{
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 1
    }
  }
}

PUT /_index_template/demo-security-events-template
{
  "index_patterns": ["logs-demo.security-*"],
  "data_stream": {},
  "composed_of": ["demo-security-events-mappings", "demo-security-events-settings"],
  "priority": 200
}
```

---

### 6. Detection Rule Design for Demo Events

Detection rules must target the same index pattern as the demo data stream. For `logs-demo.security-*`:

```json
POST /api/detection_engine/rules
{
  "rule_id": "demo-credential-stuffing-001",
  "name": "Demo - Credential Stuffing Attempt",
  "description": "Detects repeated authentication failures from a single source IP",
  "type": "threshold",
  "language": "kuery",
  "query": "event.category:authentication AND event.outcome:failure",
  "index": ["logs-demo.security-*"],
  "threshold": { "field": ["source.ip"], "value": 5 },
  "severity": "high",
  "risk_score": 73,
  "enabled": true,
  "interval": "5m",
  "from": "now-6m",
  "tags": ["demo", "demobuilder:<engagement_id>"],
  "version": 1
}
```

**D-032:** Never PUT/PATCH prebuilt rules (`immutable: true`). Clone with `demo-` prefix,
`version: 1`, and demobuilder tags.

---

### 7. Cases — Configure Before Create

The Cases API returns `400` if `POST /api/cases` is called before `POST /api/cases/configure`
has been called for the target owner. This is a **build-order dependency**, not a data model
issue — but it must be reflected in `bootstrap.py` step ordering.

```python
# In bootstrap.py — always before any create-case call
POST /api/cases/configure
{
  "connector": {"id": "none", "name": "none", "type": ".none", "fields": null},
  "closure_type": "close-by-user",
  "owner": "securitySolution"
}
```

---

### 8. ECS Field Checklist for Security Data Models

Use this checklist when designing any security events data stream or demo alert spec:

**Raw events (detection rules, Timeline):**
- [ ] Data stream named `logs-{something}-{namespace}` — never a custom prefix
- [ ] `event.kind: "event"` on every raw event document
- [ ] `event.category` present and matches one of the ECS category values
- [ ] `event.type` present and valid for the category
- [ ] `host.name` present on all host-related events
- [ ] `user.name` present on all user/authentication events
- [ ] Category-specific fields added (IPs for network, process fields for process, etc.)

**Detection rules:**
- [ ] Rule `index` field matches the data stream name pattern exactly
- [ ] Rule `query` references only fields present in the mapping
- [ ] Custom rules have `demo-` prefixed `rule_id`, `version: 1`, demobuilder tags (D-032)
- [ ] Rules enabled before demo — allow one interval cycle for alerts to generate

**Entity Analytics:**
- [ ] Alerts (generated by rules) carry `user.name` for User risk scoring
- [ ] Alerts (generated by rules) carry `host.name` for Host risk scoring
- [ ] Entity risk scoring feature is enabled: `PUT /api/risk_score/engine/init`

**Cases:**
- [ ] `POST /api/cases/configure` called with `owner: "securitySolution"` before any case creation
- [ ] Cases build step ordered after configure step in bootstrap.py

---

## Observability Metrics Data Streams — ECS Required Fields

Metrics data streams that must appear in the **Infrastructure UI**, **Hosts view**, or any
Observability entity-based view **require specific ECS fields** to be present in every document.
Without them, Elasticsearch will index the data but the UI will not discover or display any
entities — the data is invisible to those views even when the index has data.

### Required ECS Fields by Entity Type

**Host / VM / GPU node** — needed for Infrastructure UI Hosts view:

| Field | Type | Required | Value source |
|---|---|---|---|
| `host.name` | `keyword` | **Mandatory** | Identifies the host entity — map from source field (e.g. `instance`, `hostname`) |
| `event.dataset` | `keyword` | **Mandatory** | Dataset identifier, e.g. `gpu.dcgm.prometheus`, `system.cpu` |
| `service.type` | `keyword` | **Mandatory** | Source type, e.g. `prometheus`, `system`, `docker` |
| `data_stream.type` | `keyword` | Auto-set | Set automatically for `metrics-*-*` data streams |
| `data_stream.dataset` | `keyword` | Auto-set | Set automatically from the data stream name |
| `data_stream.namespace` | `keyword` | Auto-set | Set automatically from the data stream name |
| `host.hostname` | `keyword` | Recommended | Full hostname; can match `host.name` |
| `host.ip` | `ip` | Recommended | Array of IPs; enables IP-based entity lookup |
| `host.os.type` | `keyword` | Recommended | e.g. `linux`, `windows` |
| `agent.type` | `keyword` | Recommended | e.g. `metricbeat`, `elastic_agent`, `prometheus` |

**Container** — needed for Container / Docker / Kubernetes views:

| Field | Type | Required |
|---|---|---|
| `container.id` | `keyword` | **Mandatory** for container entity |
| `container.name` | `keyword` | Recommended |
| `container.image.name` | `keyword` | Recommended |
| `host.name` | `keyword` | Required (parent host) |

**Kubernetes Pod** — needed for Kubernetes entity views:

| Field | Type | Required |
|---|---|---|
| `kubernetes.pod.name` | `keyword` | **Mandatory** |
| `kubernetes.namespace` | `keyword` | **Mandatory** |
| `kubernetes.node.name` | `keyword` | Required (parent node) |
| `host.name` | `keyword` | Required (parent host) |

### Component Template: Metrics with Full ECS Fields

Example for a GPU/Prometheus metrics data stream (`metrics-gpu.dcgm.prometheus-*`):

```json
PUT /_component_template/gpu-dcgm-ecs-mappings
{
  "template": {
    "mappings": {
      "properties": {
        "@timestamp":          { "type": "date" },
        "host": {
          "properties": {
            "name":            { "type": "keyword" },
            "hostname":        { "type": "keyword" },
            "ip":              { "type": "ip" }
          }
        },
        "event": {
          "properties": {
            "dataset":         { "type": "keyword" }
          }
        },
        "service": {
          "properties": {
            "type":            { "type": "keyword" }
          }
        },
        "agent": {
          "properties": {
            "type":            { "type": "keyword" },
            "version":         { "type": "keyword" }
          }
        },
        "gpu":                 { "type": "keyword" },
        "tenant_namespace":    { "type": "keyword" },
        "exported_namespace":  { "type": "keyword" },
        "DCGM_FI_DEV_GPU_UTIL":    { "type": "float" },
        "DCGM_FI_DEV_GPU_TEMP":    { "type": "float" },
        "DCGM_FI_DEV_POWER_USAGE": { "type": "float" },
        "DCGM_FI_DEV_SM_CLOCK":    { "type": "float" },
        "DCGM_FI_DEV_MEM_CLOCK":   { "type": "float" },
        "DCGM_FI_DEV_FB_USED":     { "type": "float" },
        "DCGM_FI_DEV_FB_FREE":     { "type": "float" }
      }
    }
  }
}
```

### Ingest Pipeline: Map Source Fields → ECS at Write Time

When ingest data contains source-specific fields (Prometheus, DCGM, custom agent) that do not
already follow ECS naming, add an ingest pipeline to populate the required ECS fields.

**This is Option 1 (recommended) from the infra UI fix pattern — apply it at the template level
so every document written to the data stream gets the ECS fields automatically.**

```json
PUT /_ingest/pipeline/gpu-dcgm-ecs-pipeline
{
  "description": "Maps DCGM Prometheus source fields to required ECS fields for Infrastructure UI",
  "processors": [
    {
      "set": {
        "field": "host.name",
        "copy_from": "instance",
        "ignore_empty_value": true
      }
    },
    {
      "set": {
        "field": "host.hostname",
        "copy_from": "instance",
        "ignore_empty_value": true
      }
    },
    {
      "set": {
        "field": "event.dataset",
        "value": "gpu.dcgm.prometheus"
      }
    },
    {
      "set": {
        "field": "service.type",
        "value": "prometheus"
      }
    },
    {
      "set": {
        "field": "agent.type",
        "value": "prometheus"
      }
    }
  ]
}
```

Wire the pipeline into the index template via the `default_pipeline` setting:

```json
PUT /_component_template/gpu-dcgm-settings
{
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 1,
      "index.default_pipeline": "gpu-dcgm-ecs-pipeline",
      "index.lifecycle.name": "metrics-hot-delete-policy"
    }
  }
}

PUT /_index_template/gpu-dcgm-template
{
  "index_patterns": ["metrics-gpu.dcgm.prometheus-*"],
  "data_stream": {},
  "composed_of": ["gpu-dcgm-ecs-mappings", "gpu-dcgm-settings"],
  "priority": 200
}
```

### Backfill ECS Fields on Existing Data Streams

When data has already been indexed without ECS fields (the lenovo-gaiaas failure pattern),
**update the pipeline and template first, then reindex or use `update_by_query`** to backfill
existing documents:

```python
# In bootstrap.py — reindex with pipeline applied to backfill ECS fields
POST /_reindex
{
  "source": { "index": "metrics-gpu.dcgm.prometheus-tenant-a" },
  "dest":   { "index": "metrics-gpu.dcgm.prometheus-tenant-a", "pipeline": "gpu-dcgm-ecs-pipeline" }
}
```

Or for in-place update (slower but no data duplication):
```
POST /metrics-gpu.dcgm.prometheus-tenant-a/_update_by_query?pipeline=gpu-dcgm-ecs-pipeline
```

### ECS Field Checklist for Metrics Data Models

Use this checklist whenever designing a metrics data stream in Step 2:

- [ ] `host.name` mapped as `keyword` in component template
- [ ] `event.dataset` mapped as `keyword` in component template
- [ ] `service.type` mapped as `keyword` in component template
- [ ] Ingest pipeline created with `set` processors for all three fields
- [ ] `index.default_pipeline` set in the settings component template
- [ ] Pipeline references validated — pipeline name in template must match the `PUT /_ingest/pipeline/` name exactly
- [ ] Pipeline created BEFORE the index template in the build order
- [ ] For container/k8s entities: `container.id` and `kubernetes.pod.name` added to mapping if those views are part of the demo story

---

## IDs and Document Routing

For mutable documents that are updated by ingest events, use a deterministic `_id`:
- Inventory positions: `{store_id}_{sku}` — ensures updates hit the same document
- Sessions: `session_{associate_id}_{date}_{store_id}`
- Metadata/lookup: natural key from the source system

For data streams (append-only), let Elasticsearch auto-generate the `_id`.
