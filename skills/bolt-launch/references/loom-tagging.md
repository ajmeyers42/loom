# Loom engagement tagging (D-026)

Every deployable asset that supports **tags** (or equivalent metadata) must carry a **loom**
tag so operators can **search**, **filter**, and **correlate** demo resources in Kibana and APIs,
and to complement **INDEX_PREFIX** teardown (indices are already namespaced by name).

## Canonical tag string

Use exactly **one** string in each `tags` array (merge with any engagement-specific tags already
in the payload):

```text
loom:<engagement_id>
```

**`<engagement_id>`** (lowercase, no hyphens or underscores):

1. If **`DEMO_ASSET_TAG`** is set in `.env` — use its value after stripping outer whitespace
   and normalizing per (2).
2. Else if **`INDEX_PREFIX`** is non-empty — normalize `INDEX_PREFIX`.
3. Else — normalize **`DEMO_SLUG`**.

**Normalization:** Remove ASCII hyphens, underscores, and whitespace; lowercase. If the result
is empty, use `demo`.

#### Examples

| `.env` | `<engagement_id>` | Tag |
| --- | --- | --- |
| `INDEX_PREFIX=cb-` | `cb` | `loom:cb` |
| `INDEX_PREFIX=2026citizens-ai` | `2026citizensai` | `loom:2026citizensai` |
| `INDEX_PREFIX=` and `DEMO_SLUG=citizens-bank` | `citizensbank` | `loom:citizensbank` |
| `DEMO_ASSET_TAG=acme_poc` | `acmepoc` | `loom:acmepoc` |

## Why `INDEX_PREFIX` first when set

On **shared clusters**, `INDEX_PREFIX` is the namespace boundary for Elasticsearch resources and
teardown; normalizing it for tags keeps the tag aligned with that namespace. When the prefix is
blank (dedicated cluster), **`DEMO_SLUG`** identifies the engagement.

## Where to apply

Include **`loom:<engagement_id>`** in `tags` (or product-specific metadata) for every
**create** payload that supports it, including when not exhaustive:

- Observability **SLOs**
- **Alerting** rules and **connectors** (where the API exposes `tags`)
- **ML** anomaly detection jobs (and other ML entities that accept `tags`)
- **Agent Builder** agents and tools (`tags` arrays)
- **Transforms** / **rollup** jobs if created and tagged by API
- **Security** detection rules / exceptions — when the API supports tags or metadata for filtering

**Elasticsearch indices and templates** are already distinguished by **`p(name)`** / `INDEX_PREFIX`;
do not invent index-level tags unless the product documents a supported field.

**Saved objects (NDJSON import):** API `tags` on other assets do not apply. After import, run
**`kibana/apply_loom_tags.py`** (engagement-local script; Citizens POC includes it): it creates a
**tag** saved object (`type: tag`, id `loom-<engagement_id>`) and **PUT**s each NDJSON object
with a `references` entry to that tag. **`wind_pulse.py`** warns if the reference is missing.
Alternatively, re-export NDJSON from Kibana after tagging once in the UI.

## Bootstrap helper (Python)

```python
import os
import re

def _engagement_id_for_tag() -> str:
    override = os.environ.get("DEMO_ASSET_TAG", "").strip()
    raw = override or (
        os.environ.get("INDEX_PREFIX", "").strip()
        or os.environ.get("DEMO_SLUG", "demo")
    )
    s = re.sub(r"[-_\s]+", "", raw).lower()
    return s or "demo"

def loom_tags() -> list[str]:
    return [f"loom:{_engagement_id_for_tag()}"]

# Example: merge into an existing tags list
# body["tags"] = sorted(set((body.get("tags") or []) + loom_tags()))
```

## Teardown

**wind-reset** remains **prefix-scoped** for Elasticsearch deletes. Tags help **find** demo
assets in UIs and **Kibana** management views; they do not replace `INDEX_PREFIX` safety checks.
