# Real-world artifacts for the "journals" quiz — FOR REVIEW

`content/questions/journals.json` now ships **13 questions**: 8 MCQ + 2 True/False
+ **3 image questions** built on genuine, sourced screenshots (below). Please
**review the three live images and their provenance/licence** before publishing.

## Live image questions & their assets

| Asset (committed) | Question | Answer | Source page | Provenance |
|---|---|---|---|---|
| `predatory_email.png` | "Which sign reveals this is a predatory journal?" | Fast-publication promise + editorial-board invite + fee discount | p16 | SciencePG/AJIST invitation from [Arkansas State Univ. library guide](https://libguides.astate.edu/predatory/email). **Recipient surnames redacted** (gray bar). |
| `journal_quartile.png` | "What quartile is this journal (SCImago)?" | Q3 | p8 | Official [SCImago SJR widget badge](https://www.scimagojr.com/journalsearch.php?q=19700188151). No personal data. |
| `journal_finder.jpg` | "What does the JANE tool do?" | Suggests journals from your title/abstract | p14 | JANE results figure from an open-access [JMLA article (PMC6300233)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6300233/), likely CC BY 4.0. No personal data. |

### Licence note (please confirm before publishing)
- `journal_quartile.png` — Scimago badges are meant for public embedding; verify terms of use.
- `journal_finder.jpg` — JMLA is open access (CC BY 4.0 expected); confirm attribution.
- `predatory_email.png` — hosted on a public university library guide as a teaching
  example; licence is **unknown**. If you want a cleaner-licence artifact, swap in an
  alternate (below) or your own screenshot.

## Anonymization performed
- `predatory_email.png` — the recipient surname line ("Dear …") was covered with a gray
  redaction bar. The sender shown (SciencePG/AJIST) is the predatory entity being
  illustrated, so it is intentionally left visible.
- `predatory_email_anon.png` — an **alternate** (ACCS / Iris Publishers email) where a
  real recipient **name + .edu email** and the greeting surname were redacted. Not used
  in the quiz yet; swap it in if you prefer it.

## Alternates available locally (NOT committed)
The raw scraped candidates live in `content/assets/journals/candidates/` (gitignored
because some contain un-anonymized personal data). They include a second full predatory
email, a "Fast Publication" close-up banner, an inbox montage of predatory invites, a
**Q2** Scimago badge, and the Elsevier Journal Finder input screen. To use any: anonymize
if needed, move it up into `assets/journals/`, and reference it from a question.

## How to add / swap an image question
Add (or edit) a question object in `journals.json`. The schema requires every `image`
question to carry an `asset` with a `file` + `source_url`:

```json
{
  "type": "image",
  "prompt_ar": "…",
  "base_points": 120,
  "explanation_ar": "… (ص 16)",
  "source_page": 16,
  "options_ar": ["…", "…"],
  "correct_index": 0,
  "asset": { "file": "assets/journals/your_image.png", "source_url": "https://…", "anonymized": true, "caption_ar": "…" }
}
```

Then re-seed (Task 9, Step 7 in the Phase 1 plan) to load the change.
