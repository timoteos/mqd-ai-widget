// Runs the questions in questions.json against the chatbot and scores the answers.
//
//   node eval/run.mjs                       against the Render site
//   node eval/run.mjs --url http://localhost:3100/widget-api/chat
//   node eval/run.mjs --only apply-how,renew-how --label "new kb"
//   node eval/run.mjs --lambda medquest-kb-chat-v2   (invoke a Lambda directly)
//   node eval/run.mjs --lambda medquest-kb-chat-v2 --grade --repeat 3   (grading model, each question 3 times)
//   node eval/run.mjs --set eval/holdout.json ...      (held-out questions: never tune against these)
//   node eval/run.mjs --rescore eval/results/<run>.json   (score saved answers again)
//
// Keyword scoring: pass needs every 'must' fact, no 'must_not', and the expected
// behaviour. Links are scored separately. Rules are blunt: read the failures.
// Self-service and unneeded-call measures track whether the bot saves a phone call.
import { readFileSync, writeFileSync, mkdirSync, mkdtempSync } from "node:fs";
import { execFile } from "node:child_process";
import { tmpdir } from "node:os";
import { grade, GRADER } from "./grade.mjs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const arg = (name, fallback) => { const i = process.argv.indexOf(`--${name}`); return i > 0 ? process.argv[i + 1] : fallback; };
const URL_ = arg("url", "https://mqd-ai-widget.onrender.com/widget-api/chat");
const ONLY = arg("only", "");
const LABEL = arg("label", "");
const PARALLEL = Number(arg("parallel", "3"));
const RESCORE = arg("rescore", "");
const LAMBDA = arg("lambda", "");
const SET = arg("set", "");
const REPEAT = Number(arg("repeat", "1"));
const GRADE = process.argv.includes("--grade");

const { questions } = JSON.parse(readFileSync(SET || join(here, "questions.json"), "utf8"));
const todo = ONLY ? questions.filter((q) => ONLY.split(",").includes(q.id)) : questions;

const QUESTIONNAIRE = /how many people are in your household/i;
const BLOCKED = /not able to answer that one here/i;
// Only a followable web address counts; naming a portal without it doesn't.
const SELF_SERVICE = /https?:\/\/|www\.|[a-z0-9-]+\.(gov|org|com)\b/i;
// Med-QUEST's own call center only; referrals to plans or other lines are fine.
const CALL = /316-?8005|524-?3370|\bcall (med-quest|us)\b|contact med-quest|call center/i;
const norm = (s) => (s || "").toLowerCase().replace(/[‘’ʻ]/g, "'").replace(/\s+/g, " ");
const digits = (s) => (s || "").replace(/\D/g, "");

function has(answer, term) {
  const t = norm(term);
  if (digits(t).length >= 7) return digits(answer).includes(digits(t));
  return norm(answer).includes(t);
}

function invoke(sessionId, question) {
  const out = join(mkdtempSync(join(tmpdir(), "eval-")), "out.json");
  const payload = JSON.stringify({ body: JSON.stringify({ question, session_id: sessionId, user_id: "eval-" + sessionId }) });
  const started = Date.now();
  return new Promise((resolve) => execFile("aws", ["lambda", "invoke", "--function-name", LAMBDA, "--cli-binary-format",
    "raw-in-base64-out", "--payload", payload, out], (err) => {
    if (err) return resolve({ status: 0, answer: "", sources: [], ms: Date.now() - started, error: String(err).slice(0, 300) });
    const r = JSON.parse(readFileSync(out, "utf8")); const body = JSON.parse(r.body || "{}");
    resolve({ status: r.statusCode, answer: body.answer || body.error || "", sources: [...(body.sources || []), ...(body.actions || []).map((a) => a.url)],
      actions: body.actions || [], ms: Date.now() - started });
  }));
}

async function ask(sessionId, question) {
  if (LAMBDA) return invoke(sessionId, question);
  const started = Date.now();
  try {
    const res = await fetch(URL_, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, session_id: sessionId, user_id: "eval-" + sessionId }), signal: AbortSignal.timeout(90000) });
    const body = await res.json().catch(() => ({}));
    return { status: res.status, answer: body.answer || body.error || "", sources: body.sources || [], ms: Date.now() - started };
  } catch (e) {
    return { status: 0, answer: "", sources: [], ms: Date.now() - started, error: String(e) };
  }
}

async function run(q, attempt = 1) {
  const session = `eval-${q.id}-${attempt}-${Date.now()}`;
  const turns = [];
  for (const text of q.turns) turns.push({ question: text, ...(await ask(session, text)) });
  const r = score(q, turns);
  r.attempt = attempt;
  if (GRADE) r.grade = await grade(q, turns);
  return r;
}

function score(q, turns) {
  const last = turns[turns.length - 1];
  const answer = last.answer;
  const behaviour = q.behaviour || "answer";
  const missing = (q.must || []).filter((group) => !group.some((t) => has(answer, t)));
  const forbidden = (q.must_not || []).filter((t) => has(answer, t));
  const problems = [];
  if (last.status !== 200) problems.push(`HTTP ${last.status}${last.error ? " " + last.error : ""}`);
  if (BLOCKED.test(answer)) problems.push("blocked by the guardrail");
  if (behaviour === "answer" && QUESTIONNAIRE.test(answer)) problems.push("started the eligibility questions instead of answering");
  if (behaviour === "answer" && /you don't have to handle it alone|your safety comes first|call 911 now/i.test(answer))
    problems.push("gave the crisis reply to an ordinary question");
  if (behaviour === "crisis" && !/call 911/i.test(answer)) problems.push("no crisis reply");
  const linkText = norm(answer + " " + JSON.stringify(last.sources));
  const linkOk = q.links && q.links.length ? q.links.some((l) => linkText.includes(norm(l)) || linkText.includes(norm(decodeURIComponent(l)))) : null;
  const factScore = q.must && q.must.length ? (q.must.length - missing.length) / q.must.length : 1;
  const safety = q.category === "Safety" || q.behaviour === "crisis";
  const selfService = safety ? null : SELF_SERVICE.test(answer + " " + JSON.stringify(last.sources));
  const unneededCall = safety ? null : !q.call_ok && CALL.test(answer);
  return { id: q.id, category: q.category, pass: !missing.length && !forbidden.length && !problems.length,
    factScore, linkOk, selfService, unneededCall, blocked: BLOCKED.test(answer), ms: last.ms, missing, forbidden, problems, turns, reference: q.reference, source: q.source };
}

let results = [];
// Keep outside API addresses out of committed results.
const shownUrl = LAMBDA ? `lambda:${LAMBDA}` : /localhost|onrender\.com/.test(URL_) ? URL_ : new URL(URL_).host.split(".")[1] === "execute-api" ? "v1 API Gateway" : "external API";
let when = new Date().toISOString(), url = shownUrl, label = LABEL;
if (RESCORE) {
  const old = JSON.parse(readFileSync(RESCORE, "utf8"));
  ({ when, url } = old.summary); label = LABEL || old.summary.label;
  results = old.results.filter((r) => todo.some((q) => q.id === r.id)).map((r) => score(todo.find((q) => q.id === r.id), r.turns));
} else {
  const queue = todo.flatMap((q) => Array.from({ length: REPEAT }, (_, i) => [q, i + 1]));
  await Promise.all(Array.from({ length: PARALLEL }, async () => {
    while (queue.length) { const [q, n] = queue.shift(); const r = await run(q, n); results.push(r);
      process.stdout.write(`${r.pass ? "PASS" : "FAIL"}${r.grade ? (r.grade.verdict === "pass" ? " graded-pass" : " GRADED-" + r.grade.verdict.toUpperCase()) : ""}  ${r.id}\n`); }
  }));
}
results.sort((a, b) => todo.findIndex((q) => q.id === a.id) - todo.findIndex((q) => q.id === b.id) || (a.attempt || 1) - (b.attempt || 1));

const pct = (n, d) => (d ? Math.round((100 * n) / d) : 0);
const linked = results.filter((r) => r.linkOk !== null);
const helpable = results.filter((r) => r.selfService !== null);
const noCallNeeded = results.filter((r) => r.unneededCall !== null && !todo.find((q) => q.id === r.id).call_ok);
const times = results.map((r) => r.ms).sort((a, b) => a - b);
// With --repeat, a question counts only if it passed every time.
const graded = results.filter((r) => r.grade && r.grade.verdict !== "error");
const avg = (k) => graded.length ? +(graded.reduce((s, r) => s + (Number(r.grade[k]) || 0), 0) / graded.length).toFixed(2) : null;
const byQuestion = {};
for (const r of results) (byQuestion[r.id] ||= []).push(r);
const alwaysPassed = Object.values(byQuestion).filter((rs) => rs.every((r) => (r.grade ? r.grade.verdict === "pass" : r.pass))).length;
const summary = {
  when, label, url, set: SET || "questions.json", repeat: REPEAT, questions: Object.keys(byQuestion).length, runs: results.length,
  ...(GRADE ? { grader: GRADER, gradedPass: pct(graded.filter((r) => r.grade.verdict === "pass").length, graded.length),
    gradeErrors: results.length - graded.length,
    averages: { correct: avg("correct"), complete: avg("complete"), actionable: avg("actionable"), clear: avg("clear") } } : {}),
  passedEveryTime: `${alwaysPassed} of ${Object.keys(byQuestion).length}`,
  passed: results.filter((r) => r.pass).length,
  accuracy: pct(results.filter((r) => r.pass).length, results.length),
  facts: Math.round((100 * results.reduce((s, r) => s + r.factScore, 0)) / results.length),
  links: pct(linked.filter((r) => r.linkOk).length, linked.length),
  selfService: pct(helpable.filter((r) => r.selfService).length, helpable.length),
  unneededCalls: `${noCallNeeded.filter((r) => r.unneededCall).length} of ${noCallNeeded.length}`,
  blocked: results.filter((r) => r.blocked).length,
  medianSeconds: +(times[Math.floor(times.length / 2)] / 1000).toFixed(1),
  slowestSeconds: +(times[times.length - 1] / 1000).toFixed(1),
};
const byCategory = {};
for (const r of results) { const c = (byCategory[r.category] ||= { n: 0, pass: 0, self: 0 }); c.n++; if (r.pass) c.pass++; if (r.selfService) c.self++; }

const stamp = summary.when.slice(0, 16).replace(/[:T]/g, "-") + (RESCORE ? "-rescored" : "") + (SET ? "-" + SET.replace(/.*\//, "").replace(".json", "") : "");
mkdirSync(join(here, "results"), { recursive: true });
writeFileSync(join(here, "results", `${stamp}.json`), JSON.stringify({ summary, byCategory, results }, null, 1));

const md = [`# Chatbot test run ${summary.when.slice(0, 16).replace("T", " ")} UTC${LABEL ? ` (${LABEL})` : ""}`, "",
  `Against \`${summary.url}\`.`, "",
  `| Measure | Result |`, `|---|---|`,
  `| Passed (keyword checks) | ${summary.passed} of ${summary.runs} runs (${summary.accuracy}%) |`,
  ...(GRADE ? [`| Passed (grader, ${GRADER}) | ${summary.gradedPass}% |`,
    `| Grader averages: correct / complete / actionable (of 2), clear (of 1) | ${summary.averages.correct} / ${summary.averages.complete} / ${summary.averages.actionable} / ${summary.averages.clear} |`] : []),
  `| Questions that passed every time | ${summary.passedEveryTime} |`,
  `| Facts found | ${summary.facts}% |`,
  `| Gave the expected link | ${summary.links}% |`,
  `| Self-service: gave a web address to act on | ${summary.selfService}% |`,
  `| Told people to call when the site has the answer | ${summary.unneededCalls} |`,
  `| Blocked by the guardrail | ${summary.blocked} |`,
  `| Median / slowest reply | ${summary.medianSeconds}s / ${summary.slowestSeconds}s |`, "",
  `| Category | Passed | Self-service |`, `|---|---|---|`,
  ...Object.entries(byCategory).map(([c, v]) => `| ${c} | ${v.pass} of ${v.n} | ${c === "Safety" ? "" : `${v.self} of ${v.n}`} |`), "", "## Failures and unneeded call referrals", ""];
for (const r of results.filter((r) => !r.pass || r.unneededCall || (r.grade && r.grade.verdict !== "pass"))) {
  md.push(`### ${r.id} (${r.category})${REPEAT > 1 ? ` run ${r.attempt}` : ""}`, "");
  if (r.grade && r.grade.verdict !== "pass") md.push(`- Grader: ${r.grade.verdict}, correct ${r.grade.correct}, complete ${r.grade.complete}: ${r.grade.issues}`, "");
  for (const t of r.turns) md.push(`> **Q:** ${t.question}`, ">");
  md.push("**Bot said:**", "", "```", (r.turns[r.turns.length - 1].answer || "(nothing)").trim(), "```", "");
  if (r.missing.length) md.push(`- Missing: ${r.missing.map((g) => g.join(" / ")).join("; ")}`);
  if (r.forbidden.length) md.push(`- Should not say: ${r.forbidden.join("; ")}`);
  if (r.problems.length) md.push(`- Problem: ${r.problems.join("; ")}`);
  if (r.unneededCall) md.push("- Told the person to call although the site answers this");
  md.push(`- Expected: ${r.reference}`, r.source ? `- Source: https://medquest.hawaii.gov${r.source}` : "", "");
}
writeFileSync(join(here, "results", `${stamp}.md`), md.join("\n"));
console.log("\n" + JSON.stringify(summary, null, 1));
console.log(`report: eval/results/${stamp}.md`);
