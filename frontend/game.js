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

  window.mapState = mapState;
  window.MENTOR = MENTOR;
  window.mentorLineFor = mentorLineFor;
})();
