import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const convertSrc = fs.readFileSync(path.join(root, "docs", "convert.js"), "utf8");

const sandbox = { console };
sandbox.globalThis = sandbox;
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(convertSrc, sandbox);
const api = sandbox.YandexConstructorGpx;
if (!api) throw new Error("convert.js did not set YandexConstructorGpx");

function load(name) {
  return JSON.parse(fs.readFileSync(path.join(root, "tests", "fixtures", name), "utf8"));
}

function check(name, jsonFile, expect) {
  const files = api.exportGpxFiles(load(jsonFile));
  if (files.length !== expect.n) {
    throw new Error(`${name}: expected ${expect.n} GPX files, got ${files.length}`);
  }
  for (let i = 0; i < expect.n; i++) {
    const file = files[i];
    if (expect.titles && file.lineTitle !== expect.titles[i]) {
      throw new Error(`${name}: line ${i} title ${file.lineTitle} != ${expect.titles[i]}`);
    }
    if (expect.trk && file.nTrk !== expect.trk[i]) {
      throw new Error(`${name}: line ${i} trkpt ${file.nTrk} != ${expect.trk[i]}`);
    }
    if (expect.wpt && file.nWpt !== expect.wpt[i]) {
      throw new Error(`${name}: line ${i} wpt ${file.nWpt} != ${expect.wpt[i]}`);
    }
    if (!file.gpx.includes("<trkpt")) throw new Error(`${name}: missing trkpt`);
  }
  console.log("ok", name, files.map((f) => f.filename).join(", "));
}

const html = `<html><script>window.x={"userMap":${fs.readFileSync(path.join(root, "tests", "fixtures", "nesvizh.json"), "utf8")}}</script></html>`;
const fromHtml = api.parseEmbeddedObject(html, "userMap");
if (!fromHtml.features) throw new Error("JS HTML scrape failed");

check("nesvizh", "nesvizh.json", { n: 1, wpt: [23], trk: [135] });
check("bison", "bison-trail.json", { n: 3, titles: ["3K", "5K", "10K"], trk: [59, 121, 195], wpt: [3, 3, 3] });
console.log("js converter ok");
