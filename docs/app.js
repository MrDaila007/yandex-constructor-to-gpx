(function () {
  const api = window.YandexConstructorGpx;
  const form = document.querySelector("#convert-form");
  const urlInput = document.querySelector("#map-url");
  const statusEl = document.querySelector("#status");
  const resultsEl = document.querySelector("#results");
  const fileInput = document.querySelector("#file");
  const drop = document.querySelector("#drop");
  const submitBtn = document.querySelector("#submit");

  const I18N = {
    en: {
      title: "Yandex Constructor → GPX",
      kicker: "Trail export",
      titleLine: "Yandex Constructor",
      convertTitle: "From a map link",
      badgeBest: "Most reliable",
      start: "Start",
      finish: "Finish",
      lead: "Export a public Constructor map to GPX: track and waypoints. Several lines on the map become several files.",
      howtoTitle: "Save the bookmarklet",
      howtoDragBefore: "Drag",
      bookmarkName: "Yandex → GPX",
      howtoDragAfter: "onto the bookmarks bar. The bookmark name will be “Yandex → GPX”.",
      howtoThen:
        "Then open the map on Yandex and click that bookmark — GPX files download. The button does not export while you stay on this site (Yandex CSP blocks our scripts, so the converter lives inside the bookmark).",
      howtoCopyBefore: "If the browser will not drag:",
      copyJs: "copy javascript:",
      howtoCopyAfter: "create a bookmark by hand and paste into the URL field.",
      urlLabel: "Map link",
      download: "Download GPX",
      downloadAll: "Download all GPX",
      drop: "Or drop a saved map HTML/JSON file.",
      foot: "Static page; URL import goes through a CORS proxy to Yandex.",
      dragHint: "Drag the “Yandex → GPX” button onto the bookmarks bar, then open the Yandex map and click the bookmark.",
      copied:
        "Copied. Create a bookmark named “Yandex → GPX” and paste javascript:… into the URL field. Then open the Yandex map.",
      copyFail: "Could not copy. Drag the “Yandex → GPX” button onto the bookmarks bar.",
      fetching: "Fetching the map through a proxy…",
      fetchFail:
        "A CORS proxy to Yandex often fails from GitHub Pages — save the map as HTML and drop the file, or open the map and use the bookmarklet.",
      reading: (name) => `Reading ${name}…`,
      doneOne: (pts, wpts) => `Done: ${pts} points, ${wpts} waypoints`,
      doneMany: (n) => `Done: ${n} routes`,
      meta: (title, pts, km, wpts) => `${title} · ${pts} points · ~${km.toFixed(2)} km · ${wpts} waypoints`,
      desc: "Export a public Yandex Map Constructor map to GPX: track and waypoints. Several distances become several files.",
    },
    ru: {
      title: "Яндекс Конструктор → GPX",
      kicker: "Экспорт трассы",
      titleLine: "Яндекс Конструктор",
      convertTitle: "По ссылке на карту",
      badgeBest: "Надёжнее всего",
      start: "Старт",
      finish: "Финиш",
      lead: "Экспорт публичной карты конструктора в GPX: трек и метки. Несколько линий на карте — несколько файлов.",
      howtoTitle: "Как сохранить букмарклет",
      howtoDragBefore: "Перетащи",
      bookmarkName: "Яндекс → GPX",
      howtoDragAfter: "на панель закладок. Имя закладки будет «Яндекс → GPX».",
      howtoThen:
        "Затем открой карту в Яндексе и нажми эту закладку — скачаются GPX. На этой странице кнопка карту не экспортирует (CSP Яндекса не даёт подгружать наш скрипт, поэтому код лежит внутри закладки).",
      howtoCopyBefore: "Если браузер не даёт перетащить:",
      copyJs: "скопировать javascript:",
      howtoCopyAfter: "создай закладку вручную и вставь это в поле адреса.",
      urlLabel: "Ссылка на карту",
      download: "Скачать GPX",
      downloadAll: "Скачать все GPX",
      drop: "Или перетащи сохранённый HTML/JSON карты.",
      foot: "Страница статическая; импорт по ссылке идёт через CORS-прокси к Яндексу.",
      dragHint: "Перетащи кнопку «Яндекс → GPX» на панель закладок, затем открой карту Яндекса и нажми закладку.",
      copied:
        "Скопировано. Создай закладку с именем «Яндекс → GPX» и вставь javascript:… в поле адреса. Потом открой карту Яндекса.",
      copyFail: "Не вышло скопировать. Перетащи кнопку «Яндекс → GPX» на панель закладок.",
      fetching: "Качаю карту через прокси…",
      fetchFail:
        "Прокси до Яндекса с GitHub Pages часто недоступен — сохрани карту как HTML и перетащи файл, либо открой карту и нажми букмарклет.",
      reading: (name) => `Читаю ${name}…`,
      doneOne: (pts, wpts) => `Готово: ${pts} точек, ${wpts} меток`,
      doneMany: (n) => `Готово: ${n} маршрута`,
      meta: (title, pts, km, wpts) => `${title} · ${pts} точек · ~${km.toFixed(2)} км · ${wpts} меток`,
      desc: "Экспорт публичной карты Яндекс Конструктора в GPX: трек и метки. Несколько дистанций — несколько файлов.",
    },
  };

  const EXAMPLES = [
    {
      label: "Nesvizh 2026",
      url: "https://yandex.com/maps/?um=constructor%3Afbd12684307cb322481c9e279ba4e3cd969a565ab626ec9ecb92fc2b36949e83&source=constructorLink",
    },
    {
      label: "Bison Trail",
      url: "https://yandex.com/maps/?um=constructor%3Aaf3b2c797a2526fe5b2a9971ff9e4886428b32275259e851d19a9b778c22fe48&source=constructorLink",
    },
  ];

  let lang = "en";
  let lastFiles = null;

  function t(key) {
    return I18N[lang][key] || I18N.en[key];
  }

  function detectLang() {
    const q = new URLSearchParams(window.location.search).get("lang");
    if (q === "ru" || q === "en") return q;
    try {
      const saved = localStorage.getItem("ycg-lang");
      if (saved === "ru" || saved === "en") return saved;
    } catch (_err) {
      /* ignore */
    }
    const nav = (navigator.language || "en").toLowerCase();
    return nav.startsWith("ru") ? "ru" : "en";
  }

  function applyLang(next) {
    lang = next === "ru" ? "ru" : "en";
    try {
      localStorage.setItem("ycg-lang", lang);
    } catch (_err) {
      /* ignore */
    }
    const url = new URL(window.location.href);
    url.searchParams.set("lang", lang);
    history.replaceState({}, "", url);
    document.documentElement.lang = lang;
    document.title = t("title");
    const desc = document.querySelector('meta[name="description"]');
    if (desc) desc.setAttribute("content", t("desc"));
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      const value = t(key);
      if (typeof value !== "string") return;
      if (el.hasAttribute("data-i18n-attr")) {
        el.setAttribute(el.getAttribute("data-i18n-attr"), value);
      }
      el.textContent = value;
    });
    document.querySelectorAll(".lang [data-lang]").forEach((btn) => {
      btn.classList.toggle("is-active", btn.getAttribute("data-lang") === lang);
    });
    if (lastFiles) renderFiles(lastFiles);
  }

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.className = `status ${kind || ""}`.trim();
  }

  function renderFiles(files) {
    lastFiles = files;
    resultsEl.innerHTML = "";
    const actions = document.createElement("div");
    actions.className = "row";
    const all = document.createElement("button");
    all.type = "button";
    all.className = "secondary";
    all.textContent = files.length > 1 ? t("downloadAll") : t("download");
    all.addEventListener("click", () => api.downloadGpxFiles(files));
    actions.append(all);
    resultsEl.append(actions);

    files.forEach((file) => {
      const card = document.createElement("article");
      card.className = "card result";
      const info = document.createElement("div");
      const heading = document.createElement("h2");
      heading.textContent = file.lineTitle;
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = t("meta")(file.mapTitle, file.nTrk, file.km, file.nWpt);
      const km = document.createElement("div");
      km.className = "km";
      km.textContent = `~${file.km.toFixed(2)} ${lang === "ru" ? "км" : "km"}`;
      info.append(heading, meta, km);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = file.filename;
      btn.addEventListener("click", () => api.downloadGpxFiles([file]));
      card.append(info, btn);
      resultsEl.append(card);
    });
  }

  function convertUserMap(userMap) {
    const files = api.exportGpxFiles(userMap);
    renderFiles(files);
    setStatus(
      files.length === 1 ? t("doneOne")(files[0].nTrk, files[0].nWpt) : t("doneMany")(files.length),
      "ok",
    );
  }

  async function convertUrl(url) {
    submitBtn.disabled = true;
    setStatus(t("fetching"));
    resultsEl.innerHTML = "";
    lastFiles = null;
    try {
      const userMap = await api.fetchUserMapHtml(url);
      convertUserMap(userMap);
    } catch (err) {
      setStatus(`${err.message || err}. ${t("fetchFail")}`, "error");
    } finally {
      submitBtn.disabled = false;
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    convertUrl(urlInput.value);
  });

  document.querySelector("#examples").innerHTML = EXAMPLES.map(
    (ex) => `<button type="button" class="chip" data-url="${ex.url}">${ex.label}</button>`,
  ).join("");

  document.querySelector("#examples").addEventListener("click", (event) => {
    const btn = event.target.closest("[data-url]");
    if (!btn) return;
    urlInput.value = btn.dataset.url;
    convertUrl(btn.dataset.url);
  });

  async function fromFile(file) {
    setStatus(t("reading")(file.name));
    try {
      const text = await file.text();
      convertUserMap(api.parseInputText(text));
    } catch (err) {
      setStatus(err.message || String(err), "error");
    }
  }

  fileInput.addEventListener("change", () => {
    const file = fileInput.files && fileInput.files[0];
    if (file) fromFile(file);
  });

  ["dragenter", "dragover"].forEach((name) => {
    drop.addEventListener(name, (event) => {
      event.preventDefault();
      drop.classList.add("is-over");
    });
  });
  ["dragleave", "drop"].forEach((name) => {
    drop.addEventListener(name, (event) => {
      event.preventDefault();
      drop.classList.remove("is-over");
    });
  });
  drop.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files && event.dataTransfer.files[0];
    if (file) fromFile(file);
  });

  function setupBookmarklet() {
    const a = document.getElementById("bookmarklet");
    const src = document.getElementById("bookmarklet-src");
    const copyBtn = document.getElementById("copy-bookmarklet");
    if (!a || !src) return;
    const href = src.textContent.trim();
    a.setAttribute("href", href);
    a.addEventListener("click", (event) => {
      event.preventDefault();
      setStatus(t("dragHint"), "ok");
    });
    if (copyBtn) {
      copyBtn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(href);
          setStatus(t("copied"), "ok");
        } catch (_err) {
          setStatus(t("copyFail"), "error");
        }
      });
    }
  }

  document.querySelector(".lang").addEventListener("click", (event) => {
    const btn = event.target.closest("[data-lang]");
    if (btn) applyLang(btn.getAttribute("data-lang"));
  });

  setupBookmarklet();
  applyLang(detectLang());
})();
