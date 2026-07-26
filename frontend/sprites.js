(function () {
  // Arcane palette
  const I = "#04020a", GOLD = "#c8aa6e", GOLDH = "#e2c687", CY = "#0ac8b9",
        SH = "#ff2e97", AC = "#2fe6a0", VI = "#8a3bff", IV = "#f0e6d2",
        BR = "#9b6b3a", STL = "#7b8aa6", PNK = "#ff8fc7";
  function svg(body) {
    return `<svg viewBox="0 0 16 16" class="sprite" shape-rendering="crispEdges" xmlns="http://www.w3.org/2000/svg">${body}</svg>`;
  }
  const r = (x, y, w, h, f) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${f}"/>`;
  const c = (cx, cy, rr, f) => `<circle cx="${cx}" cy="${cy}" r="${rr}" fill="${f}"/>`;
  const SP = {
    // The Tinkerer — goggled inventor-mentor (brass + gold)
    tinkerer: svg(r(4,3,8,5,IV) + c(6,5,1.1,CY) + c(10,5,1.1,CY) + r(5,4,1,1,I) + r(10,4,1,1,I) + r(4,2,8,1,BR) + r(6,8,4,5,GOLD) + r(5,9,1,3,BR) + r(10,9,1,3,BR)),
    // The Brawler — gauntlets + pink hair-flash
    brawler: svg(r(5,3,6,4,PNK) + r(4,7,8,5,SH) + r(3,8,2,3,GOLD) + r(11,8,2,3,GOLD) + r(6,5,1,1,I) + r(9,5,1,1,I) + r(6,12,4,2,STL)),
    // The Sniper — top-hat + monocle, Piltover blue/gold
    sniper: svg(r(4,1,8,2,I) + r(3,3,10,1,I) + r(5,4,6,5,IV) + c(10,6,1.4,CY) + r(6,6,1,1,I) + r(6,9,4,5,STL) + r(7,10,2,3,GOLD)),
    // The Alchemist — hood + acid vials (Zaun green)
    alchemist: svg(r(5,2,6,5,VI) + r(4,3,8,2,VI) + c(7,5,0.9,AC) + c(9,5,0.9,AC) + r(6,7,4,6,I) + r(7,8,2,4,AC)),
    // The Enforcer — helmet + gold trim
    enforcer: svg(r(4,3,8,5,STL) + r(4,3,8,1,GOLD) + r(6,6,4,1,CY) + r(5,8,6,5,STL) + r(7,9,2,3,GOLD)),
    // The Gremlin — chaos boss, magenta sparks
    gremlin: svg(r(5,4,6,5,SH) + r(4,2,2,2,VI) + r(10,2,2,2,VI) + r(6,6,1,1,I) + r(9,6,1,1,I) + r(6,9,4,1,GOLDH) + r(4,11,8,2,SH) + r(3,12,1,1,AC) + r(12,12,1,1,AC)),
    // stage icons
    book: svg(r(3,3,5,10,SH) + r(8,3,5,10,CY) + r(7,3,2,10,I) + r(4,5,3,1,IV) + r(9,5,3,1,IV)),
    puzzle: svg(r(3,3,6,6,CY) + r(8,7,5,6,GOLD) + r(9,5,2,2,GOLD) + r(6,8,2,2,CY)),
    doc: svg(r(4,2,8,12,IV) + r(5,4,6,1,I) + r(5,6,6,1,I) + r(5,8,6,1,I) + r(5,10,4,1,I) + r(10,2,2,2,GOLD)),
    magnifier: svg(r(4,3,6,6,IV) + r(5,4,4,4,CY) + r(3,3,7,1,I) + r(3,9,7,1,I) + r(3,4,1,5,I) + r(9,4,1,5,I) + r(10,10,3,3,GOLD)),
    checklist: svg(r(3,2,10,12,IV) + r(3,2,10,1,GOLD) + r(4,5,2,2,CY) + r(7,5,5,1,I) + r(4,8,2,2,CY) + r(7,8,5,1,I) + r(4,11,2,2,CY) + r(7,11,5,1,I)),
    send: svg(r(7,4,2,9,CY) + r(7,2,2,1,GOLDH) + r(5,5,2,2,CY) + r(9,5,2,2,CY) + r(3,7,2,2,CY) + r(11,7,2,2,CY) + r(4,13,8,1,GOLD)),
    // misc / badges
    crown: svg(r(3,8,10,4,GOLD) + r(3,4,2,4,GOLD) + r(7,4,2,4,GOLD) + r(11,4,2,4,GOLD) + r(3,4,2,2,CY) + r(11,4,2,2,CY) + r(7,4,2,2,CY)),
    star: svg(r(7,2,2,12,GOLD) + r(2,7,12,2,GOLD) + r(4,4,8,8,GOLD) + r(6,6,4,4,IV)),
    check: svg(r(11,4,2,2,CY) + r(9,6,2,2,CY) + r(7,8,2,2,CY) + r(5,7,2,2,CY) + r(3,6,2,2,CY) + r(5,9,2,2,CY)),
    flag: svg(r(4,2,1,12,I) + r(5,3,7,5,SH) + r(5,3,7,1,I) + r(11,3,1,5,I)),
    perfect_quiz: svg(r(5,2,6,6,GOLD) + r(6,3,4,4,IV) + r(5,8,2,5,SH) + r(9,8,2,5,SH) + r(6,13,4,1,I)),
    self_reliant: svg(r(4,2,8,3,CY) + r(3,4,10,5,CY) + r(5,9,6,4,CY) + r(7,5,2,5,IV)),
    streak_master: svg(r(7,2,2,2,GOLD) + r(6,4,4,3,SH) + r(5,7,6,4,SH) + r(6,11,4,2,GOLD) + r(7,5,2,5,GOLD)),
    first_finish: svg(r(7,2,2,12,GOLD) + r(2,7,12,2,GOLD) + r(4,4,8,8,GOLD)),
    bug: svg(r(6,2,4,3,SH) + r(4,5,8,6,SH) + r(5,11,6,2,SH) + r(6,6,1,1,I) + r(9,6,1,1,I) + r(3,6,2,1,I) + r(11,6,2,1,I) + r(3,9,2,1,I) + r(11,9,2,1,I) + r(7,5,2,7,I)),
  };
  SP.mentor = SP.tinkerer;
  SP.boss = SP.gremlin;
  function sprite(name) { return SP[name] || SP.tinkerer; }
  window.sprite = sprite;
  window.AVATAR_SPRITES = ["tinkerer", "brawler", "sniper", "alchemist", "enforcer", "gremlin"];
  // Painterly champion portraits (relay-generated) — used when art exists, else the SVG above.
  window.AVATAR_ART = {
    tinkerer: "champ_tinkerer.png", brawler: "champ_brawler.png", sniper: "champ_sniper.png",
    gremlin: "champ_gremlin.png", alchemist: "champ_alchemist.png",
  };
  window.champArt = function (id) {
    return AVATAR_ART[id] ? '<img class="champ-art" src="/content/assets/art/' + AVATAR_ART[id] + '" alt="" />' : null;
  };
  window.STAGE_SPRITES = { foundations: "book", "paper-parts": "puzzle", "paper-types": "doc", journals: "magnifier", publishing: "checklist", submission: "send" };
  window.BADGE_SPRITES = { perfect_quiz: "perfect_quiz", self_reliant: "self_reliant", streak_master: "streak_master", first_finish: "first_finish" };
})();
