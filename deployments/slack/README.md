# Slack Bot — Discovery (Deferred)

This deployment target is reserved and pending IT approval.

---

## Status

**Not yet built.** Implementation begins only if Elastic IT approves installation of a
custom Slack app in the Elastic workspace.

---

## Design Documentation

The full Slack bot design is documented in the plan and in `docs/runtimes/slack.md`
(to be written when implementation begins). Key design decisions already made:

- **Invocation:** `@loom` mention in a channel or DM
- **Input:** pasted notes or file attachment (`.txt`, `.pdf`, `.docx`)
- **Opportunity confirmation:** Block Kit interactive buttons before processing
- **Outputs:** Qualification summary, customer confirmation doc (file upload), open questions, SA handoff with `@ajm` mention
- **SA notification:** `@ajm` tagged in `#loom-scout` channel on every run
- **Infrastructure:** Socket Mode (no public webhook), Anthropic Claude API, optional file write to `LOOM_ENGAGEMENTS_ROOT`
- **Scope:** Minimum OAuth scopes only — `app_mentions:read`, `im:history`, `chat:write`, `files:read`, `files:write`, `users:read`, `reactions:write`

## Underlying Skill

The Slack bot uses `skills/warp-discovery/SKILL.md` as its AI system prompt —
the same skill that powers the Gemini Gem. No skill changes are required when
this deployment is built.

---

## Next Steps (when approval is granted)

1. Create `feature/sdr-slack` branch off the current state of `feature/sdr-discovery`
2. Implement `deployments/slack/` following the design in the plan
3. Test against a free Slack workspace before submitting for Elastic IT approval
4. Submit `manifest.json` + data handling summary for IT review
5. Merge to main once approved and validated
