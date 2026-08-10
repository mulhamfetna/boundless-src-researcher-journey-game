# Launch kit — «رحلة الباحث»

Everything needed to announce the game to the Arabic research community.

| File | What it is |
|---|---|
| [`announcement-copy.md`](announcement-copy.md) | Copy for every channel, in two audience variants, plus the bot broadcast and the publishing schedule |
| [`poster-prompts.md`](poster-prompts.md) | Five posters, each with **two** prompt variants — Arabic baked in, or text-free — plus the type to set afterwards and a review checklist |
| `assets/gameplay.mp4` · `assets/gameplay.gif` | An 18-second recording of real play, produced by `scripts/capture/` |
| `assets/carousel/` | The nine carousel slides and the all-stations poster, **built from HTML** by `scripts/posters/build.mjs` — ready to post, no generation needed |
| `posters/carousel.src.html` | Source for those slides; open `posters/carousel.html` in a browser to preview |

---

## The one decision everything follows from

**The game is themed. The launch is not.**

The audience is academic and has, for the most part, never encountered the world the
game is set in. A public asset that opens with an unexplained proper noun spends the
reader's first and most valuable seconds on decoding instead of on the offer. So every
public asset — copy, poster, clip — speaks plain academic Arabic, and the themed world
stays inside the product, where it works as a reward for opening it rather than as a
toll for understanding the pitch.

This is enforced, not merely intended: `scripts/capture/capture.mjs` keeps a list of
in-world terms and skips any question carrying one when recording a public beat.

## The positioning

> ## «لا تحفظ منهجية البحث… مارِسها»

Methodology is taught as lectures and then met, at the first real submission, without
practice. The product's answer is that every task is a decision performed on real
material rather than a definition recalled. That sentence does more work than any
amount of styling, and it is the reason the clip shows a COPE/ICMJE violation being
caught rather than a multiple-choice question being answered.

## What to lead with

Five things, all verifiable — an academic audience checks:

1. Built from the six sessions of معسكر البحث العلمي
2. Practice on genuinely published papers and real submission screens
3. Application-first task design — six task types, none of them "pick the definition"
4. Open source (AGPL-3.0) with a citable DOI — another institution can cite it, fork it, run it
5. No install, no account, no fees — it runs inside Telegram

Item 4 is the institutional wedge; item 2 is the consumer wedge.
`announcement-copy.md §0` lists what may **not** be claimed. Please keep to it.

## The clip

18 seconds of real play, captured from the running app: the map, catching COPE/ICMJE
violations in an AI-authorship declaration, ordering the submission pipeline from
technical check through to DOI assignment, and a genuinely earned score.

Nothing is staged and no frame is a mockup. Regenerate at any time with:

```bash
scripts/capture/run.sh --scene clip
```

The question sample is random per attempt, so the exact questions shown will differ
between runs — the beats and their pacing will not.

## Still open

- **The carousel and the all-stations poster are finished** — real PNGs in `assets/carousel/`,
  built from HTML so the Arabic is simply correct rather than gambled on. Nothing to generate,
  nothing to proofread for invented glyphs.
- The remaining posters (hero, differentiator, teaser, institutional) are **prompts only**;
  no images have been generated. Run them in
  Gemini and send the results back to be checked against the list at the end of
  `poster-prompts.md`.

  Try the **text-baked variant (A)** first — if it spells correctly, the poster is finished in
  one shot and only small areas need touching up in Canva. Fall back to the **text-free
  variant (B)** whenever it cannot. The odds table at the top of `poster-prompts.md` says which
  posters are worth the attempt: the hero and the differentiator carry one headline each and
  have the best chance; the teaser and the institutional poster carry more and are riskier —
  both could be moved to the HTML builder too if you would rather not gamble on them.

  The rule that matters: **one malformed Arabic word means discard, not edit.** Shipping
  convincing-looking nonsense to researchers costs far more than regenerating.
- The publishing schedule is relative (ت−٢ / ت=٠ / ت+٢ / ت+٤ / ت+٧). Fix a launch date
  and the dates follow.
