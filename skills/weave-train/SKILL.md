---
name: weave-train
description: >
  Reads a demo script and data model to generate Elastic ML job configurations: anomaly
  detection job JSON, datafeed configs, and a demo anomaly injection plan that ensures
  the right red cells appear in the swimlane at the right moment. Also generates trained
  model deployment configs for NLP/semantic scenes when applicable.

  ALWAYS use this skill when the user needs to configure ML anomaly detection for a demo,
  asks "how do I set up the ML job", "what detector do I use", "how do I make the anomaly
  appear", or has a demo script with an ML scene and needs the technical config. Run after
  weave-model — ML jobs depend on the index structure being defined first.
---

# Demo ML Designer

You are configuring Elastic ML jobs for a pre-sales demo. The goal is not just a working
ML job — it's a job that produces a compelling anomaly at the right moment for the right
entity, with enough baseline training data to make the anomaly visually obvious.

A demo ML job that doesn't show a clear red cell is worse than no ML job. Design for the
wow moment first, then work backwards to the job config.

## Step 1: Identify the ML Scenes

Read the demo script (`demo/{slug}-demo-script.md`). For each scene that uses ML:

- What is the **anomaly narrative**? (e.g., "inventory gap grows faster than normal sales
  velocity", "unusual authentication volume from a single source", "SLA breach rate spikes
  outside normal pattern")
- What **entity** is anomalous? (store + SKU, IP address, user account, vendor, etc.)
- What **metric** is anomalous? (count, mean, sum, rare event, absence of event)
- What is the **normal pattern** the job must learn? (daily seasonal rhythm, per-entity
  baseline, steady-state rate)
- When in the demo does the anomaly need to appear? (T-minus from demo start, or live
  during the presentation)

## Step 2: Design the Anomaly Detection Job

### Detector selection

Choose the detector function that matches the anomaly narrative:

| Narrative | Detector function | Notes |
|---|---|---|
| "More X than usual" (count spike) | `count` or `high_count` | Use `high_count` to only flag upward anomalies |
| "Mean value higher/lower than usual" | `mean(field)` or `high_mean` / `low_mean` | |
| "Never seen this before" | `rare` or `freq_rare` | For new entity values |
| "Unusual sum" (e.g., total transaction value) | `sum(field)` or `high_sum` | |
| "Expected event didn't happen" | `low_count` or `non_zero_count` | |
| "Ratio changed" (e.g., error rate) | `mean(field)` where field is a rate/pct | |

**Partition by** — always partition the detector by the entity that varies. This gives each
entity its own baseline:
```
mean(discrepancy_pct) PARTITION BY store_id, sku_group
```

**Influence fields** — add fields that help explain the anomaly after detection:
```json
"influencers": ["store_id", "sku", "event_type"]
```

### Bucket span selection

The bucket span must match the granularity of the anomaly narrative:
- Event-level anomalies (fraud, auth spikes): 5m or 15m
- Hourly operational anomalies (inventory drift, SLA patterns): 1h
- Daily business anomalies (sales patterns, shrink): 4h or 1d

**Rule:** bucket span should be 1/10th to 1/20th of the anomaly's natural duration.
If a shrink event builds over 4 hours, a 15m–30m bucket span detects it while it's still
forming rather than after it's complete.

### Minimum training data

The job needs enough data to learn a stable baseline before the demo anomaly appears.
Calculate: `training_hours = (anomaly_detection_lag_factor) * bucket_span_hours * 72`

For most demo jobs: **24–48 hours of baseline data** at realistic volume, with the anomaly
injected in the last 2–4 hours before demo start.

Do not train on the anomaly period — the model must learn what "normal" looks like first.

### Complete job config

```json
{
  "job_id": "inventory-shrink-monitor",
  "description": "Detects abnormal inventory discrepancy growth by store and SKU group",
  "analysis_config": {
    "bucket_span": "1h",
    "detectors": [
      {
        "function": "mean",
        "field_name": "discrepancy_pct",
        "partition_field_name": "sku_group",
        "by_field_name": "store_id",
        "detector_description": "Mean discrepancy_pct by store and SKU group"
      }
    ],
    "influencers": ["store_id", "sku", "event_type"]
  },
  "data_description": {
    "time_field": "@timestamp",
    "time_format": "epoch_ms"
  },
  "model_plot_config": {
    "enabled": true,
    "annotations_enabled": true
  },
  "analysis_limits": {
    "model_memory_limit": "256mb"
  }
}
```

### Datafeed config

```json
{
  "datafeed_id": "datafeed-inventory-shrink-monitor",
  "job_id": "inventory-shrink-monitor",
  "indices": ["inventory-positions"],
  "query": {
    "bool": {
      "must": [
        { "range": { "stock_on_hand": { "gte": 0 } } },
        { "range": { "system_on_hand": { "gt": 0 } } }
      ]
    }
  },
  "scroll_size": 1000,
  "delayed_data_check_config": { "enabled": true }
}
```

**Important — geo_point fields in datafeed source indices:** If the datafeed source
index contains a `geo_point` field (e.g., `store_location`), the ML datafeed will
fail when it encounters it. Shadow the field via `runtime_mappings` in the datafeed
config, or exclude it from `_source`:

```json
"runtime_mappings": {
  "store_location": {
    "type": "keyword",
    "script": "emit('')"
  }
}
```

### Serverless: ML field names differ from documentation

When querying `.ml-anomalies-*` on Serverless, the actual field names differ from
what the self-managed documentation shows:

| Self-managed docs | Serverless actual |
|---|---|
| `anomaly_score` | `record_score` |
| `@timestamp` | `timestamp` |
| The partition field name (e.g., `store_id`) | `partition_field_value` |
| The by field name (e.g., `sku`) | `by_field_value` |

Before writing any dashboard panel or ES|QL query against `.ml-anomalies-*`, confirm
field names with: `GET .ml-anomalies-*/_mapping`

### Serverless: ML Anomaly Explorer UI not available

The Kibana ML Anomaly Explorer (swimlane UI) is not available on Serverless. Replace
it with a custom Kibana dashboard panel using ES|QL or Lens querying `.ml-anomalies-*`
directly. Update the demo script accordingly — any scene that references the swimlane
UI must use a custom dashboard instead. The `record_score` field renders identically
when displayed in a Kibana heatmap visualization.

## Step 3: Design the Anomaly Injection Plan

This is what makes the demo work. Define exactly what data to insert, for which entities,
at what time, to guarantee the anomaly appears.

**Injection strategy — skew the signal:**

For an inventory shrink scenario:
- Normal period (T-48h to T-2h): balanced POS/receive/stock events at realistic ratios
  (e.g., 3 sales per receive, discrepancy_pct drifts 5–15% by end of day)
- Anomaly period (T-2h to demo time): for the target store+SKU, suppress receive events,
  inject POS events at 3–5× normal velocity. `discrepancy_pct` climbs to 40–60% while
  `typical` value stays at 10–12%. Anomaly score crosses 75+ threshold.

For an authentication anomaly:
- Normal period: auth events at steady per-user rates (Poisson distribution)
- Anomaly period: one source IP generates 10–20× normal auth volume, plus new user accounts
  not seen in training period (`rare` detector fires)

**Injection timing:**
```
demo_start = T+0
anomaly_visible = T-30min (ML job processes up to current time)
inject_start = T-3h (gives model time to process and flag)
training_end = T-3h (clean separation between train and anomaly periods)
```

**Injection specification document:**

```json
{
  "job_id": "inventory-shrink-monitor",
  "anomaly_scenario": "Inventory shrink — store 1842, SKU group: fasteners",
  "target_entities": [
    { "store_id": "1842", "sku": "174239", "anomaly_type": "high_discrepancy" },
    { "store_id": "1842", "sku": "182041", "anomaly_type": "high_discrepancy" },
    { "store_id": "1842", "sku": "196723", "anomaly_type": "high_discrepancy" }
  ],
  "normal_period": {
    "duration_hours": 46,
    "pos_receive_ratio": "3:1",
    "discrepancy_pct_range": [5, 15]
  },
  "anomaly_period": {
    "duration_hours": 2,
    "trigger_time": "T-2h from demo start",
    "pos_events_multiplier": 4,
    "receive_events": 0,
    "expected_discrepancy_pct": [40, 60],
    "expected_anomaly_score": [75, 95]
  },
  "verification": "Open ML swimlane 30 min before demo — confirm red cells on store 1842"
}
```

## Step 4: NLP / Trained Model Config (if applicable)

When the script includes ELSER semantic search or NLP features:

**ELSER v2 deployment** (if not already in the data model):

For **Serverless** — use the managed endpoint (no model_id):
```json
PUT /_inference/sparse_embedding/elser-v2-endpoint
{
  "service": "elser",
  "service_settings": {
    "num_allocations": 1,
    "num_threads": 1
  }
}
```

For **ECH / self-managed** — deploy the model explicitly:
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

**Warmup query** (run 30 min before demo — first inference is always slow):
```json
POST /associate-knowledge-base/_search
{
  "query": {
    "semantic": {
      "field": "body_semantic",
      "query": "warmup query for model initialization"
    }
  },
  "size": 1
}
```
Wait for sub-2s response before considering the endpoint warm.

**NER / classification models** — if the script includes entity extraction or
classification on text fields, specify:
- Model ID (from Elastic's model hub or a custom uploaded model)
- Target field and output field
- Inference pipeline processor config

## Step 5: Write the Outputs

### Output 1: `data/{slug}-ml-config.json`

Machine-readable collection of all ML artifacts:

```json
{
  "anomaly_detection_jobs": [ { ...job config... } ],
  "datafeeds": [ { ...datafeed config... } ],
  "inference_endpoints": [ { ...endpoint config... } ],
  "anomaly_injection_plan": [ { ...per-entity injection spec... } ],
  "training_data_requirements": {
    "minimum_hours": 48,
    "anomaly_injection_start": "T-2h from demo",
    "verification_checklist": [ ... ]
  }
}
```

### Output 2: `data/{slug}-ml-setup.md`

Step-by-step ML setup guide for the SE:

```
# ML Setup — [Demo Name]

## Jobs to Configure
[Table: job_id | detector | partition | bucket_span | index]

## Setup Sequence
1. Verify index has data (minimum N documents)
2. Create job via API or Kibana ML UI
3. Create and start datafeed
4. Wait for first bucket to complete (bucket_span time)
5. Run datafeed on historical data (open job → start datafeed from T-48h)
6. Verify swimlane shows clean baseline (no anomalies in normal period)
7. Run anomaly injection script
8. Wait 2× bucket_span for anomaly to surface
9. Verify red cells appear on target entities

## Anomaly Injection
[Exact script command or API calls to inject the demo anomaly]

## Verification Checklist
- [ ] Swimlane open in Kibana — confirm correct time range
- [ ] Red/orange cells visible on [specific store/entity]
- [ ] Anomaly score ≥ 75 on at least one record
- [ ] `typical` value visible and clearly lower than `actual`
- [ ] ES|QL join query returns the same SKUs as the ML anomaly
```

## What Good Looks Like

**Inventory shrink pattern:** `mean(discrepancy_pct) PARTITION BY sku_group BY store_id`,
1h bucket, 48h training on 4 stores. Three specific SKUs at store 1842 injected with 4×
POS velocity and 0 receives for 2 hours pre-demo. Expected: anomaly score 85–95, swimlane
shows 3 red cells for store 1842 fasteners group. All other stores stay green.

**Auth anomaly pattern (SOC):** `high_count PARTITION BY source_ip`, 15m bucket, 24h
training on per-IP auth patterns. Inject 1,000 auth attempts from a single IP that had
zero history in training. `rare` detector also fires. Anomaly visible within two buckets
(30 min) of injection start.

**SLA breach pattern (financial):** `high_mean(days_since_filed) PARTITION BY claim_type
BY vendor_id`, 4h bucket. Inject vendor VND-0412 online debit claims with day 8–11 values
(above SLA) while other vendors stay at day 1–3. Anomaly score crosses threshold after one
bucket (4h). Time the injection for T-8h from demo so the swimlane is populated by demo
time.
