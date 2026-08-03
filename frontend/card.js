// Shareable Canvas cards: capstone certificate + lab-notebook portfolio.
(function () {
  // Kept in step with CREDITS in app.js (tested in tests/credits.test.js).
  // card.js loads before app.js and must not depend on it, so the string is
  // repeated here rather than imported — the test asserts they stay identical.
  var CARD_CREDIT = "© 2026 باوندلس للخدمات الأكاديمية ومعسكر البحث العلمي";
  // Deterministic short verification code (FNV-1a).
  function shortHash(str) {
    let h = 2166136261 >>> 0;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    return h.toString(16).toUpperCase().padStart(8, "0").slice(0, 8);
  }

  function drawCard(o) {
    const W = 640, H = 400;
    const canvas = document.createElement("canvas");
    canvas.width = W; canvas.height = H;
    const ctx = canvas.getContext("2d");
    // two-world background
    const g = ctx.createLinearGradient(0, 0, W, H);
    g.addColorStop(0, "#14081e"); g.addColorStop(1, "#0e1b33");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    // hextech glow
    const rg = ctx.createRadialGradient(W - 90, 70, 10, W - 90, 70, 220);
    rg.addColorStop(0, "rgba(10,200,185,0.18)"); rg.addColorStop(1, "transparent");
    ctx.fillStyle = rg; ctx.fillRect(0, 0, W, H);
    // gold + cyan frame
    ctx.strokeStyle = "#c8aa6e"; ctx.lineWidth = 5; ctx.strokeRect(14, 14, W - 28, H - 28);
    ctx.strokeStyle = "#0ac8b9"; ctx.lineWidth = 1.5; ctx.strokeRect(22, 22, W - 44, H - 44);
    // RTL text
    ctx.direction = "rtl"; ctx.textAlign = "right";
    const R = W - 48;
    ctx.fillStyle = "#e2c687"; ctx.font = "bold 30px 'Aref Ruqaa','Cairo',serif";
    ctx.fillText(o.title, R, 80);
    ctx.fillStyle = "#f0e6d2"; ctx.font = "bold 26px 'Cairo',sans-serif";
    ctx.fillText(o.name || "باحث", R, 130);
    if (o.subtitle) { ctx.fillStyle = "#c8aa6e"; ctx.font = "17px 'Cairo',sans-serif"; ctx.fillText(o.subtitle, R, 162); }
    ctx.fillStyle = "#e8d8ff"; ctx.font = "19px 'Cairo',sans-serif";
    let y = 210;
    (o.lines || []).forEach(function (ln) { ctx.fillText(ln, R, y); y += 36; });
    // Attribution (issue #18). These cards are saved and forwarded to other
    // chats, so the credit has to travel with the image — a notice only inside
    // the app would never be seen by whoever receives it.
    ctx.textAlign = "center"; ctx.fillStyle = "#7d8bab"; ctx.font = "14px 'Cairo',sans-serif";
    ctx.fillText(CARD_CREDIT, canvas.width / 2, H - 66);

    // footer: verification code (LTR) + brand stamp (RTL)
    ctx.textAlign = "left"; ctx.fillStyle = "#9aa4bf"; ctx.font = "13px monospace";
    ctx.fillText("رحلة الباحث • " + (o.code || ""), 48, H - 34);
    ctx.textAlign = "right"; ctx.fillStyle = "#0ac8b9"; ctx.font = "bold 16px 'Cairo',sans-serif";
    ctx.fillText(o.stamp || "", R, H - 34);
    return canvas.toDataURL("image/png");
  }

  function showCard(dataUrl, filename) {
    const ov = document.createElement("div");
    ov.className = "card-overlay";
    ov.innerHTML =
      '<div class="card-box"><img class="card-img" src="' + dataUrl + '" alt="بطاقة الإنجاز" />' +
      '<div class="card-actions">' +
      '<button class="card-save">💾 حفظ</button>' +
      '<button class="card-share">📤 مشاركة</button>' +
      '<button class="card-close">إغلاق</button></div></div>';
    document.body.appendChild(ov);
    const save = function () { const a = document.createElement("a"); a.href = dataUrl; a.download = (filename || "card") + ".png"; a.click(); };
    ov.querySelector(".card-close").onclick = function () { ov.remove(); };
    ov.querySelector(".card-save").onclick = save;
    ov.querySelector(".card-share").onclick = async function () {
      try {
        const blob = await (await fetch(dataUrl)).blob();
        const file = new File([blob], (filename || "card") + ".png", { type: "image/png" });
        if (navigator.canShare && navigator.canShare({ files: [file] })) {
          await navigator.share({ files: [file], title: "رحلة الباحث" });
        } else if (window.Telegram && Telegram.WebApp && typeof Telegram.WebApp.shareToStory === "function") {
          Telegram.WebApp.shareToStory(dataUrl);
        } else { save(); }
      } catch (e) { /* user cancelled or unsupported */ }
    };
  }

  window.shortHash = shortHash;

  window.certificateCard = function (profile, report) {
    const name = (profile && profile.name) || "باحث";
    const firstTry = (report.items || []).filter(function (i) { return i.is_correct; }).length;
    const code = shortHash(name + "|capstone|" + (report.total_score || 0));
    showCard(drawCard({
      title: "شهادة إتمام رحلة البحث الكبرى",
      name: name,
      subtitle: "أتمّ مشروعًا بحثيًا كاملًا: من الفجوة حتى النشر",
      lines: [
        "النقاط: " + (report.total_score || 0),
        "الإجابات الصحيحة من أول محاولة: " + firstTry + "/" + (report.items || []).length,
      ],
      code: code, stamp: "كبير باحثي بيلتوفر 🎓",
    }), "certificate_" + code);
  };

  window.notebookCard = function (profile, dash) {
    const name = (profile && profile.name) || "باحث";
    const mastery = (dash && dash.mastery) || {};
    const mastered = Object.keys(mastery).filter(function (c) { return mastery[c] && mastery[c].level === "mastered"; }).length;
    const badges = ((dash && dash.badges) || []).length;
    const code = shortHash(name + "|nb|" + mastered + "|" + badges);
    showCard(drawCard({
      title: "دفتر مختبر الباحث",
      name: name,
      subtitle: "سجلّ إنجازك في رحلة البحث",
      lines: [
        "مفاهيم أُتقنت: " + mastered,
        "الأوسمة المكتسبة: " + badges,
      ],
      code: code, stamp: "رحلة الباحث 🔬",
    }), "notebook_" + code);
  };
})();
