(function () {
  const K = { name: "rq_name", avatar: "rq_avatar", onboarded: "rq_onboarded" };

  function cloud() {
    const tg = window.Telegram && window.Telegram.WebApp;
    return tg && tg.CloudStorage ? tg.CloudStorage : null;
  }
  function cloudGet(keys) {
    return new Promise((resolve) => {
      const cs = cloud();
      if (!cs) return resolve(null);
      try { cs.getItems(keys, (err, res) => resolve(err ? null : res)); }
      catch (_) { resolve(null); }
    });
  }
  function cloudSet(k, v) {
    return new Promise((resolve) => {
      const cs = cloud();
      if (!cs) return resolve(false);
      try { cs.setItem(k, v, () => resolve(true)); } catch (_) { resolve(false); }
    });
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
    for (const [k, v] of pairs) {
      if (s) s.setItem(k, v);
      await cloudSet(k, v);
    }
    return true;
  }

  window.loadProfile = loadProfile;
  window.saveProfile = saveProfile;
})();
