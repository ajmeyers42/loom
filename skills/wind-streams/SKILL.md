---
name: wind-streams
description: >
  NOT IMPLEMENTED. If this skill is selected, stop immediately and tell the SA that
  wind-streams is backlog. Do not create Kibana Streams or call a cluster.
  Use the read-only kibana-streams skill to inspect Streams. The notes below are a design sketch only.
status: planned
---

# wind-streams

**Status: BACKLOG — do not execute.**

```
⛔ wind-streams is not implemented.
   Do not create streams, attach pipelines, or call Kibana.
   Inspect existing streams with the kibana-streams skill. Authoring stays with
   finish-verify once a stream schema is confirmed.
```

**Scoped: 2026-05-01. Design notes below are not a procedure.**
**Extends: `kibana-streams` (read-only list/inspect/resync)**

## Purpose

Creates, configures, and wires Kibana Streams with ingest pipelines for demo environments. Kibana Streams (GA in 9.x) provide a named, managed data stream with built-in routing, field mapping, and retention. This skill handles the write-side operations that the existing `kibana-streams` skill does not cover.

## When to Use

- Demo scope includes showing Streams as a product feature (9.x-native ingest story)
- Customer has heterogeneous log sources that benefit from stream-based routing
- Ingest pipeline processing (field extraction, normalization, enrichment) needs to be demonstrated
- Scenario requires both agent-based AND streams-based ingest to coexist
- Customer is evaluating Streams as a replacement for Logstash pipelines

## Trigger Phrases

"create a stream", "wire a stream", "set up Kibana Streams", "configure ingest pipeline for streams", "demo Streams feature", "show stream routing", "wire logs into a stream"

## Inputs

- `data-model.json` — stream definitions, field mappings, ingest pipeline specs
- `weave-pipe` output — pipeline JSON artifacts (if available)
- `.env` — cluster credentials
- Optional: explicit stream name, routing field, retention period, pipeline definition

## Outputs

- `deploy/streams-manifest.json` — list of created streams, pipeline IDs, routing config
- Stream wiring is infrastructure for `finish-verify` / `bolt-bootstrap`, not a `bootstrap-data.py` step
- Prints stream topology: stream name → ingest pipeline → backing index pattern

## Key Capabilities to Implement

### 1. Stream creation
```
PUT /api/streams/{name}
{
  "ingest": {
    "enabled": true,
    "routing": [],
    "processors": []
  }
}
```
- Create a named stream with routing field configuration
- Handle already-existing streams (GET first, skip or update based on flag)
- Register stream in manifest

### 2. Ingest pipeline wiring
- Attach ingest pipeline processors directly to the stream definition
- Support grok, dissect, set, rename, remove, enrich processors
- Validate pipeline syntax before PUT (dry-run mode)

### 3. Routing configuration
- Define routing rules that fork stream output to sub-streams by field value
- Example: route by `tenant_namespace` to per-tenant streams for data isolation
- Generate routing rules from the engagement's tenant list

### 4. Field mapping management
- Apply field mappings to the stream's backing data stream
- Cross-reference with component templates already deployed by bootstrap step 5
- Warn on mapping conflicts

### 5. Retention configuration
- Set stream retention via the Streams API lifecycle settings
- Map engagement ILM policy names to equivalent Streams retention periods

### 6. Resync and validation
- After creation, call resync (`POST /api/streams/{name}/_resync`) to propagate changes
- Validate stream is active and accepting documents
- Write a test document and confirm it was indexed

## Stream Topology for Multi-Tenant Demos

```
logs-{source}               ← root stream (all tenants)
  └─ routing: tenant_namespace
       ├─ logs-{source}-tenant-a   ← per-tenant sub-stream
       ├─ logs-{source}-tenant-b
       └─ logs-{source}-tenant-c
```

This pattern isolates tenant data at the stream level, enabling per-space data views with no additional index-level filtering.

## Relationship to Other Skills

```
weave-pipe → wind-streams → finish-verify / bolt-bootstrap
weave-fleet     ← can coexist; Fleet manages its own indices
```

Streams and Fleet integrations are complementary:
- Fleet Agent → integration-managed indices (system, kubernetes, APM)
- Streams → custom app logs, NIM inference logs, Run.ai events, any non-integration source

## Constraints and Risks

- **Kibana Streams requires 9.x** — not available on 8.x clusters. Skill must check version gate.
- **Tech preview features** must be enabled per Kibana space before Streams UI is visible. Skill should warn and document the manual enablement step.
- **Pipeline conflicts**: if an ingest pipeline is already attached to an index pattern via an index template, adding a Streams pipeline may create duplicate processing. Skill must detect.
- **Serverless**: Streams availability on Serverless may differ by project type. Check before attempting creation.

## Pipeline Position

```
weave-model → weave-pipe → wind-streams → finish-verify / bolt-bootstrap
```

## Acceptance Criteria

- [ ] Stream creation is represented in the asset bundle and applied as infrastructure, not by this skill
- [ ] Per-tenant routing correctly isolates documents to sub-streams
- [ ] Re-run is idempotent (streams already exist → skip, not error)
- [ ] Resync completes without errors after creation
- [ ] Test document validates end-to-end pipeline execution
- [ ] `teardown.py` deletes all created streams and their backing data streams
- [ ] Works on ECH 9.x (Streams GA); warns gracefully on unsupported versions
