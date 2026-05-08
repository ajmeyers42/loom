# Demo2Win Conventions — loom Script Standard

**Source:** [2Win! Global — Demo2Win® methodology](https://www.2winglobal.com/programs/demo2win/)
**Scope:** These are the structural rules `weave-script` enforces for all custom demos.
The full Demo2Win 7-step framework (Limbic Opening, Tell-Show-Tell, Visual Roadmaps) is
optional depth for SAs who have been through the training.

---

## Three Required Rules

Every custom demo script must have these three structural elements — no exceptions.

---

### Rule 1: Opening Punch

**What it is:** The very first thing the audience hears before any product is shown.
A crisp, audience-specific statement of the business problem and its stakes.

**Why it matters:** If the audience doesn't feel the problem before they see the solution,
the demo is a product tour. The opening punch makes everything that follows feel like the
answer to a question they already care about.

**What it is not:** A company overview, an agenda slide, a "thank you for your time"
intro, or a feature list. Those are Demo Crimes (see below).

**Template:**

```
"[Role at customer] is dealing with [specific problem]. Right now, [what that costs them
— time, money, risk, missed opportunities]. Today we're going to show you how that changes."
```

**Example (operations vertical):**

```
"Your NOC operators are managing network faults across 14 systems, and when something
goes wrong at 2am, they're context-switching between five tools trying to correlate
what's happening. By the time they isolate the issue, the SLA has already been breached.
What we're going to show today is what that looks like when all of that is one place —
and when an AI that knows your environment does the first-pass diagnosis."
```

**The opening punch must:**
- Be grounded in something the customer actually said (from discovery notes or ideation.md)
- Name a specific role or team — not "your organization"
- State a consequence, not just a problem ("the SLA has already been breached" not just "faults happen")
- Take 30–60 seconds to deliver — not a paragraph, not a sentence

---

### Rule 2: Vignette Structure

**What it is:** The body of the demo is broken into **3–5 short, self-contained scenes**.
Each vignette has its own setup, product moment, and payoff. A vignette can stand alone —
an audience member who missed the previous scene does not lose the thread.

**Why it matters:** Long linear demos lose the room. Self-contained vignettes allow the SA
to skip, reorder, or cut for time without breaking the overall story. They also give the
audience natural "I get it" moments throughout — not just at the end.

**Scene count:** 3 minimum, 5 maximum (not including opening and close).
- 3 scenes: executive briefing (20–30 min total)
- 4–5 scenes: standard discovery demo (40–50 min total)
- Never more than 5 vignettes in a single demo session

**Each vignette must be independently skippable.** If removing a vignette from the
middle of the run of show would break the next vignette, they are not self-contained.
Fix by restructuring so each scene opens with its own micro-setup.

**Vignette template:**

```markdown
## Scene [N]: [Name] — [Feature] ([N] min)
**Pain point addressed:** [label from discovery]
**Can stand alone:** yes

**Setup** (30 sec — audience grounding):
[One or two sentences that re-establish the scenario context. An audience member
who just joined should be able to follow from here.]

**Product moment** ([N] min):
[The specific capability shown — one feature, one proof point. No feature dumps.
Include specific screen, query, or action.]

**Payoff** (30 sec — outcome statement):
[What just changed for the person in the story? State the business outcome, not the
feature. E.g.: "That took 8 seconds. Without this, that's a 20-minute manual correlation."]

**Wow moment** (one sentence, memorable):
*"[The crisp sentence they'll repeat to their colleagues.]*"

**Skip signal** (when to skip this vignette):
[If audience is purely technical and time is short: skip Scene 2. If exec leaves
early: skip Scene 4. Include explicit guidance so the SE can decide on the fly.]
```

---

### Rule 3: Value Confirmation Close

**What it is:** The final scene of the demo explicitly ties the ending back to the
opening punch. It is not a feature recap. It is an outcome confirmation.

**Why it matters:** Without a close that mirrors the opening, the demo ends on product
depth rather than business value. The economic buyer leaves thinking "impressive tech"
instead of "that solves our problem."

**Structure of the close:**

```
Part 1 — Echo the punch:
"We started with [the specific problem from the opening punch]."

Part 2 — Connect to what they saw:
"What you just saw was [plain-language description of the demo journey — not a
feature list]. [Role] can now [specific outcome]."

Part 3 — Technical win statement:
"[The explicit proof point from the technical win criteria.] That's what a successful
evaluation looks like for us — [restate criteria 1], [criteria 2], [criteria 3 if applicable]."

Part 4 — Next step (specific, not generic):
"[Name], you mentioned [something specific from discovery]. Here's what I'd suggest
as the next step: [specific action — not 'let's talk'."]
```

**Example close (operations vertical):**

```
"We started today talking about what happens when a fault hits at 2am — five tools,
no single view, SLA already burning.

What you just saw was your NOC team working from a single console: faults surfaced
automatically, AI doing the first-pass diagnosis, and escalation happening with one
click instead of a phone call.

The test for us is straightforward: can your on-call operator find the root cause of
a P1 fault in under 5 minutes without opening a second tool? Based on what we showed
today, the answer is yes.

Priya — you mentioned you're planning a NOC infrastructure refresh in Q3. The logical
next step is a focused POC on your top three fault categories. Can we set up a working
session with your team before the end of the month?"
```

---

## Demo Crimes Checklist

Avoid these. Each one is a documented reason demos fail to advance deals.

| # | Crime | Why it kills the deal |
|---|---|---|
| 1 | **Feature dump opening** | Audience disengages before any connection is made |
| 2 | **No opening punch** | Demo is a product tour; no urgency established |
| 3 | **Showing more than 5 vignettes** | Cognitive overload; nothing lands |
| 4 | **Scenes that depend on the previous scene** | One skip breaks the whole run |
| 5 | **Close that recaps features** | Leaves audience thinking "impressive tech," not "that's our answer" |
| 6 | **No connection back to opening punch** | The demo has no arc; it just... ends |
| 7 | **"Any questions?" close** | Passive; transfers control to the audience at the worst moment |
| 8 | **Generic next step** | "Let's schedule a follow-up" is not a next step. Name the action. |
| 9 | **Apology for going long** | Signals poor preparation; don't exceed planned runtime |
| 10 | **Reading talking points verbatim** | Loses the room; use the script as a guide, not a teleprompter |

---

## Mapping to the `weave-script` Scene Structure

The three rules map to specific sections of `{slug}-demo-script.md`:

| Convention rule | Script section |
|---|---|
| Opening punch | `## Opening` — must contain the business problem statement before any product is on screen |
| Vignette structure | `## Scene [N]` — each scene block, with the skip-signal note |
| Value confirmation close | `## Close` — structured with echo, connection, technical win statement, next step |

The `{slug}-live-script.md` At-a-Glance table has one row for the opening punch and one
row for the value confirmation close — these are never omitted from the live script.

---

## Going Deeper

SAs who want the full Demo2Win framework — Limbic Opening, Tell-Show-Tell, Visual
Roadmaps, Value Close methodology — can access:

- [Demo2Win program page](https://www.2winglobal.com/programs/demo2win/)
- [Tell-Show-Tell framework](https://www.2winglobal.com/blog/tell-show-tell-product-demo-framework)
- [Demo structure for elite SEs](https://www.2winglobal.com/blog/the-demo-structure-elite-ses-use-to-close-deals-faster-and-how-sales-teams-should-support-it)

The three rules above are the minimum required by loom. The full methodology
builds on them — same foundation, more structure.
