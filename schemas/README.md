# JSON Schemas

This directory contains versioned contracts for machine-readable loom outputs. Skills still explain how to reason about each artifact, but schemas define the stable fields downstream stages may rely on.

These schemas are intentionally lightweight at first. They validate shape and core enums without trying to encode every engagement-specific field.

| Schema | Produced by | Consumed by |
|---|---|---|
| `pipeline-state.schema.json` | `loom_state` (intake → demo path), orchestrator (later stages) | orchestrator, `loom_state next`, `scripts/inventory.py` |
| `discovery.schema.json` | `warp-listen` (registered by `loom_state listen record`) | `thread-qualify`, `thread-audit`, `weave-script` |
| `gap-responses.schema.json` | `loom_state gaps respond` (Path B) | `thread-qualify`, `loom_state qualify` |
| `opportunity-profile.schema.json` | `thread-qualify` (+ `qualification_decision` / `accepted_risk` from `loom_state qualify decide`) | `warp-spark`, `thread-audit`, `weave-script`, orchestrator |
| `capability-map.schema.json` | `warp-spark` via `loom_state vision map …` / `vision freeze` | `thread-audit`, `thread-suggest`, `weave-script` |
| `platform-audit.schema.json` | `thread-audit` (checked by `loom_state path check`) | `thread-suggest`, `weave-script`, `weave-model`, `finish-verify`, `finish-check` |
| `data-model.schema.json` | `weave-model` | `weave-train`, `finish-verify`, `bolt-bootstrap`, `finish-check` |

Validation uses the stdlib-only validator in `scripts/loomstate/schema.py` (draft 2020-12 subset: `$ref`, `anyOf`/`oneOf`, `type`, `enum`, `const`, `pattern`, `required`, `properties`, `patternProperties`, `additionalProperties`, `items`, `minItems`, `minLength`, `minimum`). Keep schemas within that subset. `scripts/run_evals.py` validates artifact fixtures in `tests/fixtures/` and `skills/*/evals/fixtures/` by filename suffix.

## Maintenance

When changing an output contract:

1. Update the relevant schema here.
2. Update the producing skill's `SKILL.md`.
3. Update any consuming skills that read the changed fields.
4. Add or update the skill eval that covers the changed contract.
5. If `loom_state` reads the field, update `scripts/loomstate/` and `tests/test_loom_state.py`.
