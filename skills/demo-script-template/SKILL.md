---
name: demo-script-template
description: >
  Generates a structured Elastic demo script from a discovery profile and optional platform
  audit. Produces three files: a full SE-facing narrative script with scenes, timing, talking
  points, on-screen steps, and wow moments; a one-page audience brief the AE can use to follow
  along; and a tabular live-delivery script (`{slug}-live-script.md`) the SE keeps on a second
  monitor during the call — numbered rows, Say/Do/Expect columns, and a Dev Tools Quick
  Reference paste buffer. The script is personalized to the customer's language, industry, and
  pain points — not a generic feature showcase. Default narrative: **solution first** (key asks
  and outcomes, then supporting capabilities); ask the SA if goals are unclear.

  ALWAYS use this skill when the user asks to "write the demo script", "build the script",
  "create the demo outline", "what should we show them", or provides a discovery JSON and
  wants a structured demo plan. Also trigger when the user says "we're ready to build" after
  running demo-discovery-parser or demo-platform-audit. Run after demo-platform-audit when
  possible — the audit shapes which features are safe to script.
---

# Demo Script Template

**Before authoring any scene, read `references/demo2win-conventions.md`.**
Every custom demo script must conform to the three structural rules defined there:
1. **Opening punch** — business problem statement before any product is shown
2. **Vignette structure** — 3–5 self-contained scenes, each independently skippable
3. **Value confirmation close** — ties the ending back to the opening punch in outcome language

Scripts that skip any of these three elements are non-conformant and will fail `demo-validator`.

---

You are writing a demo script for an Elastic pre-sales SE. The script must be good enough
to hand to a competent SE who wasn't on the discovery call and have them deliver a credible,
personalized demo. That means: every scene is grounded in something the customer actually
said, every feature serves a pain point, and no scene exists just to show off a feature.

The script is not a slide deck outline. It is a live demo plan — specific screens, specific
queries, specific words to say.

**Narrative arc — solution first (default):** Unless the SA specifies otherwise, structure
the demo so the **customer’s desired outcome** lands **before** deep dives into Elastic
**capabilities**. Open with the **solution story** (business value, what “good” looks like
for them) tied to **key asks** from discovery — then walk through the supporting
capabilities, data, and screens that get there. Execs stay engaged; technical contacts still
get their proof in later scenes. If the **key asks** are ambiguous in the inputs, **ask the
SA for guidance** before locking scene order — do not invent primary goals.

## Step 1: Read the Inputs

Read all available files in this order:
- `demo/{slug}-discovery.json` — required. This is your primary source.
- `demo/{slug}-platform-audit.json` — use this to constrain which features can be scripted.
  Any feature marked `upgrade_required` or `blocked` must not appear as a live scene.
  Features marked `setup_required` can appear but must include a setup note.
- `demo/{slug}-current-state.json` — optional context for migration or existing-customer demos.

**Stack version:** If the audit or current-state includes `cluster.version` (or equivalent),
the script must **name the target Elasticsearch/Kibana versions** in an upfront “Environment”
or “Assumptions” note so SEs do not run ES|QL or UI steps on the wrong stack. If the demo
targets a **new** cluster not yet provisioned, state that scenes assume **latest GA** at
provision time unless the SA specified a version.

**Primary solution domain:** Take from discovery and audit — **search / analytics**, **Observability**,
**Elastic Security**, or **mixed / cross-solution**. Do not default to a generic search narrative
when the customer’s pain is operational, APM, logs, SIEM, or detection; blended storylines are
appropriate when the audit supports combined capabilities.

If only raw discovery notes are provided (no parsed JSON), read them directly and extract
what you need to proceed.

## Step 1b: Apply Demo Archetype (from ideation or archetype gallery)

If `demo/{slug}-ideation.md` exists in the workspace, read it first. The ideation contract
provides frozen wow moments, capability map, and audience context that should drive
the script structure directly — do not re-derive these from discovery JSON alone.

If no ideation contract exists, consult the Demo Archetype Gallery in
`skills/demo-ideation/SKILL.md` (which mirrors `hive-mind/skills/hive-sa-coaching/references/DEMO_ARCHETYPES.md`).
Select the archetype that best matches the discovery profile:

| Customer vertical / pain | Suggested anchor archetype |
|---|---|
| Retail, product catalog, e-commerce | AI Search + Assistant or E-Commerce with Analytics |
| Operations, field service, IT ops, manufacturing | Operational Triage Console |
| Support, service desk, helpdesk | Customer Support Intelligence |
| Financial services, insurance, healthcare, government | Domain Expert Advisor |
| Cross-solution / hybrid | Operational Triage Console + Domain Expert Advisor |

Use the archetype's **wow moments** and **minimum bar** as the target for the script.
State the chosen archetype in the script header. If combining archetypes, name both:
"Anchor: Operational Triage Console | Stretch: Domain Expert Advisor elements."

## Step 2: Determine the Script Shape

Before writing a single scene, answer these questions from the discovery JSON:

**Who is in the room?**
Map each contact to their demo attention needs:
- `decision_maker` / exec: needs operational impact and business outcomes, loses interest
  during live coding. Narrate what they're seeing; never leave them on a JSON blob.
- `champion` / technical lead: wants to see the actual query, the actual index, the actual
  config. This person will replay the demo mentally after the meeting.
- `sre` / technical_user: wants to understand operational complexity. How is this maintained?
  What breaks?
- Mixed audience: design for the exec, narrate the bridge, go deep for the technical contact.
  Never apologize for technical content — just narrate it.

**What is the engagement type?**
- `champion_enablement`: One contact, DM not present. Goal is internal ammunition. The
  demo should produce something they can screenshot and share — a dashboard, a query result,
  a before/after comparison. Close with "here's how you show this to your leadership."
- `migration_assessment`: Existing on-prem customer. Lead with the delta — what they gain
  by moving, what they won't lose. Show migration tooling, not just new features.
- `technical_deep_dive` / `rag_demo` / `agentic_demo`: Feature demo. The script is a
  showcase of specific capabilities tied to specific pain points.
- `executive_alignment`: Short runtime (20–30 min), high-level, outcomes-first. No live
  queries unless they're one-liners with immediate visible payoff.

**What is the human story?**
Every good demo has a person at the center — a real role at this company facing a real
version of their core problem. The story thread runs through every scene. Name the person,
name the scenario, and return to it. Don't invent a character who has nothing to do with
the customer's world.

Example: For a bank, it might be a fraud analyst who gets 400 alerts a day and has to
manually correlate them. For a SOC team, it might be an analyst who finds a threat at 2am
that the rule engine missed. For a retailer, it might be an associate who can't answer a
customer's "do you have this in stock?" question. Ground the story in what they told you.

**What is the right runtime?**
- Executive briefing: 20–30 min
- Standard discovery demo: 40–50 min
- Technical deep-dive: 60–90 min (only when explicitly requested)
- Always leave 10–15 min for Q&A and next steps — build this into the total.

## Step 3: Design the Scenes

**Structure: opening punch → 3–5 vignettes → value confirmation close.**
This is the required structure per `references/demo2win-conventions.md` (D-051).
Scene count: 3 minimum, 5 maximum vignettes (not including the opening and close).

**Vignette independence:** Every scene must be independently skippable. If the SA
needs to drop a scene for time, the next scene must still make sense. Include a
`**Skip signal:**` note in each scene explaining when to skip it and what the impact is.

**Order:** Early scenes establish **outcome and value**; middle and later scenes expose
**how**. Avoid opening with infrastructure unless the audience is purely technical.

Each scene must answer three questions before you write it:
1. **What pain point does this address?** (from `pain_points` in the discovery JSON)
2. **What feature demonstrates the resolution?** (from `demo_scope.recommended_features`)
3. **What is the single wow moment?** (the thing they'll mention when they recap the demo)

Scene design rules:
- **First vignette earns trust.** The most immediately relatable pain point with the most
  visceral proof — live data, a query in milliseconds, a before/after contrast.
- **One feature per vignette.** A scene showing ELSER + ML anomaly + Agent Builder shows
  nothing. Pick one. The others get their own scenes.
- **Exec pivot points.** At scene breaks, give the exec one sentence of operational framing
  before moving to the next scene. Keep execs in the room.
- **Platform-constrained features:** If the platform audit marks a feature `setup_required`,
  include a pre-demo setup note. If `upgrade_required`, use a narrative or screenshot, not
  a live scene.

## Step 4: Write the Script

### Output 1: `demo/{slug}-demo-script.md`

Use this structure. Adapt section names to fit the customer's context — don't be mechanical.

```
# [Demo Title — make it evocative, not generic]
**Customer:** [Company] | **Date:** [date] | **Runtime:** [N] min
**Presenters:** [Names and roles from elastic_team]
**Audience:** [Names and roles from contacts]
**Format:** Live Kibana + Dev Tools [adjust as needed]

---

## Context
[2–3 sentences: what we learned in discovery, why this demo matters to this specific
customer. This is for the SE, not the customer.]

## Human Story
[The person at the center of the demo. Name, role, the scenario they face. 2–4 sentences.
This thread is woven through every scene.]

## Opening Punch ([N] min) — [Presenter]
[Required per D-051. The business problem statement before any product is shown.
Name a specific role, state a consequence, ground in discovery. 30–60 seconds to deliver.
No keyboard action during the opening punch. See references/demo2win-conventions.md Rule 1.]

**Opening punch (deliver before touching the keyboard):**
*"[Role at customer] is dealing with [specific problem]. Right now, [consequence — time,
money, risk, missed opportunity]. Today we're going to show you how that changes."*

**Talking points:**
- [Ground in discovery: "You mentioned X — here's what changes when Elastic addresses it."]

---

## Scene [N]: [Name] — [Feature] ([N] min)
**Pain point addressed:** [label from discovery pain_points]
**Presenter:** [Name]
**Can stand alone:** yes [required — verify this is true before publishing script]
**Skip signal:** [when to skip this scene and what the audience impact is]

**Setup** (30 sec — audience grounding):
[One or two sentences that re-establish the scenario. An audience member who just joined
should be able to follow from here. This is what makes the vignette self-contained.]

**Story:** [1–2 sentences connecting this scene to the human story thread]

> ⚙️ **Pre-demo setup required:** [If applicable — what must be done before demo day]

**On screen — Step 1 ([N] sec/min):**
[Specific screen, specific action. "Kibana Discover on `store-transactions-*`, auto-refresh
5s." Not "open Kibana and show some data."]
[Include query/config verbatim if applicable]

*Say:* "[Exact or near-exact talking point. Quote the customer back to themselves where
impactful.]"

**On screen — Step 2 ([N] min):**
[Next step]

**Wow moment:** *"[The single most memorable sentence of this scene. This is what they'll
repeat to their colleagues tomorrow.]"*

**Exec bridge:** *"[One sentence for the DM/exec contact — operational or business framing
of what just happened, before moving to the next scene.]"* [Omit if no exec in audience]

---

[Repeat scene structure for each scene]

---

## [Scene: AI Cost + Usage — Operational Transparency] (optional — include when demo has Agent Builder)

**Talking points:**
- "Everything the AI agents do is observable. This dashboard shows you the exact token
  consumption per agent, per session, what it's costing, and which models are being used."
- "Budget owners and IT governance get this visibility without asking engineering. You can
  see cache efficiency — how much is being reused versus re-tokenized — which directly
  correlates to operating costs."
- "If usage spikes after a new release, you see it here before your cloud bill arrives."

**On screen:** Navigate to AI Usage & Cost Overview dashboard. Show daily spend trend,
cost by model breakdown, sessions by agent, and recent session table.

**Wow moment:** *"You're not just deploying AI — you're operating it. This is what AI governance
looks like in practice: complete visibility into what your agents are doing and what it costs."*

**Exec bridge:** *"This is the dashboard your CFO and CTO both want to see — business value
from AI, with cost controls they can actually act on."*

*Note for SE: This scene is 3-5 minutes and lands especially well with IT leadership, finance,
and governance stakeholders. Skip if audience is purely technical/developer-focused.*

---

## Value Confirmation Close ([N] min) — [Presenter]
[Required per D-051. Ties back to the opening punch. Not a feature recap — an outcome
confirmation. See references/demo2win-conventions.md Rule 3.]

**Echo the punch:**
*"We started today talking about [the specific problem from the opening punch]."*

**Connect to what they saw:**
*"What you just saw was [plain-language description of the demo journey — not a feature list].
[Role] can now [specific outcome]."*

**Technical win statement:**
*"[The explicit proof point from the technical win criteria in demo-goals.md].
That's what a successful evaluation looks like: [criteria 1], [criteria 2]."*

**Next steps (specific, not generic):**
[Name the person and the action. Pull from next_steps in discovery JSON.
"[Name], you mentioned [specific thing from discovery]. The logical next step is [specific action].
Can we [specific ask with timeframe]?"]

---

## Audience Flow
| Segment | Time | Duration | What's Happening |
|---|---|---|---|
[One row per scene, with cumulative timing]

## Platform Notes
[Summary of any setup_required features and their pre-demo tasks, pulled from platform audit.
If no audit was run: "Platform audit not completed — run demo-platform-audit before build."]

```

### Output 3: `demo/{slug}-live-script.md`

The live delivery script. SE keeps this on the second monitor during the call. It is a
**standalone file** — compact header, the At-a-Glance table, and the Dev Tools Quick
Reference. No narrative prose. No scene context paragraphs. Everything the SE needs to
execute, nothing they need to read.

```
# [Demo Title] — LIVE SCRIPT
**Customer:** [Company] | **Date:** [date] | **Runtime:** [N] min
**Presenters:** [Names] | **Audience:** [Names and roles]

---

## At-a-Glance Run of Show

| # | Time | Say | Do | Expect |
|---|------|-----|----|--------|
| **[Scene name]** | | | | |
| 1 | 0:00 | [One sentence talking point] | [Exact action or `single-line command` or [Q1] for multi-line] | [Observable result] |
...
```

**Table rules:**
- Row numbers are flat and sequential — scene separator rows (bold, no number) do not break the sequence.
- **Say**: one tight sentence only. No narrative. If two sentences are needed, use two rows.
- **Do**: single-line commands inline as `` `code` ``; multi-line Dev Tools queries use a `[Qn]` reference that matches the Dev Tools Quick Reference below.
- **Expect**: a brief observable fact ("Count > 50 k", "Ranked list with claim IDs", "Red SLA band visible"). Not an explanation.
- Include one row per "On screen — Step N" from the narrative script. Opening and Close get rows too.

**Dev Tools Quick Reference — block format** (included at the bottom of `{slug}-live-script.md`; omit section entirely if no scene uses multi-line Dev Tools queries):

Each `[Qn]` referenced in the At-a-Glance table gets a labeled code block here. Use this format:

```
**[Q1] — Scene 1: Sample claims**

GET fraud-claims/_search
{
  "size": 3,
  "_source": ["claim_id", "source_system", "sla_deadline"],
  "query": { "match_all": {} }
}
```

Blocks are in scene order, numbered to match the table. The full section is meant to be one
continuous paste buffer — an SE can scroll to this section and copy each block directly into
Kibana Dev Tools without referring back to the narrative scenes.

### Output 2: `opportunity/{slug}-demo-brief.md`

One page. This is what the AE reads before the meeting. No queries, no config details.

```
# Demo Brief — [Company] | [Date]

**What we're showing:** [3 bullets — one per major scene, in plain language]

**Why it matters to them:** [3 bullets — one per pain point, using their language]

**The story we're telling:** [2 sentences — the human story thread, simplified]

**Watch for these moments:**
- [Wow moment from Scene 1]
- [Wow moment from Scene 2]
- [Wow moment from Scene 3]

**Your job during the demo:**
- When [feature] appears on screen: [what the AE should say or watch for]
- At the close: ask [specific next-step question from discovery]
- Do NOT mention: [competitors, internal terms, anything from the gap report that we
  haven't addressed yet]
```

## What Good Looks Like

**Integration-first data sourcing (D-043):** When scripting Observability or Security scenes, name data sources by their Fleet integration stream — `metrics-kubernetes.pod-*`, `metrics-nvidia_gpu.stats-*`, `logs-system.syslog-*` — not Prometheus-scraper-style names (`metrics-k8s.state.prometheus-*`, `metrics-gpu.dcgm.prometheus-*`). If the script references a specific index or data stream, that name must correspond to a real Fleet integration package or a confirmed custom index. Scripts that name non-existent streams cause broken dashboards and ES|QL errors downstream. When in doubt, leave the data source as `[integration TBD — probe cluster]` in the script and resolve it in demo-data-modeler.

**Lowe's pattern** (technical deep-dive, mixed audience): 45-min script, 6 scenes, human
story of an associate helping a customer who drove across town on bad inventory data. Each
scene escalates: live data → ML anomaly → semantic search → agent → observability →
supply chain ops view. Exec bridge at each transition. Verbatim from discovery woven in
("you mentioned ELSER before this call"). Wow moments are one crisp sentence.

**Citizens Bank pattern** (champion_enablement, single contact): 30-min script, 3 scenes.
No DM present — designed for Michael to screenshot and share with Joe Burke. Closing slide
is "what this looks like for your leadership" not "next steps with Elastic." Uses
"scattered everywhere" verbatim. No Bain or AWS Bedrock mention anywhere.

**Migration assessment pattern** (IHG): 40-min script opens with current-state diagnostic
view — show them their own cluster. Migration delta shown explicitly: "here's what you have
today, here's what changes on Serverless." Gaps section prominent: "before we can show you
the full picture, we need the diagnostic from your other three environments."

**SOC/Security pattern** (DT SOC-T): ML anomaly detection as Scene 1 (they already use it
— earn trust by showing you understand their world). ES|QL threat hunting as Scene 2.
AI Assistant as Scene 3 (with connector caveat). Human story is an analyst finding a
low-and-slow lateral movement pattern that rules missed. Exec bridge each time: "that
detection just saved your team four hours of manual correlation."
