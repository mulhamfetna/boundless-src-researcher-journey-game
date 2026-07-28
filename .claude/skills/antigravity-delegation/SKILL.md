---
name: antigravity-delegation
description: >
  Use when work calls for generated art, images, illustrations, painterly backgrounds, character
  or champion portraits, banners, textures, visual style variants, or evocative Arabic copy
  (fun-facts, mentor/story voice, flavor text, rephrasing for warmth), or out-of-the-box creative
  ideation — and before invoking the `agy` CLI, `scripts/agy_gen.py`, or the `agy` / `game-art`
  skills. Also use when unsure whether Gemini or Claude should do a piece of creative work.
---

# Antigravity delegation — whether and when

Two engines, two strengths. **Claude** = logic, code, correctness, orchestration, verification.
**Antigravity** (`agy` → Gemini) = image generation and creative writing. This skill decides
*whether* to hand work over. The `agy` skill covers *how* to run it; `game-art` covers the Arcane
DNA and asset wiring. Do not duplicate those here.

## The one rule

> **Never delegate silently. Never silently skip delegation.**

Both directions are failures. Quietly shelling out to `agy` puts unreviewed Gemini output in the
repo. Quietly doing creative work in Claude hides a better option the user would have chosen.
The user's standing instruction: *"never use secretly — always ask to use it when it is needed."*

## Every entrance carries the gate

`agy` and `game-art` both open with a STOP block pointing here, because agents reliably reach for
the most *specific* skill and never load a general one. Reaching either of those files by any
route means this gate applies. Do not remove those blocks.

## Step 0 — read the policy (every time)

```bash
cat .claude/antigravity-policy.json 2>/dev/null   # absent → policy is "ask"
```

`{"policy": "ask" | "always" | "never", "set_at": "YYYY-MM-DD", "note": "..."}`
Absent, unreadable, or malformed ⇒ **`ask`**. Never guess a policy from past sessions.

## Routing

| Task | Route |
|------|-------|
| Raster art: backgrounds, portraits, banners, scenes, textures | **Ask** → recommend delegate |
| Visual style exploration, mood/direction variants | **Ask** → recommend delegate |
| Evocative Arabic copy: fun-facts, mentor/story voice, flavor text | **Ask** → recommend delegate |
| Divergent ideation where imagination beats rigor | **Ask** → recommend delegate |
| Content that is creative **and** must be factually right (quiz prompts, explanations) | **Ask** → grey zone: Gemini drafts, Claude curates |
| Code, tests, schema, scoring, algorithms, state | **Keep in Claude** — no prompt |
| Orchestration: file edits, git, Docker, deploy | **Keep in Claude** — no prompt |
| Verifying a fact against a source, checking a standard | **Keep in Claude** — no prompt |

Classification sets your *recommendation*, never whether you ask. Every row that says "Ask" asks,
including the grey zone, even when delegating is obviously right.

## The permission gate

Ask with `AskUserQuestion` **before** any `agy` invocation. The question REQUIRES four slots:

1. **What** would be sent — the gist of the generation prompt.
2. **Which** path — `agy_gen.py image` or `text`, and the model.
3. **Where** the result lands — a local path. Never an upload.
4. **Why** — one line for your recommended option.

Four options, always these:

| # | Option | Effect |
|---|--------|--------|
| 1 | Delegate this one to Antigravity | Run `agy` for this task only |
| 2 | Keep it in Claude | Do it yourself this time |
| 3 | Always delegate this kind of work in this project | Write `"always"` to the policy file |
| 4 | Never delegate in this project | Write `"never"` to the policy file |

**A persisted policy is still never silent.** With `"always"`, don't ask — but state, in your own
visible text before running: *"Project policy is always-delegate → sending this to Antigravity:
\<gist\>."* With `"never"`, say once that you're keeping it in Claude per project policy. The user
can override in that same turn either way.

## After approval

Read `references/round-trip.md` before generating. Antigravity output is a **draft, never a
commit** — Claude authors the prompt, verifies the result inline, and only then integrates.

## Rationalizations — all of these are wrong

Captured verbatim from agents doing this task without this skill:

| Excuse | Reality |
|--------|---------|
| "'make it' is an explicit command to generate the asset" | They asked for an *outcome*, not an *engine*. Which engine is exactly what you're asking. |
| "The local-only rule only restricts publishing; this writes a local file" | Local output is why it's *allowed*, not why it's *unannounced*. The gate is about authorship, not upload. |
| "The pipeline was built and used for this in prior sessions" | Past approval is not standing consent. Global rule: "Approval once does not carry over to the next task." |
| "The skill lists this exact use case" | The `agy` skill says how to run it, not that you may run it unasked. |
| "The `agy` docs use this exact prompt as their canonical example" | **Documentation is not consent.** A usage sample shows syntax, never permission. |
| "The global rule needs an explicit ask 'in that message' — 'make it' is that ask" | That rule is about *going online*. This gate is about *who authors the work*. "Make it" names a deliverable, not an engine. |
| "`game-art`/`agy` is purpose-built for this, so it's pre-approved" | Purpose-built means it's the right *tool once approved*. Existence ≠ authorization. |
| "I'll call the wrapper directly, no separate gating step needed" | The gate is not optional overhead. It is the precondition for the call. |
| "Asking is friction; the answer is obviously yes" | Then the prompt costs one keystroke. Obviousness is not consent. |
| "I'll just write it in Claude, no need to mention agy" | Silent omission is the other half of the violation. Offer it. |
| "It's a small asset / a quick draft" | Size is irrelevant. Unreviewed Gemini authorship is the thing being gated. |
| "I'll show the user the output afterwards" | After is not before. The gate is a *pre*-condition. |

## Red flags — STOP

- About to run `agy` / `agy_gen.py` and no `AskUserQuestion` happened this turn
- About to hand-write flavor text or draw CSS art without offering Antigravity
- Reasoning "the user already knows we use Gemini here"
- Assuming a policy without reading `.claude/antigravity-policy.json`
- Pasting Gemini text into a content file before verifying it inline

**All of these mean: stop, and ask first.**

## Common mistakes

- **Asking for logic work.** Don't gate a scoring fix — that's pure friction and the routing table says keep it.
- **Committing raw output.** Grey-zone drafts must be fact-checked inline before landing.
- **Silently substituting on quota failure.** If `agy` 429s, say so; don't hand back Claude-made
  work as if it were the approved Antigravity asset.
