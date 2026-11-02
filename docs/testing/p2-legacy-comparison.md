# P2 functional test — legacy engagement vs P2 re-run

**Purpose:** prove the P2 control plane (`loom_state` + updated intake → demo-path skills) on a
real, previously-run engagement, and compare its results with the legacy artifacts.
**Baseline:** syncpoint tag `syncpoint/p2-full` (see `git show syncpoint/p2-full`).
**Harness:** `scripts/compare_engagements.py` (read-only; gates apply to the candidate only).
**Contracts:** `docs/ux/p2-handoff.md`, `docs/ux/p2-p3-validation.md`, `docs/decisions.md` D-052.

## Safety rules (non-negotiable)

1. **Never modify the legacy engagement.** Read it in place; H0 fingerprints it and H7 proves it is
   unchanged. Do not run `loom_state` with `--root` pointing at the legacy engagements root.
2. **Sandbox root outside git and outside cloud sync:** `LOOM_ENGAGEMENTS_ROOT=~/loom-compare`
   (not Google Drive / OneDrive / iCloud, not inside any repo).
3. **No cluster mutation.** No `bolt-spin`, `terraform apply`, `bootstrap-data.py` (even
   `--dry-run` is out of scope), Kibana/ES writes. Keystore: `keys defer`, or `keys clone --no-secrets`
   from a sandbox copy. `keys validate --probe` (read-only GET) only if the SA says so.
4. **No customer data in the loom repo.** Reports, findings, and candidate engagements stay under
   `~/loom-compare/`. The harness refuses `--out` inside the repo.
5. **Gates stay SA gates.** Qualification decision, vision freeze/confirm, and demo-path commit are
   recorded only after the SA answers in chat. For this test the SA may pre-authorize "mirror the
   legacy decision" — record that in each `--rationale`.
6. No pushes. Do not edit `docs/ux/**`. P2 bugs found here are reported, fixed only if the SA asks.

## Choosing the legacy engagement

Pick one with the richest P2-stage coverage: raw notes **plus** `*-discovery.json`,
`*-opportunity-profile.json`, `*-ideation.md`, `*-platform-audit.json`, and ideally a demo script
or predefined recommendation. Legacy file prefixes may differ from folder names — the harness
auto-detects the prefix (override with `--legacy-prefix`).

## Variables

```bash
export LOOM_ENGAGEMENTS_ROOT=~/loom-compare
LEGACY="<absolute path to the legacy engagement folder>"
SLUG="acme-<vertical>"          # public codename — never derived from the customer name
DISPLAY="Acme <Vertical>"
L()   { python3 scripts/loom_state.py "$@"; }          # functions, not variables (zsh does not word-split)
CMP() { python3 scripts/compare_engagements.py "$@"; }
```

## Handoffs

Each handoff has an entry check, the work, and an exit check. Run them in one chat (preferred for
this test) or one per chat; `loom_state next $SLUG` is the resume point between chats.

### H0 — Prep and baseline (no LLM work)

- Entry: loom repo at `syncpoint/p2-full` (or later), clean tests:
  `python3 -m unittest discover -s tests` and `python3 scripts/run_evals.py`.
- Work:
  - `mkdir -p ~/loom-compare/_runs`
  - `CMP manifest "$LEGACY" > ~/loom-compare/_runs/legacy.manifest.json`
  - Inventory the legacy tree read-only: prefix, artifacts present, legacy pipeline-state stage
    statuses, legacy path (predefined recommendation vs demo script).
  - Extract private identity from legacy discovery (`customer.company`) and profile (opportunity
    name / CRM id if present). Confirm `SLUG` / `DISPLAY` with the SA.
  - List raw inputs: text-readable notes, transcripts, follow-ups (`.md`, `.txt`, `.pdf`). Skip
    `.gdoc`/`.gsheet` stubs and binary Office files when a `.txt`/`.md` extraction exists. Skip
    generated artifacts and session decks unless they are the only source of a fact.
- Exit: manifest written; SA confirmed slug, display name, and input list.

### H1 — Bootstrap candidate A (notes mode — full re-run)

- Work:
  `L new --slug $SLUG --display "$DISPLAY" --company "<company>" --opportunity "<opp>" --opportunity-id "<id>" --entry-mode notes --solution <search|observability|security|cross_solution> --notes <file>…`
  then `L keys defer $SLUG`.
- Exit: `L next $SLUG` → phase Intake; `.env.example` has no private identity;
  tag `loom:<normalized slug>`.

### H2 — Intake (warp-listen)

- Work: `L listen plan $SLUG` → run `skills/warp-listen/SKILL.md` on `inputs/` → `L listen record $SLUG`.
  Diagnostic present in legacy? Add it with `L inputs add`, run warp-scan, `L scan record`;
  otherwise `L scan skip $SLUG`.
- Exit: discovery-parser complete; claims with verified excerpts; every gap has a `gap_id`.
- Optional Path A probe: if the legacy tree has a later follow-up note that was not part of the
  original parse, `L inputs add` it, re-listen, and record `closed_by_reinference`.

### H3 — Qualify (thread-qualify)

- Work: run `skills/thread-qualify/SKILL.md` → `L qualify record $SLUG` → show the recommendation
  and open blocking gaps → SA decides → `L qualify decide $SLUG --status … [--accept-risk g_… --rationale …] [--ae-aligned]`.
  If the SA chooses `continue_discovery` but wants the test to continue:
  `L qualify design-anyway $SLUG --rationale "functional test — mirror legacy"`.
- Exit: opportunity-review complete with a recorded decision; profile validates.

### H4 — Vision (warp-spark)

- Work: `L vision plan $SLUG` → run `skills/warp-spark/SKILL.md` (Mode 1 if demo-goals exist).
  To keep the comparison meaningful, seed the direction from the legacy ideation (archetype, wow
  moments, capabilities) and let the SA add ≥1 capability. Build the map with
  `L vision map add|exclude`, write `demo/$SLUG-ideation.md`, `L vision freeze $SLUG`, refresh the
  confirmation + summary TL;DR (`Demo direction:`), SA approves → `L vision confirm $SLUG`.
- Exit: ideation complete; map frozen; approvals `vision_freeze` + `confirmation_approve`.

### H5 — Platform audit and Demo path (thread-audit, thread-suggest)

- Work: `L path plan $SLUG` → run `skills/thread-audit/SKILL.md` scoped to the map (partial audit
  unless a diagnostic exists; use the legacy current-state if present) → `L path check $SLUG` →
  run `skills/thread-suggest/SKILL.md` → SA decides → `L path commit $SLUG --path custom|predefined --rationale …`.
- Exit: platform-audit + build-path complete; top-level `path` set; approval `demo_path_commit`.

### H6 — Candidate B (import mode) — optional but recommended

Exercises the AE/SDR import path against the same legacy intake artifacts.

- Stage an intake-only package (copy, never move):
  `~/loom-compare/_runs/pkg/` ← legacy `*-discovery.json`, `*-gaps.md`, `*-confirmation.md`,
  `*-opportunity-summary.md`, `*-opportunity-profile.json`, `*-demo-goals.md`, `*-current-state.json`
  (if present) + the raw notes used in H1. Nothing else (no `.env`, state, data, deploy, decks).
- `L new --slug ${SLUG}-imp --display "$DISPLAY" --company … --entry-mode import --import ~/loom-compare/_runs/pkg --solution …`
  → `L listen record ${SLUG}-imp` (expect gap-id backfill warnings) → `L qualify record` → decide.
- Exit: run the harness `--through qualify` for B. Legacy profile/discovery schema failures here are
  findings, not test-process errors.

### H7 — Compare and triage

- Work:
  ```bash
  CMP compare --legacy "$LEGACY" --candidate ~/loom-compare/$SLUG \
      --legacy-manifest ~/loom-compare/_runs/legacy.manifest.json --through path \
      --out ~/loom-compare/_runs/$SLUG-comparison.md
  L hygiene --root ~/loom-compare
  L next $SLUG --no-fs        # resume-from-state check
  ```
  (and `--candidate ~/loom-compare/${SLUG}-imp --through qualify` for B).
- Triage every failed gate and every `changed`/`regressed` row into:
  **P2 bug** (CLI/schema/skill contract defect — repro + proposed fix),
  **intentional change** (listed below), or **LLM variance** (same inputs, different judgment).
- Write `~/loom-compare/_runs/$SLUG-findings.md`: summary, gate table, triage table, P2 bug list
  (file + line + repro), UX-chat notes (contract gaps only), and timings per handoff.
- Exit: harness PASS (or every failure triaged), legacy manifest gate ✅, hygiene clean for the
  candidate, findings written. Report the bug list back; do not fix without SA approval.

## Expected differences (intentional — not regressions)

| Area | Legacy | P2 |
|---|---|---|
| Slug / file prefix | Often company-derived | Public `acme-…` codename; identity only in state |
| Schema conformance | Fails new discovery/audit schemas (no `gap_id`, `claims`, `scope_source`) | Validates |
| Order | Ideation may precede discovery | Intake → qualify decision → ideation → audit → path |
| Qualification | Status only | Recommendation + recorded SA decision (`approvals[]`) |
| Capability map | Markdown table only | `capability-map.json` + rendered table with Origin; D-036 implied row |
| Platform audit scope | Discovery signals | Selected capability map; `remediation_owner` per row |
| Demo path | Implied by which files exist | Top-level `path` + `stages.build-path` |
| State hashes | mtime-based / absent | sha256 content hashes; phase derived |
| `.env` reuse | Manual `cp` | `keys clone` (out of scope here — `keys defer`) |

## Pass criteria

1. All harness gates ✅ for candidate A (`--through path`), including `legacy tree unmodified`.
2. `loom_state hygiene` reports no findings for the candidate engagements.
3. `next --no-fs` reproduces the phase from state alone.
4. Every non-`same` comparison row is triaged; zero untriaged regressions.
5. No cluster calls other than an SA-approved read-only probe.
