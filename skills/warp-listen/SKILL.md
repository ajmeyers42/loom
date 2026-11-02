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

**Inputs live in `{engagement_dir}/inputs/`** — it is the Path A source of truth. If the SA
hands you a file outside it, add it first (`python3 scripts/loom_state.py inputs add <slug>
<file>`), then run `loom_state listen plan <slug>` to get the input list and the **prior gap
ids** you must keep stable. Every `source_ref.file` you write must point under `inputs/`.

Read every file under `inputs/`. If given a PDF, use the Read tool. If given markdown or plain
text, read it directly. Reconcile multiple files for the same customer into one output; on
re-listen (new follow-up notes added), re-read **all** inputs — a gap that the new notes answer
simply disappears from `gaps[]` (closed by re-inference).

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

**Evidence (required — `schemas/discovery.schema.json`):**
- `claims[]` — one entry per load-bearing extracted fact (pain, objective, stakeholder role,
  volume, timeline). Each has `claim_id` (`c_<snake>`), `field` (the discovery field it
  supports), `text`, and `source_ref: {file: "inputs/…", locator, excerpt}`. The `excerpt`
  must be a **verbatim span** from that file (whitespace/case-insensitive) — registration
  fails on paraphrased excerpts. Notes-mode engagements need at least one claim.
- Pain points with a verbatim quote also carry `source_ref`.
- `gaps[]` — every gap has `gap_id` (`g_<field_snake>`, e.g. `g_economic_buyer`),
  `field`, `question`, `impact`, optional `blocks_qualification: true` (MEDDPIC-critical),
  `suggested_input` (which `inputs/` file the SA should update), and `source_ref` when the
  notes explicitly flag the unknown ("budget owner not identified").
- **Gap-id stability:** reuse the prior `gap_id` for the same `field` (from `listen plan`).
  Never rename an id for an unchanged field — gap responses, accepted risks, and approvals
  reference it.

```json
{
  "meta": {
    "slug": "{slug}",
    "inputs": ["inputs/call-notes.md"],
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
      "verbatim_quote": "",
      "source_ref": { "file": "inputs/call-notes.md", "locator": "¶3", "excerpt": "" }
    }
  ],
  "claims": [
    {
      "claim_id": "c_alert_noise",
      "field": "pain_points[0]",
      "text": "",
      "source_ref": { "file": "inputs/call-notes.md", "locator": "¶3", "excerpt": "" }
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
      "gap_id": "g_economic_buyer",
      "field": "meddpic.economic_buyer",
      "question": "",
      "impact": "blocks_demo_build | reduces_personalization | low",
      "blocks_qualification": true,
      "suggested_input": "inputs/call-notes.md",
      "source_ref": { "file": "inputs/call-notes.md", "excerpt": "" }
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

**Use the engagement's existing slug** (the `{engagement_dir}` folder name, set by
`loom_state new`). **Never derive a slug from the company name** — the slug is a public demo
codename (e.g. `acme-pharma`); the real company stays in `customer.company` and the private
pipeline-state identity. If no engagement exists yet, stop and create one with `loom_state new`.

### Output 1: `demo/{slug}-discovery.json`

The populated JSON from Step 2. Must be valid JSON. Every null field must have a corresponding
entry in `gaps`.

### Output 2: `opportunity/{slug}-confirmation.md`

This goes TO THE CUSTOMER. Write it as if you're handing it to them the day after the
discovery call. Tone: collaborative, specific, technically credible. Not marketing copy.

**Document posture — read before writing any section:**

This document summarizes what was heard in a first or early conversation. It is not a
proposal, a statement of work, or a commitment of any kind. Write it accordingly.

- **No absolute language about Elastic's capabilities or delivery.** Prohibited words and
  phrases include: "precise", "exact", "final", "guaranteed", "complete", "fully",
  "will deliver", "will provide", "you will receive", and any phrasing that implies
  a firm estimate, a committed scope, or a definitive timeline. Use directional,
  conditional language instead: "based on what we've heard", "we expect to work toward",
  "our initial read is", "subject to confirming".
- **No embellishments.** Do not make the opportunity sound more advanced, more confirmed,
  or more strategically significant than the notes support. If one pain was mentioned,
  describe one pain — not "a comprehensive initiative across the organization." Match the notes.
- **No premature conclusions.** Do not conclude that requirements are understood, that a
  decision is imminent, that the customer is "ready to move forward", or that Elastic is
  the right fit — unless that was explicitly stated. Discovery is ongoing.
- **No invented content.** If something wasn't said or strongly implied in the notes,
  it does not appear in this document. Gaps are named in "Before We Build", not papered over.

Additional rules:
- Use the customer's own language and verbatim phrases where impactful — it shows you listened
- Do NOT use internal sales language: no "champion", "deal stage", "blocker", "ICP", "ACV"
- Do NOT include competitive intelligence (no mention of rival vendors, competitor names)
- Scale length to what was captured: rich notes → full doc; sparse notes → shorter doc with
  more prominent gaps section
- **Tense:** If the demo is upcoming, write in future tense ("What We'll Demonstrate").
  If notes describe something already built or approved, use past tense ("What We Demonstrated").

Structure (adapt as needed — don't be mechanical about it):

```
# Discovery Confirmation — [Company Name]
**Prepared by:** [SA name] | **Date:** [date]

---

## What We Heard
[3–5 bullets in the customer's language. Use their phrases. If they said "scattered everywhere"
use "scattered everywhere", not "data fragmentation".]

## [What We'll Demonstrate — OR — Measures of Success]

Use "What We'll Demonstrate" ONLY if a demo was explicitly requested or confirmed in the
notes (e.g. "they asked for a demo", "demo scheduled for [date]", "they want to see it in
action"). If a demo was not mentioned, use "Measures of Success" instead.

If a demo was confirmed — "What We'll Demonstrate":
Map each planned demo scenario to a specific pain point the customer raised. Name the role,
the task, and the measurable outcome. Make success criteria quantifiable wherever the notes
support it.
  Not: "We'll demonstrate AI search capabilities."
  Instead: "We'll show how [role] goes from [current state] to [outcome] in under [timeframe]
  — addressing the '[verbatim pain]' problem directly."

If no demo was mentioned — "Measures of Success":
Describe what good looks like for the customer — the outcomes they would experience if the
initiative succeeded. Make these quantifiable wherever the notes support it. If the notes
don't support a quantified target, use a directional qualifier ("significantly faster than
today's manual process") rather than inventing numbers.

## What You Can Expect

Based on what we've heard so far, describe the likely shape of next steps — not final
commitments. This section is directional. More will be defined as discovery continues.

Do not use absolute language ("you will receive", "we will deliver", "precise estimate").
Use hedged, forward-looking language: "based on what we've heard", "our initial read is",
"we expect to work toward", "subject to confirming [gap]".

Keep this section to 2–3 sentences. If the notes don't support even a directional statement,
omit this section rather than filling it with generic language.

## Before We Build
[List only genuine gaps — things you actually need from them to proceed.
Phrase as requests: "Please share the diagnostic files from your four environments"
not "we need more information".
If you have everything you need: "We have everything we need to get started."]

## Next Steps
| Action | Owner | Target Date |
| --- | --- | --- |
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

Head each gap with its `gap_id` so the SA can answer it via Path A (update the named
`inputs/` file and re-listen) or Path B (`loom_state gaps respond <slug> <gap_id> …`).

## Step 5: Register the Output

Run `python3 scripts/loom_state.py listen record <slug>`. It validates the discovery JSON,
verifies every `source_ref` excerpt against `inputs/`, rejects duplicate or renamed gap ids,
checks the confirmation for internal sales jargon, and records `stages.discovery-parser` with
a sha256 `input_hash` of `inputs/`. On failure, fix the JSON (do not pass
`--allow-unverified-excerpts` unless the SA accepts unverified evidence). Report the
`closed_by_reinference` and `new_gaps` it prints.

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
