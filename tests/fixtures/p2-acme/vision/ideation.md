# Demo Ideation Contract — Acme Pharma (acme-pharma)

## Engagement Context
- **Customer / Event:** Acme Pharma (public demo identity)
- **Audience:** mixed — SOC manager, detection engineer, CISO
- **Timeline / Meeting Date:** three weeks
- **Delivery Method:** hosted

## Chosen Archetype
Operational Triage Console — the analyst triages a noisy alert queue with guided explanation and one investigation per incident.

## Top 3 Wow Moments
1. Guided triage explains an alert in plain language and proposes the next pivot.
2. A burst of related alerts collapses into one case.
3. An ES|QL pivot from alert to entity activity in seconds.

## Main Demo Paths
### Path 1: Alert to hypothesis
Steps: open the alert queue → ask the assistant → pivot with ES|QL → open a case.

## Elastic Capability Map
| Capability | Outcome Enabled | Proof Point |
|---|---|---|
| Detection rules + alerts `detection-rules` | Noise becomes actionable alerts | Prebuilt + demo rules fire on seeded events |

## Data Strategy
- **Starter data sufficient?** partial
- **Custom data needed:** synthetic endpoint and authentication events for Acme Pharma
- **Volume minimum:** 50k events over 7 days

## Out of Scope
- Custom search relevance UI — not required for this SOC storyline

## Minimum Bar (if time runs short)
Detection rules + cases + AI Assistant without Agent Builder.

## Build Effort
Customized Build — ~3 hours (effort estimate only; the Demo path is committed later)

## Risks / Open Questions
- Ingest volume unknown; seed volume is illustrative.
