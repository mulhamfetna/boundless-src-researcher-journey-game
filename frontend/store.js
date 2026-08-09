(function () {
  const K = { name: "rq_name", avatar: "rq_avatar", onboarded: "rq_onboarded" };

  function cloud() {
    const tg = window.Telegram && window.Telegram.WebApp;
    return tg && tg.CloudStorage ? tg.CloudStorage : null;
  }
  // CloudStorage is answered by the Telegram client posting an event back to us.
  // A client that accepts the request and never replies leaves the callback
  // pending forever — and because loadProfile() awaits it on its first line and
  // loadHome() awaits loadProfile(), one unanswered request deadlocked the whole
  // boot and left the player staring at an empty background with nothing to
  // report (#48). The try/catch below only ever caught the *synchronous* throw
  // from the library's version guard, which is the healthy fallback path.
  //
  // localStorage holds the same three keys, so waiting longer buys nothing:
  // every cloud call is now bounded and degrades to the local copy.
  const CLOUD_TIMEOUT_MS = 1500;
  function bounded(fallback, run) {
    return new Promise((resolve) => {
      let settled = false;
      const done = (v) => { if (!settled) { settled = true; clearTimeout(timer); resolve(v); } };
      const timer = setTimeout(() => done(fallback), CLOUD_TIMEOUT_MS);
      try { run(done); } catch (_) { done(fallback); }
    });
  }
  function cloudGet(keys) {
    const cs = cloud();
    if (!cs) return Promise.resolve(null);
    return bounded(null, (done) => cs.getItems(keys, (err, res) => done(err ? null : res)));
  }
  function cloudSet(k, v) {
    const cs = cloud();
    if (!cs) return Promise.resolve(false);
    return bounded(false, (done) => cs.setItem(k, v, () => done(true)));
  }
  function ls() { return typeof localStorage !== "undefined" ? localStorage : null; }

  async function loadProfile() {
    const res = await cloudGet([K.name, K.avatar, K.onboarded]);
    const get = (k) => {
      if (res && res[k] != null && res[k] !== "") return res[k];
      const s = ls();
      return s ? s.getItem(k) : null;
    };
    return {
      name: get(K.name) || "",
      avatar: get(K.avatar) || "🧑‍🎓",
      onboarded: (get(K.onboarded) || "") === "1",
    };
  }

  async function saveProfile(partial) {
    const pairs = [];
    if (partial.name != null) pairs.push([K.name, partial.name]);
    if (partial.avatar != null) pairs.push([K.avatar, partial.avatar]);
    if (partial.onboarded != null) pairs.push([K.onboarded, partial.onboarded ? "1" : "0"]);
    const s = ls();
    for (const [k, v] of pairs) if (s) s.setItem(k, v);
    // The local copy is written first and is authoritative, so the cloud writes
    // are pure best-effort. Run them together rather than one after another:
    // against an unresponsive client each costs the full timeout, and
    // serialising three keys left onboarding sitting on a dead button for 4.5s
    // instead of 1.5s (#48).
    await Promise.all(pairs.map(([k, v]) => cloudSet(k, v)));
    return true;
  }

  window.loadProfile = loadProfile;
  window.saveProfile = saveProfile;
})();
