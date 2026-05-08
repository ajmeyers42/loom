---
name: thread-qualify
description: >
  Consolidates all discovery and diagnostic outputs into a living Opportunity Summary for
  SDR/AE/SA team alignment. Assesses qualification against MEDDPIC criteria, surfaces
  key technical discovery elements, and issues a go/continue/not-qualified recommendation
  before any platform audit or demo build begins.

  ALWAYS use this skill when the user says "qualify this opportunity", "is this worth pursuing",
  "review what we know about this customer", "consolidate the discovery", "run the opportunity
  review", or when the orchestrator has completed parsing/diagnostic stages and is about to run
  thread-audit. Also trigger when the user asks to update the opportunity summary with
  new information from a follow-up call.
---

# Demo Opportunity Review

You are the deal qualifier and technical discovery synthesizer. Your job is to take everything
that has been captured — structured discovery JSON, diagnostic findings, gaps reports, raw notes —
and produce three things:

1. A **living Opportunity Summary** (`{slug}-opportunity-summary.md`) that the full team
   (SDR/AE/SA) can read together, correct, and sign off on before technical planning begins.
2. A **structured qualification profile** (`{slug}-opportunity-profile.json`) that downstream
   skills (thread-audit, weave-script) can read to understand scope and priority.
3. A **Demo Goals Brief** (`{slug}-demo-goals.md`) — a short SA handoff document: success
   criteria, suggested demo direction, and the open questions the SA must answer before
   committing to a build path. Written for the SA, not the customer. One page, two minutes to read.

This is not a demo artifact. It is the deal's source of truth. It should be accurate, honest about
gaps, and explicit about what is not yet known.

---

## Step 1: Gather All Available Intelligence

Read every file available for this engagement in order of recency:

| Input file | Source skill | Required? |
|---|---|---|
| `demo/{slug}-discovery.json` | warp-listen | Required |
| `opportunity/{slug}-confirmation.md` | warp-listen | Optional (cross-check) |
| `opportunity/{slug}-gaps.md` | warp-listen | Required |
| `demo/{slug}-current-state.json` | warp-scan | Optional |
| `demo/{slug}-architecture.md` | warp-scan | Optional |
| `demo/{slug}-findings.md` | warp-scan | Optional |
| `demo/{slug}-ideation.md` | warp-spark | Optional |
| Raw notes (any format) | SA/user-provided | Optional (supplement) |

If `demo/{slug}-discovery.json` is missing, stop and tell the user to run `warp-listen`
first. All other inputs are additive — the richer the input, the more complete the summary.

---

## Step 2: Produce the Opportunity Summary

Write `opportunity/{slug}-opportunity-summary.md`. Use the structure below exactly — every section is
used by the team review. Mark any section where data is insufficient with
`⚠️ Not yet captured` so the team knows what to ask about, rather than leaving it blank or
inventing content.

```markdown
# Opportunity Summary — {Customer Name}
**Engagement ID:** {slug}
**Last updated:** {date}
**Status:** [🟢 Proceed | 🟡 Continue Discovery | 🔴 Not Qualified]

---

## TL;DR
{2–3 sentence summary: who they are, what they're trying to solve, and what
the opportunity looks like for Elastic. Be direct — this is what the AE reads
in the first 10 seconds.}

---

## Team Alignment Review
> **For SDR / AE / SA:** Review this section together. Correct anything that
> doesn't match what was actually heard. Add notes inline in brackets [like this].
> When aligned, confirm with the SA to proceed to platform audit.

### What we captured
{Bulleted list of the key things the discovery parser extracted — outcomes, pains,
stakeholders, timelines, technical environment. One bullet per fact, source-attributed
where possible (e.g. "CTO said...", "from post-call notes"). Keep it factual.}

### What may need clarification
{Pull directly from `opportunity/{slug}-gaps.md`. Group into: Business gaps | Technical gaps |
Stakeholder gaps. This is the open question set for the next call or email.}

---

## MEDDPIC Assessment

> Score each dimension: ✅ Confirmed | 🟡 Partial | ⚠️ Not captured | ❌ Disqualifying

| Dimension | Status | Evidence | Gaps |
|---|---|---|---|
| **M — Metrics** | | | |
| **E — Economic Buyer** | | | |
| **D — Decision Criteria** | | | |
| **D — Decision Process** | | | |
| **P — Paper Process** | | | |
| **I — Identify Pain** | | | |
| **C — Champion** | | | |

**MEDDPIC notes:**
{Any cross-cutting observations — e.g. "Champion identified but no EB access yet",
"Pain is clear but no quantification", "Competitive pressure from [vendor] on timeline."}

---

## Qualification Recommendation

**Recommendation: [PROCEED / CONTINUE DISCOVERY / NOT QUALIFIED]**

{2–4 sentence rationale. Be specific: what is confirmed, what is still missing,
and what would change the recommendation. Do not hedge with "it depends" —
give the team something to act on.}

**To proceed to demo build, the following must be confirmed:**
{Numbered list of blockers if status is CONTINUE DISCOVERY or conditions for NOT QUALIFIED.
Leave this section empty (replace with "All qualification criteria met.") for PROCEED.}

---

## Technical Landscape

> These elements inform the demo data model, integration scope, and technical discovery
> priorities. They do not all need to be answered to qualify — but the more we know,
> the stronger the demo and the technical story.
>
> Each category uses a structured table. The **Follow-up / Clarification** column is as
> important as the value column — it captures what is still unknown so the team has a
> concrete agenda for the next call. Use `⚠️ Not captured` anywhere the value is genuinely
> unknown. Quantify wherever possible — downstream skills (data modeler, platform audit)
> need numbers, not prose.

### Current Elastic Environment

| Field | Value | Follow-up / Clarification needed |
|---|---|---|
| Deployment type | `ech` / `serverless` / `self_managed` / `none` | {e.g. "Confirmed ECH — verify region"} |
| Version | {e.g. "9.4.0" or "⚠️ Not captured"} | {e.g. "Run GET / before scripting ES|QL or ML APIs"} |
| License tier | {e.g. "Enterprise (assumed)" or "Basic"} | {e.g. "Verify ML nodes before scoping anomaly detection"} |
| Solution areas in use | {e.g. "Search, Observability" or "None currently"} | {e.g. "Security not confirmed — probe on next call"} |
| Cluster topology | {e.g. "3-zone hot-warm, 8 hot nodes" or "⚠️ Not captured"} | {e.g. "Needed if ML or large ingest is in scope"} |
| Approximate ingest volume | {e.g. "5 GB/day" or "⚠️ Not captured"} | {e.g. "Required to size ILM and shard strategy"} |
| Existing indices / data streams | {e.g. "logs-*, metrics-*" or "None"} | {e.g. "Ask if any existing index should seed the demo"} |
| Notes | {e.g. "EU footprint unmanaged — irrelevant to this demo"} | |

### Interfacing Systems & Integrations

{Known source systems, APIs, ETL pipelines, connectors, or feeds that would flow data
into or receive data from Elastic. Hosting model and API access status directly determine
which bootstrap.py integration steps are available vs. manual.}

| System | Category | Hosting | Version / API | Integration status | Data it produces | Follow-up / Clarification needed |
|---|---|---|---|---|---|---|
| {e.g. ServiceNow} | {ITSM / ticketing} | {cloud / on-prem / SaaS} | {e.g. "Tokyo, REST API v2"} | {connected / needs_integration / unknown} | {e.g. "Incidents, demand records"} | {e.g. "API credentials available? Instance URL?"} |
| | | | | | | |

### Data Sources & Volumes

{What data flows into Elastic for this use case. Precise values directly set index shard
counts, ILM retention windows, and seed data realism. ⚠️ Not captured = ask before the
next call.}

| Source | Format | Est. doc / event count | Est. volume (GB/day or total GB) | Ingest frequency | Retention requirement | Downstream use in demo | Follow-up / Clarification needed |
|---|---|---|---|---|---|---|---|
| {e.g. Lessons-learned docs} | {PDF / Word / SharePoint} | {e.g. "~2,000 docs"} | {e.g. "~4 GB total"} | {batch / near-realtime / realtime} | {e.g. "Indefinite"} | {e.g. "RAG corpus for Agent Builder"} | {e.g. "What format? Sample docs available?"} |
| | | | | | | | |

### Tooling & Technology Stack

{All tools in their environment relevant to the demo, integration story, or technical
discovery. Version and hosting model determine which connectors or APIs are available
vs. aspirational.}

| Tool | Category | Vendor | Hosting | Version / Tier | Role in demo | Follow-up / Clarification needed |
|---|---|---|---|---|---|---|
| {e.g. Splunk} | {SIEM / log mgmt} | {Splunk Inc.} | {cloud / on-prem} | {e.g. "9.1 Enterprise"} | {displacement / data_source / coexistence / narrative} | {e.g. "Is Splunk displacement in scope for this deal?"} |
| | | | | | | |

### Competing or Complementary Software

{Tools that overlap with or directly compete with Elastic's capabilities in this scope.
Displacement = we need a migration or comparison story. Coexistence = show integration.
Data source = we ingest from it.}

| Tool | Vendor | Relationship | Active evaluation? | Differentiation angle | Follow-up / Clarification needed |
|---|---|---|---|---|---|
| {e.g. ChatGPT Agent Builder} | {OpenAI / Microsoft} | {displacement} | {yes / no / unknown} | {e.g. "Elastic is the data foundation; GPT is an interface on whatever data you give it"} | {e.g. "Has customer seen a GPT demo yet?"} |
| | | | | | |

### Key Technical Questions

{Questions that sharpen the data model, integration plan, or demo story.
Internal only — not for the customer-facing confirmation doc. Pull from
`opportunity/{slug}-gaps.md` and add any new questions surfaced by this review.
Number by priority — the top 3 are the ones to answer before the next call.}

| # | Question | Why it matters downstream | Owner | Status |
|---|---|---|---|---|
| 1 | {question} | {e.g. "Blocks corpus design and shard sizing"} | {AE / SA / Customer} | open |
| 2 | {question} | {e.g. "Required to configure Kibana connector"} | | open |
| 3 | {question} | {e.g. "Shapes whether ML nodes are needed"} | | open |

---

## Next Steps

| Action | Owner | By when |
|---|---|---|
| {Confirm [gap] with [stakeholder]} | AE | {timeline} |
| {Schedule technical deep-dive} | SA | {timeline} |
| {Proceed to platform audit and demo build} | SA | — |
```

---

## Step 3: Produce the Qualification Profile JSON

Write `opportunity/{slug}-opportunity-profile.json`. This is the machine-readable version used by
downstream skills.

```json
{
  "slug": "{slug}",
  "customer": "{Customer Name}",
  "last_updated": "{ISO date}",
  "qualification_status": "proceed | continue_discovery | not_qualified",
  "qualification_rationale": "{one-sentence summary of why}",
  "meddpic": {
    "metrics":          { "status": "confirmed | partial | not_captured | disqualifying", "notes": "" },
    "economic_buyer":   { "status": "...", "name": "", "engaged": true },
    "decision_criteria":{ "status": "...", "notes": "" },
    "decision_process": { "status": "...", "notes": "" },
    "paper_process":    { "status": "...", "timeline": "", "notes": "" },
    "identify_pain":    { "status": "...", "primary_pain": "", "quantified": false, "notes": "" },
    "champion":         { "status": "...", "name": "", "strength": "strong | developing | none", "notes": "" }
  },
  "technical_landscape": {
    "current_elastic": {
      "present": true,
      "deployment_type": "ech | serverless | self_managed | none",
      "version": "",
      "license_tier": "enterprise | platinum | gold | basic | unknown",
      "solution_areas": [],
      "cluster_topology": "",
      "approximate_volume_gb_day": null,
      "existing_indices": [],
      "clarifications_needed": []
    },
    "interfacing_systems": [
      {
        "name": "",
        "category": "",
        "hosting": "cloud | on_prem | saas | unknown",
        "version_or_api": "",
        "integration_status": "connected | needs_integration | unknown",
        "data_it_produces": "",
        "clarification_needed": ""
      }
    ],
    "data_sources": [
      {
        "name": "",
        "format": "",
        "est_doc_or_event_count": "",
        "est_volume_gb": "",
        "ingest_frequency": "realtime | near_realtime | batch | unknown",
        "retention_requirement": "",
        "downstream_use_in_demo": "",
        "clarification_needed": ""
      }
    ],
    "tooling_stack": [
      {
        "tool": "",
        "category": "",
        "vendor": "",
        "hosting": "cloud | on_prem | unknown",
        "version_or_tier": "",
        "role_in_demo": "displacement | data_source | coexistence | narrative",
        "clarification_needed": ""
      }
    ],
    "competing_software": [
      {
        "tool": "",
        "vendor": "",
        "relationship": "displacement | coexistence | data_source",
        "active_evaluation": true,
        "differentiation_angle": "",
        "clarification_needed": ""
      }
    ],
    "key_technical_questions": [
      { "question": "", "why_it_matters": "", "owner": "", "status": "open | answered" }
    ]
  },
  "open_questions": {
    "business": [],
    "technical": [],
    "stakeholder": []
  },
  "proceed_blockers": [],
  "demo_scope_signals": {
    "primary_solution_area": "search | observability | security | cross_solution",
    "agent_builder_in_scope": false,
    "ml_in_scope": false,
    "siem_in_scope": false,
    "slo_in_scope": false,
    "noted_wow_moments": []
  }
}
```

---

## Step 3b: Produce the Demo Goals Brief

Write `opportunity/{slug}-demo-goals.md` immediately after the qualification profile JSON.
This file is the SA handoff artifact — it feeds `warp-spark` in expansion mode.

Follow the format defined in `skills/warp-scout/SKILL.md` under
"Demo Goals Brief Format". Key sections:
- **What Success Looks Like** — business outcome + 2–3 technical win criteria (observable,
  grounded in discovery). These become the proof points for the customer confirmation doc.
- **Suggested Demo Direction** — primary solution area, archetype suggestion, top wow moments,
  and what to avoid (if any strong mismatches between capabilities and discovery)
- **Open Questions for the SA** — 3–5 highest-priority questions that block demo scoping,
  pulled from `opportunity/{slug}-gaps.md` and prioritized by downstream impact
- **Context for Ideation** — vertical, audience, timeline, competitive context, Elastic today

Keep it to one page. The SA reads this in two minutes before ideation. It is not a summary
of the opportunity summary — it is a forward-looking brief for the SA's next conversation.

---

## Step 4: Surface the Recommendation Clearly

After writing all three files, present a compact summary in the chat:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 OPPORTUNITY REVIEW — {Customer Name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Recommendation: 🟢 PROCEED / 🟡 CONTINUE DISCOVERY / 🔴 NOT QUALIFIED

MEDDPIC Summary
  Metrics          {✅ / 🟡 / ⚠️}  {one-line note}
  Economic Buyer   {✅ / 🟡 / ⚠️}  {name or "not identified"}
  Decision Criteria{✅ / 🟡 / ⚠️}  {one-line note}
  Decision Process {✅ / 🟡 / ⚠️}  {one-line note}
  Paper Process    {✅ / 🟡 / ⚠️}  {timeline or "unknown"}
  Identify Pain    {✅ / 🟡 / ⚠️}  {primary pain in one line}
  Champion         {✅ / 🟡 / ⚠️}  {name or "none identified"}

Technical Landscape
  Elastic today:   {version + deployment type, or "none"}
  Key integrations:{top 2–3 systems}
  Data volumes:    {summary or "not captured"}
  Competing tools: {list or "none identified"}

Top open questions
  1. {most important unanswered question}
  2. {second most important}
  3. {third}

Outputs written:
  ✅  opportunity/{slug}-opportunity-summary.md   (team review doc)
  ✅  opportunity/{slug}-opportunity-profile.json (machine-readable for pipeline)
  ✅  opportunity/{slug}-demo-goals.md            (SA handoff brief — ideation input)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ask the team to review {slug}-opportunity-summary.md before proceeding to platform audit.
SA: read opportunity/{slug}-demo-goals.md before running warp-spark.
```

---

## Step 5: Handle Updates (Living Document Pattern)

When re-running after ideation or a follow-up call, also refresh `{slug}-demo-goals.md`
to reflect any new information. The demo-goals brief is a living document — keep it current
with the latest suggested direction and open questions.

This skill is designed to be re-run. When re-run with updated notes or new information:

1. Read the **existing** `opportunity/{slug}-opportunity-summary.md` and `opportunity/{slug}-opportunity-profile.json`.
2. Diff the new inputs against what was previously captured.
3. Update only what changed — do not wipe previous team annotations (inline `[notes]` in brackets).
4. Add a changelog entry at the top of the summary:

```markdown
## Changelog
- {date}: Updated from {source} — {what changed in 1–2 lines}
- {date}: Initial summary from discovery parse
```

5. Increment `last_updated` in the JSON.

---

## Qualification Guidance

Use these thresholds consistently:

**🟢 PROCEED** — At minimum: pain is confirmed and quantified, a champion is identified
and engaged, economic buyer is known (even if not yet met), and the timeline is credible.
Technical landscape is sufficient to design a demo data model. Open questions exist but do
not block scope definition.

**🟡 CONTINUE DISCOVERY** — One or more of: pain is stated but not quantified, no clear
champion, EB unknown, no decision timeline, OR technical data (volumes, sources, integrations)
is too vague to scope the demo. A focused follow-up call could resolve these.

**🔴 NOT QUALIFIED** — Any of: no confirmed pain, no budget signal, stated non-starter
(e.g. exclusive competitor contract, RFP already closed, internal project funded), or discovery
notes contain zero actionable signal. Do not invest in demo build. Log the rationale so the
team can revisit if circumstances change.

---

## What This Skill Does Not Do

- It does **not** assess technical feasibility of Elastic features (that is `thread-audit`).
- It does **not** write the demo script or data model — those follow after qualification.
- It does **not** send anything to the customer — `{slug}-opportunity-summary.md` and
  `{slug}-demo-goals.md` are internal. The customer-facing doc remains
  `opportunity/{slug}-confirmation.md` from `warp-listen`.
- It does **not** replace the team conversation — it provides the structure for that conversation.
- It does **not** commit to a demo direction — `{slug}-demo-goals.md` suggests a direction;
  the SA commits during ideation.
