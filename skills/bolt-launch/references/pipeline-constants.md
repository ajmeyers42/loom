# Pipeline Constants

**Loaded by:** `skills/bolt-launch/SKILL.md`, `skills/wind-reset/SKILL.md`, `skills/wind-pulse/SKILL.md`, `skills/weave-cost/SKILL.md`

This file is the **single source of truth** for numeric thresholds, special index names, header values, and other constants that appear in generated scripts and skill logic. Update here; skills read from here rather than hardcoding values.

---

## Data Ingestion

| Constant | Value | Used in |
|----------|-------|---------|
| Seed data skip threshold | `0.9` (90%) | `bootstrap.py` / `bootstrap-data.py` seed step; `wind-pulse` doc count check |
| Bulk batch size | `500` documents per `_bulk` call | `bootstrap-data.py` seed loop |
| Seed count floor (always load at least N docs regardless of skip) | `50` | `bootstrap-data.py` |

**Rationale for 90% skip:** If the index already has ≥ 90% of the expected seed count, skip re-ingestion to keep re-deploy fast. Below 90% always re-ingest to ensure demo data is complete.

---

## Inference / ELSER

| Constant | Value | Used in |
|----------|-------|---------|
| ELSER warm-up latency gate | `2000 ms` | `bootstrap-data.py` warm step; `wind-pulse` ELSER check |
| ELSER warm-up retry interval | `5 s` | `bootstrap-data.py` |
| ELSER warm-up max retries | `12` (1 minute total) | `bootstrap-data.py` |

---

## Stable Object IDs (UUID5)

| Constant | Value | Used in |
|----------|-------|---------|
| UUID5 namespace | `6ba7b810-9dad-11d1-80b4-00c04fd430c8` | All `stable_id()` calls in `bootstrap.py` / `bootstrap-data.py` |

**Critical:** This namespace must never change. All Kibana dashboard and saved object IDs are derived from it via `uuid.uuid5(NS, f"{SLUG}:{name}")`. Changing it would shift every stable ID across all existing engagements.

```python
import uuid
_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

def stable_id(name: str) -> str:
    """Return a deterministic UUID for a Kibana saved object."""
    return str(uuid.uuid5(_NS, f"{SLUG}:{name}"))
```

---

## Manifest

| Constant | Value | Used in |
|----------|-------|---------|
| Manifest index name | `loom-manifests` | `bootstrap-data.py`, `teardown.py`, `weave-fleet`, `weave-pipe` |
| Manifest document ID | normalized engagement ID (same as `demobuilder:<id>` tag value) | All manifest operations |

The `loom-manifests` index is never prefixed with `INDEX_PREFIX` and is never deleted by teardown. It is a cluster-wide registry of all engagements deployed to that cluster.

---

## Kibana API Headers

| Constant | Value | Notes |
|----------|-------|-------|
| `kbn-xsrf` header value | `"loom"` | Use this value consistently across all Kibana API calls in generated scripts. Do not use `true` or script-specific strings. |

```python
KB_HEADERS = {
    "Authorization": f"ApiKey {KIBANA_API_KEY}",
    "Content-Type": "application/json",
    "kbn-xsrf": "loom",
}
```

---

## Token Visibility (D-036)

These defaults apply when `INCLUDE_TOKEN_VISIBILITY` is not `false` and Agent Builder is in scope.

| Constant | Value | Used in |
|----------|-------|---------|
| Synthetic session doc count | `30–60 documents` | `bootstrap-data.py` token visibility seed |
| Session date range | `7–14 days` back from deploy date | Seed data generation |
| Cost per session range | `$0.02–$2.50` | Seed data generation |
| Session ILM retention | `90 days` (hot-only delete) | ILM policy for `{prefix}agent-sessions` |
| Dashboard name suffix | `"ai-usage"` | `stable_id(f"{SLUG}:ai-usage")` |

---

## Anomaly Injection

| Constant | Value | Used in |
|----------|-------|---------|
| Anomaly injection doc count | `5–15 documents` with elevated `record_score` | `bootstrap-data.py` anomaly step |
| Anomaly timestamp offset | `T-2h` from demo time (configurable via `ANOMALY_OFFSET_HOURS`) | Seed to appear in recent ML swimlane |

---

## Enrich Policy Execution

| Constant | Value | Used in |
|----------|-------|---------|
| Enrich execute poll interval | `3 s` | `bootstrap-data.py` enrich polling loop |
| Enrich execute max wait | `120 s` | Abort with error after this duration |
