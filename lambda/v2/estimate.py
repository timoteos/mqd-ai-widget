"""The eligibility questions and the estimate at the end of them.

Calculated in code, not by the model, so the figures are always the same.
"""
import math
import re


def normalize_text(text):
    t = text.lower().strip().replace("eedgible", "eligible").replace("eligble", "eligible").replace("insurane", "insurance")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t)


PREASSESS_QUESTIONS = [
    {"id": "household_size", "q": "How many people are in your household (including you)?"},
    {"id": "monthly_income", "q": "What is your total household monthly income before taxes?"},
    {"id": "age_group", "q": "How old is the person who needs coverage? If they have a disability, please say so too."},
    {"id": "pregnant", "q": "Is the person who needs coverage pregnant? (yes or no)"},
    {"id": "hawaii_resident", "q": "Do you live in Hawaii? (yes or no)"}
]

# UNVERIFIED: 2025 Hawaii poverty guideline and income chart percentages.
# Not yet checked by Med-QUEST staff; they change every year.
FPL_YEAR = 2025
FPL_FIRST_PERSON = 17990
FPL_EACH_ADDITIONAL = 6330
INCOME_GROUPS = {
    "child": {"label": "Children ages 0-18", "percent": 313},
    "pregnant": {"label": "Pregnant applicants", "percent": 196},
    "adult": {"label": "Adults ages 19-64", "percent": 138},
    "senior": {"label": "Adults age 65 and over", "percent": 100},
}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

def monthly_limit(group, household_size):
    annual = FPL_FIRST_PERSON + FPL_EACH_ADDITIONAL * (household_size - 1)
    return math.ceil(annual * INCOME_GROUPS[group]["percent"] / 100 / 12)

def parse_household_size(text):
    s = normalize_text(text)
    m = re.search(r"\d+", s)
    if m:
        size = int(m.group())
    else:
        size = next((n for word, n in NUMBER_WORDS.items() if re.search(rf"\b{word}\b", s)), None)
        if size is None and re.search(r"\b(just me|only me|myself|alone)\b", s):
            size = 1
    return size if size and 1 <= size <= 20 else None

def parse_monthly_income(text):
    # Not normalize_text: it drops the comma and the decimal point in "$3,000.50".
    s = text.lower().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k\b)?", s)
    if not m:
        return 0.0 if re.search(r"\b(none|nothing|no income|zero)\b", s) else None
    amount = float(m.group(1)) * (1000 if m.group(2) else 1)
    if re.search(r"year|annual", s):
        amount /= 12
    elif re.search(r"every two weeks|every 2 weeks|biweekly|bi-weekly", s):
        amount = amount * 26 / 12
    elif re.search(r"week", s):
        amount = amount * 52 / 12
    return amount

def parse_group(age_text, pregnant_text):
    if normalize_text(pregnant_text).startswith("y"):
        return "pregnant"
    s = age_text.lower()
    numbers = [int(n) for n in re.findall(r"\d+", s)]
    # "19-64" and "65+" are read by their first number.
    first = numbers[0] if numbers else None
    if "senior" in s or (first is not None and first >= 65):
        return "senior"
    if "child" in s or "kid" in s or (first is not None and first <= 18):
        return "child"
    return "adult"

YES = re.compile(r"^(y|yes|yeah|yep|yup|i am|i do|we do|we are|she is|he is|correct|true|sure|of course)\b")
NO = re.compile(r"^(n|no|nope|nah|not|i am not|i'?m not|we don'?t|i don'?t|she is not|he is not|none|false)\b")
PLACES = re.compile(r"\b(hawaii|oahu|maui|kauai|molokai|lanai|big island|hilo|kona|honolulu|here)\b")


def understood(question_id, text):
    """Whether a reply answers this question; anything else is a new question."""
    s = normalize_text(text)
    if "?" in text or re.match(r"(how|what|where|when|why|who|which|can|could|does|is|are|will|should|tell me)\b", s):
        return False
    if question_id == "household_size": return parse_household_size(text) is not None and len(s.split()) <= 12
    if question_id == "monthly_income": return parse_monthly_income(text) is not None and len(s.split()) <= 12
    if question_id == "age_group":
        return bool(re.search(r"\d|child|kid|baby|infant|teen|adult|senior|elder|disab|blind|pregnan", s)) and len(s.split()) <= 12
    if question_id == "hawaii_resident":
        return bool(YES.match(s) or NO.match(s) or PLACES.search(s)) and len(s.split()) <= 12
    return bool(YES.match(s) or NO.match(s) or "pregnan" in s) and len(s.split()) <= 12


def from_facts(facts):
    """Valid answers taken from facts the person already gave."""
    # The model doesn't always use the exact key names asked for.
    alias = {"pregnancy": "pregnant", "is_pregnant": "pregnant", "hawaii": "lives_in_hawaii", "hawaii_resident": "lives_in_hawaii",
             "disabled": "disability", "household": "household_size", "income": "monthly_income", "applicant_age": "age"}
    f = {alias.get(k, k): str(v).strip() for k, v in (facts or {}).items()
         if str(v).strip().lower() not in ("", "none", "null", "unknown")}
    answers = {}
    if f.get("household_size"): answers["household_size"] = f["household_size"]
    if f.get("monthly_income"): answers["monthly_income"] = f["monthly_income"]
    age = " ".join(x for x in (f.get("age", ""), "disability" if f.get("disability", "").lower().startswith("y") else "") if x)
    if age: answers["age_group"] = age
    if f.get("pregnant"): answers["pregnant"] = f["pregnant"]
    if f.get("lives_in_hawaii"): answers["hawaii_resident"] = f["lives_in_hawaii"]
    return {k: v for k, v in answers.items() if understood(k, v)}


def build_estimate(answers):
    """Return the estimate as chat text, or None if an answer can't be read."""
    size = parse_household_size(answers.get("household_size", ""))
    income = parse_monthly_income(answers.get("monthly_income", ""))
    if size is None or income is None:
        return None

    apply_lines = (
        "**Applying is the only way to know for sure, and it is free:**\n"
        "- Online at [medical.mybenefits.hawaii.gov](https://medical.mybenefits.hawaii.gov)\n"
        "- By phone: **1-800-316-8005** (TTY 711)"
    )
    if normalize_text(answers.get("hawaii_resident", "")).startswith("n"):
        return (
            "Med-QUEST is for people who live in Hawaii. If you live in another state, "
            "that state's Medicaid office can help you. If you are moving to Hawaii, "
            "call Med-QUEST at **1-800-316-8005** (TTY 711)."
        )

    group = parse_group(answers.get("age_group", ""), answers.get("pregnant", ""))
    limit = monthly_limit(group, size)
    people = "1 person" if size == 1 else f"{size} people"
    lines = [
        "Here is an estimate from what you told me. It is not a decision.",
        "",
        f"- Household: {people}",
        f"- Monthly income: ${income:,.0f}",
        f"- {INCOME_GROUPS[group]['label']}: the monthly income limit is about **${limit:,}**",
        "",
    ]
    if income <= limit:
        lines.append("Your income is under that limit, so **you may qualify**.")
    else:
        lines.append(
            "Your income is over that limit. **You may still qualify another way**, "
            "because Med-QUEST looks at more than income, so it is still worth applying."
        )
    child_limit = monthly_limit("child", size)
    if group != "child" and size >= 2 and income <= child_limit:
        lines.append(
            f"Children in the household have a higher limit, about **${child_limit:,}** a month, "
            "so they may qualify even when an adult does not."
        )
    if group == "senior":
        lines.append("For people 65 and over, savings and other assets are also looked at.")
    if re.search(r"after[- ]tax|take[- ]home|net\b", answers.get("monthly_income", ""), re.I):
        # The limits are for income before taxes.
        lines.append("You gave your income after taxes. The limit is based on income before taxes, so use that "
                     "figure when you apply; it may change the result.")
    if "disab" in normalize_text(answers.get("age_group", "")) and group != "child":
        # The aged, blind and disabled group is a second way to qualify.
        lines.append("With a disability, you may also qualify through the program for people who are aged, blind or "
                     "disabled, which also looks at savings and other assets.")
    lines += [
        "",
        apply_lines,
        "",
        f"*This estimate uses {FPL_YEAR} income limits, which change each year. Med-QUEST makes the decision.*",
    ]
    return "\n".join(lines)
