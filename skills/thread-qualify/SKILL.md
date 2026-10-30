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

**Sourcing the new top sections — read before writing:**

- **Customer Overview:** Synthesize from `customer.company`, `customer.industry`,
  `customer.industry_vertical`, `customer.location`, `customer.company_size_signal`,
  `elastic_relationship.status`, `elastic_relationship.footprint_description`, and any
  company-level background in the raw notes. Write as a short company biography — not a
  pain description. If company-level detail is sparse in the discovery JSON, use industry
  knowledge to provide market context, but flag any inferred detail with "(inferred)".

- **Opportunity Overview — Pain Points table:** Pull from `pain_points[]` in
  `demo/{slug}-discovery.json`. Map each entry's `label`, `description`, `severity`, and
  `verbatim_quote` into the table. If `verbatim_quote` is present, include it as a footnote
  below the table row or in the description cell in italics.

- **Opportunity Overview — Success Goals table:** Pull from `objectives.success_criteria[]`
  in `demo/{slug}-discovery.json`. For each criterion, surface any quantified measure found
  in the notes (time savings, percentage targets, throughput goals). If no measure was
  stated, mark as "⚠️ Not quantified" — never invent a target. Goals without a quantified
  measure are still listed; they set the qualitative bar for demo success.

- **Solution field:** Derive from `demo_scope.recommended_type` and the primary pain
  cluster. When cross-solution applies, name the dominant solution first (e.g.,
  "Observability + Security").

```markdown
# Opportunity Summary — {Customer Name}
**Engagement ID:** {slug}
**Last updated:** {date}
**Status:** [🟢 Proceed | 🟡 Continue Discovery | 🔴 Not Qualified]

---

## Customer Overview

{1–2 paragraphs profiling the customer as a company. Who they are, what they do, what
industry/vertical, their scale (size, employee count, markets served, team structure), and
any relevant technical or market context that shapes the engagement. Sourced from
`customer.*`, `elastic_relationship.*`, and any company-level background in the discovery
notes. No deal language — this section describes the company, not the sales situation.

Example: "Acme Corp is a mid-market logistics software provider (~800 employees) serving
North American freight carriers. They operate a Python/Postgres-centric stack and are
mid-way through a shift from batch nightly reporting to near-real-time operational
intelligence across their dispatch and inventory functions."}

---

## Opportunity Overview

**Opportunity:** {1–2 sentences on what this initiative is about — the business problem or
project the customer is trying to solve, and why it matters now. Describes the initiative,
not the company. E.g.: "Acme is evaluating Elastic to replace a fragmented log management
setup that is preventing their SRE team from correlating incidents across services fast
enough to meet their SLA commitments."}

**Solution:** {Search | Observability | Security | Cross-solution} — {one-line rationale
tying the solution area to the primary pain and what Elastic addresses.}

### Pain Points

| Pain | Severity | Quantified impact |
|---|---|---|
| {label: description} | Critical / High / Medium / Low | {e.g. "3–4 h/incident for manual triage" — or "⚠️ Not quantified"} |

### Success Goals

| Goal | Measure of success |
|---|---|
| {goal description} | {e.g. "MTTR < 15 min", "< 3% false positive rate" — or "⚠️ Not quantified"} |

---

## TL;DR
{2–3 sentence deal summary — what the AE reads in the first 10 seconds. Cover the deal
stage, urgency, what the customer is evaluating Elastic for, and the qualification status
preview. "Who they are" now lives in Customer Overview above; keep this section focused on
the sales situation.}

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
| --- | --- | --- | --- |
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

**Status: [🟢 PROCEED / 🟡 CONTINUE DISCOVERY / 🔴 NOT QUALIFIED]**

{2–4 sentence rationale. Be specific: what is confirmed, what is still missing,
and what would change the recommendation. Do not hedge with "it depends" —
give the team something to act on.}

**To proceed to demo build, the following must be confirmed:**
{Numbered list of blockers if status is CONTINUE DISCOVERY or conditions for NOT QUALIFIED.
Leave this section empty (replace with "All qualification criteria met.") for PROCEED.}

---

## SA Build Readiness

> For the SA: independent of deal qualification — answers whether there is enough
> technical context to start scoping a demo or developing a sizing estimate now.

| | Status | Details |
| --- | --- | --- |
| Demo direction | 🟢 Ready to scope / 🟡 Need: {item(s)} / 🔴 Cannot scope yet | {brief note} |
| Sizing estimate | 🟢 Ready to estimate / 🟡 Need: {item(s)} / 🔴 Cannot estimate yet | {brief note} |

{1–2 sentences: what the SA can act on immediately and what needs to be confirmed
before committing to a build direction or sizing approach.}

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
which Fleet packages finish-verify can install vs. what stays manual.}

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
  "customer_overview": "{1–2 paragraph plain-English profile of the customer as a company — industry, scale, what they do, relevant technical or market context. No deal language. Synthesized from customer.*, elastic_relationship.*, and discovery notes.}",
  "opportunity_overview": {
    "description": "{1–2 sentences on what this initiative is about — the business problem or project the customer is trying to solve, and why it matters now}",
    "solution": "search | observability | security | cross_solution",
    "pain_points": [
      {
        "label": "{short name matching pain_points[].label in discovery.json}",
        "severity": "critical | high | medium | low",
        "quantified_impact": "{e.g. '3–4 h/incident for manual triage' — or null if not stated}"
      }
    ],
    "success_goals": [
      {
        "goal": "{goal description from objectives.success_criteria[]}",
        "measure": "{quantified target e.g. 'MTTR < 15 min' — or null if not quantified}"
      }
    ]
  },
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

After writing all three files, present a compact summary in the chat using the two-score
format below. MEDDPIC as a table first, SA Build Readiness after.

**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**
**OPPORTUNITY REVIEW — {Customer Name}**
**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**

**OPPORTUNITY QUALIFICATION**
**Status:** 🟢 PROCEED / 🟡 CONTINUE DISCOVERY / 🔴 NOT QUALIFIED

{2–3 sentence rationale. What is confirmed, what is missing, what would change the status.
Be specific — reflect the confidence level the notes actually support.}

| Dimension | Score | Notes |
| --- | --- | --- |
| Metrics (M) | ✅/🟡/⚠️/❌ | {business impact or "not quantified"} |
| Economic Buyer (E) | ✅/🟡/⚠️/❌ | {name / title or "not identified"} |
| Decision Criteria (D) | ✅/🟡/⚠️/❌ | {one-line note} |
| Decision Process (D) | ✅/🟡/⚠️/❌ | {one-line note} |
| Paper Process (P) | ✅/🟡/⚠️/❌ | {timeline or "unknown"} |
| Identify Pain (I) | ✅/🟡/⚠️/❌ | {primary pain in one line} |
| Champion (C) | ✅/🟡/⚠️/❌ | {name / role or "none identified"} |

*Score key: ✅ Confirmed  🟡 Partial  ⚠️ Not captured  ❌ Disqualifying*

{If CONTINUE DISCOVERY or NOT QUALIFIED — omit if PROCEED:}
To move forward on qualification, confirm:

1. {specific gap}
2. {specific gap}

─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─

**SA BUILD READINESS**

| | Status | Details |
| --- | --- | --- |
| Demo direction | 🟢 Ready to scope / 🟡 Need: {item(s)} / 🔴 Cannot scope yet | {brief note} |
| Sizing estimate | 🟢 Ready to estimate / 🟡 Need: {item(s)} / 🔴 Cannot estimate yet | {brief note} |

{1–2 sentences: what the SA can act on now and what is still needed. If both are 🟢, say so
directly. If both are 🔴, name the single piece of information that would unlock the most
progress.}

Technical Landscape snapshot:
  Elastic today:    {version + deployment type, or "none"}
  Key integrations: {top 2–3 systems, or "none identified"}
  Data volumes:     {summary or "not captured"}
  Competing tools:  {list or "none identified"}

Top open questions:
  1. {most important unanswered question}
  2. {second most important}
  3. {third}

Outputs written:
  ✅  opportunity/{slug}-opportunity-summary.md   (team review doc)
  ✅  opportunity/{slug}-opportunity-profile.json (machine-readable for pipeline)
  ✅  opportunity/{slug}-demo-goals.md            (SA handoff brief — ideation input)

**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**
Ask the team to review {slug}-opportunity-summary.md before proceeding to platform audit.
SA: read opportunity/{slug}-demo-goals.md before running warp-spark.

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

### Opportunity Qualification Thresholds

Use these thresholds consistently for the MEDDPIC-based deal score:

**🟢 PROCEED** — At minimum: pain is confirmed and quantified, a champion is identified
and engaged, economic buyer is known (even if not yet met), and the timeline is credible.
Open questions exist but do not block the deal. A single call with one contact who has no
stated authority is CONTINUE DISCOVERY, not PROCEED.

**🟡 CONTINUE DISCOVERY** — One or more of: pain is stated but not quantified, no clear
champion, EB unknown, no decision timeline, or a focused follow-up is needed to confirm
the opportunity is real.

**🔴 NOT QUALIFIED** — Any of: no confirmed pain, no budget signal, stated non-starter
(exclusive competitor contract, RFP already closed, internal project funded, regulatory
blocker), or discovery notes contain zero actionable signal. Do not invest in demo build.
Log the rationale so the team can revisit if circumstances change.

---

### SA Build Readiness Thresholds

Produce two independent sub-scores. These are independent of Opportunity Qualification — a
deal can be PROCEED on qualification but not yet ready to build (technical details missing),
or CONTINUE DISCOVERY on qualification but ready to scope a demo (technical picture is clear).

**Demo Direction Readiness** — can the SA identify a viable demo direction?

Criteria:
- Primary use case is identifiable (what problem, for which role)
- Solution area is determinable (search / observability / security / cross-solution)
- At least one pain maps to a demonstrable Elastic capability
- Audience roles are known (technical depth, decision-making level)
- No hard technical blockers present (data residency requirement, air-gap mandate, exclusive
  competitor contract that rules out Elastic)

- 🟢 `Ready to scope` — all criteria met; SA can identify a demo archetype and begin scoping
- 🟡 `Need: [specific item(s)]` — most criteria met; one or two gaps would sharpen the direction
- 🔴 `Cannot scope yet` — use case, audience, or capability mapping is too unclear to start

**Sizing Estimate Readiness** — can the SA develop a rough infrastructure or cost estimate?

Criteria:
- Data volumes captured, even roughly ("~5 GB/day", "millions of records")
- At least one data source identified (logs, tickets, documents, metrics, etc.)
- Ingest frequency known or inferable (batch / near-real-time / real-time)
- Retention requirements stated or inferable from context
- Infrastructure environment described (cloud preference, on-prem, serverless, ECH)

- 🟢 `Ready to estimate` — enough to produce a directional sizing; exact numbers can be refined
- 🟡 `Need: [specific item(s)]` — one or two technical details would enable a rough estimate
- 🔴 `Cannot estimate yet` — volumes, sources, and environment are all unknown

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
