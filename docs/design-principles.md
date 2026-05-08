# Design Principles

These are the architectural choices that shape how loom works. Most have a corresponding entry in [decisions.md](decisions.md) with fuller rationale.

## Each skill is a specialist

Drop into any stage independently — you don't need to run the full pipeline every time. The orchestrator handles sequencing when you want it. Running `bolt-launch` on an existing engagement re-uses everything already built; running `warp-listen` on updated notes triggers only the downstream stages that depend on its output.

## Outputs feed inputs

Every skill's JSON output is designed as a machine-readable input to the next skill. The discovery JSON drives the platform audit; the platform audit constrains the script; the script shapes the data model; the data model drives `bootstrap.py`. Nothing is re-inferred downstream — what you approved is what gets built.

Core machine-readable contracts are documented in [`../schemas/`](../schemas/). Skills may include richer examples and reasoning guidance, but schemas define the stable fields downstream stages can rely on.

## Nothing is hallucinated

Confirmation docs use only the customer's own language. Platform audits only clear features that are actually supported on the customer's platform and license tier. Scripts are grounded in specific pain points from discovery, not generic feature showcases. If a capability can't be confirmed from inputs, it's flagged as a gap.

## Stack version is explicit (D-020, D-033)

API baseline is **Elastic 9.4+**. New cloud resources default to the latest GA unless you specify otherwise. Existing deployments require a validated version (from diagnostic, `GET /`, or Kibana status) before scripting starts. ES|QL, mappings, and API calls are scoped to that version. No legacy compatibility shims.

## Solution scope matches the customer (D-021)

Inputs include discovery notes, diagnostics, team notes, and architecture diagrams. Demos showcase enterprise-appropriate Elastic capabilities for the outcomes described — Search, Observability, Security, or a combined storyline. The pipeline does not default to core-search unless that's what the inputs describe.

## Solution first (D-022)

Scripts and plans lead with business value and the customer's key asks, then the capabilities that deliver them. If those asks aren't clear from the inputs, the assistant asks before locking the storyline.

## Approvals before cluster spend (D-024)

The assistant will not run `bolt-spin` or `bolt-launch` (create resources, execute `bootstrap.py` against a live cluster) until the SA has explicitly asked to proceed **and** has reviewed `bootstrap.py`, the platform audit, risks, and the demo checklist. Generating or editing artifacts, and running `bootstrap.py --dry-run`, do not require approval.

## Elastic truthfulness (D-025)

Every defined asset must be deployable on Elastic using supported APIs. Mappings use Elasticsearch field types (`keyword`, `text`, `date`, `long`, etc.). Agent Builder tool parameters match the 9.4+ schema. Rules, saved objects, and API shapes follow product conventions — not abstract or invented types.

## Engagement tagging (D-026)

Every deployed asset with a `tags` field carries `demobuilder:<engagement_id>`. This makes the engagement's assets discoverable by tag at teardown time — no hardcoded ID lists required. See `skills/bolt-launch/references/loom-tagging.md`.

## ILM is hot-only by default (D-027)

Unless warm/cold/frozen tiers are explicitly in scope, all indices use a hot-only ILM policy. Rollover and forcemerge actions are never applied to plain (non-data-stream) indices. Available tiers are probed at deploy time via `GET /_nodes?filter_path=nodes.*.roles` — the policy is built from what the cluster actually has.

## Inference uses EIS, not ML nodes (D-028)

Embeddings and reranking use Elastic Inference Service (`service: "elastic"` on ECH, `service: "elser"` on Serverless). ML nodes are reserved for anomaly detection and data frame analytics — work better suited for local execution. This separation avoids resource contention on demo clusters.

## Clone, don't modify, Elastic-managed assets (D-032)

Prebuilt SIEM rules are cloned and the clone is modified for the demo. Elastic-managed originals are never touched — version bumps on managed assets fail silently and create confusing state. The clone is tagged and versioned like any other created asset.

## Asset manifest lives on the cluster (D-031)

`bootstrap.py` writes a document per engagement to the `loom-manifests` Elasticsearch index. `teardown.py` reads this as its trusted source of asset IDs — no local state, no `.env` entries for IDs, no hardcoded lists. If an engagement was deployed from a different machine, teardown still has everything it needs.

## Credentials stay local (D-024)

Each engagement workspace has its own `.env` — never committed, never shared between customers unless explicitly copied and updated. `INDEX_PREFIX` namespaces all resources when sharing a cluster across multiple demos so there are no collisions.

## Resumes intelligently

The orchestrator inventories existing outputs before running any stage. If you change one thing (e.g., a new pain point surfaces after the first discovery call), it re-runs only the affected downstream stages and leaves everything else intact.

## Repo structure (for reference)

```
loom/
├── AGENTS.md                 ← agent behavior: orchestrator, engagement root, approvals
├── README.md                 ← getting started
├── .cursor/
│   ├── rules/
│   │   ├── loom.mdc   ← Cursor: orchestrator + key decisions
│   │   └── hive-mind.mdc     ← Cursor: hive-mind skills routing
│   └── skills/               ← hive-mind skills symlinked here
├── .claude/skills/           ← same hive-mind symlinks for Claude Code
├── .agents/skills/           ← same hive-mind symlinks for other agents
├── docs/
│   ├── pipeline.md           ← stage diagram, skills table, workspace layout, validation
│   ├── design-principles.md  ← this file
│   ├── dependencies.md       ← agent-skills + hive-mind full setup
│   ├── decisions.md          ← decision log D-001 – D-036
│   ├── engagements-path.md   ← engagement root, env-var override
│   ├── todo.md               ← one-time setup checklist
│   └── runtimes/
│       ├── cursor.md         ← Cursor-specific setup
│       └── claude.md         ← Claude Code setup
└── skills/
    ├── loom/          ← orchestrator
    ├── warp-spark/        ← SA coaching + archetype selection (D-035)
    ├── warp-listen/
    ├── warp-scan/
    ├── thread-audit/
    ├── weave-script/
    ├── weave-model/
    ├── weave-train/
    ├── finish-check/
    ├── weave-agent/
    ├── weave-cost/     ← AI cost + usage dashboard (D-036)
    ├── bolt-spin/
    ├── bolt-launch/
    │   └── references/       ← env-reference, tagging, asset-manifest, serverless, workflows
    ├── wind-pulse/
    └── wind-reset/
```
