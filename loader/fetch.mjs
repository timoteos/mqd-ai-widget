// Downloads medquest.hawaii.gov pages, file list and forms-page links to raw/site.json.
//
//   node loader/fetch.mjs
//
// The site's firewall blocks non-browser requests, so this drives headless Chrome.
// A scheduled job in AWS would need the site team to allow the loader instead.
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9333;
const here = dirname(fileURLToPath(import.meta.url));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Runs inside the page, so it shares the browser's standing with the firewall.
const inPage = async () => {
  const pause = () => new Promise((r) => setTimeout(r, 300));
  const all = async (collection, depth, keep) => {
    const out = []; let page = 1;
    while (true) {
      const res = await fetch(`/api/${collection}?limit=50&depth=${depth}&page=${page}`);
      if (!res.ok) throw new Error(`${collection} page ${page}: HTTP ${res.status}`);
      const body = await res.json();
      out.push(...body.docs.map(keep));
      if (!body.hasNextPage) return out;
      page++; await pause();
    }
  };
  const pages = await all("pages", 2, (d) => d);
  const media = await all("media", 0, (d) => ({ filename: d.filename, url: d.url, mimeType: d.mimeType, size: d.filesize,
    created: d.createdAt, updated: d.updatedAt, description: typeof d.description === "string" ? d.description : "",
    title: typeof d.alt === "string" ? d.alt : "" }));
  const linked = {};
  for (const path of ["/en/members-applicants/member-forms", "/en/plans-providers/provider-forms", "/en/resources/forms"]) {
    const html = await (await fetch(path)).text();
    // The forms pages fill in their file lists by script, so read the data, not links.
    linked[path] = [...new Set([...html.matchAll(/\/api\/media\/file\/([^"'\\ ]+)/g)].map((m) => decodeURIComponent(m[1])))]
      .map((file) => ({ file, text: "" }));
    await pause();
  }
  return { pulled: new Date().toISOString(), pages, media, linked };
};

const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${PORT}`, "--no-first-run",
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "mq-"))}`,
  "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
  "about:blank"], { stdio: "ignore" });
try {
  let targets;
  for (let i = 0; i < 40 && !targets; i++) { try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); } catch { await sleep(250); } }
  const ws = new WebSocket(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r));
  let id = 0; const waiting = new Map();
  ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); if (waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); } });
  const send = (method, params = {}) => new Promise((r) => { waiting.set(++id, r); ws.send(JSON.stringify({ id, method, params })); });

  await send("Page.enable");
  await send("Page.navigate", { url: "https://medquest.hawaii.gov/" });
  await sleep(8000);
  const res = await send("Runtime.evaluate", { expression: `(${inPage})()`, awaitPromise: true, returnByValue: true, timeout: 600000 });
  if (res.result.exceptionDetails) throw new Error(res.result.exceptionDetails.exception?.description || "page script failed");
  const site = res.result.result.value;
  mkdirSync(join(here, "raw"), { recursive: true });
  writeFileSync(join(here, "raw", "site.json"), JSON.stringify(site));
  console.log(`${site.pages.length} pages, ${site.media.length} files -> loader/raw/site.json`);
  ws.close();
} finally {
  chrome.kill();
}
