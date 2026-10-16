(function () {
  const api = window.YandexConstructorGpx;
  if (!api) {
    alert("Сначала загрузи convert.js с GitHub Pages");
    return;
  }
  try {
    const html = document.documentElement.outerHTML;
    const userMap = api.parseEmbeddedObject(html, "userMap");
    const files = api.exportGpxFiles(userMap);
    api.downloadGpxFiles(files);
    alert(`GPX: ${files.map((f) => f.filename).join(", ")}`);
  } catch (err) {
    alert(err.message || String(err));
  }
})();
