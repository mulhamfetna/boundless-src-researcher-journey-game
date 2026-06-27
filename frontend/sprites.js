(function () {
  const I = "#06101f", P = "#ff5277", G = "#ffd23f", T = "#2ec4b6", W = "#eaf2ff", S = "#9fb3d6", B = "#7c5cff", BR = "#b5651d";
  function svg(body) {
    return `<svg viewBox="0 0 16 16" class="sprite" shape-rendering="crispEdges" xmlns="http://www.w3.org/2000/svg">${body}</svg>`;
  }
  const r = (x, y, w, h, f) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${f}"/>`;
  const SP = {
    scholar: svg(r(4,2,8,2,I) + r(3,3,10,1,I) + r(5,4,6,5,G) + r(6,9,4,4,T) + r(5,13,6,1,I)),
    scientist: svg(r(5,3,6,5,W) + r(6,2,4,1,I) + r(6,8,4,5,T) + r(5,9,1,3,W) + r(10,9,1,3,W)),
    coder: svg(r(4,3,8,5,S) + r(5,8,6,5,B) + r(6,5,1,1,I) + r(9,5,1,1,I) + r(5,11,6,1,W)),
    owl: svg(r(4,3,8,8,BR) + r(5,5,2,2,W) + r(9,5,2,2,W) + r(6,6,1,1,I) + r(10,6,1,1,I) + r(7,7,2,2,G) + r(5,11,6,2,BR) + r(6,2,1,1,BR) + r(9,2,1,1,BR)),
    fox: svg(r(4,5,8,6,P) + r(3,3,3,3,P) + r(10,3,3,3,P) + r(6,7,1,1,I) + r(9,7,1,1,I) + r(7,9,2,1,I) + r(6,5,4,2,W)),
    cat: svg(r(4,5,8,6,S) + r(4,3,2,3,S) + r(10,3,2,3,S) + r(6,7,1,1,I) + r(9,7,1,1,I) + r(7,9,2,1,P)),
    book: svg(r(3,3,5,10,P) + r(8,3,5,10,T) + r(7,3,2,10,I) + r(4,5,3,1,W) + r(9,5,3,1,W)),
    puzzle: svg(r(3,3,6,6,T) + r(8,7,5,6,G) + r(9,5,2,2,G) + r(6,8,2,2,T)),
    doc: svg(r(4,2,8,12,W) + r(5,4,6,1,I) + r(5,6,6,1,I) + r(5,8,6,1,I) + r(5,10,4,1,I) + r(10,2,2,2,S)),
    magnifier: svg(r(4,3,6,6,W) + r(5,4,4,4,T) + r(3,3,7,1,I) + r(3,9,7,1,I) + r(3,4,1,5,I) + r(9,4,1,5,I) + r(10,10,3,3,I)),
    crown: svg(r(3,8,10,4,G) + r(3,4,2,4,G) + r(7,4,2,4,G) + r(11,4,2,4,G) + r(3,4,2,2,P) + r(11,4,2,2,P) + r(7,4,2,2,P)),
    star: svg(r(7,2,2,12,G) + r(2,7,12,2,G) + r(4,4,8,8,G) + r(6,6,4,4,W)),
    check: svg(r(11,4,2,2,T) + r(9,6,2,2,T) + r(7,8,2,2,T) + r(5,7,2,2,T) + r(3,6,2,2,T) + r(5,9,2,2,T)),
    flag: svg(r(4,2,1,12,I) + r(5,3,7,5,P) + r(5,3,7,1,I) + r(11,3,1,5,I)),
    perfect_quiz: svg(r(5,2,6,6,G) + r(6,3,4,4,W) + r(5,8,2,5,P) + r(9,8,2,5,P) + r(6,13,4,1,I)),
    self_reliant: svg(r(4,2,8,3,T) + r(3,4,10,5,T) + r(5,9,6,4,T) + r(7,5,2,5,W)),
    streak_master: svg(r(7,2,2,2,G) + r(6,4,4,3,P) + r(5,7,6,4,P) + r(6,11,4,2,G) + r(7,5,2,5,G)),
    first_finish: svg(r(7,2,2,12,G) + r(2,7,12,2,G) + r(4,4,8,8,G)),
  };
  function sprite(name) { return SP[name] || SP.scholar; }
  window.sprite = sprite;
  window.AVATAR_SPRITES = ["scholar", "scientist", "coder", "owl", "fox", "cat"];
  window.STAGE_SPRITES = { foundations: "book", "paper-parts": "puzzle", "paper-types": "doc", journals: "magnifier" };
  window.BADGE_SPRITES = { perfect_quiz: "perfect_quiz", self_reliant: "self_reliant", streak_master: "streak_master", first_finish: "first_finish" };
})();
