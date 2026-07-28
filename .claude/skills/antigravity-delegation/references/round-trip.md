# The Claude ↔ Antigravity round-trip

Read after the user approves delegation. Covers prompt authoring, verification, and failures.
Execution mechanics (wrapper flags, quota, the stable headless pattern) live in the `agy` skill;
Arcane presets and asset wiring live in `game-art`. This file is the *protocol between* them.

## The loop

```
Claude authors the prompt  →  agy generates  →  Claude verifies inline  →  Claude integrates
        ▲                                              │
        └───────────── iterate if it drifts ───────────┘
```

Each engine keeps its strength. Claude does not try to draw; Antigravity does not decide what is
true, what ships, or what a file should contain.

## 1. Claude authors the prompt

The prompt is Claude's work product, not a relay of the user's sentence. A good one carries:

- **Subject** — the concrete thing, in specific nouns.
- **Style anchors** — from `docs/superpowers/specs/2026-06-30-arcane-design-dna.md` for art, or an
  existing sample for copy ("match the register of these three fun-facts: …").
- **Negative constraints** — for images: no text, no logos, no watermarks, no UI chrome. For
  Arabic copy: no Latin script, no transliteration, no invented statistics.
- **Format** — exact aspect/size for art; for text, the number of items and max length per item.

For grey-zone content, add the accuracy frame explicitly: *"only claims that are standard in
research-methodology literature; no numbers or citations you cannot ground."* This does not make
the output trustworthy — it makes the drift easier to spot in step 3.

## 2. agy generates

Use `scripts/agy_gen.py` (`image` or `text`) exactly as the `agy` skill documents. Never call
`agy` ad-hoc for images, and never pass `--dangerously-skip-permissions`.

## 3. Claude verifies inline — the non-negotiable step

The user's global rule applies to Antigravity output exactly as it does to subagent output:
**re-verify inline before relying on it.** Never commit what you have not personally checked.

**Images — VIEW the file with Read before wiring anything:**

- [ ] Subject is what was approved
- [ ] No baked-in text, logos, signatures, or watermarks
- [ ] Matches the Arcane DNA (palette, lighting, world grading), not generic fantasy art
- [ ] Aspect/crop works at the real display size, and nothing important sits under UI overlays
- [ ] No artifacts (extra limbs, melted geometry, unreadable focal point)

**Text — read every line:**

- [ ] Every factual claim verified against a primary source, inline. Delete or fix anything you
      cannot ground. Gemini invents plausible statistics and citations.
- [ ] Arabic register is right, RTL punctuation is correct, terminology matches existing content
- [ ] Length and shape fit the schema; validate with `app.content_schema.validate_quiz`
- [ ] No Latin-script leakage, no English idioms translated literally

Anything that fails a check goes back to step 1 with a tightened prompt.

## 4. Integrate and record provenance

Land the asset or copy the normal way, then note in the commit body or the design doc that it was
**Antigravity-drafted, Claude-curated**. Provenance stays traceable; nothing in the repo is silently
of unknown authorship.

## Failure playbook

| Failure | Response |
|---------|----------|
| `429` / `quota_exhausted` (~4h image quota) | Report it plainly. Offer: Claude does it, or wait for reset. **Never** silently substitute Claude-made work for the approved Antigravity asset — the user approved an engine, not just an outcome. |
| `agy` missing / not authenticated | State it, fall back to Claude, don't retry blindly. |
| Output drifts twice in a row | Stop. Show the user what came back and ask for direction rather than burning quota on a third guess. |
| Output is good but the user dislikes it | That's a new decision, not a retry — ask before regenerating. |

## Worked example — a champion portrait

1. **Gate:** *"I'd send Antigravity: 'the Alchemist — hooded Zaun chemist, shimmer-green vials,
   backlit haze, Arcane painterly style, no text'. Path: `agy_gen.py image --preset arcane-champion`.
   Lands at `content/assets/art/champ_alchemist.png`. I recommend delegating — Claude can't paint
   this."* → user picks option 1.
2. **Generate** via the wrapper.
3. **Verify:** Read the PNG. Check the DNA checklist above.
4. **Integrate:** circular-crop token per `game-art`, wire the sprite, commit noting provenance.
