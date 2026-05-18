# warp-discovery — Component Map

This skill is a self-contained distillation of two canonical pipeline skills.
It is authored to run without a Cursor or Claude Code runtime — no reads of other
SKILL.md files at execution time. When the canonical skills change, this file is the
maintenance checklist.

---

## Upstream Skills

| Skill | What it contributes to warp-discovery | Last synced |
|---|---|---|
| `skills/warp-listen/SKILL.md` | Discovery note parsing, input type classification, JSON extraction schema, customer confirmation doc structure, gaps report format | 2026-05-18 |
| `skills/thread-qualify/SKILL.md` | MEDDPIC qualification logic, qualification thresholds (PROCEED / CONTINUE / NOT QUALIFIED), opportunity summary structure, SA demo goals brief format | 2026-05-18 |

---

## What Was Omitted (by design)

| Omitted from warp-discovery | Reason |
|---|---|
| `warp-scan` diagnostic file parsing | SDRs/AEs rarely receive Elastic diagnostic ZIPs; adds complexity with no SDR/AE value |
| SA pipeline handoff language | SDRs/AEs don't operate Cursor, loom, or any SA tooling |
| Full opportunity summary (team review doc) | Replaced by the shorter SA handoff brief — SDR/AE audience doesn't need the full MEDDPIC table in prose form |
| `opportunity-profile.json` output | Machine-readable output for SA pipeline; irrelevant in a Gem chat session |
| Changelog / living document pattern | Gem sessions are stateless; follow-up calls are handled by pasting new content |
| File path instructions | No file system in Gem; all outputs are inline in the chat |

---

## Re-sync Checklist

Run this checklist whenever `warp-listen/SKILL.md` or `thread-qualify/SKILL.md` changes.
The goal is to keep `warp-discovery/SKILL.md` accurate without over-syncing minor edits.

### After changes to `warp-listen/SKILL.md`

- [ ] **New extraction fields** — does `warp-discovery` Step 3 ("Extract the Discovery Profile")
  need to capture any new field? Add it if it meaningfully improves the qualification or SA handoff.
- [ ] **New input types** — does Step 2 ("Note the Input Type") need a new input style?
- [ ] **Confirmation doc structure** — does Output 2 ("Customer Confirmation Document") need
  updated sections or tense rules?
- [ ] **Gaps report format** — does Output 3 ("Open Questions") need updated groupings or
  priority logic?
- [ ] Recompile `deployments/gem/system-prompt.md` if changes are substantive (see below).

### After changes to `thread-qualify/SKILL.md`

- [ ] **MEDDPIC scoring** — do the thresholds (PROCEED / CONTINUE / NOT QUALIFIED) or
  dimension definitions change? Update Step 5.
- [ ] **Qualification rationale format** — does the qualification summary block (Output 1)
  need restructuring?
- [ ] **SA handoff brief** — does the demo goals brief format change? Update Output 4.
- [ ] Recompile `deployments/gem/system-prompt.md` if changes are substantive (see below).

---

## Recompiling the Gem System Prompt

After updating `warp-discovery/SKILL.md`:

1. Open `deployments/gem/system-prompt.md`
2. Replace its contents with the body of `warp-discovery/SKILL.md` — strip the YAML
   frontmatter (the `---` block at the top) and paste everything below it
3. Open the live Gem in Gemini (gemini.google.com → Gems → Discovery)
4. Click Edit → replace the Instructions field with the new content → Save
5. Test with a short sample note to confirm the output format is correct
6. Update the `Last synced` dates in this file

Total time: under five minutes.
