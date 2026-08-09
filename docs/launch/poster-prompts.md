# Poster prompts — «رحلة الباحث» launch

Five prompts to run in Gemini, then hand the results back for review.

---

## Read this before generating

**1. Every prompt produces TEXT-FREE art.**
Image models render Arabic script as convincing-looking nonsense — correct letterforms,
meaningless words. In front of an academic audience that is fatal, and it is the single
most likely way this set fails. So each prompt asks for a composition with **empty
reserved zones**, and the Arabic headline is set afterwards in real type (Cairo /
Aref Ruqaa, both already in `frontend/fonts/`). Each prompt states where its empty
space must be.

If a render comes back with any lettering in it — Arabic, Latin, or invented — it is
rejected, not retouched.

**2. The palette is the product's own**, so the posters and the game read as one thing:

| Role | Hex |
|---|---|
| Ground | `#0a1428` → `#0e1b33` (deep navy) |
| Primary accent | `#c8aa6e` (gold), highlight `#e2c687` |
| Secondary accent | `#0ac8b9` (teal), highlight `#cdfafa` |
| Paper / type | `#f0e6d2` (warm ivory) |

**3. Visual register: scientific-editorial, not game art.** The reference points are a
journal cover, a well-made conference poster, a scientific-diagram plate. Nothing
fantastical, no characters, no neon, no "epic". The game's themed world is deliberately
absent from all public material.

**4. Every prompt ends with the same negative clause.** Keep it — it is doing most of
the work:

> `--no text, letters, words, typography, watermarks, signatures, human faces, characters, cartoon, anime, video-game art, neon cyberpunk, magic, glowing runes, fantasy, cluttered composition, lens flare, stock-photo people`

---

## Poster A — «خط الرحلة» · The research pipeline
**Role:** hero, launch day (ت=٠). **Ratios:** 4:5 (Telegram/Instagram), 1200×630 (LinkedIn/Facebook).

### Prompt
```
A refined scientific-editorial poster illustration: a single continuous pathway
crossing the composition, marked by seven evenly spaced station nodes rendered as
small precise hexagonal medallions in brushed gold. Each node is connected by a thin
engraved gold line with fine tick marks, like a measured scale on a scientific
instrument. Background is a deep navy gradient (#0a1428 to #0e1b33) with a barely
visible technical grid and faint concentric contour lines. Behind the pathway,
translucent layered manuscript pages float at low opacity — visible as paper texture
and column blocks only, never as readable writing. A soft teal (#0ac8b9) light rises
from the final node, the only cool accent in an otherwise warm gold scheme. Restrained,
generous negative space, museum-quality print finish, subtle paper grain.

COMPOSITION REQUIREMENT: the entire upper third must remain empty deep-navy field with
no detail, reserved for a headline. Keep a clear margin around all four edges.

Style: scientific journal cover, editorial infographic, engraved plate, matte print.
--no text, letters, words, typography, watermarks, signatures, human faces, characters,
cartoon, anime, video-game art, neon cyberpunk, magic, glowing runes, fantasy,
cluttered composition, lens flare, stock-photo people
```

### Type to composite afterwards
- Headline: **«من الفكرة إلى النشر — سبع محطات تتدرّب فيها، لا تُحاضَر»**
- Wordmark: **رحلة الباحث**
- Footer: `t.me/src_quize_bot` · `© باوندلس للخدمات الأكاديمية ومعسكر البحث العلمي`

---

## Poster B — «تتدرّب على أوراق حقيقية» · The differentiator
**Role:** the "why this is different" post. **Ratio:** 4:5.

### Prompt
```
A scientific-editorial illustration of a single printed research paper page seen at a
slight three-quarter angle, floating on a deep navy field (#0a1428). The page is warm
ivory (#f0e6d2) with realistic paper grain; its content is rendered as abstract
greeked column blocks and rule lines — texture that reads as an academic page without
any legible writing. One paragraph block is marked by a precise teal (#0ac8b9)
highlight rectangle, and a thin gold (#c8aa6e) leader line runs from that block toward
empty space at the edge, ending in a small hexagonal gold node. Two or three fine
gold circles suggest annotation marks elsewhere on the page. Soft directional light
from upper left, gentle shadow beneath the sheet.

COMPOSITION REQUIREMENT: the left third must remain an empty deep-navy field with no
detail, reserved for a headline and a caption.

Style: scientific journal cover, editorial infographic, precise technical illustration,
matte print, shallow depth of field.
--no text, letters, words, typography, watermarks, signatures, human faces, characters,
cartoon, anime, video-game art, neon cyberpunk, magic, glowing runes, fantasy,
cluttered composition, lens flare, stock-photo people
```

### Type to composite afterwards
- Headline: **«لا أمثلة نظرية»**
- Sub: **«تتدرّب على أوراق منشورة فعلًا، وعلى شاشات الإرسال الحقيقية»**

---

## Poster C — «كيف تكشف مجلة مفترسة؟» · The teaser
**Role:** ت−٢, released with **no branding at all**. **Ratios:** 1:1 (WhatsApp) and 4:5.

> This is the highest-forward asset in the set. It sells nothing and asks a question
> that concerns every researcher personally, which is exactly why it travels. Publish it
> with the question only — the product is not mentioned until launch day.

### Prompt
```
A scientific-editorial illustration: five identical blank card panels arranged in a
clean vertical stack on a deep navy field (#0a1428), seen straight on. Four cards are
warm ivory (#f0e6d2) with a fine gold (#c8aa6e) hairline border and a small precise
hexagonal marker at the leading edge; each card's surface carries faint greeked rule
lines suggesting a printed checklist item, never legible writing. The fifth and final
card is different: empty, unfilled, its border drawn as a broken dashed gold outline,
its marker missing — visibly incomplete. Subtle teal (#0ac8b9) rim light along the
stack's edge. Restrained, high contrast, generous margins, museum print quality,
subtle paper grain.

COMPOSITION REQUIREMENT: the upper quarter must remain an empty deep-navy field with no
detail, reserved for a headline. Each card must contain a clear empty band for a line
of type.

Style: scientific journal cover, editorial infographic, engraved plate, matte print.
--no text, letters, words, typography, watermarks, signatures, human faces, characters,
cartoon, anime, video-game art, neon cyberpunk, magic, glowing runes, fantasy,
cluttered composition, lens flare, stock-photo people
```

### Type to composite afterwards
- Headline: **«مجلة تَعِدك بالنشر خلال ٤٨ ساعة دون مراجعة. هل تعرف كيف تكشفها؟»**
- Four filled cards — each of these is checkable and non-controversial:
  1. **وعد بنشر سريع مضمون قبل بدء التحكيم**
  2. **دعوة فورية للانضمام إلى هيئة التحرير دون سجلّ علمي**
  3. **بريد تحرير على نطاق عام لا مؤسسي**
  4. **إطراء مبالغ فيه في رسالة عامة لا تذكر عنوان بحثك**
- Fifth card, left empty: **«… والخامسة؟»**

---

## Poster D — «المحطات السبع» · Carousel
**Role:** ت+٢ carousel; the same plate also opens each chapter of the player handbook.
**Ratio:** 1:1, seven slides.

### Prompt (run once; recolour per slide, or regenerate with the node index moved)
```
A single precise hexagonal medallion centred on a deep navy field (#0a1428), rendered
as a brushed gold (#c8aa6e) engraved emblem with a fine double border and small
machined notches at each vertex. The medallion's interior is an empty recessed panel
of darker navy, lit by a faint teal (#0ac8b9) inner glow. Around it, a thin gold
circular scale with fine tick marks, and a subtle radial gradient falling off into
darkness. Symmetrical, centred, generous margins, museum-quality engraved print,
subtle paper grain.

COMPOSITION REQUIREMENT: the medallion's interior panel must remain completely empty,
and the lower third of the image must remain an empty navy field, both reserved for
type.

Style: engraved medal plate, scientific instrument detail, editorial infographic, matte print.
--no text, letters, words, typography, watermarks, signatures, human faces, characters,
cartoon, anime, video-game art, neon cyberpunk, magic, glowing runes, fantasy,
cluttered composition, lens flare, stock-photo people
```

### Type per slide — station name, then what you *practise* there
| # | المحطة | يُمارَس فيها |
|---|---|---|
| ١ | تصنيف المجلات العلمية | فحص رصانة المجلة وكشف المؤشّرات المفترسة |
| ٢ | أسس البحث واختيار الفجوة البحثية | استخراج فجوة بحثية حقيقية من الأدبيات |
| ٣ | أنواع الأوراق البحثية العلمية | مطابقة الهدف البحثي بنوع الورقة المناسب |
| ٤ | أجزاء الورقة البحثية | تقييم الملخّص والعنوان والكلمات المفتاحية |
| ٥ | متطلبات النشر | تضارب المصالح وإقرار المساهمات وخطاب التغطية |
| ٦ | الإرسال والتتبع | مسار الإرسال من الفحص الفنّي حتى منح الـDOI |
| ٧ | الرحلة الكبرى | محطة ختامية تجمع المحطات الستّ |

---

## Poster E — «مفتوحة المصدر وقابلة للاقتباس» · Institutional
**Role:** ت+٤, LinkedIn. Aimed at departments and other camps, not students. **Ratio:** 1200×630.

### Prompt
```
A restrained scientific-editorial composition on a deep navy field (#0a1428): a stack
of three offset printed pages in warm ivory (#f0e6d2), and beside them a precise
engraved gold (#c8aa6e) hexagonal seal with a fine double border and an empty recessed
centre. A thin gold line links the seal to the page stack, with small tick marks along
it. The pages show only greeked column texture and rule lines, never legible writing.
Cool teal (#0ac8b9) rim light along the top edge of the stack. Wide horizontal
composition, strongly asymmetric, very generous empty space on the right half.

COMPOSITION REQUIREMENT: the entire right half must remain an empty deep-navy field
with no detail, reserved for a headline and three short lines. The seal's centre must
remain empty.

Style: scientific journal cover, editorial infographic, engraved plate, matte print.
--no text, letters, words, typography, watermarks, signatures, human faces, characters,
cartoon, anime, video-game art, neon cyberpunk, magic, glowing runes, fantasy,
cluttered composition, lens flare, stock-photo people
```

### Type to composite afterwards
- Headline: **«اقتبسها. اشتقّها. استخدمها في معسكرك.»**
- Three lines:
  - `AGPL-3.0 — مفتوحة المصدر بالكامل`
  - `DOI: 10.5281/zenodo.21759627`
  - `github.com/mulhamfetna/boundless-src-researcher-journey-game`

---

## Review checklist — apply to every render before it ships

1. **No lettering of any kind.** Any glyph, in any script, invented or not → reject.
2. **Reserved zones actually empty** — headline space must be flat field, not "mostly clear".
3. **Palette holds** — navy ground, gold primary, teal secondary. No stray purple, magenta or orange.
4. **No characters, no faces, no fantasy** — if it reads as game art rather than a journal plate, reject.
5. **Legible at thumbnail size** — shrink to 150px wide; if the structure disappears, the composition is too busy.
6. **Margins survive cropping** — Telegram, Instagram and LinkedIn crop differently; nothing essential within 8% of any edge.

Send the renders back and they will be checked against this list before any are used.
