---
name: weave-cost
description: >
  Two-dimensional skill for AI token and cost transparency in Elastic demos.
  (A) SA tooling: helps the SA track their own Claude Code / Cursor token usage
  using hive-mind's Group B ES Analytics pattern — session tracking, cost dashboards,
  model tiering. (B) Demo feature: adds an AI Cost + Usage dashboard to any generated
  demo that includes Elastic Agent Builder, giving customers operational transparency
  into AI spend and usage patterns as a first-class demo deliverable.

  ALWAYS use this skill when a demo script includes Agent Builder or another AI-powered
  component, unless `INCLUDE_TOKEN_VISIBILITY=false` is set for the engagement. Also use
  it when the SA asks about token costs, wants to track AI spend, or asks "what does this
  agent cost to run".
---

# Token Visibility

Two independent use cases. Apply one or both based on context.

---

## Use Case A: SA Tooling — Track Your Own AI Spend

Elastic's own development environment can index Claude Code / Cursor session data
into Elasticsearch, giving you cost visibility and dashboards for your own build sessions.

**Reference implementation:** `hive-mind/skills/hive-token-optimization/SKILL.md`
and `hive-mind/skills/hive-token-optimization/references/GROUP_B_ES_ANALYTICS.md`.
Follow those instructions for personal SA token tracking setup (setup.sh, Stop hook,
4 Kibana dashboards).

**Quick summary of what Group B provides:**
- Session-level token doc per Claude Code session (model, cost, turns, files touched)
- Per-turn cost tracking (cumulative, burn rate)
- Subagent tracking (each Agent tool call tracked separately)
- 4 pre-built Kibana dashboards: Token Overview, Session Deep Dive, Turn Drill Down, Efficiency & ROI
- ES|QL queries for cost by model, daily burn rate, most expensive sessions, cache hit rate

**When to set up:** Any time the SA wants to understand their own AI costs during
demo builds. Especially useful during heavy build sessions (bootstraps, data generation,
multi-stage pipeline runs).

---

## Use Case B: Demo Feature — AI Cost + Usage Dashboard for Customers

When a demo includes **Elastic Agent Builder** (or any AI-powered component), include
an operational transparency layer that customers can see. This transforms the demo from
"AI does things" to "AI does things and you can see exactly what it costs and how it behaves" —
a key enterprise buying signal for AI governance, budget owners, and IT leadership.

### What to include in the demo

**Index:** `{prefix}agent-sessions` — same schema as hive-mind Group B, scoped to this engagement.

**Mapping** (add to `weave-model` output alongside other indices):

```json
PUT /{prefix}agent-sessions
{
  "mappings": {
    "properties": {
      "session_id":         { "type": "keyword" },
      "session_type":       { "type": "keyword" },
      "parent_session_id":  { "type": "keyword" },
      "action":             { "type": "keyword" },
      "agent_name":         { "type": "keyword" },
      "model":              { "type": "keyword" },
      "all_models":         { "type": "keyword" },
      "turns":              { "type": "integer" },
      "input_tokens":       { "type": "long" },
      "output_tokens":      { "type": "long" },
      "cache_creation_tokens": { "type": "long" },
      "cache_read_tokens":  { "type": "long" },
      "total_tokens":       { "type": "long" },
      "session_cost_usd":   { "type": "float" },
      "session_start":      { "type": "date" },
      "session_end":        { "type": "date" },
      "@timestamp":         { "type": "date" },
      "tools_used":         { "type": "keyword" },
      "user_query_preview": { "type": "text" },
      "engagement_id":      { "type": "keyword" }
    }
  }
}
```

**ILM:** Hot-only, delete after 90 days (D-027).

**Seed data:** Generate 30-60 synthetic session documents covering:
- Mix of model types (claude-sonnet, claude-haiku, gpt-4o)
- 7-14 day date range at realistic daily volumes (5-20 sessions/day)
- Per-session token variation ($0.02–$2.50 cost range)
- Realistic tool usage patterns (search queries, document retrievals, workflow invocations)
- 2-3 agent names matching the demo's deployed agents

**ES|QL dashboard panels to include:**

```esql
// Daily AI spend by agent
FROM {prefix}agent-sessions
| WHERE action == "token-usage"
| EVAL day = DATE_TRUNC(1 day, @timestamp)
| STATS daily_cost = SUM(session_cost_usd) BY day, agent_name
| SORT day ASC

// Cumulative cost this month
FROM {prefix}agent-sessions
| WHERE action == "token-usage" AND @timestamp >= NOW() - 30 days
| STATS total_cost_usd = SUM(session_cost_usd), total_sessions = COUNT()

// Model usage breakdown
FROM {prefix}agent-sessions
| WHERE action == "token-usage"
| STATS sessions = COUNT(), avg_cost = AVG(session_cost_usd) BY model
| SORT sessions DESC

// Average cost per query by agent
FROM {prefix}agent-sessions
| WHERE action == "token-usage"
| STATS avg_cost = AVG(session_cost_usd), p95_cost = PERCENTILE(session_cost_usd, 95) BY agent_name

// Token efficiency (cache hit rate)
FROM {prefix}agent-sessions
| WHERE action == "token-usage" AND input_tokens > 0
| EVAL cache_hit_rate = cache_read_tokens / (input_tokens + cache_read_tokens + 0.0001) * 100
| STATS avg_cache_rate = AVG(cache_hit_rate), total_input = SUM(input_tokens), total_cached = SUM(cache_read_tokens)
```

**Kibana dashboard:** `{slug} — AI Usage & Cost Overview`

Include panels for:
- **Total AI spend** (stat panel, current period)
- **Daily spend trend** (area chart over 14 days)
- **Cost by model** (donut chart — shows model tier selection)
- **Sessions by agent** (bar chart — shows which agents are used most)
- **Average cost per session** (stat panel, per agent)
- **Cache efficiency** (gauge 0-100% — higher = smarter context management)
- **Recent sessions** (table — last 20 sessions with cost, model, turn count)

### Talking Points for the Demo Scene

> "This dashboard shows exactly what your AI agents are costing — in real time.
> Every session is logged: which model was used, how many tokens were consumed,
> what it cost, and which tools were invoked. Budget owners and IT governance teams
> can see this without having to ask engineering."

> "Notice the cache efficiency metric — this shows how effectively the system
> is reusing prior context rather than retokenizing the same content. A high cache
> rate translates directly to lower operating costs."

> "You can filter by agent, by model, or by time range. If a new release causes
> a spike in token usage, you'll see it in this dashboard before your cloud bill arrives."

---

## Integration with bolt-launch

When the demo script includes Agent Builder, `bootstrap.py` should:

1. **Create the `{prefix}agent-sessions` index** with the mapping above (step 4, alongside other indices)
2. **Load seed data** with 30-60 synthetic session documents (step 10, data load)
3. **Create the AI Usage data view** in the demo Kibana space
4. **Create the AI Usage & Cost dashboard** with the ES|QL panels above
5. **Tag all created assets** with `demobuilder:{engagement_id}` (D-026)
6. **Add to manifest** (D-031)

Add `INCLUDE_TOKEN_VISIBILITY=true` to `.env` (default: `true` when demo includes Agent Builder).
Set to `false` to skip if the customer engagement does not include an AI component.

---

## Cost Formula (for seed data generation)

Model-aware USD cost:

```python
def session_cost_usd(input_tokens, output_tokens, cache_creation=0, cache_read=0, model="claude-sonnet"):
    if "opus" in model:
        return (input_tokens * 5.0 + cache_creation * 6.25 + cache_read * 0.50 + output_tokens * 25.0) / 1_000_000
    elif "haiku" in model or "gpt-4o-mini" in model:
        return (input_tokens * 0.25 + output_tokens * 1.25) / 1_000_000
    else:  # sonnet / default
        return (input_tokens * 3.0 + cache_creation * 3.75 + cache_read * 0.30 + output_tokens * 15.0) / 1_000_000
```

---

## Decisions Reference

- **D-036:** Token visibility as a standard demo feature when Agent Builder is in scope.
  See `docs/decisions.md`.
- **Data:** Index uses `{prefix}agent-sessions` (engagement-scoped, never shared across demos).
- **ILM:** Hot-only, delete after 90 days (D-027).
- **Schema:** Compatible with hive-mind Group B schema for SA who wants to compare their own
  session data patterns with demo scenario data.
