"""Summarises an eval/compare.sh run: accuracy, consistency, speed and cost.
Prices are list prices per million tokens; check Bedrock's before budgeting.

    python3 eval/compare-report.py eval/results/compare-<timestamp>
"""
import glob, json, statistics, subprocess, sys
from pathlib import Path

PRICE = {"claude-haiku-4-5": (1.00, 5.00), "claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00)}
folder = Path(sys.argv[1])
windows = [l.split() for l in (folder / "windows.txt").read_text().splitlines()]
results = [json.load(open(f)) for f in glob.glob(str(folder.parent / "*.json")) if "rescored" not in f]


def usage(start, end):
    """Sum token use per model from the Lambda's usage log lines."""
    out = subprocess.run(["aws", "logs", "filter-log-events", "--log-group-name", "/aws/lambda/medquest-kb-chat-v2",
                          "--start-time", str(int(start) * 1000), "--end-time", str(int(end) * 1000),
                          "--filter-pattern", '"usage"', "--query", "events[].message", "--output", "json"],
                         capture_output=True, text=True, check=True)
    totals, requests = {}, 0
    for line in json.loads(out.stdout):
        try: u = json.loads(line[line.index("{"):])["usage"]
        except Exception: continue
        requests += 1
        for model, t in u.items():
            name = next((k for k in PRICE if k in model), model)
            agg = totals.setdefault(name, {"input": 0, "output": 0, "thinking": 0})
            for k in agg: agg[k] += t.get(k, 0)
    return totals, requests


rows = []
for name, start, end in windows:
    runs = [r for r in results if r["summary"].get("label") == name]
    main = next((r for r in runs if r["summary"].get("set", "questions.json").endswith("questions.json")), None)
    held = next((r for r in runs if "holdout" in r["summary"].get("set", "")), None)
    totals, requests = usage(start, end)
    cost = sum(t["input"] / 1e6 * PRICE[m][0] + t["output"] / 1e6 * PRICE[m][1] for m, t in totals.items() if m in PRICE)
    times = [x["ms"] for r in runs for x in r["results"]]
    rows.append((name, main, held, cost / max(1, requests), requests, statistics.median(times) / 1000 if times else 0,
                 sorted(times)[int(len(times) * 0.95)] / 1000 if times else 0, totals))

print("| Setup | Main set: graded pass | Main: passed both runs | Held-out: graded pass | Held-out: passed both runs | Median / 95th pct reply | Cost per question |")
print("|---|---|---|---|---|---|---|")
for name, main, held, cpq, n, med, p95, totals in rows:
    m, h = main["summary"], held["summary"]
    print(f"| {name} | {m['gradedPass']}% | {m['passedEveryTime']} | {h['gradedPass']}% | {h['passedEveryTime']} | {med:.1f}s / {p95:.1f}s | ${cpq:.4f} |")
print()
for name, main, held, cpq, n, med, p95, totals in rows:
    print(f"{name}: {n} requests; tokens {json.dumps(totals)}; grader averages main {main['summary']['averages']}, held-out {held['summary']['averages']}")
