# Engagement workspaces (outside this repository)

Per-customer demo folders — credentials (`.env`), generated scripts, discovery notes, and pipeline outputs — **do not live under this git clone**. They live under your **user profile** by default.

## Default location

**`~/engagements/`** — one subfolder per engagement (e.g. `~/engagements/2026CitizensAI/`).

The environment variable **`LOOM_ENGAGEMENTS_ROOT`** points at that parent directory. If it is **unset**, agents and docs assume:

```bash
export LOOM_ENGAGEMENTS_ROOT="$HOME/engagements"
```

Add that line to `~/.zshrc` or `~/.bashrc` if you want it explicit in every shell.

To use a different root:

```bash
export LOOM_ENGAGEMENTS_ROOT="/path/to/your/engagements-parent"
```

Each engagement is: `$LOOM_ENGAGEMENTS_ROOT/{slug}/`

**Artifacts:** Pipeline outputs (discovery JSON, demo script, data model, platform audit,
risks, checklist, etc.) and deploy collateral (`bootstrap.py`, optional `kibana-objects/*.ndjson`,
`kibana/**`, `elasticsearch/**`) live in that folder. **`bootstrap.py`** is the single script
that applies them to a cluster; see **`docs/decisions.md` D-024**. Tagged Kibana/Observability
resources should include **`loom:<engagement_id>`** — see **`docs/decisions.md` D-026**.

**Deploy:** Do **not** run provision/deploy or execute `bootstrap.py` against a live cluster
until the SA has **reviewed** `bootstrap.py` and the analysis docs (audit, risks, checklist).
`bootstrap.py --dry-run` does not require deploy approval. See **`AGENTS.md`**.

See **[`docs/engagements-path.md`](../docs/engagements-path.md)** for full detail.
