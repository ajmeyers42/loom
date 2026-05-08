---
name: finish-check
description: >
  Reads all available loom pipeline outputs for a given engagement and produces a
  pre-demo checklist, a known-risks summary, and a go/no-go recommendation. Designed to
  be run the day before the demo — catches gaps before the audience does.

  ALWAYS use this skill when the user asks "are we ready for the demo", "what do I need
  to check before tomorrow", "pre-demo checklist", "is everything set up", or has completed
  demo build work and wants a final readiness review. Also trigger when the user explicitly
  says they're running the skill before a scheduled demo. This is the last planning /
  readiness stage before provision or deploy — run it after weave-model and
  weave-train outputs exist.
---

# Demo Validator

You are doing a pre-demo readiness check. Your job is to produce a checklist that an SE
can work through in the two hours before the demo starts, in the right order, with specific
commands to run and specific things to look for.

A good checklist has no ambiguous items. "Check that Kibana is working" is useless.
"Open the ML swimlane, confirm red cells on store_id=1842, anomaly_score ≥ 75" is a
checklist item.

## Step 1: Read All Available Pipeline Outputs

Collect everything available for this engagement:
- `demo/{slug}-discovery.json` — who's in the room, what we're trying to prove
- `demo/{slug}-platform-audit.json` — what features are ready vs. need setup
- `demo/{slug}-demo-script.md` — the exact scenes and queries to verify
- `data/{slug}-data-model.json` — what indices and pipelines must exist
- `data/{slug}-ml-config.json` — what ML jobs must be trained and anomalies must be visible
- `demo/{slug}-current-state.json` — if existing customer, their cluster state

Note which files are missing — a missing data model or ML config means those items can't
be verified automatically and must be marked as manual checks.

## Step 1b: Mechanical Decision Compliance Check

Before building the readiness checklist, run this binary compliance check against
the pipeline outputs for this engagement. These are **pass/fail** — not judgment calls.
A FAIL on any item is a **no-go blocker** regardless of other readiness status.

| # | Decision | How to check | Pass condition | Fail action |
|---|---|---|---|---|
| C-1 | **D-033: Version gate** | Read `demo/{slug}-platform-audit.json` → `platform.version_verified` AND `asset-bundle/asset-schema.json` → `platform.version_gate_passed` | Both `true`; version ≥ 9.4 | NO-GO — version unverified or below 9.4 |
| C-2 | **D-043: Schema probe ran** | Check `deploy/asset-bundle/asset-schema.json` exists and has `confirmed_schemas` entries | File exists, at least one schema entry for every index in data model | NO-GO — re-run finish-verify |
| C-3 | **D-044: Field population** | Check `deploy/asset-bundle/asset-index.json` for any `"all_non_null_confirmed": false` | No false entries | NO-GO — fix null fields and re-run finish-verify |
| C-4 | **D-025: ES|QL validation** | Check `deploy/asset-bundle/asset-index.json` for any `"validation_status": "failed"` queries | No failed queries | NO-GO — fix queries and re-run finish-verify |
| C-5 | **D-045: Asset bundle exists** | Check `deploy/asset-bundle/asset-index.json` exists | File present | NO-GO — run finish-verify |
| C-6 | **D-046: Infrastructure in Terraform** | Check `deploy/main.tf` or `deploy/main-serverless.tf` exists if deployment was generated | File present OR deployment not yet generated (allowed) | NO-GO if deployment generated but only `bootstrap.py` exists — must re-run bolt-bootstrap |
| C-7 | **D-026: Engagement tags** | Search `deploy/main.tf` and `deploy/bootstrap-data.py` for `demobuilder:` tag string | Present in at least one resource in `main.tf` AND in `loom_tags()` function in `bootstrap-data.py` | WARN — re-run bolt-bootstrap |
| C-8 | **D-032: Managed assets checked** | Check `deploy/asset-bundle/asset-index.json` for any entry with `source: "package"` | At least one package-sourced entry if Fleet packages are installed for the demo domain (Obs/Sec) | WARN — finish-verify may have skipped package probe |
| C-9 | **D-022: Solution-first narrative** | Read `demo/{slug}-demo-script.md` — does Scene 1 or the intro lead with business outcome before feature capabilities? | Yes, or demo is developer/technical audience where capability-first is appropriate | DELIVERY RISK for exec/mixed audiences |
| C-10 | **D-015: T-10min cleanup** | Check `deploy/{slug}-demo-checklist.md` for `_delete_by_query` cleanup step | Present in "10 Minutes Before" section | WARN — add manually to checklist |

**Output a compliance table before the readiness checklist:**

```
── Decision Compliance Check ──────────────────────────────────────────
  C-1  D-033 Version gate          ✅ PASS  (9.4.2, verified)
  C-2  D-043 Schema probe          ✅ PASS  (5 schemas confirmed)
  C-3  D-044 Field population      ✅ PASS  (no null viz-queried fields)
  C-4  D-025 ES|QL validation      ✅ PASS  (12/12 queries passed)
  C-5  D-045 Asset bundle          ✅ PASS  (asset-index.json present)
  C-6  D-046 Terraform infra       ✅ PASS  (main.tf present)
  C-7  D-026 Engagement tags       ✅ PASS
  C-8  D-032 Managed assets        ⚠  WARN  (no package entries — verify if Obs/Sec in scope)
  C-9  D-022 Solution-first        ✅ PASS
  C-10 D-015 T-10min cleanup       ✅ PASS

  Overall compliance: PASS (1 warning — see C-8)
──────────────────────────────────────────────────────────────────────
```

If any C-1 through C-6 is FAIL: set overall go/no-go to **NO-GO** immediately.
Warnings (C-7 through C-10) contribute to risk register, not no-go.

## Step 2: Build the Verification Matrix

For each component in the demo, define what "ready" looks like:

### Data layer checks
For each index/data stream in the data model:
- Does it exist? (`GET /{index}/_count`)
- Does it have the expected document count? (compare to seed data spec)
- Are demo-critical documents present? (check specific IDs or field values from the
  injection spec)
- Is the ingest pipeline attached and processing? (check pipeline stats)
- **Field population check (D-044):** For every field referenced in a visualization query (`WHERE`, `STATS`, `BY`, `SUM`, `AVG`, etc.), verify non-null across all documents: `POST /{index}/_count {"query": {"exists": {"field": "{field}"}}}` must equal total doc count. A null viz-queried field produces `Unknown column` errors in ES|QL and causes neighboring dashboard panels to render as broken even when their own data is valid. Flag as **no-go blocker** if any viz-queried field has nulls.

### ML checks (if ML scene in script)
- Is the job open and the datafeed started?
- Is the swimlane populated? (non-zero bucket results)
- Are anomalies visible on the target entities? (anomaly score ≥ 75 on the right store/IP/entity)
- Is the `typical` value clearly lower than `actual` (visual contrast in the swimlane)?
- Does the ES|QL cross-join query (if scripted) return the same entities as the ML anomalies?

### ELSER / semantic checks (if semantic scene in script)
- Is the inference endpoint deployed and responding? (`GET /_inference/sparse_embedding/{id}`)
- Is the response time sub-2 seconds? (first query after cold start will be slow — this
  must be run at least once before the audience arrives)
- Does a test semantic query return expected results? (run the demo query from the script,
  verify top result is correct)

### Agent / Workflow checks (if agent scene in script)
- Is the agent config saved in Agent Builder?
- Do all tool definitions resolve (no missing index, no missing workflow ID)?
- Has each scenario been run end-to-end in the test panel?
- Do Workflow executions complete and write expected documents?
- Is session persistence working? (follow-up message correctly references prior context)

### Dashboard / Kibana checks
- Is the dashboard saved and loading without errors?
- Does the geo heatmap render on first load? (tile rendering can be slow — click it once
  before the meeting to warm the tile cache)
- Do drill-down filters work? (click a data point and verify the dashboard updates)
- Are all relevant time ranges set correctly for the demo data?

### Connectivity and environment checks
- Is the live data simulator running (if applicable)? (check event count incrementing in Discover)
- Are browser tabs pre-opened and pre-loaded?
- Is the screen layout configured for the demo (correct window size, dark mode, etc.)?
- Is screen sharing tested and working?
- Are screenshot fallbacks ready for every major screen?

### Version alignment check (D-025)
- Does `demo/{slug}-platform-audit.json` have a **verified** `platform.version`? If `version_verified`
  is `false` or the field is absent, flag as a **no-go blocker** — artifact deployability cannot
  be confirmed without a resolved stack version.
- For each field type in `data/{slug}-data-model.json` mappings, confirm it is valid for the resolved
  stack version (`keyword`, `text`, `date`, `semantic_text`, etc. — not abstract or invented
  types). See `docs/decisions.md` **D-025**.
- For each API payload in the data model or bootstrap template, confirm the parameter shapes
  and required fields match the resolved version's API (use `skills/bolt-launch/references/`
  and `docs/references-observability-slo.md` as the version-scoped reference).
- If the data model was generated **without** a verified version in Step 0 of `weave-model`,
  mark the data layer as **conditional go** until a live `GET /` confirms the version matches.

### Script narrative checks (when `{slug}-demo-script.md` exists)
- Does the script **lead with outcomes** (business value, customer **key asks** from discovery)
  **before** deep capability or infrastructure scenes — **solution first** (see `docs/decisions.md`
  D-022)? If it opens capability-first without a clear outcome hook, flag as a **delivery risk**
  for exec or mixed audiences unless the SA intended that ordering.

## Step 3: Assess Overall Readiness

**Go:** All critical checks pass. Setup-required items from the platform audit are complete.
ML anomalies visible. ELSER warm. Agent scenarios tested end-to-end.

**Conditional go:** One or two amber items that have documented fallbacks. The demo can
proceed with minor adjustments — the SE knows what to say if a scene doesn't render.

**No-go:** Any of the following:
- A demo-critical document is missing and the scenario cannot run without it
- ML swimlane shows no anomalies on the target entity and there is no fallback
- ELSER endpoint is not responding and the semantic scene has no fallback
- Agent scenarios have not been tested end-to-end
- The environment is unreachable (connectivity issue)
- Any viz-queried field is null in any document in a custom index (D-044) — one broken panel can render adjacent panels as broken regardless of their own data state

## Step 4: Write the Outputs

### Output 1: `deploy/{slug}-demo-checklist.md`

The working document the SE takes into demo prep. Organized by timing.

```
# Pre-Demo Checklist — [Company] | [Date]
**Go / No-Go Status:** 🟢 Go | 🟡 Conditional Go | 🔴 No-Go

---

## Day Before (complete by end of day)

- [ ] **Data layer verified** — all indices exist with expected doc counts
  - `GET /fraud-claims/_count` → expect ~500 docs
  - `GET /fraud-escalations/_count` → expect 0 (empty until agent runs)
- [ ] **Demo-critical documents confirmed** — SKU 174239, store 1842: `GET /inventory-positions/_doc/1842_174239`
- [ ] **ML anomaly injection run** — `python3 scripts/inject-anomaly.py --store 1842 --skus 174239,182041,196723`
- [ ] **ML swimlane verified** — open Kibana ML, confirm anomaly_score ≥ 75 on store 1842
- [ ] **ELSER endpoint warm** — `python3 scripts/warm-elser.py` — confirm sub-2s response

---

## Morning of Demo (2 hours before)

- [ ] **Data simulator running** — `python3 scripts/live-data-simulator.py --inject-shrink`
  Verify: Kibana Discover → store-transactions-* → event count incrementing
- [ ] **ML swimlane still showing anomalies** — red cells on store 1842, fasteners group
- [ ] **All 3 agent scenarios tested** — run each in Agent Builder Test panel:
  - Scenario A (item in stock): response includes aisle/bay location ✓
  - Scenario B (zero stock, nearby store found): transfer request document created ✓
  - Scenario C (zero stock, no nearby stores): email notification triggered ✓
- [ ] **Dashboard drill-down warm** — click the geo heatmap once, verify it renders in < 3s
- [ ] **All queries in Dev Tools console history** — paste from script before audience arrives

---

## 30 Minutes Before

- [ ] **Tabs open and positioned:** (1) Kibana Discover, (2) Dev Tools, (3) ML Explorer,
      (4) Agent Builder, (5) Workflows execution history, (6) Supply Chain Dashboard
- [ ] **ELSER re-warmed** — run one semantic query in Playground, confirm fast response
- [ ] **Screenshot fallbacks accessible** — local folder or second device, not buried in Finder
- [ ] **Screen share tested** — confirmed sharing the correct window/display

## 10 Minutes Before

- [ ] **Clear test agent sessions** — testing populates session history; clean it before going live:
  ```
  POST /{slug}-sessions/_delete_by_query
  { "query": { "range": { "@timestamp": { "lt": "now-10m" } } } }
  ```
  Verify: `GET /{slug}-sessions/_count` → only pre-seeded sessions remain (typically 2–3)

---

## Known Risks and Fallbacks

| Risk | Likelihood | Fallback |
|---|---|---|
[One row per risk identified during validation]

---

## Go / No-Go Decision

**Go criteria (all must be true):**
[List the specific pass criteria for this demo]

**Current status:** [GO / CONDITIONAL GO / NO-GO]
**Decision owner:** [SA name]
**If no-go:** [specific action — reschedule, swap to recorded demo, etc.]
```

### Output 2: `deploy/{slug}-risks.md`

Internal risk register — one line per risk with mitigation. Useful for post-demo retro.

```
# Demo Risks — [Company] | [Date]

## Open Risks at Validation Time
[Each risk: description, likelihood (H/M/L), impact (H/M/L), mitigation/fallback]

## Resolved Since Platform Audit
[Items that were amber in the platform audit and are now confirmed green]

## Remaining Setup Items
[Anything that was NOT completed before this validation run — with owner and deadline]
```

## What Good Looks Like

**Clean go:** All indices populated, ML anomaly score 88 on store 1842, ELSER responding
in 1.2s, all three agent scenarios tested with correct tool traces. Zero open risks.
Checklist is a formality — everything is ready.

**Conditional go with one risk:** The geo heatmap times out on first tile load (known Kibana
tile server latency issue). Mitigation: click the map tile 5 minutes before the meeting
and leave the dashboard open. Document the risk, mark conditional go.

**No-go caught by validator:** ML datafeed stopped overnight due to a mapping conflict on
a new field added to the data stream. Swimlane shows no new buckets. Action: fix mapping
conflict, restart datafeed, rerun injection, revalidate. Reschedule demo if < 2h before.

**Missing pipeline output:** Demo-data-modeler was never run. Checklist notes that data
layer cannot be verified automatically and lists manual checks. Recommend completing the
data model before the next validation run.
