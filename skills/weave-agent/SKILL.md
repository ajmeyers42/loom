---
name: weave-agent
description: >
  Produces a concrete Elastic Agent Builder definition for a loom engagement: agent
  name, system instructions, behaviors, tool list (ES|QL, index search, workflow tools), and
  workflow linkage. Aligns with Kibana 9.3+ Agent Builder (GA on Elastic Stack since 9.3).
  Use when the demo script includes a custom agent (e.g. Fraud Assistant), when the SA asks
  to "define the Agent Builder agent", "spec the Kibana agent", or when refreshing agent
  prompts/tools after script changes. Does not replace bootstrap.py or elastic/agent-skills
  for API execution — it documents what to build in Kibana.

  ALWAYS use this skill when the user is defining or revising an Agent Builder agent for a
  customer demo scripted in loom.
---

# Demo Kibana Agent Design (Agent Builder)

You are specifying how the SE implements **Elastic Agent Builder** in Kibana for a demo. Ground everything in the **demo script**, **discovery JSON**, and **platform audit**. Official product entry point and UI paths: **[Get started with Elastic Agent Builder](https://www.elastic.co/docs/explore-analyze/ai-features/agent-builder/get-started)** (Elastic Docs).

## Canonical references (read before writing)

- **This repo:** `skills/bolt-launch/references/workflow-patterns.md` — workflow `id` vs name, Agent Builder tool wiring, stale-read warning, workflow DELETE and search-by-name API.
- **hive-mind (adopt these — D-034):**
  - `hive-mind/patterns/agent-builder/AGENT_BUILDER_API_MANAGEMENT.md` — CRUD API for agents and tools (tool types, system prompt design, agent cloning pattern)
  - `hive-mind/patterns/agent-builder/WORKFLOW_INTEGRATION.md` — wiring workflows as agent tools
  - `hive-mind/patterns/agent-builder/A2A_COORDINATOR_PATTERN.md` — multi-agent orchestration (for stretch scenarios)
- **Elastic org:** **[elastic/workflows](https://github.com/elastic/workflows)** — Elastic Workflow Library (YAML examples, docs). Local clone: `~/Documents/GitHub/workflows`. Prefer this for workflow *authoring*; use `workflow-patterns.md` for Kibana API + agent handoff.
- **Elastic Docs:** [Agent Builder get started](https://www.elastic.co/docs/explore-analyze/ai-features/agent-builder/get-started), [custom agents](https://www.elastic.co/docs/explore-analyze/ai-features/agent-builder/custom-agents), [custom tools](https://www.elastic.co/docs/explore-analyze/ai-features/agent-builder/tools/custom-tools).

## Step 1: Confirm scope

From `demo/{slug}-platform-audit.json` and cluster version: Agent Builder must be **available** (e.g. Elastic Stack **9.3+** GA per docs; Serverless as documented). If not green, say so and point to audit remediation — do not write a full agent spec that cannot run.

## Step 2: Name and role

- **Agent display name** — customer-facing (e.g. `Fraud Assistant`).
- **One-line role** — what the agent does for the champion vs leadership (POC boundaries).

## Step 3: System instructions (prompt)

Write **copy-paste-ready** agent instructions that:

1. **Ground** answers in named indices/data streams and KB indices from the data model (no invented `claim_id` / IDs).
2. **Route behavior:** when to use **ES|QL tools** vs **index search** vs **workflow tool**.
3. **Link** to the customer SLA language from discovery (e.g. acknowledge vs resolve windows).
4. **Safety:** POC only; no production or PII claims.

## Step 4: Tools (9.4+ Agent Builder v0.2.0)

List each tool with **type** and **purpose**. Reference `hive-mind/patterns/agent-builder/AGENT_BUILDER_API_MANAGEMENT.md` for the current API shape.

| Type | Use |
|------|-----|
| **ES|QL** | Parameterized queries the SA tests in the tool editor (SLA breakdowns, aggregations, lookups). Parameter `type` values must use ES-style types: `keyword`, `text`, `integer`, `date`. |
| **Index search** | Scoped to one index pattern; semantic/policy questions, document retrieval. Use `index_search` tool type (9.4+). |
| **Workflow** | **Workflow `id`** (from API) that performs an action — not the workflow *name*. Obtain `id` from POST response; do not re-fetch. |
| **Platform built-in** | `platform.core.create_visualization`, `platform.core.index_explorer` — add these to `tool_ids` to give the agent UI creation capability. |

**Platform skills** (`configuration.skill_ids`) — these are capability bundles separate from tools:
- `data-exploration` — enables the agent to run ES|QL analytics autonomously
- `visualization-creation` — enables the agent to create charts and dashboards
- Probe `GET /api/agent_builder/skills` to confirm available skill IDs before deploying

**Agent configuration shape (9.4+, D-029):**
```json
{
  "configuration": {
    "instructions": "...",
    "tools": [{"tool_ids": ["tool-id-1", "tool-id-2", "platform.core.create_visualization"]}],
    "skill_ids": ["data-exploration", "visualization-creation"]
  }
}
```

Do **not** specify **MCP tools** unless the SA explicitly asks — default loom demos use Elastic-native tools only.

## Step 5: Workflow linkage

- Name the **workflow** as scripted in `demo/{slug}-demo-script.md`.
- Create workflow first → capture **`id`** from POST response → attach as **Workflow tool** in Agent Builder per `workflow-patterns.md`.
- Do NOT re-fetch workflow ID after creation — use the value directly from POST response (stale-read risk).
- Reference `hive-mind/patterns/agent-builder/WORKFLOW_INTEGRATION.md` for the exact API wiring pattern.

## Step 5b: Agent Cloning pattern (for multi-tenant or shared cluster demos)

When the same agent needs to run in multiple engagement spaces on the same cluster, or when
you need to adapt an existing Elastic-managed agent without modifying it:

```python
# GET base agent
base = kb("GET", f"/api/agent_builder/agents/{source_agent_id}")
# Strip read-only fields
clone = {k: v for k, v in base.items()
         if k not in ("id", "created_at", "updated_at", "created_by", "updated_by")}
# Apply engagement-specific customization
clone["name"]        = f"[{SLUG}] {base['name']}"
clone["configuration"]["instructions"] = custom_instructions
# POST as new agent
resp = kb("POST", "/api/agent_builder/agents", clone)
```

Reference: `hive-mind/patterns/agent-builder/AGENT_BUILDER_API_MANAGEMENT.md`.

## Step 6: Output

Write **`demo/{slug}-agent-builder-spec.md`** in the engagement `demo/` subfolder (`$LOOM_ENGAGEMENTS_ROOT/{slug}/demo/`) containing:

- Prerequisites (Kibana URL, privileges — link [permissions doc](https://www.elastic.co/docs/explore-analyze/ai-features/agent-builder/permissions) if needed).
- Navigation (Agents, **AI Agent** button — per get-started doc for the deployment type).
- Full **system instructions** block.
- **Tools** table + test prompts for each tool.
- **Demo prompts** (3–5) copied from or aligned with the demo script scenes.

If the SA only wants an inline section inside `{slug}-demo-script.md`, merge the same content there instead of a separate file — but prefer a **spec file** in `demo/` when tools/workflows are non-trivial so `bolt-launch` / SA handoff stays traceable.

## Handoff

Point the SA to **elastic/agent-skills** for Kibana API automation if they generate configs via API; otherwise UI build following the spec is sufficient for POC.
