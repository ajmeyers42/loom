# P2 functional test 2 — UX-driven run with new inputs

**Purpose:** prove that the accepted SA-first storyboard (SB-01 → SB-07 + Overview hub) can be driven
end to end on a **new** engagement, with the P2 control plane doing the work behind each screen.
Test 1 ([`p2-legacy-comparison.md`](p2-legacy-comparison.md)) asked "does P2 reproduce a legacy run?";
this test asks "does the UX contract hold when the screens lead and nothing is mirrored from a past run?"
**Baseline:** branch `fix/p2-functional-test` (P2 + the 12 functional-test fixes) or later.
**Driver:** the storyboard — [`docs/ux/loom-ux-blueprint.md`](../ux/loom-ux-blueprint.md) §7.3 frames and
[`sa-first-journey-prototype.html`](../ux/sa-first-journey-prototype.html). The CLI is the backend, not the script.
**Contracts:** [`docs/ux/p2-handoff.md`](../ux/p2-handoff.md) §§2–3, §6; `docs/decisions.md` D-052.

## Safety rules (non-negotiable)

1. Sandbox root outside git and cloud sync: `LOOM_ENGAGEMENTS_ROOT=~/loom-compare` (or a new
   `~/loom-ux`). Never write engagement files into the loom repo.
2. No cluster mutation. Keystore: `keys defer`, or `keys clone --no-secrets` from a sandbox sibling.
   `keys validate --probe` (read-only GET) only if the SA says so.
3. Gates stay SA gates: Record decision, Freeze, Approve confirmation, Commit demo path are recorded
   only after the SA answers in chat. No "mirror legacy" pre-authorization in this test.
4. Do not edit `docs/ux/**` during the run. Copy / IA mismatches go in the friction log for the UX chat.
5. No commits or pushes unless the SA asks.

## Inputs (new — SA supplies)

Put them in `~/loom-compare/_runs/ux-inputs/` (never the repo). To exercise the contract and the fixes
from test 1, the set should cover:

| Need | Why | Exercises |
|---|---|---|
| Discovery notes (call notes / transcript, `.md` or `.txt`) | Notes-mode intake with verbatim evidence | SB-03, claims `source_ref` |
| A later follow-up note that answers ≥1 blocking gap | Path A: edit/add Inputs → re-listen closes the gap | SB-04 gap closure, `closed_by_reinference` |
| A storyline that spans two solution areas (e.g. Observability-led with a Security element) | `--solution cross_solution` → `KIBANA_SOLUTION` suggested from the notes/profile (`classic` unless clearly Observability or Security), SA override in input settings | Fix 4 |
| An Agent Builder ask | D-036 auto-include of the AI Cost + Usage dashboard | SB-05 |
| A capability the SA wants explicitly **out** (a catalog id, e.g. `ai-assistant`) | Out-of-Scope renders once | Fix 1 |
| Optional: an AE/SDR package (pre-P2 files with a company-derived prefix) | Import mode: legacy migration + legacy-slug rewrite | Fixes 2, 3 (candidate B) |

If the SA has no fresh customer inputs, write a synthetic set (Acme / Northwind style) in the sandbox —
not in `tests/fixtures/` — and say so in the run log.

## How a beat runs

For every beat: (1) open the screen in the prototype and name it; (2) show the SA what the screen would
show, sourced from CLI output (`loom_state next|gaps list|qualify status|vision plan|path check --json`);
(3) the SA acts using the screen's controls (copy as written); (4) the agent runs the backend command;
(5) log the row below. If the screen asks for something the CLI cannot do — or the CLI needs something
the screen never asks for — that is a **friction** row, not a reason to improvise.

Run log row (write to `~/loom-compare/_runs/{slug}-ux-run.md`):

| Beat | Screen / CTA | SA action (as on screen) | Backend command(s) | State change (`next` phase / approvals) | Contract check | Friction (type) | Wall-clock |
|---|---|---|---|---|---|---|---|

Friction types: **copy** (screen wording ≠ behavior), **missing-info** (screen lacks data the SA needed),
**extra-step** (CLI step with no screen), **contract-gap** (no rule says what should happen),
**CLI bug** (behavior contradicts a contract).

## Beats

| # | Screen (blueprint §7.3) | Backend | Contract check |
|---|---|---|---|
| 0 | Overview (empty root) | `L hygiene` | Root outside git; no stray `.env` |
| 1 | SB-01 Create — private identity + public slug + entry mode | `L new --slug acme-… --display "Acme …" --company … --opportunity … --entry-mode notes --solution cross_solution --notes …` | Slug unique, `loom:` tag normalized; `.env.example` has no private identity; `next` shows the suggested `KIBANA_SOLUTION` (classic unless clear) with an override hint |
| 2 | Overview → SB-02 Keystore / input settings — review, "Set up later" | `L keys status` → `L keys defer`; then `L keys set KIBANA_SOLUTION=<value>` to override | Keystore `deferred`; planning not blocked; `kibana_solution` shows value, reason, `confirmed: false` and the four options; an SA override flips it to `confirmed: true` and later `listen`/`qualify record` never change it |
| 3 | SB-03 Evidence — review claims + gaps | `L listen plan` → warp-listen → `L listen record` → `L gaps list` | Every claim has a verified excerpt; every gap has `gap_id` + "Update in Inputs" target |
| 4 | SB-04 Qualify — Refresh qualification, Record decision | `L qualify plan` → thread-qualify → `L qualify record` → `L qualify status` → SA decides → `L qualify decide …` | Decision + `approvals[]`; `continue_discovery` parks on Overview; `KIBANA_SOLUTION` suggestion refreshed from `primary_solution_area`; SA override via `L keys set` sticks |
| 4a | SB-04 → Inputs (Path A) — "Update in Inputs" | `L inputs add <follow-up>` → `L next` (stale banner) → re-listen → re-qualify → decide | Gap closes by re-inference; prior decision kept in history |
| 5 | SB-05 Vision — map chips, SA add, uncheck to Out of Scope, Freeze | `L vision plan` → warp-spark → `L vision map add/exclude …` → `L vision freeze` | ≥1 SA-added chip; D-036 row when Agent Builder is in; soft-limit warning once; Out of Scope lists each exclusion once; no private identity |
| 5a | SB-05 — Approve customer confirmation | refresh confirmation + summary TL;DR → `L vision confirm` | Confirmation customer-safe; `confirmation_approve` recorded |
| 6 | SB-07 Demo path — audit rows by owner, choose standard vs custom | `L path plan` → thread-audit → `L path check` → thread-suggest → SA decides → `L path commit --path …` | Audit = selected map; amber grouped pipeline / manual_once / customer; red blocks commit |
| 7 | Overview — resume | `L next --no-fs`, `L hygiene` | Phase reproduced from state alone; hygiene clean |
| B | Optional candidate B — SB-01 "Import AE/SDR package" | `L new … --entry-mode import --import <pkg>` → `L listen record` → `L qualify record` | Legacy-slug rewrite + migration warnings; no hand normalization |

`L() { python3 scripts/loom_state.py "$@"; }` with `LOOM_ENGAGEMENTS_ROOT` exported.

## Known UX contract gaps to probe (from test 1 — record what the screen does today)

- Identity aliases (brand / subsidiary / cluster names) — only company name, opportunity, id, and legacy slugs are protected.
- Import-mode evidence: zero `claims[]` passes; is "evidence unverified (imported)" shown anywhere?
- Kibana space solution: loom now suggests it (`classic` unless clearly Observability or Security) and the SA overrides it in input settings. Does SB-02 show the suggestion, its reason, and the override control — or does the SA only see it in `next` notes?
- Accepted risk after Design anyway: does Overview show accepted-risk gaps?
- `gap_id` built from field names can embed person names — may gap ids appear on shared surfaces?
- No "approved read-only probe" step before Demo path commit; the audit can stay `version_verified: false`.
- Legacy "resolved" gaps: CLI drops them into `closed_gaps` — does the UX agree?

## Exit

- Run log written with every beat and every friction row typed.
- `next --no-fs` reproduces the phase; `hygiene` clean; all four P2 approvals recorded (or the SA's
  stop point is explicit).
- Usability check (blueprint §10.4 items 1–3): note where the SA needed skill docs or CLI knowledge.
- Report back: friction rows grouped by type; CLI bugs with repro + file/line; contract gaps for the UX
  chat. Do not fix without SA approval.

## Kickoff prompt (fresh chat)

```text
Run docs/testing/p2-ux-driven-test.md. Baseline: branch fix/p2-functional-test.
The storyboard drives: for each beat open the prototype frame, show me what it would show from
loom_state output, let me act, then run the backend. New inputs are in ~/loom-compare/_runs/ux-inputs/.
Sandbox LOOM_ENGAGEMENTS_ROOT=~/loom-compare. No cluster access, no docs/ux edits, no commits.
Log every beat and friction row to ~/loom-compare/_runs/<slug>-ux-run.md.
At SB-02 / input settings, check the suggested KIBANA_SOLUTION (value, reason, override) and override it once.
```
