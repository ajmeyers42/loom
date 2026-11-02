# P2 handoff — SA-first control plane (Intake → Qualify → Vision freeze)

**Status:** Ready for implementation in a **fresh chat** (2026-10-30) — contracts updated after [`p2-p3-validation.md`](p2-p3-validation.md)  
**UX chat:** Keep the originating UX session for copy/IA/prototype changes only — do not implement P2 there.  
**Direction:** Accepted — see [`loom-ux-blueprint.md`](loom-ux-blueprint.md) (Status: Direction accepted) and [`sa-first-journey-prototype.html`](sa-first-journey-prototype.html).  
**Validation:** [`p2-p3-validation.md`](p2-p3-validation.md) — read blockers A1–A14 before coding.

Paste this file (or `@docs/ux/p2-handoff.md`) at the start of the implementation chat.

---

## 1. Mission

Ship **Full P2**: a vertical product slice that turns the accepted SA-first storyboard into **real engagement filesystem writes** through **vision freeze + demo-path commit**, with durable `{slug}-pipeline-state.json`.

**In scope (SB-01 → SB-07, streamlined):**

| Beat | Outcome |
|------|---------|
| SB-01 Create | Dual identity; folder under public `acme-…` slug (unique under root); initial `pipeline-state`; entry mode |
| SB-02 Keystore | Isolated `{slug}/.env` (deferrable); manual / sample / clone-from-sibling; keystore status ≠ cloud-provision |
| SB-03 Evidence | Persist notes under `inputs/`; run/wrap `warp-listen` (optional `warp-scan`); editable claims with `source_ref` |
| SB-04 Qualify | MEDDPIC + gaps; dual gap-closure; **Record decision** → `qualification_status` + `approvals[]` |
| SB-05 Vision | Single screen: draft + capability map + SA feature adds + freeze + confirmation approve |
| SB-07 Demo path | Audit **selected** map; predefined vs custom; write `path` into state |

**Out of scope (defer to P3+):** SB-08 Build progress UI, SB-09 readiness lanes, SB-09b cluster target, SB-10 deploy approval UI, SB-11 launch surfaces, SB-12 retire wizard, live cluster mutation, D-024 apply.

**Parity targets:** outputs of `warp-scout` (through `demo-goals.md`) + `warp-spark` (frozen `ideation.md` + confirmation refresh) + orchestrator `pipeline-state` contract.

---

## 2. Non-negotiables (from accepted UX)

1. **Dual identity** — Private: company, opportunity name, optional SFDC ID — stored in **pipeline-state / engagement metadata only** (not cloned via `.env`). Public: `DEMO_SLUG=acme-{industry|usecase}`, Acme display name for folder, tags, space path, seed/assets. Customer name must never land on shared demo assets.
2. **Engagements outside git** — `$LOOM_ENGAGEMENTS_ROOT/{public-slug}/` (default `$HOME/engagements`). Never write customer artifacts into the loom repo.
3. **One keystore per slug** — `{engagement_dir}/.env`; clone **copies** values; never share a live `.env` path; preserve this slug’s `DEMO_SLUG` / `KIBANA_SPACE_PATH` on clone; force distinct `INDEX_PREFIX` when ES URL matches a sibling; never clone private identity vars.
4. **Gap closure** — Path A (edit `inputs/` notes → re-listen) is first-class; Path B optional `gap-responses.json`. Qualify completes only on explicit **Record decision**.
5. **Amber = pipeline-owned by default** — agents/tools/workflows/data are Build work, not “restart discovery.”
6. **D-050** — Vision freeze includes capability map + out of scope in `demo/{slug}-ideation.md`; then SA **approves refreshed confirmation** before any platform-audit / build.
7. **No live deploy in P2** — `terraform plan` / `bootstrap-data.py --dry-run` only if needed for scaffolding; never `bolt-spin` apply / live bootstrap without D-024 (out of P2).
8. **Research order** — repo `skills/` + `docs/` → hive-mind → `org:elastic`; ask before non-Elastic web sources (`AGENTS.md`).
9. **Slug is never re-derived from company name** — `pipeline-state.slug` (and folder name) is the only source; skills must not overwrite from `ENGAGEMENT` / customer string (validation A1).

### Per-artifact identity table

| Artifact class | Name to use |
|----------------|-------------|
| Opportunity docs, `confirmation.md` (customer-facing) | **Real** company / opportunity |
| Control-plane chrome (Overview title) | Real company · public slug subtitle |
| `ideation.md` header, demo scripts, Kibana space, indices, `loom:` tags, bootstrap headers, seed data | **Public** Acme display / `DEMO_SLUG` only |

---

## 3. Artifact contract (must write)

Root: `${LOOM_ENGAGEMENTS_ROOT:-$HOME/engagements}/{DEMO_SLUG}/`

| Path | Writer / stage | Notes |
|------|----------------|-------|
| `{slug}-pipeline-state.json` | Every beat | Schema below; extend additively |
| `.env` / `.env.example` | SB-02 | `skills/references/env-reference.md`; **no** private company/opportunity vars |
| `inputs/` | SB-01 / SB-03 | Raw notes, AE emails, diagnostics uploads (Path A source of truth) |
| `demo/{slug}-discovery.json` | SB-03 / `warp-listen` | Claims include `source_ref`; gaps have stable `gap_id` |
| `opportunity/{slug}-gaps.md` | SB-03 | |
| `opportunity/{slug}-confirmation.md` | SB-03; refresh SB-05; approve after freeze | Customer-safe |
| `opportunity/{slug}-opportunity-summary.md` | SB-04 / `thread-qualify`; TL;DR refresh on vision freeze | MEDDPIC |
| `opportunity/{slug}-opportunity-profile.json` | SB-04 | Validate vs `schemas/opportunity-profile.schema.json` (+ `qualification_decision`, `accepted_risk`) |
| `opportunity/{slug}-demo-goals.md` | SB-04 | Scout parity |
| `opportunity/{slug}-gap-responses.json` | SB-04 optional | Proposed accelerator; keyed by `gap_id` |
| `demo/{slug}-ideation.md` | SB-05 / `warp-spark` | Capability map + Out of Scope + archetype / wow / data / min bar required |
| `demo/{slug}-platform-audit.json` + `.md` | SB-07 / `thread-audit` | Audits **selected** capability map; `remediation_owner` |
| `opportunity/{slug}-predefined-recommendation.md` | SB-07 if predefined | `thread-suggest` output |
| `demo/{slug}-current-state.json` etc. | SB-03 if diagnostics | Optional `warp-scan` |

**Pipeline-state extensions for P2** (additive; do not break existing stage keys):

```json
{
  "slug": "acme-pharma",
  "engagement_dir": "…/acme-pharma",
  "identity": {
    "company_name": "Northwind Pharmaceuticals",
    "opportunity_name": "NW Pharma — SOC AI FY26",
    "opportunity_id": "006…",
    "public_display_name": "Acme Pharma"
  },
  "entry_mode": "import|notes|scratch",
  "path": "custom|predefined|unset",
  "keystore": {
    "status": "empty|partial|complete|validated",
    "validated_at": null,
    "elastic_version": null
  },
  "approvals": [],
  "stages": {
    "discovery-parser": {},
    "diagnostic-analyzer": {},
    "opportunity-review": {},
    "ideation": {},
    "platform-audit": {},
    "build-path": {}
  }
}
```

**Rules:**

- **Do not store `ux.phase` as source of truth** — derive phase / “what’s next” from `stages`, `path`, `approvals`, and `keystore.status` (validation D6).
- **`approvals[]`** uses blueprint §9.5 shape: `{ "action", "approver", "timestamp", "artifacts", "rationale?" }` for at least `qualification_decision`, `vision_freeze`, `confirmation_approve`, `demo_path_commit` (later: spend, deploy_apply).
- **`stages.build-path`** records predefined vs custom commit; top-level `path` is the single field consumers read.
- Prefer **content sha256** for `input_hash` (not mtime prefix) when implementing the state library (D8).

Map UX beats → existing stage keys where possible:

| UX | `stages.*` key |
|----|----------------|
| Evidence / listen | `discovery-parser` |
| Scan | `diagnostic-analyzer` |
| Qualify decision | `opportunity-review` |
| Vision freeze + confirmation approve | `ideation` |
| Demo path (audit + suggest) | `platform-audit` + `build-path` |

---

## 4. Suggested delivery shape (implementer chooses stack)

Open design Q1 in the blueprint is unresolved. For Full P2, prefer the **smallest durable slice**:

| Preference order | Why |
|------------------|-----|
| **1. Library + CLI** under `scripts/` (extend `inventory.py` → `loom_state`) that create/update the files above, callable from Cursor agents | Matches SA-first “agent runs commands”; no premature UI framework |
| **2. Thin local control-plane** (optional) only if (1) is solid — read/write same contracts | Prototype HTML is **not** the product |
| **3. Do not** treat `docs/ux/sa-first-journey-prototype.html` as runtime | Keep it as UX reference; change it only in the UX chat |

Recommended CLI surface: `new`, `keys`, `listen`, `qualify decide`, `vision freeze`, `path`, `next`.

Recommended work packages:

1. **Engagement bootstrap API** — create dir + `inputs/`, dual-identity metadata in state, uniqueness check / suffix, initial state, `.env.example` → optional `.env` stub.
2. **Keystore API** — list sibling keystores (status only), clone with slug/space/`INDEX_PREFIX` rules, never log secrets; separate `keystore.status` from `cloud-provision`.
3. **Intake runners** — invoke or wrap `warp-listen` / optional `warp-scan`; evidence review hooks; `source_ref` / `gap_id`.
4. **Qualify runners** — wrap `thread-qualify`; gap Path A/B; Record decision → profile + `approvals[]`.
5. **Vision runners** — wrap `warp-spark` Plan Contract; capability map edit model; freeze + confirmation refresh + approve; summary TL;DR refresh.
6. **Demo-path commit** — audit selected map (`thread-audit` consumes ideation map); `thread-suggest`; write `path: predefined|custom`; if predefined, stop custom weave (catalog handoff stub OK).
7. **Acceptance fixtures** — synthetic Acme engagement under a **temp** engagements root (no real customer data in repo).
8. **Skill / schema alignment (from validation)** — A1 slug source; A7 discovery + gap-responses schemas; A8 profile `accepted_risk` + `qualification_decision`; A9 audit reads capability map + `remediation_owner`; A10 `build-path` stage; A14 orchestrator dependency order (listen → qualify → spark).

---

## 5. Skills and docs to load first (implementation chat)

Read in this order:

1. This handoff  
2. [`p2-p3-validation.md`](p2-p3-validation.md) — blockers  
3. [`loom-ux-blueprint.md`](loom-ux-blueprint.md) — §§5–8 (journey, IA, SB-01–07, interaction rules 4b/10/11), §11 roadmap  
4. [`skills/loom/SKILL.md`](../../skills/loom/SKILL.md) — inventory, pipeline-state, gates  
5. [`skills/warp-scout/SKILL.md`](../../skills/warp-scout/SKILL.md) · [`warp-listen`](../../skills/warp-listen/SKILL.md) · [`thread-qualify`](../../skills/thread-qualify/SKILL.md) · [`warp-spark`](../../skills/warp-spark/SKILL.md) · [`thread-audit`](../../skills/thread-audit/SKILL.md) · [`thread-suggest`](../../skills/thread-suggest/SKILL.md)  
6. [`skills/references/env-reference.md`](../../skills/references/env-reference.md) · [`docs/engagements-path.md`](../engagements-path.md) · [`AGENTS.md`](../../AGENTS.md)  
7. [`schemas/opportunity-profile.schema.json`](../../schemas/opportunity-profile.schema.json)  
8. Optional: hive-mind `DEMO_ARCHETYPES.md` via `hive-sa-coaching` (D-050)

Prototype for interaction intent: open `sa-first-journey-prototype.html` in a browser (file://).

---

## 6. Acceptance criteria (Full P2 exit)

An implementer / SA using the P2 surface (CLI or agent-driven) can:

1. **Create** an engagement with private company/opp + public `acme-…` slug; folder exists only under engagements root; **slug unique** under root (suffix if needed); normalized tag id documented (`loom:acmepharma` not `loom:acme-pharma`).  
2. **Save keystore** via manual, sample, or clone (or **defer**); sibling picklist shows status not secrets; this slug’s space path preserved; **distinct `INDEX_PREFIX`** when cloning onto a shared ES URL; private identity **not** copied.  
3. **Ingest notes** from `inputs/` → discovery JSON + gaps + confirmation; claims/gaps reviewable with source refs / gap ids.  
4. **Close a gap** via Inputs edit + re-listen **or** optional gap-response + refresh.  
5. **Record** `proceed` | `continue_discovery` | `not_qualified` into profile + `approvals[]`; profile validates; `opportunity-review` marked complete only after decision; continue_discovery does **not** unlock Vision without explicit override.  
6. **Freeze vision** with capability map including ≥1 SA-added feature, Out of Scope, archetype / wow / data / min bar; `demo/{slug}-ideation.md` present; confirmation refreshed and **approved**; opportunity-summary TL;DR refreshed; Agent Builder add implies token-visibility (D-036) unless opted out.  
7. **Commit demo path** predefined or custom after auditing **selected** map; state reflects `path`; predefined does not unlock weave; audit artifacts present.  
8. **Resume** from `{slug}-pipeline-state.json` alone for “what’s next?” (derived phase / Overview).  
9. **Hygiene** — no `.env` or real customer PII committed to loom git; eval/fixtures stay synthetic.

Usability stretch (nice-to-have in P2, required by P4): SA completes 1–6 without reading skill docs (blueprint §10.4 items 1–3).

---

## 7. Explicit non-goals / traps

- Do not implement Build weave chain, finish-check/verify UI, or deploy approval in P2.  
- Do not put real company names in Kibana space IDs, index names, or `loom:` tags.  
- Do not treat amber Agent Builder as a discovery restart.  
- Do not require gap-responses.json (optional only).  
- Do not expand `docs/pipeline.md` as source of truth — orchestrator SKILL wins.  
- Do not push to origin unless the SA asks.  
- Do not treat keystore stub `.env` as `cloud-provision` complete.  
- Do not store private identity fields in `.env` for clone convenience.

---

## 8. Suggested first prompt for the fresh chat

```text
Implement Full P2 per docs/ux/p2-handoff.md and docs/ux/p2-p3-validation.md.
UX direction is frozen in docs/ux/loom-ux-blueprint.md + sa-first-journey-prototype.html.
Keep UX copy/prototype edits out of this chat unless a contract gap blocks implementation — then note the gap for the UX chat.
Start with engagement bootstrap + pipeline-state + keystore APIs (loom_state CLI), then wire listen → qualify → spark freeze → demo-path commit.
Include skill/schema work packages A1, A7–A10, A14 from the validation report.
Use a temp LOOM_ENGAGEMENTS_ROOT for fixtures. Do not deploy to a live cluster.
```

---

## 9. Chat split

| Chat | Owns |
|------|------|
| **UX (this lineage)** | Blueprint, prototype HTML, copy, IA, storyboard corrections, validation report |
| **P2 implementation (fresh)** | Scripts/APIs/skills wiring, schemas, fixtures, acceptance runs |

If implementation discovers a product-rule ambiguity, add a one-line open question under blueprint §13 (or file an issue) and continue with the safest interpretation from §§7–8 of the blueprint and [`p2-p3-validation.md`](p2-p3-validation.md).
