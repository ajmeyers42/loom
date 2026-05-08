# Dependencies

Loom has two required external repositories and one optional environment variable.

## elastic/agent-skills

**https://github.com/elastic/agent-skills**

The full plugin must be installed — not a Search-only subset. Security and hybrid demos require the Security skills; Observability scenes require the Observability skills. Install everything once and all engagements work.

```bash
npx skills add elastic/agent-skills
```

Representative skills used by loom (non-exhaustive):

| Area | Skills | Purpose |
|---|---|---|
| Cloud | `cloud/setup`, `cloud/create-project`, `cloud/manage-project`, `cloud/network-security` | EC_API_KEY setup, provision, teardown, traffic filters |
| Kibana | `kibana/kibana-dashboards`, `kibana/kibana-connectors`, `kibana/kibana-alerting-rules`, `kibana/streams` | Deploy, dashboards, Workflows connectors, alerting |
| Observability | `observability/manage-slos`, `observability/logs-search`, `observability/service-health` | SLOs, log analysis, APM health when in scope |
| **Security** | `security/detection-rule-management`, `security/alert-triage`, `security/case-management`, `security/generate-security-sample-data` | Detection rules, triage, cases, sample data |
| Elasticsearch | `elasticsearch/elasticsearch-esql`, `elasticsearch/elasticsearch-authz` | ES\|QL queries, RBAC |

Run `cloud-setup` once to configure `EC_API_KEY` before using `bolt-spin`.

If `elastic/agent-skills` is not installed, the assistant will say so clearly rather than fail silently. See [docs/todo.md](todo.md) for the full one-time setup checklist.

---

## elastic/hive-mind

**https://github.com/elastic/hive-mind**

A reference library for Elastic integration patterns, SA coaching frameworks, and demo tooling. Several loom pipeline stages read hive-mind patterns directly — SA ideation archetypes, data fidelity guidelines, token optimization strategies, Kibana Workflows references, and dashboard construction patterns.

### Install

Clone as a **sibling of loom** (same parent directory):

```bash
git clone https://github.com/elastic/hive-mind ../hive-mind
```

The skill symlinks in `.cursor/skills/`, `.claude/skills/`, and `.agents/skills/` point to `../hive-mind/skills/` using relative paths. As long as hive-mind is a sibling, they resolve automatically.

### Keeping it current

```bash
cd ../hive-mind && git pull
```

No re-linking needed. The orchestrator's Step 0 currency check will warn if either repo is behind its remote.

### What's linked

Seven hive-mind skills are pre-symlinked into loom's agent skill directories:

| Skill | Used for |
|---|---|
| `hive-sa-coaching` | SA ideation (`warp-spark` stage) — Demo Archetypes, COACHING_CONVERSATION framework |
| `hive-token-optimization` | Token visibility dashboard, AI spend tracking (`weave-cost` skill) |
| `hive-workflows` | Kibana Workflows API reference, YAML step types, troubleshooting |
| `hive-dashboards` | Dashboard construction patterns, NDJSON format, Lens panel reference |
| `hive-demo-data` | Data fidelity guidelines, dataset generation, LLM data quality |
| `hive-demo-recipes` | Composite demo guides for search, Agent Builder, and e-commerce scenarios |
| `hive-elastic-agent-skills` | Elastic Agent Skills integration (`npx skills`, agentskills.io) |

### If you move hive-mind

If you need hive-mind at a different path, set `HIVE_MIND_PATH` and re-run the symlink setup from the loom root:

```bash
export HIVE_MIND_PATH="/path/to/hive-mind"

# Remove old links
for dir in .cursor/skills .claude/skills .agents/skills; do
  for skill in hive-sa-coaching hive-token-optimization hive-workflows hive-dashboards hive-demo-data hive-demo-recipes hive-elastic-agent-skills; do
    rm -f "$dir/$skill"
  done
done

# Re-link from new location (adjust path as needed)
HIVE_MIND="$HIVE_MIND_PATH"
for skill in hive-sa-coaching hive-token-optimization hive-workflows hive-dashboards hive-demo-data hive-demo-recipes hive-elastic-agent-skills; do
  for dir in .cursor/skills .claude/skills .agents/skills; do
    ln -s "$(python3 -c "import os; print(os.path.relpath('$HIVE_MIND/skills/$skill', '$dir'))")" "$dir/$skill"
  done
done
```

---

## elastic/vulcan (optional)

**https://github.com/elastic/vulcan**

An AI-powered demo generator that produces validated, parameterized ES|QL queries, LLM-generated synthetic datasets, EPR-grounded integration data, and tested RAG pipelines. Used by the `weave-query` skill (Stage 4.5) to generate the data + query layer before `weave-model` runs.

Vulcan is **optional** — it activates when the demo script has 5+ ES|QL queries, semantic/RAG search, or Fleet/Beats integrations. If not installed, the pipeline skips Stage 4.5 and `weave-model` generates the data model from the script directly.

### Install

Clone as a **sibling of loom** (same parent directory):

```bash
git clone https://github.com/elastic/vulcan ../vulcan
cd ../vulcan
pip install -r requirements.txt
cp .env.example .env   # fill in ELASTICSEARCH credentials + LLM provider keys
```

Vulcan needs its own `.env` with cluster credentials (can point to the same cluster as the engagement `.env`) and an LLM provider key (`LLM_PROVIDER=claude-sdk` recommended).

### Keeping it current

```bash
cd ../vulcan && git pull
```

### Usage

The `weave-query` skill handles invocation — either through Vulcan's Streamlit UI (`streamlit run app.py`) or programmatically. See `skills/weave-query/SKILL.md` for details.

### If Vulcan is unavailable

If the cluster is unavailable or Vulcan is not installed:
- Set `skip_indexing: true` in the Vulcan context to generate query strategy only (no cluster needed)
- Or skip Stage 4.5 entirely — `weave-model` will proceed without Vulcan outputs

---

## LOOM_ENGAGEMENTS_ROOT (optional)

By default, engagement workspaces are written to `~/engagements/{slug}/`. Set this env var in your shell profile to use a different parent directory:

```bash
export LOOM_ENGAGEMENTS_ROOT="/Volumes/work/engagements"
```

See [docs/engagements-path.md](engagements-path.md) for details and multi-customer isolation patterns.
