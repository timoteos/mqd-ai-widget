"""Side-by-side metrics for two labelled, graded test runs.

    python3 eval/compare-bots.py "<label A>" "<label B>"
"""
import glob, json, re, statistics, sys
from collections import defaultdict

DONT_KNOW = re.compile(r"I don'?t have (that information|details)|I'm not sure I have that right", re.I)
CALL_ONLY = re.compile(r"^[^\[]{0,400}(call|contact) med-quest[^\[]*$", re.I | re.S)


def load(prefix):
    runs = [json.load(open(f)) for f in sorted(glob.glob("eval/results/*.json")) if "rescored" not in f]
    return {("held-out" if "holdout" in r["summary"].get("set", "") else "main"): r
            for r in runs if r["summary"].get("label", "").startswith(prefix)}


def metrics(run):
    rs = run["results"]
    graded = [r for r in rs if r.get("grade") and r["grade"].get("verdict") in ("pass", "fail")]
    by_q = defaultdict(list)
    for r in rs: by_q[r["id"]].append(r)
    gpass = lambda r: r.get("grade", {}).get("verdict") == "pass"
    ms = sorted(r["ms"] for r in rs)
    cats = defaultdict(lambda: [0, 0])
    for r in graded:
        cats[r["category"]][0] += gpass(r); cats[r["category"]][1] += 1
    linked = [r for r in rs if r.get("linkOk") is not None]
    helpable = [r for r in rs if r.get("selfService") is not None]
    nocall = [r for r in rs if r.get("unneededCall") is not None]
    avg = lambda k: statistics.mean(float(r["grade"].get(k) or 0) for r in graded) if graded else 0
    return {
        "Graded pass": f"{100 * sum(map(gpass, graded)) / len(graded):.0f}%",
        "Questions right every time": f"{sum(all(gpass(r) for r in v) for v in by_q.values())} of {len(by_q)}",
        "Correct (0-2)": f"{avg('correct'):.2f}", "Complete (0-2)": f"{avg('complete'):.2f}",
        "Actionable (0-2)": f"{avg('actionable'):.2f}", "Clear (0-1)": f"{avg('clear'):.2f}",
        "Unsafe answers": f"{sum(1 for r in graded if r['grade'].get('safe') is False)}",
        "Expected link given": f"{100 * sum(1 for r in linked if r['linkOk']) / max(1, len(linked)):.0f}%",
        "Gave a web address to act on": f"{100 * sum(1 for r in helpable if r['selfService']) / max(1, len(helpable)):.0f}%",
        "Sent to the call center when the site had the answer": f"{100 * sum(1 for r in nocall if r['unneededCall']) / max(1, len(nocall)):.0f}%",
        "\"I don't know\" answers": f"{100 * sum(1 for r in rs if DONT_KNOW.search(r['turns'][-1]['answer'])) / len(rs):.0f}%",
        "Blocked by the guardrail": f"{sum(1 for r in rs if r.get('blocked'))}",
        "Errors (no answer)": f"{sum(1 for r in rs if r['turns'][-1].get('status') != 200)}",
        "Median / 95th percentile reply": f"{ms[len(ms) // 2] / 1000:.1f}s / {ms[int(len(ms) * .95)] / 1000:.1f}s",
    }, {c: f"{p}/{n}" for c, (p, n) in cats.items()}


a, b = sys.argv[1], sys.argv[2]
A, B = load(a), load(b)
for part in ("main", "held-out"):
    if part not in A or part not in B: continue
    (ma, ca), (mb, cb) = metrics(A[part]), metrics(B[part])
    print(f"\n### {part} set ({len({r['id'] for r in A[part]['results']})} questions, {A[part]['summary']['repeat']} runs each)\n")
    print(f"| Measure | {a} | {b} |\n|---|---|---|")
    for k in ma: print(f"| {k} | {ma[k]} | {mb[k]} |")
    print(f"\n| Category (graded passes) | {a} | {b} |\n|---|---|---|")
    for c in cb: print(f"| {c} | {ca.get(c, '-')} | {cb[c]} |")
