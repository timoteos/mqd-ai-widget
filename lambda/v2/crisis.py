"""Fixed replies for someone in crisis: suicide or self-harm, abuse, or a
medical emergency.

check() runs before the guardrail and any model call, so the reply never
depends on a model. The phrases are first-person, so coverage questions are
answered normally. NEEDS REVIEW by behavioral health staff before launch:
the wording, numbers and links.
"""
import re

SELF_HARM = re.compile(
    r"\b(kill(ing)? myself|end(ing)? (my|it all|my own) ?(life)?\b|take my (own )?life|want(ed)? to die|wish i (was|were) dead"
    r"|better off dead|no reason to live|suicidal|commit(ting)? suicide|thinking (about|of) suicide"
    r"|(hurt|harm|cut|cutting|harming|hurting) myself|don'?t want to (live|be alive|be here anymore))\b", re.I)
ABUSE = re.compile(
    r"\b((he|she|they|my (husband|wife|partner|boyfriend|girlfriend|dad|father|mom|mother|son|daughter|caregiver|ex))"
    r" (hits|hit|beats|beat|chokes|choked|hurts|hurt|abuses|abused|threatens|threatened|attacks|attacked) (me|my (kids?|child|children|baby))"
    r"|(i'?m|i am|being|been) (abused|beaten|hit|assaulted|raped)|afraid (of|to go home)|not safe at home"
    r"|(someone|somebody) is hurting (me|my))\b", re.I)
EMERGENCY = re.compile(
    r"\b((i|he|she|they|my \w+) (took|swallowed|took too many|overdosed on)\b.*\b(pills|tablets|bottle)"
    r"|overdos(e|ed|ing)\b(?! coverage)|can'?t breathe|chest pain right now|not breathing|unconscious|having a (heart attack|stroke|seizure))", re.I)

# Any question on these topics, even about coverage, gets the crisis line added.
TOPIC = re.compile(r"\b(suicid\w*|self[- ]harm\w*|kill (myself|themselves|himself|herself)|abuse[ds]?|abusive"
                   r"|domestic violence|overdos\w*|crisis)\b", re.I)
TOPIC_LINE = "If you or someone you know is in crisis, call or text 988, or call 911 in an emergency."

PHONE_911 = {"label": "Call 911", "url": "tel:911", "kind": "call"}

REPLIES = {
    "self_harm": (
        "I'm really sorry you're going through this. You don't have to handle it alone, and help is available "
        "right now, free, 24 hours a day.\n\n"
        "- **If you're in danger right now, call 911.**\n"
        "- **Call or text 988** to reach the 988 Suicide & Crisis Lifeline, or "
        "[chat with them online](https://988lifeline.org/chat/).\n"
        "- **Hawaiʻi CARES:** call 808-832-3100 or toll-free 1-800-753-6879 for crisis support and help finding "
        "mental health or substance use care.\n\n"
        "Med-QUEST covers mental health care. Whenever you're ready, I can help you find out how to get it.",
        [{"label": "Call or text 988", "url": "tel:988", "kind": "call"},
         {"label": "Chat with 988 online", "url": "https://988lifeline.org/chat/", "kind": "page"},
         PHONE_911]),
    "abuse": (
        "I'm sorry this is happening to you. Your safety comes first.\n\n"
        "- **If you're in danger right now, call 911.**\n"
        "- **National Domestic Violence Hotline:** call 1-800-799-7233 or text START to 88788. It's free, "
        "confidential and open 24 hours a day. You can also [chat with them online](https://www.thehotline.org).\n"
        "- **If a child is being hurt:** call 911, or the Childhelp National Child Abuse Hotline at 1-800-422-4453.\n\n"
        "Whenever you're ready, I can help with questions about Med-QUEST coverage.",
        [PHONE_911,
         {"label": "Call the Domestic Violence Hotline", "url": "tel:18007997233", "kind": "call"},
         {"label": "Chat with the hotline online", "url": "https://www.thehotline.org", "kind": "page"}]),
    "emergency": (
        "**If this is an emergency, call 911 now.**\n\n"
        "- **Possible poisoning or overdose:** call Poison Control at 1-800-222-1222, free, 24 hours a day.\n"
        "- **If you're thinking about harming yourself:** call or text 988.",
        [PHONE_911,
         {"label": "Call Poison Control", "url": "tel:18002221222", "kind": "call"},
         {"label": "Call or text 988", "url": "tel:988", "kind": "call"}]),
}


def check(text):
    """Return the kind of crisis the message states, or None."""
    if SELF_HARM.search(text): return "self_harm"
    if ABUSE.search(text): return "abuse"
    if EMERGENCY.search(text): return "emergency"
    return None


def reply(kind):
    return REPLIES.get(kind) or REPLIES["self_harm"]
