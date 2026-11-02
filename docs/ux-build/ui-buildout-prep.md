# UI build-out prep — a working SA-first control plane over `loom_state`

**Status:** draft prep, not a build. Finalize §7 after the browser-mode run of
[`docs/testing/p2-ux-driven-test.md`](../testing/p2-ux-driven-test.md); that run's friction log is the backlog.
**Why now:** the P2 control plane (`scripts/loom_state.py` + `scripts/loomstate/`) is complete and tested, but the
only UI is a static mockup ([`sa-first-journey-prototype.html`](../ux/sa-first-journey-prototype.html), no calls to
the backend). This turns the blueprint's "lightweight custom internal app" (§4) into a build plan.
**Does not change:** the blueprint, the prototype, or `docs/ux/**` — the UX lineage owns those. Gaps found here go
to the UX chat as contract gaps.
**Roadmap fit:** blueprint §11 — this is the P2 UI shell; P3 (Build & Readiness) and P4 (deploy approvals) are out
of scope here.

## 1. Decisions to close before coding

| # | Decision | Options | Recommendation | Needs |
|---|---|---|---|---|
| D1 | Form factor (blueprint §13 Q1) | Local web app · Cursor Canvas/extension · TUI | **Local web app**, bound to `127.0.0.1`, started by one command. The blueprint's P2 preference ("library + CLI first") is done; a browser UI is the next layer and is testable with the Cursor browser. | SA |
| D2 | Stack | stdlib `http.server` + static HTML/JS · FastAPI + React/EUI | **Start stdlib + vanilla JS**, reusing the prototype's markup, so the backend keeps its "stdlib only" property and there is no build step. Revisit EUI once the contract is stable (blueprint §10.1 prefers EUI patterns). | SA |
| D3 | How the UI runs the LLM steps | see §3 | **Hand-off first**, orchestration later | SA |
| D4 | Who is the approver | `LOOM_APPROVER` env · OS user · UI sign-in | Env/OS user for a local single-user app; real identity is a P4/P5 concern (blueprint §9.4) | SA |
| D5 | Call the library or the CLI | in-process library calls · shell out to `loom_state --json` | **In-process `cli.main([..., "--json"])`-style adapter** for v0 (the 44 tests already drive it that way), then lift the command bodies into library functions | Eng |

## 2. Hard constraints (carry over from the contracts)

- **Root:** engagements stay under `$LOOM_ENGAGEMENTS_ROOT`, outside git (AGENTS.md; `hygiene` must stay green). The
  server refuses to start if the root is inside a git work tree and warns when it is cloud-synced, matching
  `loom_state new`.
- **Dual identity (D-052):** private company / opportunity live only in `pipeline-state`. The UI shows them only on the
  Overview header and the qualification screens, never in a slug, display name, `.env`, tag, or anything copyable to a
  shared surface. Every response that feeds a shared surface goes through `find_identity_leaks`.
- **Secrets:** the keystore view returns present / missing / validated only — never values. Password fields post
  straight to `keys set KEY=-` equivalents and are not logged.
- **Approvals:** Record decision, Design anyway, Freeze, Approve confirmation, and Commit demo path each need a
  deliberate UI action and write `approvals[]` with artifact hashes (blueprint §9.5: a chat "yes" is not evidence).
  The UI shows what is being approved (artifact names + hash prefixes) before the button enables.
- **No cluster:** the only network call is `keys validate --probe` (read-only GET `/` and Kibana `/api/status`),
  behind an explicit button.
- **Local only:** bind `127.0.0.1`, require a per-launch token (header or cookie), reject cross-origin requests, and
  refuse path parameters that escape the engagement directory. No telemetry.
- **Accessibility:** WCAG 2.2 AA target; the primary flow (Create → Qualify → Vision approve → Path commit) must be
  keyboard-complete (blueprint §10.1).

## 3. The LLM-step problem (the main design question)

Four P2 stages need a skill run by an agent before the CLI can record the result: `warp-listen`, `thread-qualify`,
`warp-spark`, and `thread-audit` / `thread-suggest`. The `plan` commands emit the inputs, outputs and contract; the
`record` commands validate what the agent wrote. A web UI cannot run a skill by itself.

| Option | How | Pros | Cons |
|---|---|---|---|
| **A. Hand-off (recommended for v1)** | The screen shows the plan, a "Copy agent prompt" button, and a **Check outputs** button that runs the `record` step. The SA runs the skill in Cursor / Claude. | No new runtime, no keys, matches the SA's existing workflow | Two windows; the UI can't show progress inside the skill |
| B. Agent runtime from the UI | The server launches an agent run (Cursor SDK / Claude API) with the plan as the prompt and streams status | One window, real progress | New dependency and credentials, cost control, and approval-boundary risk (agent must never reach Freeze/Commit) |
| C. Hybrid | A for most stages; B only for the deterministic `listen` / `qualify` refreshes | Incremental | Two code paths |

Whatever the option, the rule holds: **the agent produces artifacts; only the UI's explicit SA action records an
approval.** Open question for the SA: is A acceptable for the first pilot?

## 4. Screen → backend contract (proposed API)

Verbs follow the CLI (`new, inputs, keys, listen, scan, gaps, qualify, vision, path, next, hygiene`). Reads are
`GET`; every state change is a `POST` returning the same JSON the CLI's `--json` returns plus a refreshed `next`.
All routes take `{slug}` except create/list.

| Screen | Reads | Actions (`POST`) | CLI source |
|---|---|---|---|
| Overview (hub) | `GET /engagements`, `GET /e/{slug}/next` (phase, next action, blockers, notes, stale), `GET /hygiene` | — | `next`, `hygiene` |
| SB-01 Create | slug availability | `POST /engagements` (company, opportunity, display, slug, entry mode, solution, notes/import) | `new` |
| SB-02 Keystore / input settings | `GET keys/status` (incl. `kibana_solution`: value, reason, confirmed, options), `GET keys/list` | `keys/set`, `keys/clone`, `keys/defer`, `keys/validate?probe=` | `keys *` |
| SB-03 Evidence | `GET listen/plan`, `GET gaps` (+ claims) | `inputs/add`, `listen/record`, `gaps/respond`, `scan/record|skip` | `listen`, `gaps`, `inputs`, `scan` |
| SB-04 Qualify | `GET qualify/plan`, `GET qualify/status` | `qualify/record`, `qualify/decide`, `qualify/design-anyway` | `qualify *` |
| SB-05 Vision | `GET vision/plan` (catalog, map, soft-limit state), `GET vision/map` | `vision/map/add|exclude|token-visibility`, `vision/freeze`, `vision/confirm` | `vision *` |
| SB-07 Demo path | `GET path/plan`, `GET path/check` (audit rows by owner) | `path/commit` | `path *` |

Contract rules for the adapter:

1. Responses are the CLI JSON, unmodified, wrapped as `{ok, data, warnings, state: <next>}`; errors are `LoomError`
   text with a stable `code`, never a stack trace.
2. Every `POST` is idempotent where the CLI is (re-record, re-set), and rejects when the stage is stale
   (`next.stale`), returning the "re-run required" reason for the banner.
3. File edits happen only through `inputs/add` and the existing artifact paths — no generic file-write endpoint.
4. The server holds no state of its own; refreshing the browser reproduces the screen from `pipeline-state.json`
   (blueprint §8 rule 5).

## 5. Build slices

Each slice ships behind the previous one and ends with: unit tests on the adapter (reuse `P2Base` in
`tests/test_loom_state.py`), a browser E2E through the Cursor browser against a sandbox root, and `hygiene` green.

| Slice | Scope | Exit |
|---|---|---|
| S0 Shell | Server + token + root checks; read-only Overview (`next`, `hygiene`, engagement list); static assets from the prototype | Overview reproduces `next --no-fs` for a sandbox engagement; no write routes exist |
| S1 Create + input settings | SB-01 create, SB-02 keystore incl. the `KIBANA_SOLUTION` suggestion and override, clone picklist, defer | Create → `.env.example` has no private identity; SA override sticks and shows "confirmed" |
| S2 Evidence | `inputs/add`, plan + Check outputs, claims with source excerpts, gaps inbox with "Update in Inputs" | A follow-up note closes a gap via re-listen; stale banner appears and clears |
| S3 Qualify | status/readiness, Record decision, Design anyway, accepted-risk visibility | Decision writes `approvals[]` with hashes; prior decision kept in history |
| S4 Vision | capability chips, SA add / exclude, soft-limit warning, Freeze, Approve confirmation | Out-of-Scope lists each item once; D-036 row appears with Agent Builder |
| S5 Demo path | audit rows by owner, standard vs custom, Commit | Red rows block commit; amber grouped by owner |
| S6 (optional) | Agent orchestration (§3 option B/C) | Agent can never reach an approval action |

## 6. Test plan

- **Adapter/unit:** route → CLI parity tests on the synthetic `p2-acme` fixtures; one test per forbidden case
  (private identity in a response, path escape, missing token, cross-origin request, secret value in a response).
- **Contract:** the existing schemas (`pipeline-state`, `discovery`, `opportunity-profile`, `platform-audit`) validate
  every state the UI writes.
- **Browser E2E:** the Cursor browser drives the real UI on a sandbox root (`browser_navigate`, `browser_snapshot`,
  `browser_take_screenshot`); the run log format from `p2-ux-driven-test.md` carries over, now with real clicks.
- **Usability (blueprint §10.4):** an SA who hasn't read the skill docs completes Create → qualified decision in
  under 10 minutes; record where the CLI or a skill doc was needed.
- **Accessibility smoke:** keyboard-only pass of the primary flow, plus a screen-reader landmarks check.

## 7. Inputs from the browser test (fill in after the run)

Source: `~/loom-compare/_runs/<slug>-ux-run.md` and `<slug>-ux-shots/`. Do not paste customer data here.

| Friction type | Count | Becomes |
|---|---|---|
| contract-gap | _tbd_ | UX decisions to close before the affected slice |
| missing-info (screen lacks data) | _tbd_ | New fields / panels on the screen |
| extra-step (CLI step with no screen) | _tbd_ | New controls, or an automatic step |
| copy | _tbd_ | Wording fixes (UX chat) |
| CLI bug | _tbd_ | Fix in `loomstate` before the slice that surfaces it |

Already known (from test 1, still to be confirmed on screen):

- No home for `identity.aliases[]` (brand / subsidiary / cluster names).
- Import mode shows zero claims as a pass — needs an "evidence unverified (imported)" state.
- Accepted-risk gaps are not shown on Overview after Design anyway.
- Gap ids built from field names can embed person names — decide whether ids may appear on shared surfaces.
- No approved read-only probe step before the demo-path commit (`version_verified: false` still commits).
- Legacy "resolved" gaps are dropped into `closed_gaps` — UX to confirm.
- SB-02 has nowhere to show the suggested `KIBANA_SOLUTION`, its reason, or an override.

## 8. Out of scope

Deploy approval and Kibana deep links (P4), build/readiness progress UI (P3), engagement-scoped key wizard and
retention wizard (P5), hosted/multi-user deployment, and any change to `docs/ux/**`.

## 9. Kickoff prompt (fresh chat, after the browser run)

To start building before the browser run, use [`ui-handoff.md`](ui-handoff.md) §11 instead — it is the executable
brief for S0–S2 and assumes the recommendations in §1 and §3 (hand-off for LLM steps).

```text
Read docs/ux-build/ui-buildout-prep.md, then the run log and screenshots from the browser-mode UX test
(~/loom-compare/_runs/<slug>-ux-run.md, <slug>-ux-shots/). Branch off fix/p2-functional-test as feat/ui-s0.

1. Fill in §7 from the friction log and list the contract gaps that block S0-S2 for the UX chat.
2. Ask me to close D1-D5 (use the recommendations if I agree) and the LLM-step option in §3.
3. Then build S0 only: the local server and read-only Overview over loom_state, with adapter tests and a
   browser E2E on a sandbox root. No write routes, no cluster access, no edits to docs/ux/**, no commits
   without asking.
```
