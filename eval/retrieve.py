"""Checks whether a direct knowledge base search finds each test question's
expected facts and link.

    python3 eval/retrieve.py HDEFCGHQPX [number of results, default 5] [--no-answers]

--no-answers leaves the hand-written answers out of the search.
"""
import json, re, subprocess, sys
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith("--")]
kb = args[0]
top = int(args[1]) if len(args) > 1 else 5
no_answers = "--no-answers" in sys.argv
questions = json.loads((Path(__file__).parent / "questions.json").read_text())["questions"]
norm = lambda s: s.lower().replace("’", "'").replace("ʻ", "'")
digits = lambda s: re.sub(r"\D", "", s)


def has(text, term):
    return digits(text).find(digits(term)) >= 0 if len(digits(term)) >= 7 else norm(term) in norm(text)


def search(q):
    out = subprocess.run(["aws", "bedrock-agent-runtime", "retrieve", "--knowledge-base-id", kb, "--retrieval-query",
                          json.dumps({"text": q}), "--retrieval-configuration",
                          json.dumps({"vectorSearchConfiguration": {"numberOfResults": top,
                          **({"filter": {"notEquals": {"key": "type", "value": "answer"}}} if no_answers else {})}}), "--output", "json"],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)["retrievalResults"]


rows, ok_facts, ok_links, n_links = [], 0, 0, 0
for q in questions:
    if q["category"] == "Safety" or q.get("behaviour") == "estimate": continue
    question = " ".join(q["turns"]) if len(q["turns"]) > 1 else q["turns"][0]
    hits = search(question)
    text = " ".join(h["content"]["text"] + " " + json.dumps(h.get("metadata", {})) for h in hits)
    missing = [g for g in q["must"] if not any(has(text, t) for t in g)]
    link = any(norm(l) in norm(text) or norm(re.sub("%20", " ", l)) in norm(text) for l in q["links"]) if q["links"] else None
    ok_facts += not missing
    if link is not None: n_links += 1; ok_links += link
    first = hits[0]["metadata"] if hits else {}
    rows.append((q["id"], not missing, link, f"{first.get('type','?')}: {first.get('title','')[:60]}", missing))

for r in rows:
    print(f"{'ok ' if r[1] else 'MISS'} {'link' if r[2] else '----'}  {r[0]:<24} top: {r[3]}" + (f"  missing {r[4]}" if r[4] else ""))
print(f"\nFacts found in the top {top}: {ok_facts} of {len(rows)}. Expected link in the top {top}: {ok_links} of {n_links}.")
