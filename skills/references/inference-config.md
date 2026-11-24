# Inference Configuration Reference

**Loaded by:** `skills/bolt-launch/SKILL.md`, `skills/weave-model/SKILL.md`, `skills/weave-train/SKILL.md`

This file is the **single source of truth** for Elastic inference service/model configuration by deployment type. When model IDs, service names, or task types change, update here.

**Decision reference:** `docs/decisions.md` D-028 (EIS for all embeddings/reranking).

---

## ELSER (Sparse Embedding)

### ECH / Self-managed / ECK (9.4+)

```json
{
  "service": "elastic",
  "service_settings": {
    "model_id": ".elser-2",
    "num_allocations": 1,
    "num_threads": 1
  }
}
```

API call:
```
PUT /_inference/sparse_embedding/{inference_id}
```

### Serverless (all project types)

```json
{
  "service": "elser",
  "service_settings": {
    "num_allocations": 1,
    "num_threads": 1
  }
}
```

**Do not** specify `model_id` on Serverless — it is ignored and may cause errors. `service: "elser"` uses the managed ELSER endpoint automatically.

---

## Text Embedding (Dense Vector)

### ECH / Self-managed / ECK

```json
{
  "service": "elastic",
  "service_settings": {
    "model_id": "sentence-transformers__msmarco-minilm-l-12-v3",
    "num_allocations": 1,
    "num_threads": 1
  }
}
```

### Serverless

```json
{
  "service": "elastic",
  "service_settings": {
    "model_id": "sentence-transformers__msmarco-minilm-l-12-v3"
  }
}
```

---

## Reranker

### ECH / Self-managed / ECK

```json
{
  "service": "elastic",
  "service_settings": {
    "model_id": "elastic-reranker-v1",
    "num_allocations": 1,
    "num_threads": 1
  }
}
```

API call:
```
PUT /_inference/rerank/{inference_id}
```

### Serverless

```json
{
  "service": "elastic",
  "service_settings": {
    "model_id": "elastic-reranker-v1"
  }
}
```

---

## Python Helper Pattern

```python
def _inference_config(task_type: str, inference_id: str) -> dict:
    """Build inference endpoint config for the current DEPLOYMENT_TYPE."""
    if DEPLOYMENT_TYPE == "serverless":
        if task_type == "sparse_embedding":
            return {
                "service": "elser",
                "service_settings": {"num_allocations": 1, "num_threads": 1}
            }
        else:
            # text_embedding, rerank — same service: "elastic" on both
            return _elastic_service_config(task_type)
    else:
        return _elastic_service_config(task_type)

_ELASTIC_MODELS = {
    "sparse_embedding": ".elser-2",
    "rerank":           "elastic-reranker-v1",
    # text_embedding: set model_id to the target model
}

def _elastic_service_config(task_type: str) -> dict:
    model_id = _ELASTIC_MODELS.get(task_type)
    cfg = {"service": "elastic", "service_settings": {"num_allocations": 1, "num_threads": 1}}
    if model_id:
        cfg["service_settings"]["model_id"] = model_id
    return cfg
```

---

## Warm-Up

After deploying ELSER, run a warm-up inference call before the demo. Cold start on Serverless can take 30+ seconds.

```python
# Warm-up — send a dummy inference request and wait for latency < ELSER_WARM_MS
# ELSER_WARM_MS = 2000  (see pipeline-constants.md)
```

---

## `semantic_text` Field Mapping

For indices using `semantic_text` field type, the `inference_id` in the mapping must match the inference endpoint ID:

```json
{
  "mappings": {
    "properties": {
      "product_description_semantic": {
        "type": "semantic_text",
        "inference_id": "{prefix}elser"
      }
    }
  }
}
```

---

## Known Issues

### Stale D-028 / D-014 in decisions.md
D-014 and older versions of D-028 in `docs/decisions.md` referenced `"service": "elasticsearch"` for ECH. This was **incorrect** and has been superseded. The correct value for ECH is `"service": "elastic"` (EIS). This file is authoritative; ignore any `"service": "elasticsearch"` references in older decision text.

### Legacy model references
`weave-train/SKILL.md` and older `mapping-patterns.md` examples may reference the local ECH model path `".elser_model_2_linux-x86_64"`. This is a pre-EIS pattern. Use `".elser-2"` for ECH and `service: "elser"` for Serverless as documented above.
