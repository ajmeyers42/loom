# P2 handoff — SA-first control plane (Intake → Qualify → Vision freeze)

**Status:** Ready for implementation in a **fresh chat** (2026-10-30)  
**UX chat:** Keep the originating UX session for copy/IA/prototype changes only — do not implement P2 there.  
**Direction:** Accepted — see [`loom-ux-blueprint.md`](loom-ux-blueprint.md) (Status: Direction accepted) and [`sa-first-journey-prototype.html`](sa-first-journey-prototype.html).

Paste this file (or `@docs/ux/p2-handoff.md`) at the start of the implementation chat.

---

## 1. Mission

Ship **Full P2**: a vertical product slice that turns the accepted SA-first storyboard into **real engagement filesystem writes** through **vision freeze + build-path commit**, with durable `{slug}-pipeline-state.json`.

**In scope (SB-01 → SB-07):**

| Beat | Outcome |
|------|---------|
| SB-01 Create | Dual identity; folder under public `acme-…` slug; initial `pipeline-state` |
| SB-02 Keystore | Isolated `{slug}/.env`; manual / sample / clone-from-sibling |
| SB-03 Evidence | Persist notes; run/wrap `warp-listen` (optional `warp-scan`); editable claims |
| SB-04 Qualify | MEDDPIC + gaps; dual gap-closure; **Record decision** → `qualification_status` |
| SB-05–06 Vision | Draft → capability map + SA feature adds → freeze into ideation |
| SB-07 Path | Audit **selected** map; predefined vs custom; write path into state |

**Out of scope (defer to P3+):** SB-08 Build progress UI, SB-09 readiness lanes, SB-10 deploy approval UI, SB-11 launch surfaces, SB-12 retire wizard, live cluster mutation, D-024 apply.

**Parity targets:** outputs of `warp-scout` (through `demo-goals.md`) + `warp-spark` (frozen `ideation.md` + confirmation refresh) + orchestrator `pipeline-state` contract.

---

## 2. Non-negotiables (from accepted UX)

1. **Dual identity** — Private: company, opportunity name, optional SFDC ID (control plane / opportunity docs only). Public: `DEMO_SLUG=acme-{industry|usecase}`, Acme display name for folder, tags, space path, seed/assets. Customer name must never land on shared demo assets.
2. **Engagements outside git** — `$LOOM_ENGAGEMENTS_ROOT/{public-slug}/` (default `$HOME/engagements`). Never write customer artifacts into the loom repo.
3. **One keystore per slug** — `{engagement_dir}/.env`; clone **copies** values; never share a live `.env` path; preserve this slug’s `DEMO_SLUG` / `KIBANA_SPACE_PATH` on clone.
4. **Gap closure** — Path A (edit Inputs / notes → re-listen) is first-class; Path B optional `gap-responses.json`. Qualify completes only on explicit **Record decision**.
5. **Amber = pipeline-owned by default** — agents/tools/workflows/data are Build work, not “restart discovery.”
6. **D-050** — Vision freeze includes capability map + out of scope in `demo/{slug}-ideation.md` before any platform-audit / build.
7. **No live deploy in P2** — `terraform plan` / `bootstrap-data.py --dry-run` only if needed for scaffolding; never `bolt-spin` apply / live bootstrap without D-024 (out of P2).
8. **Research order** — repo `skills/` + `docs/` → hive-mind → `org:elastic`; ask before non-Elastic web sources (`AGENTS.md`).

---

## 3. Artifact contract (must write)

Root: `${LOOM_ENGAGEMENTS_ROOT:-$HOME/engagements}/{DEMO_SLUG}/`

| Path | Writer / stage | Notes |
|------|----------------|-------|
| `{slug}-pipeline-state.json` | Every beat | Schema in `skills/loom/SKILL.md` Step 2; extend with UX fields below |
| `.env` / `.env.example` | SB-02 | `skills/references/env-reference.md`; include private identity vars |
| `demo/{slug}-discovery.json` | SB-03 / `warp-listen` | |
| `opportunity/{slug}-gaps.md` | SB-03 | |
| `opportunity/{slug}-confirmation.md` | SB-03; refresh SB-06 | Customer-safe |
| `opportunity/{slug}-opportunity-summary.md` | SB-04 / `thread-qualify` | MEDDPIC |
| `opportunity/{slug}-opportunity-profile.json` | SB-04 | Validate vs `schemas/opportunity-profile.schema.json` |
| `opportunity/{slug}-demo-goals.md` | SB-04 | Scout parity |
| `opportunity/{slug}-gap-responses.json` | SB-04 optional | Proposed accelerator |
| `demo/{slug}-ideation.md` | SB-05–06 / `warp-spark` | Capability map + Out of Scope required |
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
  "path": "custom|predefined|unset",
  "ux": {
    "phase": "intake|qualify|design",
    "qualification_decision_at": null,
    "vision_frozen_at": null,
    "capability_map_frozen": false
  },
  "stages": { }
}
```

Map UX beats → existing stage keys where possible:

| UX | `stages.*` key |
|----|----------------|
| Evidence / listen | `discovery-parser` |
| Scan | `diagnostic-analyzer` |
| Qualify decision | `opportunity-review` |
| Vision freeze | `ideation` |

---

## 4. Suggested delivery shape (implementer chooses stack)

Open design Q1 in the blueprint is unresolved. For Full P2, prefer the **smallest durable slice**:

| Preference order | Why |
|------------------|-----|
| **1. Library + CLI** under `scripts/` or `skills/` helpers that create/update the files above, callable from Cursor agents | Matches SA-first “agent runs commands”; no premature UI framework |
| **2. Thin local control-plane** (optional) only if (1) is solid — read/write same contracts | Prototype HTML is **not** the product |
| **3. Do not** treat `docs/ux/sa-first-journey-prototype.html` as runtime | Keep it as UX reference; change it only in the UX chat |

Recommended work packages:

1. **Engagement bootstrap API** — create dir, dual-identity metadata, initial state, `.env.example` → `.env` stub.
2. **Keystore API** — list sibling keystores (status only), clone with slug/space preservation, never log secrets.
3. **Intake runners** — invoke or wrap `warp-listen` / optional `warp-scan`; evidence review hooks.
4. **Qualify runners** — wrap `thread-qualify`; gap Path A/B; Record decision → profile + state.
5. **Vision runners** — wrap `warp-spark` Plan Contract; capability map edit model; freeze + confirmation refresh.
6. **Path commit** — write `path: predefined|custom`; if predefined, stop custom weave (catalog handoff stub OK).
7. **Acceptance fixtures** — synthetic Acme engagement under a **temp** engagements root (no real customer data in repo).

---

## 5. Skills and docs to load first (implementation chat)

Read in this order:

1. This handoff  
2. [`loom-ux-blueprint.md`](loom-ux-blueprint.md) — §§5–8 (journey, IA, SB-01–07, interaction rules 4b/10/11), §11 roadmap  
3. [`skills/loom/SKILL.md`](../../skills/loom/SKILL.md) — inventory, pipeline-state, gates  
4. [`skills/warp-scout/SKILL.md`](../../skills/warp-scout/SKILL.md) · [`warp-listen`](../../skills/warp-listen/SKILL.md) · [`thread-qualify`](../../skills/thread-qualify/SKILL.md) · [`warp-spark`](../../skills/warp-spark/SKILL.md)  
5. [`skills/references/env-reference.md`](../../skills/references/env-reference.md) · [`docs/engagements-path.md`](../engagements-path.md) · [`AGENTS.md`](../../AGENTS.md)  
6. [`schemas/opportunity-profile.schema.json`](../../schemas/opportunity-profile.schema.json)  
7. Optional: hive-mind `DEMO_ARCHETYPES.md` via `hive-sa-coaching` (D-050)

Prototype for interaction intent: open `sa-first-journey-prototype.html` in a browser (file://).

---

## 6. Acceptance criteria (Full P2 exit)

An implementer / SA using the P2 surface (CLI or agent-driven) can:

1. **Create** an engagement with private company/opp + public `acme-…` slug; folder exists only under engagements root.  
2. **Save keystore** via manual, sample, or clone; sibling picklist shows status not secrets; this slug’s space path preserved.  
3. **Ingest notes** → discovery JSON + gaps + confirmation; claims/gaps reviewable.  
4. **Close a gap** via Inputs edit + re-listen **or** optional gap-response + refresh.  
5. **Record** `proceed` | `continue_discovery` | `not_qualified`; profile validates; `opportunity-review` marked complete only after decision.  
6. **Freeze vision** with capability map including ≥1 SA-added feature and Out of Scope; `demo/{slug}-ideation.md` present; confirmation refreshed (customer-safe).  
7. **Commit path** predefined or custom; state reflects `path`; predefined does not unlock weave.  
8. **Resume** from `{slug}-pipeline-state.json` alone for “what’s next?”  
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

---

## 8. Suggested first prompt for the fresh chat

```text
Implement Full P2 per docs/ux/p2-handoff.md.
UX direction is frozen in docs/ux/loom-ux-blueprint.md + sa-first-journey-prototype.html.
Keep UX copy/prototype edits out of this chat unless a contract gap blocks implementation — then note the gap for the UX chat.
Start with engagement bootstrap + pipeline-state + keystore APIs, then wire listen → qualify → spark freeze → path commit.
Use a temp LOOM_ENGAGEMENTS_ROOT for fixtures. Do not deploy to a live cluster.
```

---

## 9. Chat split

| Chat | Owns |
|------|------|
| **UX (this lineage)** | Blueprint, prototype HTML, copy, IA, storyboard corrections |
| **P2 implementation (fresh)** | Scripts/APIs/skills wiring, schemas, fixtures, acceptance runs |

If implementation discovers a product-rule ambiguity, add a one-line open question under blueprint §13 (or file an issue) and continue with the safest interpretation from §§7–8 of the blueprint.
