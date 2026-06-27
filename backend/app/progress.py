CONCEPT_LABELS_AR = {
    # journals
    "predatory_signs": "علامات المجلات المفترسة",
    "indexing": "الفهرسة",
    "quartiles": "تصنيف الأرباع (Quartiles)",
    "metrics": "مؤشرات التأثير",
    "open_access": "الوصول المفتوح",
    "journal_selection": "اختيار المجلة",
    # foundations
    "methodology_basics": "أساسيات المنهج العلمي",
    "originality": "الأصالة",
    "research_gap": "الفجوة البحثية",
    "gap_types": "أنواع الفجوات البحثية",
    "finding_gaps": "اكتشاف الفجوات",
    # paper-types
    "choosing_type": "اختيار نوع الورقة",
    "original_research": "البحث الأصلي",
    "review_types": "أنواع المراجعات",
    "secondary_research": "البحوث الثانوية (تحليل/مراجعة)",
    "special_formats": "الصيغ الخاصة",
    # paper-parts
    "title": "العنوان",
    "abstract": "الملخص",
    "keywords": "الكلمات المفتاحية",
    "introduction": "المقدمة",
    "methods": "المنهجية",
    "results": "النتائج",
    "discussion": "المناقشة",
    "references": "المراجع",
    "structure": "بنية الورقة",
}


def first_try_of(answer: dict) -> bool:
    return int(answer.get("retries", 0)) == 0 and not answer.get("hint_used")


def level_for(rate: float, count: int) -> str:
    if count == 0:
        return "not_started"
    if rate >= 0.85 and count >= 3:
        return "mastered"
    if rate >= 0.50:
        return "proficient"
    return "familiar"


def mastery_for_concepts(answers: list[dict], recent_n: int = 5) -> dict:
    by_concept: dict[str, list] = {}
    for a in answers:
        by_concept.setdefault(a["concept"], []).append(a)

    result = {}
    for concept, items in by_concept.items():
        recent = sorted(items, key=lambda x: x["order"])[-recent_n:]
        kept = len(recent)
        first_tries = sum(1 for x in recent if first_try_of(x))
        rate = first_tries / kept if kept else 0.0
        result[concept] = {"rate": rate, "count": kept, "level": level_for(rate, kept)}
    return result


def summarize_stats(attempts: list[dict]) -> dict:
    if not attempts:
        return {"total_points": 0, "attempts_count": 0, "best_by_quiz": {},
                "best_streak": 0, "first_try_accuracy": 0.0}
    best_by_quiz: dict[str, int] = {}
    for a in attempts:
        slug = a["quiz_slug"]
        best_by_quiz[slug] = max(best_by_quiz.get(slug, 0), a["total_score"])
    return {
        "total_points": sum(a["total_score"] for a in attempts),
        "attempts_count": len(attempts),
        "best_by_quiz": best_by_quiz,
        "best_streak": max(a.get("max_streak", 0) for a in attempts),
        "first_try_accuracy": round(sum(a["accuracy"] for a in attempts) / len(attempts), 4),
    }


def next_steps(mastery: dict, quiz_of_concept: dict, limit: int = 2) -> list:
    weak = [(c, m) for c, m in mastery.items() if m["level"] in ("familiar", "proficient")]
    weak.sort(key=lambda cm: (cm[1]["rate"], cm[1]["count"]))
    picks = [c for c, _ in weak]
    if len(picks) < limit:
        picks += [c for c, m in mastery.items() if m["level"] == "not_started"]

    out = []
    for concept in picks[:limit]:
        q = quiz_of_concept.get(concept, {})
        out.append({
            "concept": concept,
            "label_ar": CONCEPT_LABELS_AR.get(concept, concept),
            "quiz_slug": q.get("quiz_slug", ""),
            "quiz_title_ar": q.get("quiz_title_ar", ""),
            "level": mastery[concept]["level"],
        })
    return out
