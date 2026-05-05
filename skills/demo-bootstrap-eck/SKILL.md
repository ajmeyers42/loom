---
name: demo-bootstrap-eck
description: >
  ECK (Elastic Cloud on Kubernetes) deployment variant for demo-bootstrap-generator.
  PLACEHOLDER — ECK support is not yet implemented. This skill will route ECK deployments
  to the ECH variant with documented exceptions until ECK-specific patterns are validated.
---

# Demo Bootstrap — ECK Variant (Placeholder)

**Status: Placeholder — not yet validated for production use.**

ECK deployments share most of the ECH API surface but differ in:
- Cluster endpoint format (ingress/LoadBalancer vs Elastic Cloud URL)
- API key provisioning (Kubernetes secret vs Cloud API)
- ILM tier availability (depends on node roles in Kubernetes StatefulSets)
- Feature flag availability (Agent Builder, Workflows — depends on ECK version and Kibana config)

## Current behavior

When `DEPLOYMENT_TYPE=eck` is set, this skill:

1. Reads `references/feature-compatibility.md` for ECK-specific notes
2. Routes to the ECH variant (`../demo-bootstrap-ech/SKILL.md`) as the base
3. Logs a warning:
   ```
   ⚠  ECK deployment type detected. ECK-specific patterns are not yet validated.
      Using ECH variant as a base. Verify the following before deploying:
      - Cluster endpoints are accessible from the SA's workstation
      - KIBANA_API_KEY has Kibana system privileges (not just cluster privileges)
      - Desired Kibana features (Agent Builder, Workflows) are enabled in the Kibana CR
      - ILM tier availability matches node roles in the StatefulSet
   ```

## To implement ECK support

When ECK patterns are validated end-to-end:

1. Document ECK-specific Terraform provider configuration (endpoint format, TLS)
2. Document feature flag enablement via Kibana CR annotations
3. Add ECK-specific ILM tier detection (node roles differ from ECH)
4. Update `references/feature-compatibility.md` ECK column
5. Update this SKILL.md with the ECK-specific patterns
6. Remove the placeholder warning

## Tracking

File a ticket or note in `docs/todo.md` when ECK validation is planned.
