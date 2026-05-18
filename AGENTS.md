# Loom — agent instructions

This repository is meant to be driven by an **assistant** (Cursor, Claude Code, Elastic Agent, or similar) helping a **Solutions Architect**, not by asking the SA to manually run repo scripts as the primary path.

## Canonical behavior

1. **Orchestrator:** Read and follow [`skills/loom/SKILL.md`](skills/loom/SKILL.md). Sub-skills live alongside it under [`skills/`](skills/).
2. **Outputs:** Write all engagement artifacts under **`$LOOM_ENGAGEMENTS_ROOT/{slug}/`** (`{slug}` = one engagement). If **`LOOM_ENGAGEMENTS_ROOT`** is unset, default to **`$HOME/engagements`** (see [`docs/engagements-path.md`](docs/engagements-path.md)). The git repo holds pipeline code only (`skills/`, `docs/`), not customer workspaces. Only ask the SA for a different root if they need a non-default path.
3. **Execution:** Run terminal commands, API calls, and skill workflows **on behalf of the SA** when they agree — scripts in this repo are **backends**, not the SA’s homework.
4. **Approvals:** Do **not** run `bolt-spin` or `bolt-launch` (create/spend cloud resources, mutate clusters, run `bootstrap.py` against a **live** cluster) until the SA has **explicitly** asked to provision or deploy **and** has **reviewed** the generated **`bootstrap.py`**, **`{slug}-platform-audit`**, **`{slug}-risks`**, **`{slug}-demo-checklist.md`**, and any other analysis outputs the deploy depends on. Generating or editing those artifacts, or running **`bootstrap.py --dry-run`**, does **not** require cluster access. See `docs/decisions.md` **D-024**.

5. **Elastic version:** For **new** cloud deployments or Serverless projects, default to the **latest GA** stack for that product unless the SA specifies a version. For **existing** deployments, **resolve and validate** `version` (e.g. `GET /`, Kibana `/api/status`, or diagnostic output) **before** producing scripts, data models, or step-by-step plans. Scope all guidance, ES|QL, and API usage to that version (and deployment type).

6. **Enterprise scope and solution areas:** Prefer **enterprise-appropriate** Elastic capabilities that address the customer outcomes in the inputs (discovery, diagnostics, team notes, **architecture diagrams** when supplied). Demos may center **search**, **Observability**, **Security**, or a **deliberate mix** — use cross-solution storylines when that best matches the customer need; do not default to core-search-only unless the artifacts are search-only.

7. **Solution first:** Scripts and plans should **lead with outcomes** tied to the customer’s **key asks** from discovery, then show **supporting capabilities**. If those asks are not clear, **ask the SA** before locking the storyline.

8. **Deployable on Elastic; Elastic datatypes:** Do not define assets (mappings, tools, rules,
   dashboards, APIs, ES|QL) that cannot be applied on a real cluster with supported payloads.
   Use **Elasticsearch field types**, **Kibana/Security/Observability API shapes** for the target
   version, and **product conventions** from `elastic/agent-skills` and reference repos — not
   invented types or generic JSON. See `docs/decisions.md` **D-025**.

9. **Engagement tagging (D-026):** Every asset with a `tags` field must carry `loom:<engagement_id>` — see **`skills/bolt-launch/references/loom-tagging.md`** for the full spec, helper functions, and NDJSON post-import tagging.

## Runtime-specific setup

| Runtime | Audience | Setup |
|--------|--------|--------|
| **Cursor** | Solutions Architects | [`docs/runtimes/cursor.md`](docs/runtimes/cursor.md) |
| **Claude Code / Claude projects** | Solutions Architects | [`docs/runtimes/claude.md`](docs/runtimes/claude.md) |
| **Gemini Gem** | SDRs / AEs (non-technical) | [`docs/runtimes/gem.md`](docs/runtimes/gem.md) — uses `warp-discovery` skill only; no SA pipeline stages |
| **Slack bot** | SDRs / AEs (non-technical) | `deployments/slack/` — deferred pending IT approval |

Do **not** duplicate skill bodies per runtime. One [`skills/`](skills/) tree; deployment-target artifacts live under [`deployments/`](deployments/). The `warp-discovery` bundle is the single source for all SDR/AE targets — see [`skills/warp-discovery/components.md`](skills/warp-discovery/components.md) for the update workflow.

## Research, skills, and external sources

When looking for **additional skills**, **implementation details**, or **product facts** not already in context:

1. **This repository first** — search [`skills/`](skills/), [`docs/`](docs/), and the repo root before reaching outside the workspace.
2. **Elastic org next** — prefer **[github.com/elastic](https://github.com/elastic)** repositories (e.g. **[elastic/agent-skills](https://github.com/elastic/agent-skills)**, **[elastic/workflows](https://github.com/elastic/workflows)** for Kibana Workflow YAML/examples, **[elastic/integration-packages-slo](https://github.com/elastic/integration-packages-slo)** for SLO / Observability integration-package patterns in Cursor, product repos, public examples). Use these when the answer is not in-repo.
3. **General web or non-`elastic` sources** — **do not treat as authoritative** for loom work. **Ask the SA for approval** before relying on them (citing, building plans, or recommending steps based on them).

If the SA has already approved a specific non-Elastic source in the session, you may use it within that scope.

## External dependencies

Cloud provisioning and Kibana / Observability / **Elastic Security** operations require the
**full** **[elastic/agent-skills](https://github.com/elastic/agent-skills)** install (see
[`docs/todo.md`](docs/todo.md)) — not a Search-only subset. If missing, say so clearly instead
of failing silently.

## hive-mind-start
# Hive Mind

This project has hive-mind skills installed at `.agents/skills/`, `.cursor/skills/`, and `.claude/skills/`
(symlinked to `../hive-mind/skills/`). Use these for Elastic integration patterns.

## Pattern-First Workflow
1. Before implementing, check `../hive-mind/.hive-mind-index.json` for relevant patterns by tag.
2. Read the full pattern file before coding.
3. Follow established conventions and code structure.
4. Check skill `references/` directories for troubleshooting docs.

## Skills Routing
Route tasks through domain skills:
- SA coaching, demo ideation, hackathon brainstorming → `.agents/skills/hive-sa-coaching`
- token optimization, reduce tokens, save tokens, cost, vibe coding, model tiering → `.agents/skills/hive-token-optimization`
- Elastic Workflows API, workflow YAML, automation → `.agents/skills/hive-workflows`
- Kibana dashboards, NDJSON, Lens panels, data views → `.agents/skills/hive-dashboards`
- demo data, dataset generation, LLM data, data fidelity → `.agents/skills/hive-demo-data`
- composite demo guides, end-to-end build → `.agents/skills/hive-demo-recipes`
- Elastic Agent Skills, npx skills, agentskills.io → `.agents/skills/hive-elastic-agent-skills`

## Discovery Commands
- /hive-mind list → `python ../hive-mind/scripts/hive-mind-index-cli.py list`
- /hive-mind search <tag> → `python ../hive-mind/scripts/hive-mind-index-cli.py search <tag>`
- /hive-mind tags [prefix] → `python ../hive-mind/scripts/hive-mind-index-cli.py tags [prefix]`
## hive-mind-end
