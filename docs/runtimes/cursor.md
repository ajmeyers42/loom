# Running loom in Cursor

## What you need

- Clone or open this repo as the **workspace root** so paths like `skills/loom/SKILL.md` resolve.
- Optional: install **[elastic/agent-skills](https://github.com/elastic/agent-skills)** per [`docs/todo.md`](../todo.md) if you will provision clusters or use cloud/Kibana skills from the Elastic plugin set.

## How Cursor picks up instructions

- **Rules:** [`.cursor/rules/loom.mdc`](../../.cursor/rules/loom.mdc) is set to always apply and points the agent at the orchestrator and `$LOOM_ENGAGEMENTS_ROOT` outputs.
- **AGENTS.md:** Cursor reads [`AGENTS.md`](../../AGENTS.md) at the repo root when present — same content as the practical "what the agent should do" manifest.

## Prompting

Examples:

- "Run loom for discovery notes in `~/engagements/acme/discovery/`"
- "Refresh the demo script from `acme-discovery.json` only"
- "Deploy the demo to the cluster in `~/engagements/acme/.env`" (after approval)

Outputs should land under `$LOOM_ENGAGEMENTS_ROOT/{slug}/` — default **`~/engagements/{slug}/`** when the env var is unset (see [`docs/engagements-path.md`](../engagements-path.md)).

## Skills location and research order

Use the **in-repo** [`skills/`](../../skills/) tree first. Do not maintain a second copy of skills for Cursor-only; symlink from `~/.claude/skills` to this repo if another tool needs the same files on disk.

When searching for extra skills or external facts: **this repo**, then **github.com/elastic**; for **general web** or non-Elastic sources, **ask the SA before using** — see **Research, skills, and external sources** in [`AGENTS.md`](../../AGENTS.md).

## Session Boundaries

**One pipeline stage = one Cursor chat session.** This is the single biggest accuracy and
cost win: the model starts each stage with a clean context containing only that stage's input,
rather than carrying the accumulated noise of all prior stages.

**How to hand off between sessions:**

1. At the end of a stage, the orchestrator emits a `🔁 Next session:` line naming the output
   file to attach and the next stage to run. Use that line as your starting prompt.
2. Start a new chat, attach only the file(s) named in the handoff.
3. State the exit condition upfront: *"Run weave-script. Output: `acme-demo-script.md`."*
4. For `weave-model` and later stages, also attach `.env` — the cluster credentials are
   needed for live schema probes (D-043).

**Do not** carry the full prior conversation forward. The structured JSON output files are
the canonical handoff — they contain everything downstream stages need.

**Inventory shortcut:** If you need to orient quickly without re-reading all prior outputs,
start a fresh session, attach `{slug}-pipeline-state.json`, and ask *"what stage is next?"*.
This file is the authoritative record of what has run and what files were produced.

## Subagents (optional)

Fresh chats remain the default for sequential stages. For **parallel** or **noisy** Tier A
work inside a long session, use Cursor Task workers or the thin wrappers under
[`.cursor/agents/`](../../.cursor/agents/) — they only point at `skills/*/SKILL.md` (no
procedure fork). Decision matrix: [`docs/agent-patterns.md`](../agent-patterns.md).
Parallel pairs: [`docs/efficiency.md`](../efficiency.md) §4.

## Model selection by stage

Cursor lets you switch models per chat. Different pipeline stages have different cost/quality
trade-offs. Use this as a guide:

| Stage(s) | Recommended model | Reason |
|----------|------------------|--------|
| **warp-listen**, **warp-scan** | Fast/smaller (e.g. claude-3-5-haiku, gpt-4o-mini) | Structured extraction from large documents — speed matters, creativity does not |
| **thread-qualify** | Fast/smaller | JSON aggregation of already-parsed files; low ambiguity |
| **thread-audit**, **thread-suggest** | Fast/smaller | Matrix comparison against known rules; not generative |
| **weave-script**, **warp-spark** | Full model (Sonnet/Opus/GPT-4o) | Creative, customer-specific narrative; quality dominates |
| **weave-model** | Full model | Complex multi-index design with interdependencies |
| **weave-train** | Full model | ML config + anomaly injection planning; correctness-sensitive |
| **weave-agent** | Full model | Agent tool design requires careful schema adherence |
| **weave-query** | Full model | ES|QL + RAG architecture; context-heavy |
| **finish-check**, **wind-pulse** | Fast/smaller | Checklist and status — deterministic; no creativity needed |
| **finish-verify**, **bolt-bootstrap** | Full model | Code generation that runs against a live cluster |
| **Resuming a partial build** | Fast/smaller for inventory, full for writing | Use a quick model to check state; switch for active generation |

**Practical flow:** Start a new chat, use a fast model to run inventory and confirm what's
pending, then either continue in that chat with a full model or start a fresh chat with the
full model once you know exactly which stage to run.

**weave-model session requirement:** This stage requires cluster credentials (`.env` at the
engagement root) for live schema probes (D-043). Include `.env` in the session file
attachments alongside `{slug}-demo-script.md` and `{slug}-discovery.json`.

## reasoning_effort (Claude Code users)

Set `"reasoning_effort": "medium"` in `~/.claude/settings.json` as the session default.
Switch to `"high"` for `weave-model`, `weave-train`, and `bolt-bootstrap` where
correctness-sensitive generation warrants deeper reasoning.

```json
{ "preferences": { "reasoning_effort": "medium" } }
```

## Output compression — optional, Claude Code only

Shell output from `git diff`, test runners, and verbose commands enters LLM context at full
size. [RTK](https://github.com/contextvibes/rtk) intercepts bash output and compresses it
before it reaches the model:

```bash
brew install contextvibes/tap/rtk
```

Add to `~/.claude/settings.json` hooks:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "rtk rewrite-hook", "timeout": 5000 }]
      }
    ]
  }
}
```

After a session: `rtk gain` shows compression stats. This hook applies to Bash tool calls
only — Cursor's native Read/Grep/Glob tools are not affected.

## Observability SLOs (integration packages)

For **SLO demos**, **Fleet / Elastic Agent integration packages**, or **Observability package** structure and conventions, prefer the Elastic org repo **[integration-packages-slo](https://github.com/elastic/integration-packages-slo)** alongside in-repo skills and **[elastic/agent-skills](https://github.com/elastic/agent-skills)**. Use it when scripting or explaining SLO-related data ingest—not as a substitute for the engagement's `finish-verify` asset bundle unless the demo is explicitly package-driven.
