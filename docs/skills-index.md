# Skills Index

Use `loom` when you want the guided end-to-end pipeline. Use an individual skill when you know the exact stage you want to run or refresh.

## Guided Pipeline

| Skill | Use when | Primary outputs |
|---|---|---|
| `loom` | Build or resume a complete engagement from any combination of discovery notes, diagnostics, and existing outputs | Runs the pipeline, skips completed stages, delivers the final handoff |

## Planning and Qualification

| Skill | Use when | Primary outputs |
|---|---|---|
| `warp-spark` | No discovery notes exist yet and the SA needs help choosing a demo direction, archetype, and wow moments | `{slug}-ideation.md` |
| `warp-listen` | Discovery notes, meeting notes, or sales notes need to become structured customer context | `{slug}-discovery.json`, `{slug}-confirmation.md`, `{slug}-gaps.md` |
| `warp-scan` | Elastic diagnostic ZIPs or API exports need to become a current-state profile | `{slug}-current-state.json`, `{slug}-architecture.md`, `{slug}-findings.md` |
| `thread-qualify` | Parsed discovery and diagnostics need MEDDPIC qualification and SDR/AE/SA team alignment before demo planning | `{slug}-opportunity-summary.md`, `{slug}-opportunity-profile.json` |
| `thread-audit` | Planned scope needs to be checked against version, license, deployment type, and known platform constraints | `{slug}-platform-audit.json`, `{slug}-platform-audit.md` |

## Demo Design

| Skill | Use when | Primary outputs |
|---|---|---|
| `weave-script` | Discovery and platform audit are ready and the SA needs a solution-first demo script and AE brief | `{slug}-demo-script.md`, `{slug}-demo-brief.md` |
| `weave-query` | Script has 5+ ES\|QL queries, semantic/RAG search, or integration-grounded data (Fleet/Beats) — run before weave-model | `{slug}-vulcan-queries.json`, `{slug}-vulcan-data-profile.json`, `vulcan-data/*.csv` |
| `weave-model` | The script is ready and the demo needs indices, mappings, data streams, pipelines, seed data, and build order | `{slug}-data-model.json`, `{slug}-data-model.md`, mapping files |
| `weave-train` | The script includes ML anomaly detection, data frame analytics, anomaly injection, or model deployment scenes | `{slug}-ml-config.json`, `{slug}-ml-setup.md` |
| `weave-agent` | The script includes Elastic Agent Builder custom agents, tools, workflows, or multi-agent orchestration | `{slug}-agent-builder-spec.md` |
| `weave-cost` | Agent Builder or another AI component is in scope and the demo should include AI cost and usage transparency | `{prefix}agent-sessions` spec, AI Cost + Usage dashboard guidance |

## Readiness, Deploy, and Operations

| Skill | Use when | Primary outputs |
|---|---|---|
| `finish-check` | The planning/build artifacts are ready and the SE needs a pre-demo checklist and go/no-go risk register | `{slug}-demo-checklist.md`, `{slug}-risks.md` |
| `bolt-spin` | A new Elastic Cloud deployment or Serverless project is needed, or a reusable `.env` must be prepared | `.env`, `.env.example`, `{slug}-provision-log.md` |
| `bolt-launch` | The SA approved live cluster changes and wants `bootstrap.py` generated or executed | `bootstrap.py`, `{slug}-deploy-log.md` |
| `wind-pulse` | A deployed demo needs a quick health/readiness pulse check before the meeting | Terminal readiness report |
| `wind-reset` | A deployed demo should be cleaned up after the meeting | `teardown.py`, `{slug}-teardown-log.md` |

## Invocation Tips

- If you have raw notes and want a full build, invoke `loom`.
- If you already have `{slug}-discovery.json` and only want qualification, invoke `thread-qualify`.
- If you only changed the storyline, rerun `weave-script`, then rerun downstream affected stages (`weave-model`, `weave-train` if relevant, and `finish-check`).
- If Agent Builder appears in the script, run `weave-agent` and `weave-cost` before deploy planning.
- If the script has 5+ ES|QL queries, semantic search, or Fleet/Beats integrations, run `weave-query` before `weave-model` to get cluster-validated queries and synthetic CSV data.
- If you only need to check the environment on demo morning, invoke `wind-pulse`; do not rerun the whole pipeline.
