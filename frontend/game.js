(function () {
  function mapState(quizzes, dashboard) {
    const best = (dashboard && dashboard.stats && dashboard.stats.best_by_quiz) || {};
    let nextAssigned = false;
    return (quizzes || []).map((q, i) => {
      const done = best[q.slug] != null;
      let status;
      if (done) status = "done";
      else if (!nextAssigned) { status = "next"; nextAssigned = true; }
      else status = "open";
      return { slug: q.slug, title_ar: q.title_ar, index: i, status };
    });
  }

  const MENTOR = {
    welcome_anon: "أهلاً! أنا البروفيسور 🦉. أخبِرني باسمك واختَر رمزك، ولنبدأ رحلة الباحث!",
    welcome: "أهلاً بك يا {name}! أنا البروفيسور 🦉، وسأرافقك لتصبح باحثاً ناشراً.",
    stage: {
      foundations: "📚 أوّل محطّاتنا: أسس البحث — من هنا يبدأ كل باحث عظيم.",
      "paper-parts": "🧩 لنتعرّف على تشريح الورقة البحثية جزءاً جزءاً.",
      "paper-types": "📄 أنواع الأوراق كثيرة — لنتعلّم كيف نختار النوع الصحيح.",
      journals: "🕵️ مهمّة التحرّي: سنكشف المجلات المفترِسة ونختار المجلة المناسبة.",
    },
    boss: "👑 هذا تحدّي الزعيم! ركّز جيداً — إنه أصعب سؤال في المحطّة.",
    levelUp: "ارتقيتَ إلى مستوى جديد يا {name}! أنا فخور بك.",
    victory: "🎉 مبروك يا {name}! أكملتَ المحطّة كباحث حقيقي.",
    encourage: "لا بأس — الباحث الجيّد يتعلّم من المحاولة. واصِل!",
  };

  function mentorLineFor(key, ctx) {
    ctx = ctx || {};
    let raw;
    if (key.indexOf("stage:") === 0) raw = MENTOR.stage[key.slice(6)] || "هيا بنا!";
    else raw = MENTOR[key] || "هيا بنا!";
    return raw.replace(/\{name\}/g, ctx.name || "صديقي");
  }

  const THRESHOLDS = [0, 300, 700, 1200, 1900, 2800, 3900, 5200, 6700, 8400]; // cumulative xp for level 1..10
  const RANKS = [{ min: 1, ar: "طالب" }, { min: 3, ar: "باحث" }, { min: 6, ar: "باحث رئيسي" }, { min: 10, ar: "بروفيسور" }];

  function rankFor(level) {
    let r = RANKS[0].ar;
    for (const b of RANKS) if (level >= b.min) r = b.ar;
    return r;
  }
  function levelStart(level) {
    if (level - 1 < THRESHOLDS.length) return THRESHOLDS[level - 1];
    return THRESHOLDS[THRESHOLDS.length - 1] + (level - THRESHOLDS.length) * 2000;
  }
  function levelFromXp(xp) {
    xp = Math.max(0, Number(xp) || 0);
    let level = 1;
    while (xp >= levelStart(level + 1)) level++;
    const start = levelStart(level), next = levelStart(level + 1);
    const span = next - start;
    const intoLevel = xp - start;
    return { level, rank_ar: rankFor(level), intoLevel, span, progress: span > 0 ? intoLevel / span : 0 };
  }
  function worldFromLevel(level) {
    const t = (Number(level) - 1) / 9; // level 1 -> 0, level 10 -> 1
    return Math.max(0, Math.min(1, t));
  }
  function emberCountForWorld(world) {
    const w = Math.max(0, Math.min(1, Number(world) || 0)); // junk -> 0 (deep Zaun)
    return 14 + Math.round(16 * (1 - w)); // 30 in deep Zaun -> 14 in Piltover
  }
  function pickBoss(questions) {
    if (!questions || !questions.length) return { bossId: null, ordered: [] };
    let boss = questions[0];
    for (const q of questions) if ((q.base_points || 0) >= (boss.base_points || 0)) boss = q;
    const ordered = questions.filter((q) => q !== boss).concat([boss]);
    return { bossId: boss.id, ordered };
  }

  window.mapState = mapState;
  window.MENTOR = MENTOR;
  window.mentorLineFor = mentorLineFor;
  window.levelFromXp = levelFromXp;
  window.worldFromLevel = worldFromLevel;
  window.emberCountForWorld = emberCountForWorld;
  window.RANKS = RANKS;
  window.rankFor = rankFor;
  window.pickBoss = pickBoss;
})();
