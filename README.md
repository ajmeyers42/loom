# loom

An agent-driven pipeline that turns customer discovery notes into a fully deployed Elastic demo — mappings, data, ML jobs, dashboards, Agent Builder agents, Workflows, and SIEM rules — without the SA having to hand-write scripts or click through Kibana.

Drop in discovery notes (and optionally a diagnostic export) and say **"build the demo for [company]"**. The assistant runs each stage in order, skips completed work on re-runs, and delivers a ready-to-present environment.

## Why use it

- **Discovery → demo in one session.** No manual index design, no copy-pasting curl commands, no dashboard JSON assembly.
- **Consistent, repeatable.** Every engagement gets the same pipeline: structured discovery profile, platform audit, versioned script, data model, bootstrap script, pre-demo checklist.
- **Agent-first.** The assistant executes; you review and approve before anything touches a live cluster.
- **Elastic 9.4+ native.** Scripts target supported APIs and correct field types — nothing that fails on a real cluster.

## Prerequisites

| Requirement | How to satisfy |
|---|---|
| **Cursor** or **Claude Code** | The assistant drives the pipeline; you provide inputs and approvals |
| **Python 3** | Required for `bootstrap.py`, `teardown.py`, `demo_status.py` |
| **elastic/agent-skills** (full install) | `npx skills add elastic/agent-skills` — install all skill areas (Search, Observability, **Security**) |
| **elastic/hive-mind** | `git clone https://github.com/elastic/hive-mind ../hive-mind` — sibling clone is the default; set `HIVE_MIND_PATH` if you keep it elsewhere |
| **Elastic Cloud API key** | Run the `cloud-setup` skill once to set `EC_API_KEY` |
| **`DEMOBUILDER_ENGAGEMENTS_ROOT`** | Optional. Defaults to `~/engagements`. Set in your shell profile to use a different root. |

> **hive-mind location matters.** The skill symlinks in `.cursor/skills/`, `.claude/skills/`, and `.agents/skills/` point to `../hive-mind/skills/`. Clone hive-mind into the same parent directory as loom and the links resolve automatically. If your clone lives elsewhere, set `HIVE_MIND_PATH` and re-link using [Dependencies](docs/dependencies.md).

## Quick Start

```
git clone https://github.com/elastic/demobuilder
git clone https://github.com/elastic/hive-mind ../hive-mind
npx skills add elastic/agent-skills
```

Open `loom` in Cursor (or Claude Code — see [docs/runtimes/claude.md](docs/runtimes/claude.md)), then:

1. Paste your discovery notes into the chat.
2. Say **"build the demo for [Company]"**.
3. The `loom` orchestrator runs the pipeline, asks for approvals before any cluster spend, and delivers a complete engagement workspace under `~/engagements/{slug}/`.

For runtime-specific setup (MCP, rules, plugin paths): [Cursor](docs/runtimes/cursor.md) · [Claude Code](docs/runtimes/claude.md)

## What's inside

| | |
|---|---|
| [Pipeline & skills](docs/pipeline.md) | Stage-by-stage overview, skills table, outputs, validation coverage |
| [Skills index](docs/skills-index.md) | When to invoke the full orchestrator vs. a specific skill |
| [Design principles](docs/design-principles.md) | Why things work the way they do — API baseline, tagging, ILM, EIS, approvals |
| [JSON schemas](schemas/README.md) | Versioned contracts for machine-readable pipeline outputs |
| [Dependencies](docs/dependencies.md) | Full setup for `elastic/agent-skills` and `elastic/hive-mind` |
| [Architecture decisions](docs/decisions.md) | Decision log D-001 – D-036 with rationale |
| [Engagement workspace layout](docs/engagements-path.md) | Where output files go, env var override, multi-customer isolation |
| [Open items / setup checklist](docs/todo.md) | Things requiring one-time user action before a run |
