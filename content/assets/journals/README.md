# Real-world artifacts for the "journals" quiz — PENDING USER CURATION

The current `content/questions/journals.json` ships **10 grounded MCQ/True-False
questions** — a fully playable vertical slice that needs no images.

The spec also calls for **`image` questions** built on **genuine public
screenshots** (real predatory-journal email vs. a legitimate one, a real DOAJ /
Think.Check.Submit view, etc.). Per the design spec, sourcing these is the one
**human-gated** step: each artifact needs verified provenance, an acceptable
licence, and **anonymization of any real names/emails** — a judgement call left
to the owner. They were intentionally **not auto-fabricated** (the spec forbids
slide screenshots or invented artifacts).

## How to add an image question

1. Drop the approved, anonymized screenshot here, e.g.
   `content/assets/journals/predatory_vs_legit.png`.
2. Add a question object to `journals.json` (the schema validator enforces that
   every `image` question carries an `asset` with a `file` + `source_url`):

```json
{
  "type": "image",
  "prompt_ar": "أمامك رسالتان من مجلتين. أيّهما من مجلة مفترسة (Predatory)؟",
  "base_points": 120,
  "explanation_ar": "الرسالة (ب) تَعِد بقبول خلال 48 ساعة مع رسوم فورية ودعوة مبالغ فيها — علامات مجلة مفترسة (ص 16).",
  "source_page": 16,
  "options_ar": ["الرسالة (أ)", "الرسالة (ب)"],
  "correct_index": 1,
  "asset": {
    "file": "assets/journals/predatory_vs_legit.png",
    "source_url": "https://REAL-PUBLIC-SOURCE",
    "anonymized": true,
    "caption_ar": "مقارنة بين بريدين حقيقيين"
  }
}
```

## Drafted image questions awaiting artifacts

| # | Concept (PDF page) | Artifact needed | Candidate genuine public sources |
|---|--------------------|-----------------|----------------------------------|
| A | Predatory vs. legitimate solicitation email (p15–16) | Side-by-side of a real spam "call for papers" email vs. a genuine editor invite, names/emails blurred | University library research-integrity guides; Think.Check.Submit case examples |
| B | Indexing/quartile badge (p8) | Real Scimago/JCR journal page showing the Q1–Q4 quartile badge | scimagojr.com journal page; publisher "metrics" tab |
| C | Journal-selection helper (p11–14) | Real Elsevier Journal Finder / Wiley Journal Finder / JANE results screen | Publisher journal-finder tools |

Once an artifact is approved and added, re-run the seed step (Task 9, Step 7)
to load it into the database.
