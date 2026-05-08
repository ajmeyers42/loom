# weave-pipe

**Status: BACKLOG — not yet implemented**
**Scoped: 2026-05-01**

## Purpose

Designs and generates Elasticsearch ingest pipeline definitions from a field mapping specification. Produces deployment-ready pipeline JSON artifacts consumed by `wind-streams` (for Streams wiring) or directly deployed by `bootstrap.py` step 4. Handles field extraction, ECS normalization, enrichment processor wiring, and routing logic.

## When to Use

- Demo requires showing real log parsing (grok/dissect on raw log lines)
- Streams-based ingest needs pipeline processors defined before stream creation
- Fleet integration defaults are insufficient and custom processing is required
- Customer wants to see how raw vendor logs (Nvidia, Run.ai, K8s) are normalized to ECS
- Enrich processor demonstrations (tenant rate card lookup, geo_ip, user-agent)

## Trigger Phrases

"design the ingest pipeline", "write the grok pattern", "parse the logs", "normalize to ECS", "create the pipeline for {source}", "wire the pipeline", "define processors for {stream}"

## Inputs

- `data-model.json` — field schemas and source log formats
- `demo-script.md` — identifies which log parsing steps need to be visible in the demo
- Raw log sample strings (if provided by user or generated synthetically)
- Optional: explicit processor list, grok patterns, enrichment targets

## Outputs

- `data/ingest-pipelines/` directory containing one JSON file per pipeline:
  - `{slug}-{source}-pipeline.json` — full pipeline definition with processors array
  - `{slug}-pipelines-manifest.json` — index of all pipelines, their source streams, and processor summary
- Updates `data-model.json` to record pipeline names alongside their target indices/streams
- Adds pipeline deployment to `bootstrap.py` step 4

## Key Capabilities to Implement

### 1. Source log format analysis
- Accept raw log sample lines and infer structure (structured JSON vs. unstructured text)
- For JSON logs: generate `json` processor + field rename/copy to ECS
- For unstructured text: generate grok pattern with named captures

### 2. ECS normalization
Map vendor-specific fields to ECS equivalents:

| Source field | ECS target |
|---|---|
| `kubernetes.labels.app` | `service.name` |
| `nvidia.nim.latency_ms` | `event.duration` (nanoseconds) |
| `runai.event_type` | `event.action` |
| `log_level` / `severity` | `log.level` |
| `ts` / `time` / `timestamp` | `@timestamp` |

### 3. Processor generation
Support generating the following processor types:
- `grok` — pattern-based field extraction from message
- `dissect` — delimiter-based extraction (faster than grok for predictable formats)
- `json` — parse JSON string in a field
- `set` — derive fields (e.g., `event.dataset` from index name)
- `rename` / `remove` — field normalization and cleanup
- `enrich` — lookup enrichment (requires enrich policy; coordinate with weave-model)
- `date` — timestamp normalization to `@timestamp`
- `pipeline` — sub-pipeline chaining for modular design

### 4. Pipeline chaining for multi-tenant routing
Generate a root pipeline that calls per-tenant sub-pipelines:
```json
{
  "processors": [
    { "pipeline": {
        "if": "ctx.tenant_namespace == 'tenant-a'",
        "name": "{slug}-tenant-a-enrich-pipeline"
    }}
  ]
}
```

### 5. Simulation mode
- Generate a simulated input document and trace it through the pipeline definition
- Output the expected transformed document for review before deployment
- Flag missing fields, type mismatches, or grok pattern failures

### 6. Pipeline artifact format
Each output pipeline file:
```json
{
  "_meta": {
    "engagement": "{slug}",
    "source": "nvidia.nim",
    "version": "1.0.0",
    "generated_by": "weave-pipe"
  },
  "description": "Nvidia NIM inference log normalization — {slug}",
  "processors": [ ... ],
  "on_failure": [
    { "set": { "field": "_index", "value": "failed-{{{_index}}}" }},
    { "set": { "field": "error.message", "value": "{{{_ingest.on_failure_message}}}" }}
  ]
}
```

Always include `on_failure` to prevent pipeline failures from dropping documents.

## Grok Pattern Library (starter set)

Pre-built patterns to include for common demo log sources:

```
NVIDIA_NIM_LOG  %{TIMESTAMP_ISO8601:@timestamp} %{LOGLEVEL:log.level} %{DATA:nim.model} req=%{UUID:nim.request_id} in=%{INT:nim.input_tokens} out=%{INT:nim.output_tokens} lat=%{NUMBER:nim.latency_ms}ms
RUNAI_SCHED_LOG %{TIMESTAMP_ISO8601:@timestamp} \[%{LOGLEVEL:log.level}\] job=%{DATA:runai.job_id} event=%{WORD:runai.event_type} gpu=%{INT:runai.gpu_requested} wait=%{NUMBER:runai.wait_time_sec}s
K8S_CONTAINER   %{TIMESTAMP_ISO8601:@timestamp} %{LOGLEVEL:log.level} %{GREEDYDATA:message}
```

## Relationship to Other Skills

```
weave-model           → defines field schemas (consumed as input)
weave-pipe → produces pipeline JSON artifacts
  └─ wind-streams  → wires pipelines into Streams
  └─ bootstrap.py step 4    → deploys pipelines directly via ES API
```

Independent of `weave-fleet` — Fleet manages its own ingest pipelines internally. This skill is for custom/non-integration sources only.

## Pipeline Position in loom

```
Stage 5 (new): weave-pipe
  → Input:  data-model.json, demo-script.md, optional log samples
  → Output: data/ingest-pipelines/*.json, data/pipelines-manifest.json
  → Runs after: weave-model (Stage 5)
  → Runs before: wind-streams, bootstrap.py
```

## Constraints and Risks

- **Grok compilation**: Patterns must be validated before deployment. Skill should test patterns against sample lines and report failures before writing output files.
- **Enrich processor dependency**: Enrich processors require an enrich policy to exist at deploy time. Skill must declare enrich dependencies and ensure `bootstrap.py` creates enrich policies (step 3) before pipelines (step 4).
- **On_failure required**: All generated pipelines must include `on_failure` handlers. Documents must never be silently dropped by pipeline failures in a demo.
- **Pipeline naming**: Use `{slug}-{source}-pipeline` convention to avoid collisions with system pipelines.

## Acceptance Criteria

- [ ] Given a field schema from `data-model.json`, generates a syntactically valid pipeline JSON
- [ ] Generated pipeline passes `POST /_ingest/pipeline/_simulate` validation against sample docs
- [ ] All `on_failure` handlers present in every generated pipeline
- [ ] ECS normalization applied for all standard vendor fields (see mapping table above)
- [ ] Pipeline artifacts registered in `loom-manifests` for teardown
- [ ] Pipelines deployed idempotently via `bootstrap.py --step 4`
- [ ] Works with both `wind-streams` wiring and direct `_index` pipeline attachment
