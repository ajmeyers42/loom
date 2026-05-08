---
name: warp-scan
description: >
  Parses Elastic diagnostic files — ZIP archives from the Elastic Support Diagnostic tool,
  or individual JSON exports from a running cluster — to produce a structured current-state
  profile of a customer's Elastic deployment. Outputs three files: a machine-readable JSON
  profile (consumed by downstream pipeline skills), a human-readable architecture summary,
  and an internal findings report mapping discovered issues to Elastic features that resolve them.

  ALWAYS use this skill when the user provides Elastic diagnostic files, cluster exports, or
  says "analyze this diagnostic", "parse the diagnostic", "what's their current state",
  "assess their Elastic setup", "what version are they on", or provides a .zip file described
  as coming from an Elastic cluster or the support diagnostic tool. Also trigger when
  warp-listen output mentions diagnostic files are pending or when the user asks to
  "complete the discovery profile" with cluster data.
---

# Demo Diagnostic Analyzer

You are reading the output of an Elastic Support Diagnostic or equivalent cluster export to
build a structured picture of the customer's current Elastic deployment. This feeds into the
demo-builder pipeline — specifically, it informs what migration path to recommend, what
features are already in use (and therefore safe to demo with minimal explanation), and where
the gaps are that Elastic's current capabilities can close.

## Step 1: Identify What You Have

Diagnostic input comes in several forms. Identify which you have before extracting:

**ZIP archive (Elastic Support Diagnostic tool):** Contains many JSON files in a structured
directory. Extract and read the key files listed in Step 2. File paths follow a consistent
pattern: `<cluster-name>-diagnostics-YYYYMMDD-HHMMSS/`.

**Individual JSON exports:** Customer may paste or share specific API responses — `GET /_nodes`,
`GET /_cluster/health`, `GET /_cat/indices?v&format=json`, etc. Read what's available; note
what's missing and its impact.

**Mixed:** Diagnostic ZIP plus additional files the SE/AE collected separately (e.g., a
screenshot of the monitoring UI, notes about specific indices). Reconcile all sources.

**Note what's missing.** If a key file isn't in the archive, note it in gaps — don't guess.
Missing data is not the same as a zero value.

## Step 2: Extract the Structured Profile

Read the following files from the diagnostic (priority order — stop when you have enough for
the task, but always get cluster health and nodes):

| File | What to Extract |
|------|----------------|
| `cluster_health.json` | status (green/yellow/red), node count, active shards, unassigned shards |
| `nodes.json` | per-node: version, roles, OS (name/arch), JVM version, installed plugins |
| `nodes_stats.json` | per-node: heap_used_percent, disk.used_percent, CPU percent |
| `cluster_stats.json` | total docs, total store size, indices count |
| `license.json` | type (basic/gold/platinum/enterprise/trial), expiry date |
| `_cat/indices.json` or `indices.json` | per-index: health, doc count, store size, status |
| `ilm_policies.json` | ILM policies defined (none → missing ILM, a gap to flag) |
| `cluster_settings.json` | persistent settings that affect behavior (ML enabled, security, etc.) |
| `mappings.json` | detect legacy patterns: `text` fields without `keyword` subfield, no `semantic_text`, large nested objects |
| `ml/anomaly_detectors.json` or `ml/jobs.json` | ML jobs configured (any → ML in use; none → opportunity) |
| `snapshots.json` or `_snapshot/*/` | snapshot repos and policies (none → data resilience gap) |
| `security.json` or `xpack.security` in settings | security enabled? TLS configured? |

Populate this JSON schema:

```json
{
  "meta": {
    "diagnostic_source": "support_diagnostic_zip | api_export | manual_notes | mixed",
    "diagnostic_date": "",
    "cluster_name": "",
    "extraction_confidence": "low | medium | high",
    "missing_files": []
  },
  "cluster": {
    "version": "",
    "health_status": "green | yellow | red | unknown",
    "deployment_type": "self_managed | eck | elastic_cloud_hosted | elastic_cloud_serverless | unknown",
    "license_type": "basic | gold | platinum | enterprise | trial | unknown",
    "license_expiry": "",
    "security_enabled": null,
    "tls_enabled": null
  },
  "nodes": {
    "total_count": null,
    "master_eligible_count": null,
    "data_node_count": null,
    "ml_node_count": null,
    "coordinating_only_count": null,
    "ingest_node_count": null,
    "node_details": [
      {
        "name": "",
        "roles": [],
        "version": "",
        "heap_max_gb": null,
        "heap_used_percent": null,
        "disk_total_gb": null,
        "disk_used_percent": null,
        "cpu_percent": null,
        "os": "",
        "jvm_version": "",
        "plugins": []
      }
    ]
  },
  "indices": {
    "total_count": null,
    "total_docs": null,
    "total_store_gb": null,
    "red_count": null,
    "yellow_count": null,
    "unassigned_shards": null,
    "notable": [
      {
        "name": "",
        "health": "",
        "doc_count": null,
        "store_gb": null,
        "notes": ""
      }
    ]
  },
  "features_in_use": {
    "ilm": null,
    "slm": null,
    "ml_anomaly_detection": null,
    "ml_nlp": null,
    "semantic_text": null,
    "elser": null,
    "apm": null,
    "fleet": null,
    "security": null,
    "cross_cluster_replication": null,
    "cross_cluster_search": null,
    "snapshots_configured": null,
    "data_streams": null,
    "runtime_fields": null
  },
  "resource_signals": {
    "heap_pressure": "healthy | elevated | high | critical | unknown",
    "disk_pressure": "healthy | elevated | high | critical | unknown",
    "shard_density_signal": "healthy | elevated | high | unknown",
    "notes": ""
  },
  "mapping_patterns": {
    "has_legacy_mappings": null,
    "has_semantic_text": null,
    "dynamic_mapping_heavy": null,
    "notes": ""
  },
  "gaps": [
    {
      "field": "",
      "question": "",
      "impact": "blocks_assessment | reduces_accuracy | low"
    }
  ]
}
```

**Resource signal thresholds** (use these to populate `resource_signals`):
- Heap: < 60% → healthy, 60–75% → elevated, 75–85% → high, > 85% → critical
- Disk: < 70% → healthy, 70–80% → elevated, 80–90% → high, > 90% → critical
- Shard density: Check both dimensions:
  - Shards/GB of data: < 0.1 shards/GB (>10GB avg shard) may indicate very large shards; > 20 shards/GB indicates many tiny shards (inefficient). Healthy range: 0.1–20.
  - Shards/node vs heap: (total shards / node count) / heap_GB_per_node. < 20 → healthy, 20–40 → elevated, > 40 → high. This is the more operationally significant metric.
- Note: disk watermarks may be set as absolute byte values on large-disk nodes — check cluster_settings.json before assuming percentage-only thresholds apply.

## Step 3: Generate Findings

This is the analytical core. For each finding, connect what you observed in the diagnostic
to a specific Elastic capability that addresses it. Findings are only useful if they're
actionable — don't list a finding unless you can name the feature that resolves it.

**Finding categories:**

**Version currency** — If the cluster is more than one minor version behind the current
release, flag the gap and note what capabilities they're missing. Don't list every feature;
pick the 2–3 most relevant to a typical demo scenario (ELSER, Agent Builder, Workflows, etc.).

**Resource health** — Elevated heap/disk/shard density deserves a finding. Frame it as an
operational risk, not a failure. Include the specific metric and threshold.

**ILM/lifecycle** — No ILM policies means data management is manual. Flag it. ILM with hot
only (no warm/cold/delete) means they're not getting cost efficiency.

**ML readiness** — No ML nodes or ML jobs means the ML demo layer needs more setup discussion.
ML nodes with high heap may constrain the anomaly demo.

**Semantic search readiness** — No `semantic_text` mappings and no ELSER endpoint means the
RAG/semantic demo needs either mapping migration or a new index. Call this out specifically —
it's a common demo blocker.

**Snapshot / resilience** — No snapshot repos configured is a genuine risk finding, not just
a gap. Frame it seriously.

**Shard health** — Red indices or high unassigned shard count blocks demos that touch those
indices. Must be flagged if present.

**Legacy mappings** — `text` fields without `.keyword` subfields, missing `doc_values`, or
heavy use of dynamic mapping in high-cardinality indices — all common sources of performance
pain that Elastic's current mapping templates address.

## Step 4: Write the Three Output Files

Derive the slug from the cluster name or company name if available (lowercase, hyphens).
Example: `"prod-cluster-lowes"` → `lowes`, `"thermo-fisher-es01"` → `thermo-fisher`.
If a `demo/{slug}-discovery.json` already exists from warp-listen, use the same slug.

### Output 1: `demo/{slug}-current-state.json`

The populated JSON from Step 2. Valid JSON. Every null field with meaningful impact gets a
corresponding gaps entry. Include a `findings_summary` array at the root level:

```json
{
  ...schema above...,
  "findings_summary": [
    {
      "id": "F-01",
      "category": "version_currency | resource_health | ilm | ml_readiness | semantic_readiness | resilience | shard_health | mapping",
      "severity": "critical | high | medium | low",
      "title": "",
      "observation": "",
      "elastic_capability": "",
      "demo_impact": "blocks_demo | reduces_realism | talking_point | none"
    }
  ]
}
```

### Output 2: `demo/{slug}-architecture.md`

A human-readable description of the customer's current Elastic deployment, written for a
technical audience. This will be used to create an architecture diagram — write it so someone
building a diagram has everything they need.

Structure:
```
# Current Architecture — [Company / Cluster Name]
**Assessed:** [date] | **Cluster Version:** [version] | **License:** [type]

## Cluster Topology
[Table or prose: node roles, count, specs. Be specific — "3 data nodes (128GB heap each),
1 dedicated master, 1 ML node (64GB heap)" not just "4 nodes".]

## Data Layer
[Notable indices by size/purpose. Data streams if any. Total footprint.]

## Features Active
[Bulleted list of what's actually running: ILM, ML jobs, security, APM, etc.]

## Resource Health
[Current heap/disk/shard density signals with specific numbers where available.]

## Version Context
[What version they're on, what the current release is, key capabilities they're missing.]
```

### Output 3: `demo/{slug}-findings.md`

Internal — not sent to the customer. Organizes the findings by severity.

```
# Diagnostic Findings — [Company / Cluster Name]

## Critical / High
[Each finding: observation, the specific Elastic capability that addresses it, demo impact]

## Medium
[Same]

## Low / Informational
[Same]

## Demo Readiness Assessment
[One paragraph: what's ready to demo now, what needs setup before the demo, what needs a
conversation about the customer's environment rather than a live demo.]
```

Close with: "Safe to proceed to demo build" or "Review [specific finding] before scoping demo."

## What Good Looks Like

**Healthy, modern cluster:** Green health, recent version, ILM configured, ML running, ELSER
endpoint active. Findings are medium/low — opportunity notes, not blockers. Architecture doc
is thorough. Demo readiness assessment says "safe to proceed."

**Outdated self-managed:** 7.x cluster, no ML nodes, no ILM, basic license, red/yellow
indices. Findings are high/critical. Version gap finding names the 3–4 most relevant
capabilities they're missing. Demo readiness says "recommend migration assessment path."

**Healthy cloud, feature gaps:** Modern version, green health, but no ELSER endpoint deployed,
no ML jobs, `text` mappings throughout. Findings are medium — good baseline, needs feature
enablement before semantic or ML demo. Demo readiness says "2–3 setup steps required."

**Partial data only:** Customer sent only `GET /_cat/indices` output and a version string.
Extract what's there. Gaps section is prominent. Architecture doc is shorter. Findings are
appropriately hedged. Ask for the full diagnostic in the gaps/follow-up section.
