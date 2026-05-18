# warp-discovery

**Who it's for:** SDRs and Account Executives  
**What it does:** Parses discovery notes and qualifies opportunities — no technical setup required  
**Deployment targets:** Gemini Gem (`deployments/gem/`) · Slack bot (`deployments/slack/`, deferred)

---

## What This Bundle Produces

From a single paste or file upload, warp-discovery returns:

| Output | Audience | Purpose |
|---|---|---|
| Qualification recommendation (MEDDPIC) | AE / SDR | Go / continue / no-go decision with rationale |
| Customer confirmation document | Customer | Send the day after the call — shows you listened |
| Open questions report | AE / SDR (internal) | Prioritized follow-up agenda |
| SA handoff brief | Solutions Architect | Two-minute read before ideation |

---

## How to Use It

**Via the Gemini Gem** (primary path):
1. Open the Discovery Gem in Gemini
2. Paste your notes or attach a file (`.txt`, `.pdf`, `.docx`)
3. Confirm the opportunity name when prompted
4. Receive all four outputs in the chat — copy, share, or download as needed

**Via Cursor / Claude Code** (SA/maintainer path):
This skill can also be invoked directly in Cursor. It behaves the same way as the Gem
but within the loom workspace. Useful for testing changes before recompiling the Gem.

---

## What This Skill Does NOT Do

- Does not write demo scripts, data models, or deployment artifacts — those are SA tasks
- Does not connect to Elasticsearch, Kibana, or any Elastic cluster
- Does not send anything to the customer automatically — you review and send the confirmation doc
- Does not require any configuration, API keys, or technical setup from the SDR/AE

---

## How It Relates to the Full Loom Pipeline

```
warp-listen          ←── canonical parsing skill (SA pipeline)
thread-qualify       ←── canonical qualification skill (SA pipeline)
        ↓
warp-discovery       ←── distilled bundle for SDR/AE deployment (this skill)
        ↓
deployments/gem/     ←── Gemini Gem system prompt
deployments/slack/   ←── Slack bot (deferred, pending IT approval)
```

The full loom SA pipeline reads `warp-listen` and `thread-qualify` directly and is
unaffected by this bundle. When those canonical skills change, see `components.md`
for the re-sync checklist.

---

## Maintaining This Bundle

See [`components.md`](components.md) for:
- The upstream skill dependency table with last-synced dates
- The re-sync checklist (run after changes to warp-listen or thread-qualify)
- Step-by-step instructions for recompiling and updating the live Gem
