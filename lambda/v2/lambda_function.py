"""Med-QUEST website chatbot (AWS Lambda).

Each question goes through four steps: understand (rewrite it as a standalone
search and classify it), search (knowledge base from loader/build.py), answer
(self-service first, phone only when a person is needed), and check (links and
numbers must come from the search results or the checked facts).
"""
import json
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
from boto3.dynamodb.conditions import Key

import crisis
import estimate
import bm25

REGION = os.environ.get("AWS_REGION", "us-east-2")
KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
MODEL_ID = os.environ["MODEL_ID"]
# The two model calls can use different models. EFFORT is skipped for models
# that reject it (see call_model).
UNDERSTAND_MODEL_ID = os.environ.get("UNDERSTAND_MODEL_ID") or MODEL_ID
ANSWER_MODEL_ID = os.environ.get("ANSWER_MODEL_ID") or MODEL_ID
EFFORT = os.environ.get("EFFORT", "")
GUARDRAIL_ID = os.environ.get("GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.environ.get("GUARDRAIL_VERSION", "DRAFT")
SESSION_TTL_HOURS = 24
# "monitor" only logs ungrounded answers; "enforce" replaces them with a page link.
# Monitor by default: the grounding check often scores correct answers low.
GROUNDING_MODE = os.environ.get("GROUNDING_MODE", "monitor")
# Pages and answers are searched separately so short answer cards don't crowd
# out the right page.
PAGE_RESULTS = 6
ANSWER_RESULTS = 3
HISTORY_MESSAGES = 8

agent = boto3.client("bedrock-agent-runtime", region_name=REGION)
runtime = boto3.client("bedrock-runtime", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
sessions = dynamodb.Table(os.environ["SESSIONS_TABLE"])
messages = dynamodb.Table(os.environ["MESSAGES_TABLE"])

# Page and form titles from the loader, used to label the buttons.
RESOURCES = json.loads((Path(__file__).parent / "resources.json").read_text())
PAGE_TITLES = {p["url"]: p["title"] for p in RESOURCES["pages"]}
for p in RESOURCES["pages"]:
    for s in p.get("sections", []):
        PAGE_TITLES[s["url"]] = s["label"]
# Full hand-written answers; search matches them through small cards.
ANSWERS = json.loads((Path(__file__).parent / "answers.json").read_text())
FORMS = {f["number"]: f for f in RESOURCES["forms"]}
# Checked contact details, given with every answer so they are copied exactly.
FACTS = json.loads((Path(__file__).parent / "facts.json").read_text())


def facts_text():
    lines = []
    for section, entries in FACTS.items():
        if not isinstance(entries, dict): continue
        for name, value in entries.items():
            if name == "source": continue
            if isinstance(value, dict):
                value = "; ".join(f"{k}: {v}" for k, v in value.items() if k != "source")
            lines.append(f"- {name}: {value}")
    return "\n".join(lines)


FACTS_TEXT = facts_text()
PHONE_NUMBER = re.compile(r"(?<![\d/])(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}(?!\d)")


def phone_key(number):
    d = re.sub(r"\D", "", number)
    return d[-10:]


KNOWN_PHONES = {phone_key(n) for n in PHONE_NUMBER.findall(FACTS_TEXT)}
PORTAL = "https://medical.mybenefits.hawaii.gov"
# Addresses the bot may give although no search result contains them.
ALWAYS_ALLOWED = {PORTAL, "https://medquest.hawaii.gov", "https://www.healthcare.gov"}

PHONE = "1-800-316-8005"
GUARDRAIL_FALLBACK = (
    "I'm not able to answer that one here. For help with your question, "
    f"please call Med-QUEST Customer Service at {PHONE} (TTY 711)."
)
PRIVACY_REPLY = ("For your privacy, please don't share personal details like a Social Security number, "
                 "date of birth or card number here. I can answer general questions about Med-QUEST.")
OFF_TOPIC_REPLY = ("I can only help with questions about Med-QUEST, Hawaii's Medicaid program: applying, "
                   "renewing, coverage, forms and offices. What would you like to know?")
MEDICAL_REPLY = ("I can't give medical advice. Please ask your doctor or pharmacist; for an emergency, call 911. "
                 "I can help with Med-QUEST questions, such as what's covered or how to find a doctor in your plan.")
# For guardrail-blocked questions; no phone number, since a person can't help either.
DECLINE_REPLY = ("Sorry, I can't help with that. I can answer questions about Med-QUEST: applying, renewing, "
                 "coverage, forms and offices. If you or someone you know is in danger, call 911, or call or text 988.")
ERROR_REPLY = f"Something went wrong on our side. Please try again, or call Med-QUEST Customer Service at {PHONE}."

# --- Privacy patterns ---
SSN = re.compile(r"\b(?:\d{3}-\d{2}-\d{4}|\d{9})\b")
CARD = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
DOB = re.compile(r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PUBLIC_EMAIL = re.compile(r"@(?:[A-Za-z0-9-]+\.)*(hawaii\.gov|dhsie\.com)$", re.IGNORECASE)


def has_sensitive(text):
    return any(p.search(text) for p in (SSN, CARD, DOB)) or any(not PUBLIC_EMAIL.search(m) for m in EMAIL.findall(text))


def redact(text):
    for p in (SSN, CARD, DOB):
        text = p.sub("[redacted]", text)
    return EMAIL.sub(lambda m: m.group(0) if PUBLIC_EMAIL.search(m.group(0)) else "[redacted]", text)


# --- Handler ---
def lambda_handler(event, context):
    raw = event.get("body") or "{}"
    body = json.loads(raw) if isinstance(raw, str) else raw
    question = (body.get("question") or "").strip()[:1000]
    user_id = body.get("user_id") or f"anon::{uuid.uuid4()}"
    session_id = body.get("session_id") or str(uuid.uuid4())
    CONVERSATION["key"] = f"{user_id}#{session_id}"
    USAGE.clear()
    if not question:
        return respond(400, {"error": "No question provided", "session_id": session_id})

    try:
        # Runs before anything is stored, logged or sent to a model.
        kind = crisis.check(question)
        if kind:
            return crisis_reply(session_id, kind)

        session = touch_session(user_id, session_id)
        history = recent_messages()

        if has_sensitive(question):
            save_message("user", "[message with personal details, not stored]")
            return reply(session_id, PRIVACY_REPLY)
        # The guardrail blocks attacks and masks personal details before storing.
        verdict, question = check_question(question)
        save_message("user", question)
        if verdict == "blocked":
            return reply(session_id, DECLINE_REPLY, note="guardrail blocked the question")

        state = session.get("preassess_state") or {}
        plan = None
        if state.get("active"):
            asked = estimate.PREASSESS_QUESTIONS[int(state.get("step", 1)) - 1]["id"]
            if len(question.split()) <= 4 and estimate.understood(asked, question):
                return continue_questions(user_id, session_id, state, question)
            # A longer reply can answer several questions at once, so read them all.
            plan = understand(question, history)
            answers = dict(state.get("answers", {}))
            # Skip details already answered; the understand step repeats earlier ones.
            given = mark_after_tax({k: v for k, v in estimate.from_facts(plan["facts"]).items() if k not in answers}, question)
            if plan["kind"] != "crisis" and (given or estimate.understood(asked, question)):
                answers.update(given or {asked: question.strip()})
                return next_question(user_id, session_id, answers)
            # A new question: clear the history so the model doesn't repeat its last question.
            set_state(user_id, session_id, {"active": False})
            history = []
            plan = None

        plan = plan or understand(question, history)
        if plan["kind"] == "crisis":
            print("crisis reply (understand step)")
            return reply(session_id, *crisis.reply(plan.get("crisis_type")))
        print(json.dumps({"question": redact(question), "plan": plan}))
        if plan["kind"] == "off_topic":
            return reply(session_id, OFF_TOPIC_REPLY)
        if plan["kind"] == "medical_advice":
            return reply(session_id, MEDICAL_REPLY)
        if plan["kind"] == "own_eligibility" and OVER_LIMIT.search(question):
            # Someone over the limit wants their options, not an estimate.
            plan["kind"] = "question"
        if plan["kind"] == "own_eligibility" and same_as_last_estimate(state, plan["facts"]):
            # A follow-up after an estimate gets an answer, not the same estimate.
            plan["kind"] = "question"
        if plan["kind"] == "own_eligibility":
            return start_questions(user_id, session_id, plan["facts"], question)

        results = search(plan["search"])
        answer, used = write_answer(question, history, results, plan["language"])
        answer = keep_known_numbers(keep_known_links(answer, results), results)
        print(json.dumps({"used": [[r["type"], r["title"][:60], r["form_numbers"]] for r in used]}))
        verdict = check_answer(answer, question, results, plan["language"])
        if verdict == "blocked":
            return reply(session_id, GUARDRAIL_FALLBACK, note="guardrail blocked the answer")
        if verdict == "ungrounded":
            print(json.dumps({"low_grounding": True, "mode": GROUNDING_MODE, "question": question[:300], "answer": answer[:600]}))
            if GROUNDING_MODE == "enforce":
                return not_sure(session_id, results, question)
        if crisis.TOPIC.search(question):
            # Added after the grounding check, which would flag it as unsupported.
            answer += "\n\n" + crisis.TOPIC_LINE
        return reply(session_id, answer, actions=buttons(used, answer), sources=[r["url"] for r in used])
    except Exception as e:
        import traceback
        traceback.print_exc()
        return respond(500, {"error": ERROR_REPLY, "session_id": session_id})


def crisis_reply(session_id, kind):
    print(f"crisis reply ({kind}, phrase check)")
    text, actions = crisis.reply(kind)
    save_message("user", "[crisis message, not stored]")
    return reply(session_id, text, actions=actions)


def not_sure(session_id, results, question=""):
    """Point to the most relevant page instead of an unsupported answer."""
    page = next((r for r in results if r["type"] != "form"), None)
    url = page["page_url"].split("#")[0] if page else "https://medquest.hawaii.gov/en/faq"
    title = PAGE_TITLES.get(url) or (page["title"] if page else "FAQ")
    text = (f"I'm not sure I have that right, so I'd rather not guess. The best place to check is "
            f"[{title}]({url}). If you still have questions, call Med-QUEST Customer Service at {PHONE} (TTY 711).")
    if crisis.TOPIC.search(question):
        text += "\n\n" + crisis.TOPIC_LINE
    return reply(session_id, text, actions=[{"label": f"Open: {title}", "url": url, "kind": "page"}], note="answer not grounded")


def reply(session_id, answer, actions=None, sources=None, note=None):
    if note: print(note)
    answer = redact(answer)
    save_message("assistant", answer)
    return respond(200, {"answer": answer, "session_id": session_id, "actions": actions or [], "sources": sources or []})


def respond(status, body):
    if USAGE: print(json.dumps({"usage": USAGE}))
    return {"statusCode": status,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Allow-Methods": "POST, OPTIONS"},
            "body": json.dumps(body)}


OVER_LIMIT = re.compile(r"\bover (the|my|our) (income )?limit|\b(make|earn|making|earning) too much|too much (money|income)"
                        r"|above the (income )?limit|spend ?down|medically needy", re.I)


# --- Step 1: understand ---
UNDERSTAND_PROMPT = """You prepare searches for the Med-QUEST website chatbot (Hawaii's Medicaid program).
Read the conversation and the latest message, then reply with JSON only, no other text:
{"search": "...", "language": "...", "kind": "...", "crisis_type": "...", "facts": {...}}

search: the latest message rewritten as a complete, stand-alone search in English, filling in anything it
refers to from earlier messages ("How often can they go?" after a question about children's dental becomes
"how often are children's dental checkups covered"). Leave out names and personal details.
language: the language of the latest message, as a lowercase English name such as "english" or "spanish".
kind: one of
- "question": anything about Med-QUEST, Medicaid, health coverage, forms, offices, benefits or health plans,
  including general questions about who qualifies.
- "own_eligibility": the person asks WHETHER they themselves or their household would qualify for Med-QUEST
  ("Do I qualify?", "Am I eligible?", "I make 2,500 a month with 2 kids, would I qualify?"), or answers an
  earlier offer of an estimate by giving their household, income or age. Asking HOW to get or apply for
  Med-QUEST ("how do I get Medicaid, I'm homeless") is "question", whatever their situation. So is asking what
  options there are when over a limit ("my income is a little over the limit but I have big medical bills"). Not for questions about a rule or a group ("Is there a savings limit?", "Do pregnant women
  qualify?"), about someone already covered ("Is my newborn covered?"), or about a benefit: those are "question".
- "medical_advice": asks for medical advice about symptoms, medicines or treatment.
- "crisis": the person says they, or someone with them, may be in danger now: thoughts of suicide or of
  harming themselves, being hurt or threatened by someone, or a medical emergency or overdose. Use it whenever
  in doubt about someone's safety. Not for general questions about coverage ("Is counseling covered?").
crisis_type: only when kind is "crisis": "self_harm", "abuse" or "emergency".
facts: what the person has said about the household that needs coverage, in this message or earlier ones, as
short text exactly as stated. Keys: household_size ("5"), monthly_income ("1000 a month", "40000 a year"), age
("42"), disability ("yes"/"no"), pregnant ("yes"/"no"), lives_in_hawaii ("yes"/"no"). Leave out anything not
stated; never guess. Use {} if nothing was said.
- "greeting": a greeting, thanks, an introduction ("my name is ..."), small talk, or a question about the chat
  or about what they said earlier ("what's my name?", "who are you?").
- "off_topic": anything unrelated to Med-QUEST or health coverage."""


def understand(question, history):
    convo = "\n".join(f"{m['role']}: {m['text'][:500]}" for m in history[-6:])
    text = call_model(UNDERSTAND_MODEL_ID, UNDERSTAND_PROMPT, [{"role": "user", "content":
                      f"<conversation>\n{convo or '(none)'}\n</conversation>\n<latest>{question}</latest>"}], max_tokens=200)
    plan = {"search": question, "language": "english", "kind": "question", "crisis_type": "", "facts": {}}
    try:
        found = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
        plan.update({k: str(v).strip() for k, v in found.items() if k in plan and k != "facts" and str(v).strip()})
        if isinstance(found.get("facts"), dict): plan["facts"] = found["facts"]
    except Exception:
        print(f"understand: could not read {text!r}")
    if plan["kind"] not in ("question", "own_eligibility", "greeting", "off_topic", "medical_advice", "crisis"):
        plan["kind"] = "question"
    return plan


# --- Step 2: search ---
KEYWORDS = bm25.Index(Path(__file__).parent / "search-docs.json")
KEYWORD_RESULTS = 3


def retrieve(query, count, type_filter):
    return agent.retrieve(knowledgeBaseId=KNOWLEDGE_BASE_ID, retrievalQuery={"text": query[:1000]},
                          retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": count, "filter": type_filter}}
                          ).get("retrievalResults", [])


def search(query):
    with ThreadPoolExecutor(max_workers=2) as pool:
        pages = pool.submit(retrieve, query, PAGE_RESULTS, {"notEquals": {"key": "type", "value": "answer"}})
        # Several cards can belong to one answer.
        answers = pool.submit(retrieve, query, ANSWER_RESULTS * 3, {"equals": {"key": "type", "value": "answer"}})
        found = sorted(pages.result() + answers.result(), key=lambda r: -(r.get("score") or 0))
    results, answers_seen = [], set()
    for r in found:
        m = r.get("metadata", {})
        answer_id = m.get("answer_id")
        if answer_id:
            if answer_id in answers_seen or answer_id not in ANSWERS or len(answers_seen) >= ANSWER_RESULTS: continue
            answers_seen.add(answer_id)
            r["content"]["text"] = ANSWERS[answer_id]
        results.append({"key": (m.get("url", ""), r["content"]["text"][:80]), "text": r["content"]["text"], "type": m.get("type", "page"), "title": m.get("title", ""),
                        "url": m.get("url", ""), "page_url": m.get("page_url") or m.get("url", ""),
                        # List labels come back with their quotes ('"DHS 1179A"').
                        "form_numbers": [f.strip('"') for f in m.get("form_numbers", []) if f.strip('"') != "none"],
                        "score": r.get("score")})
    # Add keyword matches not already found.
    seen = {r["key"] for r in results} | {("answer", a) for a in answers_seen}
    for score, d in KEYWORDS.search(query, KEYWORD_RESULTS):
        key = ("answer", d["answer_id"]) if d["answer_id"] else (d["url"], d["text"][:80])
        if key in seen: continue
        seen.add(key)
        results.append({"key": key, "text": d["text"], "type": d["type"], "title": d["title"], "url": d["url"],
                        "page_url": d["page_url"] or d["url"], "form_numbers": [f for f in d["form_numbers"] if f != "none"],
                        "score": None, "via": "keyword"})
    return results


# --- Step 3: answer ---
ANSWER_PROMPT = """You are Kōkua, the AI assistant on the Med-QUEST website (Hawaii's Medicaid program). Your job is to
help people do things themselves, so they don't need to call. Answer from the numbered sources only.

How to answer:
1. Answer the question directly first, in plain words. Keep it short: a few sentences or a short list.
2. Self-service first. When the sources give a way to do it online, a form to download or a page with the
   details, give it as a Markdown link, e.g. [apply online](https://medical.mybenefits.hawaii.gov) or
   [Form DHS 1179A](https://...). Use only web addresses that appear in the sources, copied exactly. Offer a
   form only for what its own source says it is for: the application is Form DHS 1100; Form DHS 1179A is for
   reporting changes once covered.
3. Give the phone number only when the person needs someone to look at their own case (an application's
   status, a letter they got, an appeal, a lost Medicaid card), or after the online and paper options when the
   sources list the phone as one of the ways. Never answer only "call Med-QUEST" when the sources say more.
4. Phone numbers, addresses, emails and websites: copy them exactly from <checked_facts> when it covers what's
   asked, otherwise from the sources. Never write one from memory.
5. If the sources don't answer the question, say so in one sentence, point to the most relevant page from the
   sources, and only then give the phone number. Never use general knowledge or guess.
6. Sources marked "answer" were written and checked for this purpose; prefer them when they fit.
7. Personal details: text like {PHONE} or {ADDRESS} is a detail the person shared that was hidden for their
   privacy. Never write these placeholders. If the person tells you their first name, you may use it, sparingly;
   never ask for it. If they ask whether you keep their phone number, address or other details, say kindly that
   those are hidden for their privacy.
8. Income: never state a dollar income limit or say whether someone qualifies. You may repeat percentages of
   the Federal Poverty Level exactly as a source gives them. Never ask for someone's household, income or age
   yourself: if they want to know whether they qualify, say they can ask "Do I qualify?" for a quick estimate,
   and that applying is the only way to know for sure.
9. Never mention sources, documents or "what I have": no "the sources show", "the sources don't say", "based on
   the information". Say what you know; if something isn't covered, say "I don't have details on that". If an earlier
   answer in the conversation already gave a detail, such as a phone number, stay consistent with it. Never repeat personal details such as a
   Social Security number or date of birth.
10. Reply in {language}. If you can't write it accurately, reply in English and add that free interpreter
   services are available at 1-800-316-8005.
11. After the answer, on its own last line, write USED: followed by the numbers of the sources you used,
   e.g. "USED: 2, 5". Write "USED: none" if you used none."""


def write_answer(question, history, results, language):
    sources = "\n\n".join(f"[{i}] ({r['type']}) {r['title']}\nLink: {r['url']}\n{r['text']}" for i, r in enumerate(results, 1))
    turns = [{"role": m["role"], "content": m["text"]} for m in history[-HISTORY_MESSAGES:]
             if m.get("role") in ("user", "assistant") and m.get("text")]
    while turns and turns[0]["role"] != "user":
        turns.pop(0)
    turns.append({"role": "user", "content": f"<checked_facts>\n{FACTS_TEXT}\n</checked_facts>\n\n"
                                             f"<sources>\n{sources or '(none found)'}\n</sources>\n\n{question}"})
    turns = merge_same_role(turns)
    text = call_model(ANSWER_MODEL_ID, ANSWER_PROMPT.replace("{language}", language or "english"), turns, max_tokens=2000)
    used_line = re.search(r"\n?\s*USED:\s*([^\n]*)\s*$", text)
    answer = text[:used_line.start()].strip() if used_line else text.strip()
    # A masked detail must never reach the person ("Hi {NAME}").
    answer = re.sub(r"[ \t]*\{(NAME|PHONE|EMAIL|ADDRESS|[A-Z_]{3,40})\}", "", answer)  # never show a masked detail
    answer = re.sub(r"\b(Hi|Hello|Aloha|Thanks|Thank you)\s*,", r"\1,", answer)
    if SOURCE_TALK.search(answer):
        print(f"answer mentions its sources: {answer[:200]!r}")
        answer = SOURCE_TALK.sub(lambda m: "Med-QUEST says" if m.group(4) else "Med-QUEST's website", answer)
    numbers = [int(n) for n in re.findall(r"\d+", used_line.group(1))] if used_line else []
    used = [results[n - 1] for n in numbers if 1 <= n <= len(results)]
    return answer, used


SOURCE_TALK = re.compile(r"\b(the|my|these|those) (sources|documents|reference documents)( I have| provided)?"
                         r"( (say|says|mention|mentions|show|shows|note|notes|state|states))?\b", re.I)


def merge_same_role(turns):
    """The model needs user and assistant turns to alternate."""
    merged = []
    for t in turns:
        if merged and merged[-1]["role"] == t["role"]:
            merged[-1]["content"] += "\n\n" + t["content"]
        else:
            merged.append(dict(t))
    return merged


# Tokens used by each model in this request, logged once at the end.
USAGE = {}


def call_model(model, system, turns, max_tokens):
    body = {"anthropic_version": "bedrock-2023-05-31", "max_tokens": max_tokens, "system": system, "messages": turns}
    if EFFORT and "claude-haiku-4" not in model:
        body["output_config"] = {"effort": EFFORT}
    out = json.loads(runtime.invoke_model(modelId=model, body=json.dumps(body))["body"].read())
    u, name = out.get("usage", {}), model.rsplit("/", 1)[-1]
    tally = USAGE.setdefault(name, {"input": 0, "output": 0, "thinking": 0, "calls": 0})
    tally["input"] += u.get("input_tokens", 0); tally["output"] += u.get("output_tokens", 0)
    tally["thinking"] += (u.get("output_tokens_details") or {}).get("thinking_tokens", 0); tally["calls"] += 1
    return "".join(c.get("text", "") for c in out.get("content", []) if c.get("type") == "text")


# --- Step 4: check ---
def norm_url(url):
    return re.sub(r"^https?://(www\.)?", "", url.strip().rstrip("/).,;")).lower()


def keep_known_numbers(answer, results):
    """Remove phone numbers not in the checked facts or the search results."""
    allowed = KNOWN_PHONES | {phone_key(n) for r in results for n in PHONE_NUMBER.findall(r["text"])}

    def check(m):
        if phone_key(m.group(0)) in allowed: return m.group(0)
        print(f"removed unknown phone number ending {phone_key(m.group(0))[-4:]}")
        return "(see the [Contact Us page](https://medquest.hawaii.gov/en/contact-us) for the number)"
    return PHONE_NUMBER.sub(check, answer)


def keep_known_links(answer, results):
    """Remove web addresses not in the search results, keeping the link text."""
    known = {norm_url(u) for u in ALWAYS_ALLOWED}
    known.update(norm_url(u) for u in re.findall(r"https?://[^\s,;)]+", FACTS_TEXT))
    for r in results:
        known.add(norm_url(r["url"])); known.add(norm_url(r["page_url"]))
        known.update(norm_url(u) for u in re.findall(r"https?://[^\s)\]>\"']+", r["text"]))

    def check_link(m):
        if norm_url(m.group(2)) in known: return m.group(0)
        print(f"removed unknown link: {m.group(2)}")
        return m.group(1)
    answer = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", check_link, answer)

    def check_bare(m):
        if norm_url(m.group(0)) in known: return m.group(0)
        print(f"removed unknown address: {m.group(0)}")
        return ""
    return re.sub(r"(?<!\()https?://[^\s)\]>\"']+", check_bare, answer)


def buttons(used, answer):
    """Build up to three buttons from the results the answer used."""
    out, seen = [], set()

    def add(label, url, kind):
        if url and norm_url(url) not in seen and len(out) < 3:
            seen.add(norm_url(url)); out.append({"label": label, "url": url, "kind": kind})

    for r in used:
        if r["type"] == "form":
            add(f"Download Form {r['form_numbers'][0]}" if r["form_numbers"] else "Download the form", r["url"], "download")
        else:
            # Forms named by both the result and the answer.
            for number in r["form_numbers"]:
                if number in answer and number in FORMS:
                    add(f"Download Form {number}", FORMS[number]["download"], "download")
    if PORTAL.split("//")[1] in answer:
        add("Go to the online portal", PORTAL, "page")
    for r in used:
        url = r["page_url"] if r["type"] == "form" else r["url"]
        title = PAGE_TITLES.get(url) or PAGE_TITLES.get(url.split("#")[0]) or (r["title"] if r["type"] == "page" else "")
        if title: add(f"Open: {title}", url, "page")
    return out


def guardrail(source, content):
    out = runtime.apply_guardrail(guardrailIdentifier=GUARDRAIL_ID, guardrailVersion=GUARDRAIL_VERSION,
                                  source=source, content=content)
    actions, findings, blocks, scores = set(), [], set(), {}

    def walk(x, path):
        if isinstance(x, dict):
            if "action" in x and x["action"] not in ("NONE", None):
                actions.add(x["action"])
                if x["action"] == "BLOCKED":
                    blocks.add("grounding" if x.get("type") in ("GROUNDING", "RELEVANCE") else "policy")
                # Never log "match": it is the personal detail itself.
                findings.append(f"{path}:{x.get('type') or x.get('name')}:{x['action']}"
                                + (f":score={x['score']:.2f}" if "score" in x else ""))
            if x.get("type") in ("GROUNDING", "RELEVANCE") and "score" in x:
                scores[x["type"].lower()] = round(x["score"], 2)
            for k, v in x.items():
                if k != "match": walk(v, k)
        elif isinstance(x, list):
            for v in x: walk(v, path)
    walk(out.get("assessments", []), "")
    if findings: print(f"guardrail ({source}): {', '.join(findings)[:1500]}")
    if scores: print(json.dumps({"grounding_scores": scores}))
    texts = [o.get("text", "") for o in out.get("outputs", [])]
    return actions, texts, blocks


def check_question(text):
    """Return ("blocked" or "ok", the question with personal details masked)."""
    if not GUARDRAIL_ID: return "ok", text
    # Keep known public numbers out of masking so questions about them still work.
    public = {}
    def hold(m):
        if phone_key(m.group(0)) not in KNOWN_PHONES: return m.group(0)
        token = f"PUBLICNUMBER{len(public) + 1}"
        public[token] = m.group(0)
        return token
    held = PHONE_NUMBER.sub(hold, text)
    actions, texts, _ = guardrail("INPUT", [{"text": {"text": held[:5000]}}])
    if "BLOCKED" in actions: return "blocked", text
    out = texts[0] if "ANONYMIZED" in actions and texts else held
    for token, number in public.items(): out = out.replace(token, number)
    return "ok", out


def check_answer(answer, question, results, language="english"):
    """Return "blocked", "ungrounded" or "ok".

    Non-English answers get content filters only: grounding compares against English text."""
    if not GUARDRAIL_ID: return "ok"
    if language.lower() not in ("english", "en", ""):
        content = [{"text": {"text": answer[:5000]}}]
    else:
        sources = "\n\n".join(r["text"] for r in results)[:90000]
        content = [{"text": {"text": sources or "(none)", "qualifiers": ["grounding_source"]}},
                   {"text": {"text": question[:1000], "qualifiers": ["query"]}},
                   {"text": {"text": answer[:5000], "qualifiers": ["guard_content"]}}]
    _, _, blocks = guardrail("OUTPUT", content)
    if "policy" in blocks: return "blocked"
    return "ungrounded" if "grounding" in blocks else "ok"


# --- Eligibility questions ---
AFTER_TAX = re.compile(r"after[- ]?tax|take[- ]home|\bnet\b", re.I)


def mark_after_tax(answers, question):
    """Keep "after taxes" from the person's words, which the model may drop."""
    if "monthly_income" in answers and AFTER_TAX.search(question) and not AFTER_TAX.search(answers["monthly_income"]):
        answers["monthly_income"] += " after taxes"
    return answers


def normalize_yes_no(text):
    s = estimate.normalize_text(text)
    return "no" if estimate.NO.match(s) else "yes" if estimate.YES.match(s) else ""


def same_as_last_estimate(state, facts):
    last = state.get("last_answers") or {}
    given = estimate.from_facts(facts)
    return bool(last) and all(last.get(k, "").split(" after")[0] == v.split(" after")[0] for k, v in given.items())


def start_questions(user_id, session_id, facts, question=""):
    """Start the estimate from known facts and ask only for what is missing."""
    answers = mark_after_tax(estimate.from_facts(facts), question)
    print(json.dumps({"estimate_prefilled": sorted(answers)}))
    left = len(estimate.PREASSESS_QUESTIONS) - len(answers)
    if not answers:
        intro = ("I can give you a quick estimate. It takes five short questions. Please don't include personal "
                 "details like names or numbers from your documents.")
    else:
        intro = f"Thanks, I've noted that. {'Just one more question' if left == 1 else f'Just {left} more questions'} for a quick estimate:"
    return next_question(user_id, session_id, answers, intro)


def continue_questions(user_id, session_id, state, answer):
    answers = dict(state.get("answers", {}))
    answers[estimate.PREASSESS_QUESTIONS[int(state.get("step", 1)) - 1]["id"]] = answer.strip()
    return next_question(user_id, session_id, answers)


def next_question(user_id, session_id, answers, intro=None):
    for step, q in enumerate(estimate.PREASSESS_QUESTIONS, 1):
        if q["id"] not in answers:
            set_state(user_id, session_id, {"active": True, "step": step, "answers": answers})
            return reply(session_id, (intro + "\n\n" if intro else "") + q["q"])
    set_state(user_id, session_id, {"active": False, "last_answers": answers})
    if normalize_yes_no(answers.get("hawaii_resident", "")) == "no":
        return reply(session_id, estimate.build_estimate(answers))
    result = estimate.build_estimate(answers)
    if not result:
        result = ("I couldn't read the household size or income as a number, so I can't give an estimate. "
                  f"The best way to find out is to apply. It's free: [apply online]({PORTAL}), or see "
                  "[all the ways to apply](https://medquest.hawaii.gov/en/members-applicants/get-started/how-to-apply).")
    return reply(session_id, result, actions=[{"label": "Apply online", "url": PORTAL, "kind": "page"}])


# --- Sessions ---
def touch_session(user_id, session_id):
    now = datetime.now(timezone.utc)
    out = sessions.update_item(
        Key={"user_id": user_id, "session_id": session_id},
        UpdateExpression="SET updated_at = :now, expires_at = :exp, created_at = if_not_exists(created_at, :now)",
        ExpressionAttributeValues={":now": now.isoformat(), ":exp": int((now + timedelta(hours=SESSION_TTL_HOURS)).timestamp())},
        ReturnValues="ALL_NEW")
    return out.get("Attributes", {})


def set_state(user_id, session_id, state):
    sessions.update_item(Key={"user_id": user_id, "session_id": session_id},
                         UpdateExpression="SET preassess_state = :s", ExpressionAttributeValues={":s": state})


# User and session key, set per request, so a session id alone can't load a
# conversation. Module-level is safe: a Lambda handles one request at a time.
CONVERSATION = {"key": ""}


def recent_messages():
    out = messages.query(KeyConditionExpression=Key("session_id").eq(CONVERSATION["key"]), ScanIndexForward=False,
                         Limit=HISTORY_MESSAGES)
    return list(reversed(out.get("Items", [])))


def save_message(role, text):
    # Store only redacted text, and only for a day.
    now = datetime.now(timezone.utc)
    messages.put_item(Item={"session_id": CONVERSATION["key"], "ts_msgid": f"{now.isoformat()}#{uuid.uuid4().hex[:8]}",
                            "role": role, "text": redact(text)[:4000],
                            "expires_at": int((now + timedelta(hours=SESSION_TTL_HOURS)).timestamp())})
