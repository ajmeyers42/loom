# Running warp-discovery as a Gemini Gem

The Gemini Gem is the primary SDR/AE deployment of the `warp-discovery` skill. It requires
no technical setup from the user — SDRs and AEs open a chat, paste notes or attach a file,
and receive four outputs in a single response.

---

## Prerequisites

- A Google Workspace account (Gemini is included with most Workspace tiers)
- Gemini Advanced, or a workspace plan that includes Gems
- Access to [gemini.google.com](https://gemini.google.com)

The Gem itself requires no Elastic credentials, API keys, cluster access, or local setup.

---

## Creating the Gem

1. Open [gemini.google.com](https://gemini.google.com)
2. In the left sidebar, click **Gems** → **New Gem**
3. Fill in the fields:
   - **Name:** `Discovery`
   - **Description:** paste the `description` value from `deployments/gem/gem-config.json`
   - **Instructions:** paste the full contents of `deployments/gem/system-prompt.md`
4. Click **Save**
5. Share the Gem link with your SDR/AE team (share icon → specific people or a Google Group)

The Gem is now live. No server, no deployment, no tokens.

---

## SDR/AE Usage Guide

Share this with SDRs and AEs — it is the only thing they need to know.

### Option A: Paste notes

1. Open the Discovery Gem
2. Send a message like:
   ```
   Here are my notes from today's call with [Company Name]:

   [paste notes here]
   ```
3. The Gem asks: *"I'll tag this as [Company Name] — does that look right?"*
4. Confirm or correct the name
5. The Gem returns all four outputs in one response

### Option B: Attach a file from a transcription service

1. Open the Discovery Gem
2. Click the attachment icon (📎) and upload your file (`.txt`, `.pdf`, or `.docx`)
3. Send the message — the Gem reads the file and confirms the opportunity name
4. The Gem returns all four outputs in one response

### What comes back

| Section | Who reads it | What to do |
|---|---|---|
| Qualification summary (MEDDPIC) | AE + SDR | Review together; decide next move |
| Customer confirmation document | Customer | Copy markdown → paste into email or doc |
| Open questions | AE + SDR | Prioritized agenda for next call |
| SA handoff brief | SA | Forward to SA before first ideation conversation |

### Follow-up calls

In the same Gem conversation, paste new notes from the follow-up call and say:
*"Here's what we learned on the follow-up."* The Gem updates the qualification
and flags what changed.

---

## Updating the Gem

The Gem's instructions come from `deployments/gem/system-prompt.md`, which is compiled
from `skills/warp-discovery/SKILL.md`. When the underlying skills change, update the Gem:

1. Pull the latest from the `feature/sdr-discovery` branch (or `main` after merge)
2. Open the Discovery Gem → click **Edit**
3. Replace the **Instructions** field with the updated `deployments/gem/system-prompt.md`
4. Click **Save** and test with a short sample note

See `skills/warp-discovery/components.md` for the re-sync checklist — it tells you
which upstream skill changes require a Gem update and which can be skipped.

---

## Skills and File Locations

| File | Purpose |
|---|---|
| `skills/warp-discovery/SKILL.md` | Source of truth for all SDR/AE deployment targets |
| `skills/warp-discovery/components.md` | Upstream skill dependencies + re-sync checklist |
| `deployments/gem/system-prompt.md` | Gem instructions (compiled from SKILL.md, no frontmatter) |
| `deployments/gem/gem-config.json` | Gem name, description, starter questions |
| `deployments/slack/` | Slack bot placeholder — pending IT approval |

---

## Limitations

- **Stateless sessions:** Each Gemini conversation is independent. Follow-up notes must be
  pasted in the same conversation thread to maintain context.
- **No automatic SA notification:** Outputs are delivered in the Gem chat. The SDR/AE forwards
  the SA handoff brief to the SA manually. (The Slack bot, when built, will handle `@ajm`
  notification automatically.)
- **No file storage:** Outputs are inline in the chat. The SDR/AE copies and shares them.
  Saving outputs to the engagements folder is a manual step.
- **Gemini file support:** `.txt`, `.pdf`, `.docx` work natively. Other formats (`.doc`, `.odt`,
  `.pages`) should be converted before uploading.
