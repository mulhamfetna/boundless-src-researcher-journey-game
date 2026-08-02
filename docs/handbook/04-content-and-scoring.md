# 4 — Content & scoring

← [The application](03-the-application.md) · [Index](README.md) · Next: [GitHub workflow](05-github-workflow.md)

---

## From a JSON file to a played task

```mermaid
flowchart LR
    J["content/questions/<br/>journals.json"] --> V["content_schema.py<br/><b>validate_quiz</b>"]
    V -->|invalid| ERR["seeding aborts"]
    V -->|valid| S["seed.py<br/><b>seed_quiz</b>"]
    S --> Q[("questions table<br/>type + prompt + data_json")]
    Q --> SAMP["sampling.py<br/>concept-balanced pick"]
    SAMP --> SER["api.py<br/>_serialize_question"]
    SER --> UI["app.js<br/>renders by type"]
    UI --> CHK["client checks the answer<br/>instant feedback"]
    CHK --> SUB["POST /submit<br/>{question_id, retries, hint_used}"]
    SUB --> SC["scoring.py<br/><b>server computes points</b>"]

    style V fill:#b45309,color:#fff
    style SC fill:#0f766e,color:#fff
    style ERR fill:#b91c1c,color:#fff
```

## The shape of a quiz document

```json
{
  "slug": "journals",
  "title_ar": "تصنيف المجلات العلمية",
  "pdf_filename": "…",
  "fun_facts_ar": ["…"],
  "questions": [
    {
      "type": "spot",
      "prompt_ar": "حدّد العلامات التحذيرية في رسالة الدعوة هذه",
      "concept": "predatory_journals",
      "base_points": 100,
      "options_ar": ["رسوم قبل المراجعة", "مراجعة خلال 48 ساعة", "ISSN معلن"],
      "correct_indices": [0, 1],
      "chip_explanations_ar": ["…", "…", "…"],
      "hint_ar": "…",
      "explanation_ar": "…"
    }
  ]
}
```

**`concept` is mandatory on every question.** It is what feeds the mastery dashboard and the
spaced-repetition review deck. CI fails the build if any question lacks one.

## The six task types

```mermaid
flowchart TD
    T{"type"}
    T --> MCQ["<b>mcq</b><br/>options_ar + correct_index"]
    T --> TF["<b>tf</b><br/>true/false, same shape"]
    T --> IMG["<b>image</b><br/>mcq + a real screenshot"]
    T --> MATCH["<b>match</b><br/>left_ar + right_ar + correct_pairs"]
    T --> ORDER["<b>order</b><br/>items_ar + correct_sequence<br/><i>authored in correct order</i>"]
    T --> SPOT["<b>spot</b><br/>options_ar + correct_indices<br/><i>red-flag multi-select</i>"]

    style SPOT fill:#7c3aed,color:#fff
    style IMG fill:#0f766e,color:#fff
```

**`spot` is the type the application-first redesign needed.** Recall asks "what is a predatory
journal?"; `spot` shows a real solicitation email and asks *which specific lines* are the warning
signs. Checking is exact set equality — partial credit would teach that "mostly right" is right,
which is precisely the wrong lesson when evaluating a venue.

**`order` is authored already in the correct order** with `correct_sequence: [0,1,2,…]`, and the UI
shuffles for display. Authors read the sequence as prose rather than juggling indices — fewer
authoring mistakes.

## Sampling — why you don't get the same ten questions

```mermaid
flowchart LR
    ALL["all questions<br/>in the station"] --> G["group by concept"]
    G --> RR["round-robin across concepts<br/>random within each"]
    RR --> N["≈ SAMPLE_SIZE (10)"]

    J{"is it a journey?<br/>slug in JOURNEY_SLUGS"}
    J -->|"capstone"| ORD["<b>skip sampling</b><br/>play all 14 in authored order"]

    style ORD fill:#7c3aed,color:#fff
```

Concept balance matters: random sampling could hand a learner five questions on one concept and
none on another, making the mastery signal meaningless.

**The capstone is exempt.** It is one coherent research project — gap → question → design →
IMRaD → venue → ethics → rebuttal. Shuffling it would destroy the narrative, so
`JOURNEY_SLUGS = {"capstone"}` makes `api.py` play it in order.

## Scoring

```mermaid
flowchart TD
    A["answer submitted<br/>{retries, hint_used}"] --> R{"retries?"}
    R -->|0| F["full base_points"]
    R -->|1| P1["reduced"]
    R -->|"2+"| P2["reduced further"]
    F --> H{"hint used?"}
    P1 --> H
    P2 --> H
    H -->|yes| CUT["further reduction"]
    H -->|no| KEEP["keep"]
    CUT --> T["total_score"]
    KEEP --> T

    FT{"first try AND no hint?"}
    FT -->|yes| ST["streak +1<br/>counts toward accuracy"]
    FT -->|no| BR["streak resets"]

    style T fill:#0f766e,color:#fff
    style ST fill:#7c3aed,color:#fff
```

**Retry-until-correct with decreasing points** is a teaching choice: a learner who gets there on
the third attempt has still learned the thing. A single-shot model punishes exploration, which is
the opposite of what a *methodology* course wants.

But **streak and accuracy count only first-try, hint-free answers** — so the leaderboard still
distinguishes genuine mastery from persistence.

## The tamper-proofing trade-off

```mermaid
flowchart TB
    subgraph chosen["✅ What this project does"]
        C1["server sends questions<br/><b>including answer keys</b>"]
        C2["client checks instantly<br/>no network round-trip"]
        C3["client reports retries + hint_used"]
        C4["<b>server</b> computes the score"]
    end
    subgraph rejected["❌ The alternative"]
        R1["client sends each answer"]
        R2["server validates each one"]
        R3["a round-trip per answer"]
        R4["laggy on mobile networks"]
    end

    style chosen fill:#0f766e,color:#fff
    style rejected fill:#7f1d1d,color:#fff
```

**A crafted request can claim `retries: 0` on every question.** That is a real limitation, stated
plainly in `SECURITY.md` so nobody reports it as a vulnerability.

**Why it's acceptable here:** the leaderboard is a motivational nudge among classmates, not an
assessment. Nothing is awarded on it. The cost of the alternative — a visible network round-trip
before every piece of feedback, on Syrian mobile networks, inside a Telegram webview — would damage
the teaching experience for every honest learner in order to inconvenience a dishonest one who
gains nothing.

**What is protected:** *identity*. `initData` HMAC means an attempt is always attributed to a real
Telegram account. You cannot submit as someone else.

## Badges

Ten badges, evaluated in two passes:

```mermaid
flowchart LR
    SUB["attempt submitted"] --> E1["<b>evaluate(summary)</b><br/>per-attempt"]
    E1 --> B1["first_finish, perfect_quiz,<br/>streak_master, streak_10,<br/>self_reliant, flawless,<br/>perfect_capstone"]
    SUB --> E2["<b>evaluate_stateful(conn, cid)</b><br/>needs history"]
    E2 --> B2["all_stations, dedicated"]
    B1 --> P["priority order →<br/>top_badge on the board"]
    B2 --> P
```

Two functions because some badges are decidable from one attempt and some require querying the
player's whole history. Keeping them apart means the per-attempt path stays a pure function —
easy to test, no database needed.

## Seeding, and the danger in it

⚠️ **`seed_quiz` deletes before it inserts:**

```
DELETE answers → DELETE attempts → DELETE assets → DELETE questions → DELETE quiz row → reinsert
```

Re-seeding a station therefore **erases its leaderboard**. Locally that's harmless. In production
it is guarded by per-file content hashing — a guard added *after* it destroyed real data. Read
[Ch. 11](11-incidents.md) before touching seeding.

---

Next: [The GitHub workflow](05-github-workflow.md).
