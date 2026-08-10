# Poster prompts — «رحلة الباحث» launch

Five posters. **Each has two prompt variants:**

| | |
|---|---|
| **A — text baked in** | The Arabic is written into the prompt for the model to render. Try this first: if it lands, the poster is finished in one shot and only small areas need touching up in Canva. |
| **B — text-free** | Empty reserved zones; the Arabic is set afterwards in real type. The reliable fallback. |

Both variants describe **the same composition, palette and geometry**, so a failed A can be
swapped for B without redesigning anything.

---

## Which route each asset takes

Not everything here should be generated. Anything whose value is **text** is now built from
HTML and rendered with headless Chrome (`scripts/posters/build.mjs`), because that removes the
Arabic-spelling risk entirely: the text is the text, alignment is exact across slides, and a
typo is a one-line fix and a re-run instead of another spin of the generation lottery.

| Asset | Route | Where |
|---|---|---|
| **Carousel** — cover + 7 stations + CTA | ✅ **built in HTML** | `docs/launch/assets/carousel/slide-*.png` |
| **All-stations poster** | ✅ **built in HTML** | `docs/launch/assets/carousel/poster-all-stations.png` |
| **A — hero** (pipeline key art) | 🎨 generate | prompt below |
| **B — differentiator** (paper + highlight) | 🎨 generate | prompt below |
| **C — teaser** (predatory-journal cards) | 🎨 generate, **or ask for HTML** | prompt below |
| **E — institutional** (open source + DOI) | 🎨 generate, **or ask for HTML** | prompt below |

**A and B genuinely want generation** — they are illustrative key images, and painterly depth is
something CSS cannot fake.

**C and E are mostly type on a flat ground.** They carry five short lines and a DOI respectively,
which is exactly where image models fail and exactly what HTML does perfectly. Say the word and
they can be added to the HTML builder in the same style as the carousel; the prompts below stay
as the alternative.

Rebuild the HTML assets at any time:

```bash
node scripts/posters/build.mjs          # HTML + PNGs
node scripts/posters/build.mjs --html   # HTML only, to preview in a browser
```

The builder **fails the build if any slide's content is cut off**, so a silent crop cannot ship —
that is not hypothetical, the all-stations poster lost its final row and its footer that way
before the check existed.

---

## Read this first

### How likely is variant A to work?

Image models render Arabic by imitating letter shapes, not by spelling. Success falls off
sharply with the amount of text, so try A in this order and expect to fall back:

| Poster | Arabic in variant A | Realistic odds |
|---|---|---|
| **C** — teaser | 1 headline + 5 short lines | ⚠️ moderate |
| **A** — hero | 1 headline + wordmark | ✅ best odds — try this one first |
| **B** — differentiator | 1 headline + 1 line | ✅ good |
| **E** — institutional | 1 headline + 3 technical lines | ⚠️ moderate (Latin/digits are easier than Arabic) |
| **D** — all stations | 7 names + 7 descriptions | ❌ — **now built in HTML instead**, see below |

Generate **3–4 attempts** of each variant A before giving up on it. The same prompt produces
very different spelling quality run to run.

### When to touch up in Canva, and when to discard

| Situation | What to do |
|---|---|
| Letters correct, spacing or kerning slightly off | Touch up — or leave it |
| One word malformed, rest perfect | Cover that word with real type in Canva |
| Two or more words malformed | **Discard.** Run variant B and set all the text properly |
| Letters disconnected, or reversed order | **Discard** — this is the model failing at Arabic, not a fixable blemish |
| Any invented glyph anywhere | **Discard** |

> A poster with one malformed Arabic word in front of researchers is not a poster that needs
> editing — it is a poster that failed. The reputational cost of shipping fake Arabic is far
> higher than the time saved.

**Safest hybrid, and what I would actually do:** run variant A; if the *headline* is clean,
keep the art and re-set the smaller labels in Canva anyway. Headlines are large enough to
judge at a glance; small labels are where bad spelling hides.

### Palette — the product's own, so posters and game read as one thing

| Role | Hex |
|---|---|
| Ground | `#0a1428` → `#0e1b33` (deep navy) |
| Primary accent | `#c8aa6e` (gold), highlight `#e2c687` |
| Secondary accent | `#0ac8b9` (teal), highlight `#cdfafa` |
| Paper / type | `#f0e6d2` (warm ivory) |

### Register

Scientific-editorial: a journal cover, a good conference poster, an engraved plate.
No characters, no neon, no fantasy. The game's themed world appears nowhere in public material.

### The shared negative clause — keep it on every prompt

**Variant B (text-free):**
```
--no text, letters, words, typography, watermarks, signatures, human faces, characters,
cartoon, anime, video-game art, neon cyberpunk, magic, glowing runes, fantasy,
cluttered composition, lens flare, stock-photo people
```

**Variant A (text baked in)** — same list minus the text terms:
```
--no watermarks, signatures, human faces, characters, cartoon, anime, video-game art,
neon cyberpunk, magic, glowing runes, fantasy, cluttered composition, lens flare,
stock-photo people, Latin transliteration, mirrored or disconnected Arabic letters
```

### Text instruction to paste into every variant A

```
TEXT REQUIREMENTS: render the Arabic text EXACTLY as written below, in fully connected
right-to-left Arabic script, in a clean modern Arabic sans-serif (Cairo / Tajawal style).
Do not translate it, do not transliterate it, do not invent additional words, and do not
add any text that is not listed. Arabic letters must be joined correctly within each word.
Spelling must match character for character.
```

---

# Poster A — «خط الرحلة» · The research pipeline
**Role:** hero, launch day. **Ratios:** 4:5 (Telegram/Instagram), 1200×630 (LinkedIn/Facebook).

### Variant A — text baked in
```
A refined scientific-editorial poster: a single continuous pathway crossing the lower two
thirds of the composition, marked by seven evenly spaced station nodes rendered as small
precise hexagonal medallions in brushed gold (#c8aa6e). The nodes are joined by a thin
engraved gold line with fine tick marks, like a measured scale on a scientific instrument.
Background is a deep navy gradient (#0a1428 to #0e1b33) with a barely visible technical grid
and faint concentric contour lines. Behind the pathway, translucent layered manuscript pages
float at low opacity — paper texture and column blocks only. A soft teal (#0ac8b9) light
rises from the final node, the only cool accent in an otherwise warm gold scheme. Restrained,
generous negative space, museum-quality print finish, subtle paper grain.

TEXT REQUIREMENTS: render the Arabic text EXACTLY as written below, in fully connected
right-to-left Arabic script, in a clean modern Arabic sans-serif (Cairo / Tajawal style).
Do not translate it, do not transliterate it, do not invent additional words, and do not
add any text that is not listed. Arabic letters must be joined correctly within each word.
Spelling must match character for character.

Centred across the empty upper third, as a large elegant headline in warm ivory (#f0e6d2):
«من الفكرة إلى النشر»

Directly beneath it, smaller, in gold (#c8aa6e):
«سبع محطات تتدرّب فيها، لا تُحاضَر»

Small, at the very bottom edge, centred, in muted grey:
«رحلة الباحث»

Style: scientific journal cover, editorial infographic, engraved plate, matte print.
--no watermarks, signatures, human faces, characters, cartoon, anime, video-game art,
neon cyberpunk, magic, glowing runes, fantasy, cluttered composition, lens flare,
stock-photo people, Latin transliteration, mirrored or disconnected Arabic letters
```

### Variant B — text-free
Same first paragraph as above, then:
```
COMPOSITION REQUIREMENT: the entire upper third must remain an empty deep-navy field with no
detail, reserved for a headline. Keep a clear margin around all four edges.

Style: scientific journal cover, editorial infographic, engraved plate, matte print.
--no text, letters, words, typography, watermarks, signatures, human faces, characters,
cartoon, anime, video-game art, neon cyberpunk, magic, glowing runes, fantasy,
cluttered composition, lens flare, stock-photo people
```

**Type to set in Canva (variant B):**
- Headline **«من الفكرة إلى النشر»** · sub **«سبع محطات تتدرّب فيها، لا تُحاضَر»**
- Wordmark **رحلة الباحث** · footer `t.me/src_quize_bot` · `© باوندلس للخدمات الأكاديمية ومعسكر البحث العلمي`

---

# Poster B — «تتدرّب على أوراق حقيقية» · The differentiator
**Role:** the "why this is different" post. **Ratio:** 4:5.

### Variant A — text baked in
```
A scientific-editorial illustration of a single printed research paper page seen at a slight
three-quarter angle, floating on a deep navy field (#0a1428), positioned in the right half of
the composition. The page is warm ivory (#f0e6d2) with realistic paper grain; its content is
abstract greeked column blocks and rule lines — texture that reads as an academic page. One
paragraph block is marked by a precise teal (#0ac8b9) highlight rectangle, and a thin gold
(#c8aa6e) leader line runs from it toward the left, ending in a small hexagonal gold node.
Two or three fine gold circles suggest annotation marks elsewhere. Soft directional light
from upper left, gentle shadow beneath the sheet.

TEXT REQUIREMENTS: render the Arabic text EXACTLY as written below, in fully connected
right-to-left Arabic script, in a clean modern Arabic sans-serif (Cairo / Tajawal style).
Do not translate it, do not transliterate it, do not invent additional words, and do not
add any text that is not listed. Arabic letters must be joined correctly within each word.
Spelling must match character for character.

In the empty left third, as a large headline in warm ivory (#f0e6d2):
«لا أمثلة نظرية»

Beneath it, smaller, in gold (#c8aa6e), on two lines:
«تتدرّب على أوراق منشورة فعلًا»
«وعلى شاشات الإرسال الحقيقية»

Style: scientific journal cover, editorial infographic, precise technical illustration,
matte print, shallow depth of field.
--no watermarks, signatures, human faces, characters, cartoon, anime, video-game art,
neon cyberpunk, magic, glowing runes, fantasy, cluttered composition, lens flare,
stock-photo people, Latin transliteration, mirrored or disconnected Arabic letters
```

### Variant B — text-free
Same first paragraph, then:
```
COMPOSITION REQUIREMENT: the left third must remain an empty deep-navy field with no detail,
reserved for a headline and a caption.

Style: scientific journal cover, editorial infographic, precise technical illustration,
matte print, shallow depth of field.
--no text, letters, words, typography, watermarks, signatures, human faces, characters,
cartoon, anime, video-game art, neon cyberpunk, magic, glowing runes, fantasy,
cluttered composition, lens flare, stock-photo people
```

---

# Poster C — «كيف تكشف مجلة مفترسة؟» · The teaser
**Role:** ت−٢, released with **no branding at all**. **Ratios:** 1:1 (WhatsApp) and 4:5.

> The highest-forward asset in the set. It sells nothing and asks a question that concerns
> every researcher personally, which is exactly why it travels. Publish it with the question
> only — the product is not named until launch day.

### Variant A — text baked in
```
A scientific-editorial illustration: five identical card panels arranged in a clean vertical
stack on a deep navy field (#0a1428), seen straight on. Four cards are warm ivory (#f0e6d2)
with a fine gold (#c8aa6e) hairline border and a small precise hexagonal marker at the
leading edge. The fifth and final card is different: empty, its border drawn as a broken
dashed gold outline, its marker missing — visibly incomplete. Subtle teal (#0ac8b9) rim light
along the stack's edge. Restrained, high contrast, generous margins, museum print quality,
subtle paper grain.

TEXT REQUIREMENTS: render the Arabic text EXACTLY as written below, in fully connected
right-to-left Arabic script, in a clean modern Arabic sans-serif (Cairo / Tajawal style).
Do not translate it, do not transliterate it, do not invent additional words, and do not
add any text that is not listed. Arabic letters must be joined correctly within each word.
Spelling must match character for character.

Across the empty upper area, as a headline in warm ivory (#f0e6d2), on two lines:
«مجلة تَعِدك بالنشر خلال ٤٨ ساعة دون مراجعة»
«هل تعرف كيف تكشفها؟»

On the four ivory cards, one line each, in dark navy text, right-aligned:
card 1: «وعد بنشر سريع مضمون قبل بدء التحكيم»
card 2: «دعوة فورية للانضمام إلى هيئة التحرير دون سجلّ علمي»
card 3: «بريد تحرير على نطاق عام لا مؤسسي»
card 4: «إطراء مبالغ فيه في رسالة لا تذكر عنوان بحثك»

On the fifth empty dashed card, centred, in gold (#c8aa6e):
«… والخامسة؟»

Style: scientific journal cover, editorial infographic, engraved plate, matte print.
--no watermarks, signatures, human faces, characters, cartoon, anime, video-game art,
neon cyberpunk, magic, glowing runes, fantasy, cluttered composition, lens flare,
stock-photo people, Latin transliteration, mirrored or disconnected Arabic letters
```

### Variant B — text-free
Same first paragraph, then:
```
COMPOSITION REQUIREMENT: the upper quarter must remain an empty deep-navy field with no
detail, reserved for a headline. Each card must contain a clear empty band for one line of type.

Style: scientific journal cover, editorial infographic, engraved plate, matte print.
--no text, letters, words, typography, watermarks, signatures, human faces, characters,
cartoon, anime, video-game art, neon cyberpunk, magic, glowing runes, fantasy,
cluttered composition, lens flare, stock-photo people
```

---

# Poster D — «لوحة الرحلة» · All seven stations  →  **built in HTML, no prompt needed**

Superseded. This poster carried fourteen separate Arabic strings — station names and
descriptions — which is far beyond what an image model spells reliably, and the odds table above
rated it ❌ for exactly that reason.

It is now generated from HTML instead, along with the nine-slide carousel, by
`scripts/posters/build.mjs`. Both read the **same** `STATIONS` array in that file, so the poster
and the slides cannot drift apart, and correcting a station description is one edit followed by
one command.

| Output | Size |
|---|---|
| `docs/launch/assets/carousel/poster-all-stations.png` | 1080×1620 (2:3) |
| `docs/launch/assets/carousel/slide-01-cover.png` … `slide-09-cta.png` | 1080×1350 (4:5) |

4:5 is the tallest ratio Instagram, Facebook and Telegram all keep uncropped, so the slides need
no per-platform variants.

To change the wording, edit `STATIONS` in `scripts/posters/build.mjs` and re-run it.

---

# Poster E — «مفتوحة المصدر وقابلة للاقتباس» · Institutional
**Role:** ت+٤, LinkedIn. Aimed at departments and other camps, not students. **Ratio:** 1200×630.

### Variant A — text baked in
```
A restrained scientific-editorial composition on a deep navy field (#0a1428), wide horizontal
format: on the left, a stack of three offset printed pages in warm ivory (#f0e6d2), and beside
them a precise engraved gold (#c8aa6e) hexagonal seal with a fine double border and an empty
recessed centre. A thin gold line links the seal to the page stack, with small tick marks
along it. The pages show only greeked column texture and rule lines. Cool teal (#0ac8b9) rim
light along the top edge of the stack. Strongly asymmetric, with the entire right half left
open.

TEXT REQUIREMENTS: render the text EXACTLY as written below. Arabic must be fully connected
right-to-left script in a clean modern Arabic sans-serif (Cairo / Tajawal style); Latin text
and digits must be in a clean monospace face. Do not translate, do not transliterate, do not
invent additional words, and do not add any text that is not listed. Spelling must match
character for character.

In the empty right half, as a headline in warm ivory (#f0e6d2):
«اقتبسها. اشتقّها. استخدمها في معسكرك.»

Beneath it, three short lines in gold (#c8aa6e):
«AGPL-3.0 — مفتوحة المصدر بالكامل»
«DOI: 10.5281/zenodo.21759627»
«github.com/mulhamfetna/boundless-src-researcher-journey-game»

Style: scientific journal cover, editorial infographic, engraved plate, matte print.
--no watermarks, signatures, human faces, characters, cartoon, anime, video-game art,
neon cyberpunk, magic, glowing runes, fantasy, cluttered composition, lens flare,
stock-photo people, mirrored or disconnected Arabic letters
```

### Variant B — text-free
Same first paragraph, then:
```
COMPOSITION REQUIREMENT: the entire right half must remain an empty deep-navy field with no
detail, reserved for a headline and three short lines. The seal's centre must remain empty.

Style: scientific journal cover, editorial infographic, engraved plate, matte print.
--no text, letters, words, typography, watermarks, signatures, human faces, characters,
cartoon, anime, video-game art, neon cyberpunk, magic, glowing runes, fantasy,
cluttered composition, lens flare, stock-photo people
```

> **Check the DOI and the URL character by character** on any variant A render of this poster.
> A misrendered digit in a DOI is worse than no DOI: it points at nothing, and it is the one
> line on the poster an academic reader is most likely to try.

---

## Review checklist — apply to every render before it ships

**Both variants**
1. **Palette holds** — navy ground, gold primary, teal secondary. No stray purple, magenta or orange.
2. **No characters, no faces, no fantasy.** If it reads as game art rather than a journal plate, reject.
3. **Legible at thumbnail size** — shrink to 150px wide; if the structure disappears, it is too busy.
4. **Margins survive cropping** — Telegram, Instagram and LinkedIn crop differently; nothing essential within 8% of any edge.

**Variant A only**
5. **Read every Arabic word aloud.** Not "does it look Arabic" — does it *say* the right thing.
6. **Letters joined correctly** within each word, and the text running right to left.
7. **No extra words** the model added on its own initiative — a common and easily missed failure.
8. **Latin strings and digits exact**, character by character: the DOI, the GitHub URL, `t.me/src_quize_bot`.

**Variant B only**
9. **No lettering of any kind** — any glyph, in any script, invented or not → reject.
10. **Reserved zones genuinely empty** — headline space must be flat field, not "mostly clear".

Send the renders back and they will be checked against this list before any are used.
