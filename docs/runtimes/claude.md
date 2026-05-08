# Running loom in Claude Code / Claude projects

## What you need

- This repo’s [`skills/`](../../skills/) directory is the **source of truth** for loom pipeline skills.
- Install **[elastic/agent-skills](https://github.com/elastic/agent-skills)** per [`docs/todo.md`](../todo.md) for cloud provisioning and Kibana operations used by deploy stages.

## Making skills visible to Claude Code

Pick one approach (avoid duplicating content):

1. **Open this repo as the project** and let the agent read `skills/**/*.md` directly (recommended).
2. **Symlink** this repo’s `skills` folder into the Claude Code skills directory, e.g.  
   `ln -s /path/to/loom/skills/loom ~/.claude/skills/loom`  
   Repeat per skill folder only if your Claude setup requires per-skill directories — prefer opening the repo so one tree stays canonical.

## Orchestrator

Point the session at [`skills/loom/SKILL.md`](../../skills/loom/SKILL.md) for full-pipeline runs, or individual stage skills under [`skills/`](../../skills/).

## Outputs

Write artifacts to **`$LOOM_ENGAGEMENTS_ROOT/{slug}/`** — default **`~/engagements/{slug}/`** when unset (see [`docs/engagements-path.md`](../engagements-path.md)), or the absolute workspace path the user specifies. Same layout as in [`README.md`](../../README.md).

## Human vs agent execution

The SA should not be the default runner of `bootstrap.py` or import scripts; the agent runs them when the user approves deploy. See [`AGENTS.md`](../../AGENTS.md).
