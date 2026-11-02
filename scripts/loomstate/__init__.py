"""loomstate — SA-first control-plane library for loom engagements (P2).

Deterministic, stdlib-only helpers that create and update the engagement
filesystem contract under ``$LOOM_ENGAGEMENTS_ROOT/{slug}/``:

- engagement bootstrap with dual identity (private sales identity in
  pipeline-state only; public ``acme-…`` slug for everything shared)
- per-engagement keystore (``.env``) status, sample load, sibling clone
- intake / qualify / vision / demo-path gates that validate LLM-stage outputs
  and record ``stages`` + ``approvals[]`` in ``{slug}-pipeline-state.json``
- derived "what's next" from pipeline-state alone

The LLM skills under ``skills/`` still author content; this library never
calls a cluster except the explicit read-only ``keys validate --probe``.
"""

SCHEMA_VERSION = "2"
