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
| **Cursor** | Solutions Architects | [`docs/runtimes/cursor.md`](docs/runtimes/cursor.md) — includes session boundary rules, model-per-stage table, reasoning_effort guidance, optional output compression, and subagent wrappers; see also [`docs/agent-patterns.md`](docs/agent-patterns.md) |
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

## Engagement data hygiene

Customer discovery notes, diagnostic exports, opportunity summaries, and any other engagement-specific artifacts are written to `$LOOM_ENGAGEMENTS_ROOT/{slug}/` (default: `~/engagements/{slug}/`). This directory lives **outside** the loom git repo by design.

**Rules the assistant must follow — and remind the SA of on first use:**

1. **No customer data in the repo.** The loom repo holds pipeline code only (`skills/`, `docs/`, `scripts/`). Engagement artifacts — discovery notes, opportunity summaries, demo scripts, bootstrap scripts, `.env` files — go under `~/engagements/{slug}/` exclusively. Eval fixtures in `skills/*/evals/` use illustrative composites only (never real customer names, contacts, or data).

2. **Keep `~/engagements/` outside any git-tracked directory.** If an SA's home directory is itself tracked (e.g. a dotfiles repo), confirm that `~/engagements/` is in `.gitignore` before running the pipeline. A mistakenly committed `.env` file contains cluster API keys.

3. **Never commit `.env` files.** Each engagement's `.env` carries `ES_API_KEY`, `KIBANA_API_KEY`, and `EC_API_KEY`. These are credentials — not config. If accidentally staged, run `git rm --cached .env` immediately. `.gitignore` ignores `.env`/`.env.*` in every directory (templates like `.env.example` stay tracked).

4. **Secrets live in a vault, not `.env` — in the Cloud Agent / test environment especially.** When running under a Cloud Agent (or any shared/test environment), provide `ES_API_KEY`, `KIBANA_API_KEY`, `EC_API_KEY`, and cluster endpoint URLs through the Cursor **Secrets** vault (injected as environment variables), never a plaintext `.env` committed or synced anywhere. Resolve credentials from the environment (`os.environ`) and write a `.env` only to a per-engagement folder under `$LOOM_ENGAGEMENTS_ROOT` when a local script requires one — that folder is outside the repo and git-ignored. Never place real credentials in the repo, `.cursor/environment.json`, a Dockerfile, or chat/logs.

5. **Anonymize customer identity in anything deployed to a test cluster.** Assets created in a shared/test environment must not carry a customer's real name. Use the engagement **slug**, `INDEX_PREFIX`, and the `loom:<engagement_id>` tag (D-026) — not `ENGAGEMENT=<Company>` — in index names, Kibana spaces, dashboards, SLOs, rules, ML jobs, and `CLUSTER_NAME`. Customer-identifying narrative (company name, contacts, discovery notes) stays in the engagement folder under `$LOOM_ENGAGEMENTS_ROOT`; it is not baked into deployed assets.

6. **Retention.** Delete engagement directories when the deal closes or the demo environment is torn down. Discovery notes and confirmation documents may contain customer-identifying information that should not be retained beyond their useful life. Follow your organization's data-handling policy.

7. **Dry-run safety.** `bootstrap-data.py --dry-run` and `terraform plan` are always safe to run without cluster access. Never run `terraform apply` or `bootstrap-data.py` (no `--dry-run`) against a live cluster without the SA's explicit approval per D-024.

## hive-mind-start
# Hive Mind

This project has hive-mind skills installed at `.agents/skills/`, `.cursor/skills/`, and `.claude/skills/`
(symlinked to `../hive-mind/skills/`). Use these for Elastic integration patterns.

## Pattern-First Workflow
1. Before implementing, check `{hive-mind-root}/.hive-mind-index.json` for relevant patterns by tag.
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
Path: `{hive-mind-root}` = `$HIVE_MIND_PATH` if set, otherwise `../hive-mind`. See `docs/ext-registry.yaml`.
- /hive-mind list → `python {hive-mind-root}/scripts/hive-mind-index-cli.py list`
- /hive-mind search <tag> → `python {hive-mind-root}/scripts/hive-mind-index-cli.py search <tag>`
- /hive-mind tags [prefix] → `python {hive-mind-root}/scripts/hive-mind-index-cli.py tags [prefix]`
## hive-mind-end
