# loom — Efficiency Guide

How to reduce token usage, context window pressure, and cost across the pipeline without
sacrificing output quality.

---

## 1. Token usage — pipeline-state file

**The single highest-impact change.** After every stage, the orchestrator writes
`{slug}-pipeline-state.json` to the engagement directory. On the next session, it reads
this one file (≈30 lines) instead of scanning 10+ individual output files to determine
what has run.

When the state file exists: inventory is instant and costs ~200 tokens.
When it does not exist (first run): the file scan fallback runs once, then writes the state file.

The orchestrator also prunes raw inputs from context once they are parsed. Discovery PDFs
and diagnostic ZIPs are large; once `warp-listen` or `warp-scan`
has produced its structured JSON, the original raw file is no longer read by downstream stages.
Passing raw text through the full pipeline would easily double context usage per session.

**Tip:** If a stage is re-run after a manual edit to an input file, touch the file so its
mtime changes — the orchestrator uses mtime as its change-detection signal.

---

## 2. Context window — load only what the current stage needs

Each sub-skill SKILL.md is loaded **only when that stage is about to run**, not up-front.
The orchestrator reads the list of pending stages from the pipeline-state file, then loads
one SKILL.md at a time.

When running a single stage manually (e.g., "rewrite the demo script"), start a fresh chat
and provide only the files that stage needs:

| Stage | Inputs to provide |
|-------|------------------|
| warp-listen | raw discovery notes only |
| thread-audit | `{slug}-discovery.json`, `{slug}-opportunity-profile.json`, `{slug}-current-state.json` |
| weave-script | `{slug}-discovery.json`, `{slug}-platform-audit.json` |
| weave-model | `{slug}-demo-script.md`, `{slug}-discovery.json` |
| bolt-launch | `{slug}-data-model.json`, `.env`, `{slug}-demo-script.md` |

Avoid pasting all engagement files into context "just in case." The pipeline-state file
tells you exactly what exists; load only what the stage explicitly requires.

---

## 3. Model selection — route by stage

Different stages have very different cost/quality requirements. See
[`docs/runtimes/cursor.md`](runtimes/cursor.md) for the full routing table.

**Quick rule:**
- **Extraction and aggregation stages** (discovery-parser, diagnostic-analyzer, opportunity-review,
  platform-audit, validator, wind-pulse) → fast/smaller model (Haiku, gpt-4o-mini, etc.)
- **Creative and design stages** (script-template, ideation, data-modeler, agent-design,
  deploy/bootstrap generation) → full model (Sonnet, Opus, GPT-4o)

**Practical flow in Cursor:**
1. Open a chat with a fast model.
2. Run inventory: `python3 scripts/inventory.py <slug>` or ask the agent to read the
   pipeline-state file. Confirm which stages are pending.
3. If only extraction stages are pending, stay on the fast model.
4. Switch to the full model when you hit script-template or data-modeler.

---

## 4. Subagents — parallelize independent stages

Some stages have no dependency on each other and can run concurrently when the runtime
supports parallel subagents (e.g. Cursor with parallel tool calls, Claude Code with
multiple tasks):

| Parallel pair | Condition |
|---------------|-----------|
| warp-listen + warp-scan | Both inputs provided at the start |
| weave-train + weave-agent | Both need only the completed data model |
| wind-pulse (all health checks) | Independent probes (cluster, ML, ELSER, Kibana) |

The orchestrator runs stages sequentially by default because most setups don't have reliable
parallel execution. If your runtime does, run the pairs above as concurrent subagents and
merge their outputs before moving to the next dependent stage.

**subprocess CLIs as lightweight subagents:**
- `demo_status.py` (in `skills/wind-pulse/`) runs as a subprocess — it checks cluster health
  without loading the full pipeline context into the conversation.
- `scripts/inventory.py` reads engagement state instantly without an AI session at all.
- `bootstrap.py` and `teardown.py` run entirely outside the AI context.

Use these as the first line of investigation before opening a full agent chat.

---

## 5. CLIs — do more without AI

| Script | Purpose | When to use |
|--------|---------|-------------|
| `scripts/inventory.py` | Show all engagements and stage status | Before starting a session; morning check |
| `scripts/inventory.py <slug> -v` | Full stage-by-stage status for one engagement | Picking up mid-pipeline |
| `skills/wind-pulse/demo_status.py` | Live cluster health check | Pre-demo verification |
| `{engagement_dir}/bootstrap.py --dry-run` | Validate deploy script without cluster changes | Before any live run |
| `{engagement_dir}/teardown.py --dry-run` | Preview what teardown would delete | Before cleanup |

**Zero-AI pre-session workflow:**
```bash
# See where all engagements stand
python3 /path/to/loom/scripts/inventory.py

# Check a specific engagement in detail
python3 /path/to/loom/scripts/inventory.py 2026CitizensAI -v

# Check cluster health (requires .env)
cd ~/engagements/2026CitizensAI && python3 /path/to/demo_status.py
```

Running these before opening Cursor/Claude means you come into the AI session already knowing
exactly which stage to run and what the cluster state is — no wasted tokens on inventory and
no "let me check" round-trips.

---

## Summary

| Lever | Saves | How |
|-------|-------|-----|
| Pipeline-state file | ~500–2000 tokens/session | Single JSON read replaces 10+ file scans |
| Context pruning | 30–60% context reduction | Raw inputs dropped after parsing |
| Model routing | 50–80% cost on extraction stages | Fast model for parsing, full model for design |
| CLI pre-session | Eliminates full sessions for status | `inventory.py` and `demo_status.py` |
| Subagent parallelism | Wall-clock time, not token cost | Parallel stages where dependencies allow |
