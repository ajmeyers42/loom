# UI build-out handoff — local web control plane over `loom_state` (slices S0–S2)

**For:** a fresh implementation chat. **Plan of record:** [`ui-buildout-prep.md`](ui-buildout-prep.md) (decisions,
constraints, screen → backend map, slices S0–S6, test plan). This file is the executable brief: what exists, what to
build first, what "done" means, and the traps. If the two disagree, ask the SA.
**Baseline:** branch `fix/p2-functional-test` (HEAD includes the P2 control plane, the 12 functional-test fixes, the
`KIBANA_SOLUTION` suggestion, and the prep docs). Create `feat/ui-s0` from it. 44 tests and `run_evals.py` are green.

## 1. Mission

Give the SA a real, clickable control plane for Intake → Qualify → Vision → Demo path, replacing the static
prototype with a UI that changes engagement state through `loom_state`. First deliverable is **S0–S2**:

- **S0** read-only shell: server, token, root checks, Overview (`next`, `hygiene`, engagement list).
- **S1** Create + input settings: SB-01 create, SB-02 keystore including the suggested `KIBANA_SOLUTION` and override.
- **S2** Evidence: add inputs, plan + "Check outputs" (`listen record`), claims, gaps inbox.

Stop after S2 for review. S3 (Qualify), S4 (Vision), S5 (Demo path), S6 (agent orchestration) are later handoffs.

## 2. Decisions assumed (confirm with the SA in the first reply; proceed on these unless told otherwise)

| # | Assumption |
|---|---|
| D1 | Local web app bound to `127.0.0.1`, one start command |
| D2 | Python stdlib `http.server` + static HTML/JS, no build step, no new dependencies; reuse markup/styles from `docs/ux/sa-first-journey-prototype.html` (copy into the app, do not edit the original) |
| D3 | LLM steps are **hand-off**: the UI shows the plan and a copyable agent prompt; the SA runs the skill in Cursor/Claude; a **Check outputs** button runs the `record` step |
| D4 | Approver = `LOOM_APPROVER` / OS user from server config, shown in the header; no sign-in |
| D5 | v0 adapter calls the CLI in-process (`cli.main([... "--json"])`, as the tests do); lift command bodies into library functions only where it simplifies a route |

## 3. What exists (don't rebuild)

- `scripts/loom_state.py` → `scripts/loomstate/` (stdlib only): `bootstrap` (create/import), `keystore`, `solution`
  (Kibana space suggestion), `intake` (listen/gaps/scan), `qualify`, `vision`, `demopath`, `state` (`Engagement`,
  `derive`), `core` (`get_root`, identity-leak checks, hashing), `legacy`, `schema`.
- Overview data: `overview(root, slug, use_fs=…)` in `cli.py` (what `loom_state next` prints) — the Overview route
  should return it directly; `--no-fs` = derive from `pipeline-state` only.
- Every CLI command supports `--json`. Command groups: `new, inputs add, keys {status,list,init,defer,validate,set,
  clone}, listen {plan,record}, scan {record,skip}, gaps {list,respond}, qualify {plan,record,status,decide,
  design-anyway}, vision {plan,freeze,confirm,map …}, path {plan,check,commit}, next, hygiene`.
- Test harness: `tests/test_loom_state.py` (`P2Base`: temp root, `cli(...)` helper, synthetic `p2-acme` fixtures).
  `python3 -m unittest discover -s tests`.
- `keys status --json` already returns `kibana_solution` = `{value, source, confirmed, confidence, reason, suggested,
  options}`; `keys set KIBANA_SOLUTION=<classic|es|oblt|security>` confirms/overrides it.

## 4. Where to put things

```text
scripts/loom_ui/            # new package; stdlib only
  server.py                 # http.server, routing, token, origin/path checks
  adapter.py                # route -> loom_state call, returns {ok, data, warnings, state}
  static/                   # index.html, app.js, styles.css (derived from the prototype)
scripts/loom_ui.py          # entry: python3 scripts/loom_ui.py --root ~/loom-ux --port 8765
tests/test_loom_ui.py       # adapter + server tests (reuse P2Base patterns)
```

Never write engagement data into the repo. The UI's own config (port, token) is per-launch and in memory.

## 5. Build spec

### 5.1 Server (S0)

- Bind `127.0.0.1` only; random free port by default. Print the URL with a per-launch token
  (`http://127.0.0.1:PORT/?t=TOKEN`); require the token (cookie after first load, or `X-Loom-Token`) on every route.
- Reject requests whose `Origin`/`Host` isn't the server itself (no CORS headers at all).
- Refuse to start if the root is inside a git work tree (reuse `find_git_worktree`); warn when cloud-synced.
- Routes (all JSON; reads `GET`, changes `POST`):
  - `GET /api/engagements`, `GET /api/e/{slug}/next[?fs=0]`, `GET /api/hygiene`
  - S1: `POST /api/engagements`, `GET /api/e/{slug}/keys`, `GET /api/keys/siblings`, `POST /api/e/{slug}/keys/{set|clone|defer|validate}`
  - S2: `POST /api/e/{slug}/inputs`, `GET /api/e/{slug}/listen/plan`, `POST /api/e/{slug}/listen/record`, `GET /api/e/{slug}/gaps`, `POST /api/e/{slug}/gaps/respond`
- Response envelope: `{ok, data, warnings, state}` where `state` is the refreshed `next`. Errors:
  `{ok:false, error:{code, message}}` with HTTP 4xx; never a stack trace. `LoomError` → 400/409; unknown slug → 404.
- Serve `static/` only; no directory listing; reject any path with `..`.
- Slug path param must match `^[a-z0-9]+(-[a-z0-9]+)*$` before touching the filesystem.

### 5.2 Adapter

- One function per route calling `cli.main([...argv, "--root", root, "--json"])` with stdout/stderr captured. `--approver`
  exists only on approval commands (`qualify decide|design-anyway`, `vision freeze|confirm`, `path commit`; S3+), so the server sets
  `LOOM_APPROVER` for the process and passes `--approver` explicitly on those later routes; parse JSON; map `LoomError` (non-zero exit, message on stderr) to the error envelope.
- **Serialize all adapter calls with a lock** — `contextlib.redirect_stdout` is process-global, so concurrent requests
  would interleave output. (Or call library functions directly and drop the capture; either way the lock is required until then.)
- `keys set` must never use the `-` (getpass) form. Pass the value in memory; never log request bodies for `keys/*`.
- Before returning data destined for a shared surface (slug, display name, `.env`-bound values), run
  `find_identity_leaks`; the Overview header and Qualify screens may show private identity, nothing else may.
- File edits only through `inputs` (`inputs add`) — no generic file read/write endpoint. Evidence excerpts come from
  `listen`/`gaps` output, not from reading arbitrary paths.
- **`POST /api/e/{slug}/inputs`** (browser file picker → `inputs/`):
  - Body: `{ "uploads": [ { "filename": "<basename>", "content": "<utf-8 text>" } | { "filename": "<basename>", "content_base64": "<standard base64>" } ] }`
    or legacy single `{ "filename", "content" | "content_base64" }`.
  - `filename` must be a basename only (no `/` or `\\`); max **20 MiB** per file (`too_large` → 400).
  - Writes via `bootstrap.add_input` (same as CLI `inputs add`); response includes refreshed `state` (`next`) so the UI
    can show staleness after discovery was already recorded.
  - Never log request bodies for `keys/*` or `inputs`.
- **SB-01 Create:** multi-select file picker and/or paste → `POST /api/engagements` then extra `POST …/inputs` uploads
  when the first selected file is binary or there are additional files.

### 5.3 Screens

Start from the prototype frames and keep the SA-first language (phase names, not skill names; skill names in an
expert Activity Log).

- **Overview:** phase, next action (+ its command as "what runs"), blockers, notes (incl. the `KIBANA_SOLUTION`
  suggestion note), stale banner with reason, hygiene status, engagement picker. Header shows the approver.
- **SB-01 Create:** company, opportunity, optional id (private); public slug + display name (validated live against
  `find_identity_leaks`); entry mode (notes / import / scratch) and solution; notes upload. Slug uniqueness feedback.
- **SB-02 Keystore / input settings:** status (present / missing / validated, no values), set values (password
  inputs), clone-from-sibling picklist with shared-cluster `INDEX_PREFIX` feedback, "Set up later", optional
  read-only probe button. A **Kibana space solution** row: value, reason, `suggested` vs `confirmed`, the four options,
  and an Override control that posts `KIBANA_SOLUTION`; after confirmation it reads "confirmed by you".
- **SB-03 Evidence:** inputs list with hashes, **file picker** (multi → `inputs/`) + paste follow-up, plan + copyable agent prompt, **Check outputs**
  (surfaces `warnings`, `closed_by_reinference`, `new_gaps`), claims with source excerpt, gaps inbox with
  "Update in Inputs" targets and gap responses.
- Show each warning returned by the backend verbatim; do not swallow them.

### 5.4 Accessibility

Semantic landmarks and headings, labeled controls, visible focus, no color-only status, full keyboard path for
Create → Keystore → Add notes → Check outputs. Target WCAG 2.2 AA; note gaps rather than hiding them.

## 6. Acceptance criteria (S0–S2)

1. `python3 scripts/loom_ui.py --root <sandbox>` starts, prints a tokened URL, and refuses a root inside git.
2. Overview for a CLI-created engagement equals `loom_state next --no-fs --json` field for field (test asserts it).
3. Create via UI produces the same files and state as `loom_state new`; `.env.example` contains no private identity;
   a slug or display name containing the company name is rejected with the CLI's message.
4. Keystore screen never returns a secret value (test posts a synthetic key and asserts it appears in no response,
   log line, or file other than `.env`).
5. `KIBANA_SOLUTION`: unclear notes → `classic` suggested; override to another value flips `confirmed` and survives
   `listen record`; invalid value → error envelope.
6. Add notes → plan → (SA/agent writes outputs) → Check outputs: warnings and gap closure appear; a stale input
   shows the re-run banner.
7. Security tests pass: missing/invalid token → 401, foreign Origin → 403, `..`/bad slug → 400, no stack traces.
8. Browser E2E through the Cursor browser (`cursor-ide-browser`: `browser_navigate`, `browser_snapshot`,
   `browser_take_screenshot`, `browser_fill`, `browser_click`) on a sandbox root covering Create → Keystore → Add
   notes → Check outputs, with screenshots in `~/loom-compare/_runs/<slug>-ui-shots/`.
9. Keyboard-only pass of that path succeeds; a11y gaps listed in the final report.
10. `python3 -m unittest discover -s tests`, `python3 scripts/run_evals.py`, and `loom_state hygiene` are green; no
    customer data in the repo; no new third-party dependency.

## 7. Traps and non-goals

- **No approval actions in S0–S2.** Record decision, Design anyway, Freeze, Approve confirmation, and Commit demo path
  arrive in S3–S5 with hash display; don't stub them as enabled buttons.
- **No cluster access.** `keys validate --probe` is the only network call and only behind an explicit click.
- Don't edit `docs/ux/**` (prototype, blueprint, p2 docs). Copy/IA gaps go in `docs/ux-build/ui-friction.md` for the
  UX chat, one row each: screen, what the SA needed, what the backend returns, type (copy / missing-info /
  extra-step / contract-gap / CLI bug).
- Don't invent state in the UI. The server is stateless; a browser refresh must reproduce the screen from
  `pipeline-state.json`.
- Don't put real names in fixtures; synthetic Acme / Northwind only. Don't print or log secrets.
- Don't add a build toolchain, bundler, or package install for S0–S2.
- A UI feature that needs a CLI change is a CLI change first: failing test, minimal fix, then the route.
- Don't commit or push without asking the SA.

## 8. Relationship to the browser-mode UX test

[`docs/testing/p2-ux-driven-test.md`](../testing/p2-ux-driven-test.md) (browser mode) can run **in parallel**. Its run
log feeds §7 of the prep doc. If it finishes first, apply its contract gaps to S1–S2 before building those screens
(especially where SB-02 shows the `KIBANA_SOLUTION` suggestion); if not, build to this handoff and reconcile later.

## 9. Final report (what to send back)

Per-slice status; routes added; files changed; test counts and before/after; screenshots; accessibility gaps;
`ui-friction.md` rows; contract gaps for the UX chat; anything that needed a CLI change. End by asking before
committing.

## 10. Chat split

| Chat | Owns |
|------|------|
| UX lineage | Blueprint, prototype, copy, IA, validation; consumes `ui-friction.md` |
| UI implementation (this brief) | `scripts/loom_ui/`, `tests/test_loom_ui.py`, `ui-friction.md`, and CLI fixes the UI exposes |
| Browser-test chat (optional, parallel) | Friction log from the prototype-vs-CLI run |

## 11. First prompt for the fresh chat

```text
Implement S0-S2 of the loom UI per docs/ux-build/ui-handoff.md (plan of record:
docs/ux-build/ui-buildout-prep.md). Branch feat/ui-s0 off fix/p2-functional-test.

First reply: confirm decisions D1-D5 and the hand-off approach for LLM steps (or tell me what you'd change),
then proceed on them. Build in this order: S0 server + read-only Overview, S1 Create + keystore with the
KIBANA_SOLUTION suggestion/override, S2 evidence (inputs, plan, Check outputs, gaps).

Rules: stdlib only, no new dependencies, no build step; failing test first for each route; synthetic fixtures
only; sandbox LOOM_ENGAGEMENTS_ROOT=~/loom-ux; no cluster access; no edits to docs/ux/**; log UX friction in
docs/ux-build/ui-friction.md; no approval actions yet; never log or return secret values; no commits or pushes
without asking me.

Verify each slice with unit tests, then through the Cursor browser (screenshots to
~/loom-compare/_runs/<slug>-ui-shots/). Stop after S2 and send the final report from section 9.
```
