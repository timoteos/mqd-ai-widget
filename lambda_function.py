import json
import boto3
import uuid
import re
import os
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor

# --- AWS & Bedrock Configuration ---
REGION = os.environ.get("AWS_REGION", "us-east-2")
KNOWLEDGE_BASE_ID = "36RB8W7ZSW"
WEB_KNOWLEDGE_BASE_ID = "5OFSL8ELUT"
GUARDRAIL_ID = "gg3jarufm3ni"
GUARDRAIL_VERSION = "DRAFT"
MODEL_ARN = f"arn:aws:bedrock:{REGION}:887224793602:inference-profile/global.anthropic.claude-haiku-4-5-20251001-v1:0"

# --- DynamoDB Configuration ---
SESSIONS_TABLE_NAME = "medquest-kb-chatsession"
MESSAGES_TABLE_NAME = "medquest-kb-chatmessages"
SESSION_TTL_HOURS = 24

# --- Boto3 Clients ---
bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
sessions_table = dynamodb.Table(SESSIONS_TABLE_NAME)
messages_table = dynamodb.Table(MESSAGES_TABLE_NAME)

# --- Business Logic Constants ---
ELIGIBILITY_HINTS = ["eligible", "eligibility", "qualify", "income", "limit", "can i apply", "am i eligible"]
NAV_HINTS = ["link", "url", "page", "website", "where", "find", "how do i get to"]
POLICY_HINTS = ["policy", "rule", "coverage", "benefit", "copay", "prior authorization"]

PREASSESS_QUESTIONS = [
    {"id": "household_size", "q": "How many people are in your household (including you)?"},
    {"id": "monthly_income", "q": "What is your total household monthly income before taxes?"},
    {"id": "age_group", "q": "What is the applicant age group: 0-18, 19-64, or 65+?"},
    {"id": "pregnant", "q": "Is anyone applying currently pregnant? (yes/no)"},
    {"id": "hawaii_resident", "q": "Do you currently live in Hawaii? (yes/no)"}
]

# --- Privacy Patterns ---
SSN_PATTERN = re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b")
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
DOB_PATTERN = re.compile(r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# --- Main Handler ---
def lambda_handler(event, context):
    print(f"--- STARTING INVOCATION ---")
    print(f"EVENT: {json.dumps(event)}")

    raw_body = event.get("body") or "{}"
    body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

    user_id = body.get("user_id") or f"anon::{str(uuid.uuid4())}"
    session_id = body.get("session_id") or str(uuid.uuid4())
    user_question = (body.get("question") or "").strip()

    print(f"SESSION_ID: {session_id}, USER_ID: {user_id}")
    print(f"USER_QUESTION: {user_question}")

    if not user_question:
        return build_response(400, {"error": "No question provided", "session_id": session_id})

    # --- FIX: Ensure session is created/updated on every turn ---
    update_session_state(user_id, session_id, {}) # This will create the item or update the timestamp
    session_state = get_session(user_id, session_id)

    # --- FIX: Correct the order of operations ---
    # 1. Save the CURRENT user message first.
    save_message(session_id, "user", user_question)
    # 2. NOW, fetch the history, which includes the message we just saved.
    history = list(get_recent_messages(session_id))
    print(f"FETCHED HISTORY: {json.dumps(history)}")

    if contains_sensitive_value(user_question):
        answer = "For your privacy, please do not share sensitive personal information like SSN, full date of birth, or payment card numbers in chat."
        save_message(session_id, "assistant", answer)
        return build_response(200, {"answer": answer, "session_id": session_id, "sources": []})

    try:
        preassess_state = session_state.get("preassess_state", {"active": False, "step": 0, "answers": {}})
        
        if preassess_state.get("active"):
            return handle_preassessment(user_id, session_id, preassess_state, user_question, history)

        answerability = retrieve_and_assess(user_question)

        if should_start_preassessment(user_question, answerability):
            return start_preassessment(user_id, session_id, user_question)

        # Normal RAG path
        answer, citations = generate_from_context(user_question, answerability["combined_context"], history)
        save_message(session_id, "assistant", answer, citations)
        print(f"FINAL RESPONSE: {{'answer': '{answer}', 'session_id': '{session_id}'}}")
        return build_response(200, {"answer": redact_sensitive_output(answer), "session_id": session_id, "sources": citations[:3]})

    except Exception as e:
        print(f"--- ERROR ---")
        print(f"Internal error: {e}")
        import traceback
        traceback.print_exc()
        print(f"--- END ERROR ---")
        error_message = "An internal error occurred. Please try again, or call Med-QUEST Customer Service at 1-800-316-8005."
        save_message(session_id, "assistant", error_message)
        return build_response(500, {"error": error_message, "session_id": session_id})

def handle_preassessment(user_id, session_id, preassess_state, user_question, history):
    pa_result = continue_preassessment(preassess_state, user_question)
    
    if pa_result["done"]:
        enriched_question = (
            f"User question: {pa_result.get('original_question', '')}\n"
            f"Collected pre-assessment facts: {json.dumps(pa_result['answers'])}\n"
            "Provide guidance only; do not make official eligibility determinations."
        )
        # Pass the history to the RAG function
        answer, citations = run_rag(enriched_question, history, intent_override="eligibility")
        
        new_preassess_state = {"active": False, "step": 0, "answers": {}}
        update_session_state(user_id, session_id, {"preassess_state": new_preassess_state})
        
        save_message(session_id, "assistant", answer, citations)
        return build_response(200, {"answer": redact_sensitive_output(answer), "session_id": session_id, "sources": citations[:3]})
    else:
        update_session_state(user_id, session_id, {"preassess_state": pa_result["state"]})
        save_message(session_id, "assistant", pa_result["next_question"])
        return build_response(200, {"answer": pa_result["next_question"], "sources": [], "session_id": session_id})

def start_preassessment(user_id, session_id, user_question):
    answer = (
        "I can quickly check if you might be eligible. First, please do not share any sensitive personal information.\n\n"
        + PREASSESS_QUESTIONS[0]["q"]
    )
    new_preassess_state = {"active": True, "step": 1, "answers": {}, "original_question": user_question}
    update_session_state(user_id, session_id, {"preassess_state": new_preassess_state})
    
    save_message(session_id, "assistant", answer)
    return build_response(200, {"answer": answer, "sources": [], "session_id": session_id})

# --- DynamoDB & Boto3 Helpers ---
def get_session(user_id, session_id):
    try:
        response = sessions_table.get_item(Key={"user_id": user_id, "session_id": session_id})
        return response.get("Item", {})
    except Exception as e:
        print(f"Error getting session {session_id}: {e}")
        return {}

def get_recent_messages(session_id, limit=8):
    try:
        response = messages_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('session_id').eq(session_id),
            ScanIndexForward=False, Limit=limit
        )
        return reversed(response.get("Items", []))
    except Exception as e:
        print(f"Error getting messages for session {session_id}: {e}")
        return []

def update_session_state(user_id, session_id, state_updates):
    try:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=SESSION_TTL_HOURS)
        
        update_expression = "SET #updated_at = :ts, #expires_at = :exp"
        expression_attribute_names = {"#updated_at": "updated_at", "#expires_at": "expires_at"}
        expression_attribute_values = {":ts": now.isoformat(), ":exp": int(expires_at.timestamp())}
        
        if not state_updates: # This is a simple "touch" to create the session
            update_expression += ", #created_at = if_not_exists(#created_at, :ts_created)"
            expression_attribute_names["#created_at"] = "created_at"
            expression_attribute_values[":ts_created"] = now.isoformat()
        
        for key, value in state_updates.items():
            attr_name, attr_value = f"#{key}", f":{key}"
            update_expression += f", {attr_name} = {attr_value}"
            expression_attribute_names[attr_name] = key
            expression_attribute_values[attr_value] = value

        sessions_table.update_item(
            Key={"user_id": user_id, "session_id": session_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
    except Exception as e:
        print(f"Error updating session {session_id}: {e}")

def save_message(session_id, role, text, sources=None):
    try:
        now = datetime.now(timezone.utc)
        ts_msgid = f"{now.isoformat()}#{str(uuid.uuid4())[:8]}"
        item = {"session_id": session_id, "ts_msgid": ts_msgid, "role": role, "text": text, "text_redacted": redact_sensitive_output(text)}
        if sources: item["sources"] = sources
        messages_table.put_item(Item=item)
    except Exception as e:
        print(f"Error saving message for session {session_id}: {e}")

# --- Core Logic ---
def continue_preassessment(state, user_input):
    step = int(state.get("step", 0))
    answers = dict(state.get("answers", {}))

    if contains_sensitive_value(user_input):
        return {"done": False, "next_question": "Please do not share sensitive data. " + PREASSESS_QUESTIONS[max(0, step - 1)]["q"], "state": state}

    prev_q_idx = step - 1
    if 0 <= prev_q_idx < len(PREASSESS_QUESTIONS):
        answers[PREASSESS_QUESTIONS[prev_q_idx]["id"]] = user_input.strip()

    if step >= len(PREASSESS_QUESTIONS):
        return {"done": True, "answers": answers, "original_question": state.get("original_question")}

    return {"done": False, "next_question": PREASSESS_QUESTIONS[step]["q"], "state": {"active": True, "step": step + 1, "answers": answers, "original_question": state.get("original_question")}}

def classify_intent(q):
    s = normalize_text(q)
    if any(h in s for h in ELIGIBILITY_HINTS): return "eligibility"
    if any(h in s for h in NAV_HINTS): return "navigation"
    if any(h in s for h in POLICY_HINTS): return "policy"
    return "general"

def retrieve_and_assess(user_question):
    intent = classify_intent(user_question)
    counts = {"navigation": (3, 12), "policy": (8, 4), "eligibility": (10, 6)}
    s3_count, web_count = counts.get(intent, (5, 5))

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(bedrock_agent.retrieve, knowledgeBaseId=KNOWLEDGE_BASE_ID, retrievalQuery={"text": user_question}, retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": s3_count}})
        f2 = pool.submit(bedrock_agent.retrieve, knowledgeBaseId=WEB_KNOWLEDGE_BASE_ID, retrievalQuery={"text": user_question}, retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": web_count}})
        s3_results, web_results = f1.result(), f2.result()

    all_results = s3_results.get("retrievalResults", []) + web_results.get("retrievalResults", [])
    combined_context, citations, seen = "", [], set()

    for res in all_results:
        txt = res.get("content", {}).get("text", "")
        if txt: combined_context += f"\n{txt}\n"
        loc = res.get("location", {})
        source = loc.get("s3Location", {}).get("uri", "") or loc.get("webLocation", {}).get("url", "")
        if source and source not in seen:
            citations.append(source.replace("s3://bedrock-testing-kb/", ""))
            seen.add(source)

    confidence = sum([len(combined_context.strip()) > 1500, len(citations) >= 2, intent != "general" and len(citations) >= 1])
    return {"combined_context": combined_context, "citations": citations, "confidence": confidence, "intent": intent}

def should_start_preassessment(user_question, answerability):
    q_norm = normalize_text(user_question)
    vague = len(q_norm.split()) < 7 or "eligible" in q_norm
    return answerability["intent"] == "eligibility" and (vague or answerability["confidence"] <= 1)

def run_rag(user_question, history, intent_override=None):
    answerability = retrieve_and_assess(user_question)
    return generate_from_context(user_question, answerability["combined_context"], history)

def generate_from_context(user_question, combined_context, history):
    system_prompt = """<system>
You are a helpful, stateful AI assistant named Aloha. Your ONLY purpose is to answer questions about Med-QUEST using the provided context.

**CRITICAL RULES:**
1.  **YOU HAVE A MEMORY.** The user is testing you. The conversation history is provided in the <history> messages. Use it to remember the user's name and what you have already discussed.
2.  **DO NOT BE EVASIVE.** If the user asks what their name is, and it's in the history, state their name. If they ask about your memory, confirm that you remember the conversation. Do not claim you are stateless or cannot access information.
3.  **BE DIRECT AND CONCISE.** Use short sentences and bullet points. Avoid conversational filler.
4.  **STICK TO THE FACTS.** Use ONLY the "Contextual Information" to answer questions. If the answer is not in the context, say "I do not have that information, please call Med-QUEST at 1-800-316-8005." Do not use your general knowledge.
5.  **SAFETY.** Never repeat sensitive data (SSN, DOB, etc.).
</system>"""

    messages = []
    # Add the history messages to the prompt
    for message in history:
        role, text = message.get("role"), message.get("text")
        if role and text:
            # Use a <history> tag to make it clear to the model
            messages.append({"role": role, "content": f"<history>{text}</history>"})

    # Add the current user question
    messages.append({"role": "user", "content": f"Contextual Information:\n{combined_context}\n\nUser Question: {user_question}"})

    print(f"--- BEDROCK PROMPT ---")
    print(json.dumps(messages, indent=2))
    print(f"--- END BEDROCK PROMPT ---")

    prompt_body = {"anthropic_version": "bedrock-2023-05-31", "max_tokens": 800, "system": system_prompt, "messages": messages}
    
    response = bedrock_runtime.invoke_model(modelId=MODEL_ARN, body=json.dumps(prompt_body), guardrailIdentifier=GUARDRAIL_ID, guardrailVersion=GUARDRAIL_VERSION)
    result_body = json.loads(response.get("body").read())

    print(f"--- BEDROCK RESPONSE ---")
    print(json.dumps(result_body, indent=2))
    print(f"--- END BEDROCK RESPONSE ---")

    if result_body.get("stop_reason") == "guardrail_intervention":
        return "I can only help with Med-QUEST related questions. For assistance, call 1-800-316-8005.", []
    
    return result_body.get("content", [{}])[0].get("text", "I am sorry, I could not generate a response."), []

def contains_sensitive_value(text):
    return any(p.search(text) for p in [SSN_PATTERN, CREDIT_CARD_PATTERN, DOB_PATTERN, EMAIL_PATTERN])

def redact_sensitive_output(text):
    if not isinstance(text, str): return ""
    for pattern, replacement in [(SSN_PATTERN, "[redacted]"), (CREDIT_CARD_PATTERN, "[redacted]"), (DOB_PATTERN, "[redacted]"), (EMAIL_PATTERN, "[redacted]")]:
        text = pattern.sub(replacement, text)
    return text

def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Allow-Methods": "POST, OPTIONS"},
        "body": json.dumps(body)
    }

def normalize_text(text):
    t = text.lower().strip().replace("eedgible", "eligible").replace("eligble", "eligible").replace("insurane", "insurance")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t)
