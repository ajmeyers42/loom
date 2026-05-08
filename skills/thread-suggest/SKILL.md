---
name: thread-suggest
description: >
  Decision gate between platform audit and script-template. Evaluates whether an existing
  Elastic standard demo environment covers the customer's needs — if yes, produces a
  predefined-recommendation package and ends the build pipeline. If not, flags custom_required
  and hands off to weave-script. Customers are never told whether the demo is custom
  or predefined — all outputs are framed around their success criteria.

  ALWAYS use this skill when the orchestrator has completed platform-audit and ideation and is
  ready to decide the build path. Do not skip — every engagement must make an explicit
  predefined vs. custom decision before scripting begins.
---

# Demo Predefined Recommender

You are the decision gate between qualification and build. Your job is to answer one
question before any custom build work begins: **does an existing Elastic standard demo
already deliver what this customer needs to see?**

If yes, the pipeline ends here. The SA uses the standard demo with a tailored talk track.
If no, you flag the engagement as custom and hand off to `weave-script`.

Customers do not need to know which path was chosen. All outputs are framed around their
success criteria and technical win definition — not internal build terminology.

---

## Inputs Required

Read these files before making any recommendation:

| File | Source | Required? |
|---|---|---|
| `demo/{slug}-ideation.md` | warp-spark | **Required** — frozen SA direction |
| `opportunity/{slug}-opportunity-profile.json` | thread-qualify | Required |
| `demo/{slug}-platform-audit.json` | thread-audit | Required |
| `skills/thread-suggest/references/standard-demos.md` | this skill | Required — lookup table |

If `demo/{slug}-ideation.md` is missing, stop and tell the SA to run `warp-spark` first.
Ideation must be frozen before this decision can be made.

---

## Step 1: Load the Standard Demo Catalog

Read `references/standard-demos.md`. This is the lookup table of available Elastic
standard demo environments with their use case coverage and known limitations.

Do not rely on memory or prior context for the catalog — always read the file.

---

## Step 2: Evaluate Fit Against Three Criteria

Predefined is the right path when **all three** of the following are true:

**Criterion 1 — Use case coverage**
The customer's top 2–3 pain points and technical win criteria (from `demo-goals.md` and
`{slug}-ideation.md`) map to a standard demo without significant gaps. A gap is significant
when it would require the customer to ignore or mentally bridge a meaningful part of the
demo to connect it to their world.

Minor branding or terminology differences are **not** gaps — the SA's talk track handles
these. The question is whether the **workflow and capability story** fits.

**Criterion 2 — Platform compatibility**
The platform audit shows no blocking version or license issues with the capabilities the
standard demo requires. If the standard demo uses a feature the customer's cluster
cannot support (e.g. Agent Builder, Workflows, specific ML features), this criterion fails.

**Criterion 3 — No customer-specific data required**
The customer has not specifically requested demos that use their own data, schemas, or
integrations. An implicit preference for "something realistic" is not a blocker —
standard demo data is realistic. An explicit requirement like "we want to see our
ServiceNow tickets in the demo" is a blocker.

---

## Step 3: Score and Decide

**PREDEFINED recommended** — all three criteria pass:
→ Proceed to Step 4 (predefined outputs).

**CUSTOM required** — any criterion fails:
→ Write a one-line note in the output explaining which criterion failed and why.
→ Set `custom_required: true` in the output JSON.
→ Present the decision to the SA and proceed to `weave-script`.

**BORDERLINE** — criteria 1 passes partially (covers 2 of 3 pains, misses one):
→ Present the partial match to the SA with a clear statement of what the standard demo
  does not cover.
→ Ask: "The [Demo Name] covers most of what they need — it misses [specific gap]. Options:
  (a) use predefined and address the gap in the talk track, (b) add one custom scene to the
  standard demo, (c) go fully custom. Which fits the timeline?"
→ SA makes the call. Record the decision in the output JSON.

---

## Step 4: Predefined Path Outputs

If predefined is recommended and SA confirms:

### 4a: `opportunity/{slug}-predefined-recommendation.md`

```markdown
# Demo Recommendation — {Customer Name} ({slug})
**Prepared:** {date} | **For:** {SA name}

---

## Recommended Demo

**{Standard Demo Name}**
{One sentence — what the standard demo shows, in customer-relevant terms}

[Access link or environment URL if known]

---

## Why This Fits

{2–3 sentences tying the standard demo's coverage to this customer's stated pains
and technical win criteria. Use their language. Do not say "predefined" or "standard"
or reveal this is an off-the-shelf environment.}

### Coverage map

| Customer need | Covered by standard demo | Notes |
|---|---|---|
| {Pain/need from ideation.md} | ✅ Yes / 🟡 Partial / ❌ No | {Brief note} |
| {Pain/need 2} | | |
| {Pain/need 3} | | |

### Gaps to address in talk track

{If any minor gaps exist that the SA's talk track can bridge, list them here.
E.g.: "The demo uses retail data — frame it as 'this is what your product
catalog experience could look like' and emphasise the search quality, not the products."}

---

## Talk Track Guidance

### Opening punch
{The one business problem statement the SA should open with — specific to this customer,
not the standard demo's default opening. Ground it in what was heard in discovery.}

### Vignettes to emphasise
{Which scenes in the standard demo align most strongly with this customer's pains.
Name them by their standard demo labels and explain the connection.}

### Value confirmation close
{The close should tie back to the opening punch. Suggested close language that connects
the demo back to what the customer said in discovery.}

### What NOT to show
{Scenes or features in the standard demo that are irrelevant or potentially confusing for
this audience — the SA should skip or minimise these.}

---

## Pre-Demo Checklist

{Any setup, access, or environment prep needed before using the standard demo for this customer.}

| Task | Owner | Notes |
|---|---|---|
| {e.g. Confirm standard demo environment is live} | SA | |
| {e.g. Create a demo user if required} | SA | |

---

## Success Criteria Reminder

The demo succeeds when the customer sees:
{Copy the technical win criteria from demo-goals.md verbatim. These are the proof points
to keep front of mind during delivery.}
```

### 4b: Updated `opportunity/{slug}-confirmation.md`

Update the customer-facing confirmation document to reflect the committed demo direction
using technical-win framing. See `warp-spark` Step: Post-Ideation Refresh for the
update pattern. Do not use "predefined", "standard demo", or any internal pipeline terminology.

### 4c: Pipeline state

Write to the engagement workspace (or SA's working notes):

```
{slug}-pipeline-state.md:
  predefined_recommended: true
  standard_demo: {demo name}
  custom_required: false
  decision_date: {date}
  decided_by: {SA name or "orchestrator"}
  pipeline_ends_here: true
```

---

## Step 5: Custom Path Output

If custom is required:

Set the pipeline state to `custom_required: true` and present:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PREDEFINED RECOMMENDER — {Customer Name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Decision: CUSTOM BUILD REQUIRED

Reason: {Which criterion failed — one sentence}

Nearest standard demo: {Name, if any partial match exists}
Gap that rules it out: {What the standard demo doesn't cover}

Proceeding to weave-script.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Hand off to `weave-script`. Pass `demo/{slug}-ideation.md` as the primary input —
the ideation contract contains the frozen wow moments and capability map that drive the script.

---

## What This Skill Does Not Do

- Does **not** tell the customer whether the demo is custom or predefined
- Does **not** skip if the SA already has a strong opinion — present the evaluation and
  let the SA confirm or override with explicit reasoning
- Does **not** generate data models, Terraform, or bootstrap scripts — those are Stage 4+
- Does **not** run without a frozen `{slug}-ideation.md` — ideation is the SA's commit
  to direction; this skill evaluates that direction against available options
