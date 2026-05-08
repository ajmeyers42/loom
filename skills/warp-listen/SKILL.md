---
name: warp-listen
description: >
  Parses sales discovery notes — in any format or quality level (polished post-call reports,
  raw live meeting notes with typos and abbreviations, mixed prep+live notes, or technical spec
  dumps) — plus optional supplemental team notes and architecture diagrams, into three structured
  outputs: (1) a JSON file capturing all extractable customer context for downstream demo-builder
  pipeline skills, (2) a professional customer-facing confirmation document in markdown, and
  (3) an internal gap report. Search, Observability, and Security use cases are all in scope.

  ALWAYS use this skill when the user provides discovery notes or meeting notes and asks to
  parse, structure, summarize, or generate a confirmation document from them. Also trigger when
  the user says "prep for demo build", "structure these notes", "what do we know about this
  customer", "analyze discovery", or provides one or more files described as notes from a sales
  call, discovery meeting, or qualification call. Trigger even if the notes are messy, partial,
  or heavily abbreviated — the skill is specifically designed for that.
---

# Demo Discovery Parser

You are parsing sales discovery notes to build a structured customer profile and a
customer-facing confirmation document. The notes may be polished post-call reports, raw
live captures with typos and abbreviations, technical spec dumps, or a mix of all three.
Your job is to extract signal faithfully — cleaning up noise without hallucinating content
that isn't there.

## Step 1: Read the Input

Read all provided files. If given a PDF, use the Read tool. If given markdown or plain text,
read it directly. Accept multiple files for the same customer — reconcile them into one output.

**Input types** (any combination):
- **Discovery notes** — call reports, live notes, prep notes, qualification threads.
- **Supplemental notes** — follow-ups from the AE, SE, or discovery team (email threads,
  Slack exports, addendum bullets). Merge into the same customer profile; note source and date
  when they conflict with older notes.
- **Architecture or current-state diagrams** — images (PNG/SVG/PDF), Mermaid, or Visio exports.
  Use the Read tool on images. Extract components, data flows, bottlenecks, and vendor tools
  shown; map them to Elastic-relevant opportunities (ingest, correlation, security use cases,
  observability signals). If text is unreadable in an image, say so in `gaps` rather than guessing.

Note the notes style before extracting anything. This affects how aggressively you clean and
how much you flag as ambiguous:
- **Polished**: structured headers, complete sentences, clear attribution. Extract directly.
- **Raw live notes**: typos, abbreviations, fragments, incomplete bullets. Clean and interpret,
  but flag anything genuinely ambiguous.
- **Technical spec**: heavy on system details (server counts, RAM, document counts, index sizes,
  version numbers), light on business context. Extract the technical facts precisely.
- **Mixed prep+live**: pre-meeting context written by the AE/SE followed by live capture
  (often separated by a divider or timestamp). Parse both sections and reconcile them.

## Step 2: Extract the Structured Profile

Populate the JSON schema below. For every field you cannot extract with confidence, set it to
`null` and add a corresponding entry to `gaps`. The quality of this document depends entirely
on not hallucinating — if it isn't stated or strongly implied, it's null.

**Cleaning raw notes:** Fix typos in the structured output ("dignostic"→"diagnostic",
"sice"→"size", "yeards"→"years"). Reconstruct fragmented bullets into readable phrases where
meaning is unambiguous. Preserve verbatim quotes when they're emotionally loaded or distinctive
— these are signals, not noise ("demoed out", "scattered everywhere", "institutional amnesia",
"bounty hunter mentality").

**Multiple contacts:** When notes list several customer contacts, capture each one. Infer their
role from title and context. A "SRE who supports Patrick's team a lot" is `technical_user`, not
`unknown`. An "IT Director making vendor decisions in two weeks" is `decision_maker`.

**Elastic version:** If a version is mentioned or strongly implied ("fallen behind on releases",
"on-prem cluster"), set `fallen_behind_releases: true` and note the version if known.

```json
{
  "meta": {
    "notes_quality": "raw | structured | polished",
    "notes_style": ["polished_report", "raw_live_notes", "technical_spec", "mixed_prep_and_live"],
    "extraction_confidence": "low | medium | high",
    "date_parsed": "ISO date"
  },
  "customer": {
    "company": "",
    "industry": "",
    "industry_vertical": "",
    "location": "",
    "company_size_signal": "startup | smb | mid-market | enterprise | unknown"
  },
  "contacts": [
    {
      "name": "",
      "title": "",
      "role": "champion | decision_maker | influencer | technical_user | sre | blocker | unknown",
      "linkedin": "",
      "notes": ""
    }
  ],
  "elastic_team": {
    "ae": "",
    "sa": "",
    "se": "",
    "other": []
  },
  "meeting": {
    "date": "",
    "type": "discovery | qualification | technical_review | executive_briefing | migration_assessment | unknown",
    "crm_link": ""
  },
  "elastic_relationship": {
    "status": "net_new | existing_on_prem | existing_cloud | existing_serverless | partial_fragmented | lapsed | unknown",
    "version": "",
    "footprint_description": "",
    "environments": [],
    "fallen_behind_releases": null,
    "deployment_model_requirement": "serverless | eck | ech | self_managed | unknown — capture any explicit constraint (e.g. 'must be on-prem', 'ECK required', 'no cloud')"
  },
  "current_state": {
    "tech_stack": [],
    "data_sources": [],
    "data_volumes": {
      "description": "",
      "document_counts": "",
      "index_sizes": "",
      "ingest_rate": ""
    },
    "infrastructure": {
      "description": "",
      "server_count": null,
      "ram_gb": null,
      "environment_count": null
    },
    "workflows": "",
    "integration_tools": []
  },
  "pain_points": [
    {
      "label": "",
      "description": "",
      "severity": "critical | high | medium | low",
      "verbatim_quote": ""
    }
  ],
  "objectives": {
    "primary": "",
    "secondary": [],
    "success_criteria": []
  },
  "demo_scope": {
    "recommended_type": "champion_enablement | executive_alignment | technical_deep_dive | migration_assessment | rag_demo | agentic_demo | search_demo | observability_demo | security_demo",
    "deployment_model": "",
    "target_elastic_version": "",
    "inference_guidance": {
      "note": "Default: use EIS via Cloud Connect for all semantic_text embedding and reranking. Use local ML nodes only for anomaly detection or models that cannot leave the customer environment.",
      "semantic_text_default": "EIS via Cloud Connect — ELSER v2 on EIS for sparse; jina-embeddings-v3 on EIS for dense vector",
      "reranking_default": "jina-reranker-v3 on EIS for highest precision; jina-reranker-v2-base-multilingual for low-latency multilingual",
      "llm_default": "Elastic Managed LLMs via EIS (Claude, GPT, Gemini) — created automatically via Cloud Connect",
      "local_ml_node_use_cases": "ML anomaly detection, custom trained models, models with data residency requirements"
    },
    "recommended_features": [],
    "key_scenarios": [],
    "anti_patterns": [],
    "positioning_guidance": ""
  },
  "deal_context": {
    "stage": "early_awareness | champion_building | active_evaluation | technical_validation | commercial | migration",
    "urgency": "low | medium | high | critical",
    "timeline": "",
    "budget_signal": "confirmed | implied | unknown | none",
    "blockers": [],
    "competitive_context": {
      "incumbents": [],
      "active_alternatives": [],
      "key_differentiator": ""
    }
  },
  "next_steps": {
    "demo_requested": null,
    "demo_timing": "",
    "demo_focus_verbatim": "",
    "other_actions": []
  },
  "gaps": [
    {
      "field": "",
      "question": "",
      "impact": "blocks_demo_build | reduces_personalization | low"
    }
  ]
}
```

## Step 3: Classify the Engagement Type

Before writing the confirmation doc, determine what this engagement actually needs. Not every
discovery call results in a feature demo, and building the wrong thing wastes everyone's time.

**Migration assessment** (signal: existing Elastic on-prem customer, moving to Serverless/Cloud,
discussion centers on sizing, pricing, data migration, version gaps): The primary deliverable
is a migration plan, not a feature showcase. Flag this and set `recommended_type:
migration_assessment`. The confirmation doc should reflect this.

**Champion enablement** (signal: single contact, decision-maker not in the meeting, deal is in
"wait and see" mode, goal is to arm the contact with internal ammunition): The demo is for one
person to become an internal advocate. Urgency is usually low-medium. The confirmation doc
should position the demo as a "working prototype you can show your leadership."

**Urgent close** (signal: decision-maker present, vendor decision in weeks, active projects
starting, competing vendors already talking): Fast-track. High urgency. The confirmation doc
should have tight timelines and concrete next steps.

**Technical deep-dive / RAG / agentic**: Feature demo with specific Elastic capabilities as
the focus (ELSER, Agent Builder, ML anomaly detection, etc.). Most common type.

## Step 4: Write the Three Output Files

Derive the company slug from the company name (lowercase, hyphens, no special chars).
Example: "Citizens Bank" → `citizens-bank`, "Holiday Inn Club Vacations" → `ihg-club`.

### Output 1: `demo/{slug}-discovery.json`

The populated JSON from Step 2. Must be valid JSON. Every null field must have a corresponding
entry in `gaps`.

### Output 2: `opportunity/{slug}-confirmation.md`

This goes TO THE CUSTOMER. Write it as if you're handing it to them the day after the
discovery call. Tone: collaborative, specific, technically credible. Not marketing copy.

Rules for this document:
- Use the customer's own language and verbatim phrases where impactful — it shows you listened
- Do NOT use internal sales language: no "champion", "deal stage", "blocker", "ICP", "ACV"
- Do NOT include competitive intelligence (no mention of Bain, AWS Bedrock, rival vendors)
- Do NOT pad thin notes with generic filler — if you don't know something, say so in
  "Before We Build" rather than making something up
- Scale length to what was captured: rich notes → full doc; sparse notes → shorter doc with
  more prominent gaps section
- **Tense matters:** If the demo is already built and approved (the notes are a demo script or
  post-approved artifact), write in past tense — "What We Demonstrated", "What Was Built". If
  the demo is upcoming, write in future tense — "What We'll Demonstrate", "What to Expect".

Structure (adapt as needed — don't be mechanical about it):
```
# Discovery Confirmation — [Company Name]
**Prepared by:** [SA name] | **Date:** [date]

---

## What We Heard
[3–5 bullets in the customer's language. Use their phrases. If they said "scattered everywhere"
use "scattered everywhere", not "data fragmentation".]

## What We'll Demonstrate
[Table or brief prose: each demo scenario mapped to a specific pain point they raised.
Be concrete — "we'll show an agent that answers 'what were the top risks in the 2022 Greenville
expansion?' against 40 years of project logs" not "we'll demonstrate AI capabilities".]

## What You Can Expect
[Concrete outcomes, not vague value propositions. What will they walk away with?
A working prototype? A migration sizing estimate? A live query against their own data model?]

## Before We Build
[List only genuine gaps — things you actually need from them to proceed.
Phrase as requests: "Please share the diagnostic files from your four environments"
not "we need more information".
If you have everything you need: "We have everything we need to get started."]

## Next Steps
| Action | Owner | Target Date |
|--------|-------|-------------|
[Fill from the next steps in the notes]
```

### Output 3: `opportunity/{slug}-gaps.md`

Internal use only — not sent to the customer. For each gap in the JSON:
- The field that's missing
- The specific question to ask
- The impact level (blocks demo build / reduces personalization / low)
- The best way to get the answer (follow-up email, ask at demo kickoff, will come from
  diagnostic file, etc.)

If all gaps are low-impact: close with "No blocking gaps — safe to proceed to demo build."

## What Good Looks Like

**Citizens Bank pattern** (polished, champion-building): All pain points captured with
verbatim quotes. Demo type correctly classified as `champion_enablement`. Confirmation doc
positions the demo as "internal ammunition." Competitive context (Bain/Bedrock) absent from
customer doc but present in JSON. Gap: budget and timeline are null but low-impact.

**IHG pattern** (raw notes, migration): Typos cleaned, tech specs extracted precisely
(3 servers, 50GB RAM, 220MM documents, 36GB index). Multiple contacts captured with inferred
roles. Demo type flagged as `migration_assessment`. Confirmation doc shorter, gaps section
more prominent (no clear demo scenario discussed).

**Thermo Fisher pattern** (polished, urgent RAG): High urgency flagged. Demo type
`rag_demo` + `technical_deep_dive`. Confirmation doc has tight timeline and specific
demo scenario ("answer questions about the 2022 Greenville expansion"). Reference to
"Massachusetts Semiconductor" success story noted as a proof point to use.

**Lowe's pattern** (technical, approved demo): Demo script treated as the post-discovery
artifact — the demo is already scoped. Confirmation doc reflects what was built rather than
what will be built.
