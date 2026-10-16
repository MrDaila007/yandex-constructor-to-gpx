(function () {
  const api = window.YandexConstructorGpx;
  const form = document.querySelector("#convert-form");
  const urlInput = document.querySelector("#map-url");
  const statusEl = document.querySelector("#status");
  const resultsEl = document.querySelector("#results");
  const fileInput = document.querySelector("#file");
  const drop = document.querySelector("#drop");
  const submitBtn = document.querySelector("#submit");

  const EXAMPLES = [
    {
      label: "Несвиж 2026",
      url: "https://yandex.com/maps/?um=constructor%3Afbd12684307cb322481c9e279ba4e3cd969a565ab626ec9ecb92fc2b36949e83&source=constructorLink",
    },
    {
      label: "Bison Trail",
      url: "https://yandex.com/maps/?um=constructor%3Aaf3b2c797a2526fe5b2a9971ff9e4886428b32275259e851d19a9b778c22fe48&source=constructorLink",
    },
  ];

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.className = `status ${kind || ""}`.trim();
  }

  function renderFiles(files) {
    resultsEl.innerHTML = "";
    const actions = document.createElement("div");
    actions.className = "row";
    const all = document.createElement("button");
    all.type = "button";
    all.className = "secondary";
    all.textContent = files.length > 1 ? "Скачать все GPX" : "Скачать GPX";
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
      meta.textContent = `${file.mapTitle} · ${file.nTrk} точек · ~${file.km.toFixed(2)} км · ${file.nWpt} меток`;
      info.append(heading, meta);
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
      files.length === 1
        ? `Готово: ${files[0].nTrk} точек, ${files[0].nWpt} меток`
        : `Готово: ${files.length} маршрута`,
      "ok",
    );
  }

  async function convertUrl(url) {
    submitBtn.disabled = true;
    setStatus("Качаю карту через прокси…");
    resultsEl.innerHTML = "";
    try {
      const userMap = await api.fetchUserMapHtml(url);
      convertUserMap(userMap);
    } catch (err) {
      setStatus(
        `${err.message || err}. Прокси до Яндекса с GitHub Pages часто недоступен — сохрани карту как HTML и перетащи файл, либо открой карту и нажми букмарклет.`,
        "error",
      );
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
    setStatus(`Читаю ${file.name}…`);
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
      drop.style.borderColor = "var(--accent)";
    });
  });
  ["dragleave", "drop"].forEach((name) => {
    drop.addEventListener(name, (event) => {
      event.preventDefault();
      drop.style.borderColor = "";
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
      setStatus("Перетащи кнопку «Яндекс → GPX» на панель закладок, затем открой карту Яндекса и нажми закладку.", "ok");
    });
    if (copyBtn) {
      copyBtn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(href);
          setStatus(
            "Скопировано. Создай закладку с именем «Яндекс → GPX» и вставь javascript:… в поле адреса. Потом открой карту Яндекса.",
            "ok",
          );
        } catch (_err) {
          setStatus("Не вышло скопировать. Перетащи кнопку «Яндекс → GPX» на панель закладок.", "error");
        }
      });
    }
  }

  setupBookmarklet();
})();
