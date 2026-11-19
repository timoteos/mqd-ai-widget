"""Reads DHS form numbers, kinds and revisions from the site's file names,
and picks the current version of each form.

File names are used because the site's upload dates don't reflect revisions.
"""
import re

LANGS = ["Chinese (Simplified)", "Chinese (tradition)", "Chuukese", "Ilokano", "Japanese", "Korean", "Kosraean",
         "Marshallese", "Olelo Hawaii", "Pohnpeian", "Russian", "Samoan", "Spanish", "Tagalog", "Thai", "Tongan",
         "Ukrainian", "Vietnamese", "English"]

def form_id(name, on_forms_page):
    s = name.replace("_", " ")
    m = re.search(r"DHS[ -]?(?:Form)?[ -]?(\d{3,4})([A-Za-z])?(-\d(?!\d))?", s, re.I)
    if not m and on_forms_page:
        m = re.match(r"^(?:Fillable )?(\d{3,4})([A-Za-z])?(-\d(?!\d))?\b", s)
    if m:
        return "DHS " + m.group(1) + (m.group(2) or "").upper() + (m.group(3) or "")
    if re.search(r"HJUP-?8a", name, re.I): return "HJUP-8a"
    if re.search(r"HJUP-?8\b", name, re.I): return "HJUP-8"
    return None

def kind(name):
    n = name.lower()
    if re.match(r"(qi|ffs|admx|ccs|med|bh)[ -]?\d{4}", n): return "memo or memo attachment"
    for lang in LANGS:
        if n.startswith(lang.lower()) and lang != "English":
            return "translation (" + lang + ")"
    if re.search(r"instr|inst\b|inst-|instruction", n): return "instructions"
    if "brochure" in n: return "brochure"
    if "poster" in n: return "poster"
    if "buckslip" in n: return "buckslip"
    if "fillable" in n: return "fillable form"
    return "form"

def revision(name):
    """Return (year, month) of the revision in the file name, or None."""
    # Posting dates like 'je07-26-21' or 'Post_5-11-23' are not revisions.
    s = re.sub(r"(je|em|am|jl|ma|ma?je|post)[ _.-]?\d{1,2}[._-]\d{1,2}[._-]\d{2,4}", " ", name, flags=re.I)
    s = re.sub(r"\.pdf$", "", s, flags=re.I)
    # the form number itself is not a date
    s = re.sub(r"^(?:Fillable )?\d{3,4}[A-Z]?\b|DHS[ _-]?\d{3,4}[A-Z]?(?:-\d(?!\d))?", " ", s, flags=re.I)
    # MMDDYYYY: 01242024
    m = re.search(r"(?<!\d)(0[1-9]|1[0-2])([0-3]\d)(20\d{2})(?!\d)", s)
    if m: return (int(m.group(3)), int(m.group(1)))
    # MMYY run into a posting date: 0713092613, Rev0813092313
    m = re.search(r"(?<!\d)(0[1-9]|1[0-2])(\d{2})\d{6}(?!\d)", s)
    if m: return (2000 + int(m.group(2)), int(m.group(1)))
    # month + four-digit year: 10.2026, 04. 2023, 07_2023, 11-2022, (9.2024), Dec.2024
    m = re.search(r"(?<!\d)(\d{1,2})[ ._-]{1,2}(20\d{2})(?!\d)", s)
    if m and 1 <= int(m.group(1)) <= 12: return (int(m.group(2)), int(m.group(1)))
    mon = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[ ._-]*(20\d{2})", s, re.I)
    if m: return (int(m.group(2)), mon[m.group(1).lower()])
    # 04.023 typo in a 2023 revision
    m = re.search(r"Rev\.? ?(\d{2})\.0(2\d)\b", s)
    if m: return (2000 + int(m.group(2)), int(m.group(1)))
    # Rev + month + two-digit year: Rev_12_17, Rev-0813, Rev0613, Rev 7.18, Rev. 07-26, rev2021
    m = re.search(r"rev[ ._-]*(\d{1,2})[ ._-]?(\d{2})(?!\d)", s, re.I)
    if m and 1 <= int(m.group(1)) <= 12: return (2000 + int(m.group(2)) if int(m.group(2)) < 50 else 1900 + int(m.group(2)), int(m.group(1)))
    m = re.search(r"rev[ ._-]*(20\d{2})", s, re.I)
    if m: return (int(m.group(1)), 0)
    # effective dates on the HJUP forms: 03-24-26 Effective, Jan 1.28.25
    m = re.search(r"(?<!\d)(\d{1,2})[.-](\d{1,2})[.-](\d{2})(?!\d)", s)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31: return (2000 + int(m.group(3)), int(m.group(1)))
    # bare MMYY or MM_YY after the form number: DHS-1188-0509, DHS_204_02_18, DHS_1145_Form_06_20, 1101 ... 10-13
    m = re.search(r"(?:^|[ _-])(0[1-9]|1[0-2])[_-]?(\d{2})(?=[ _-]|$)", s)
    if m: y = int(m.group(2)); return (2000 + y if y < 50 else 1900 + y, int(m.group(1)))
    # translations: 'update 022024'
    m = re.search(r"update (\d{2})(\d{2})(\d{2})\b", s)
    if m: return (2000 + int(m.group(3)), int(m.group(1)))
    return None

def describe_files(site):
    """List every DHS form PDF with its form number, kind and revision."""
    member = {x["file"] for x in site["linked"]["/en/members-applicants/member-forms"]}
    provider = {x["file"] for x in site["linked"]["/en/plans-providers/provider-forms"]}
    rows = []
    for f in site["media"]:
        if f["mimeType"] != "application/pdf": continue
        name = f["filename"]
        form = form_id(name, name in member or name in provider)
        if not form: continue
        rows.append({**f, "form": form, "kind": kind(name), "rev": revision(name),
                     "member_page": name in member, "provider_page": name in provider})
    return rows


def rank(f):
    return (f["rev"] or (0, 0), f["created"])


def current_versions(files, overrides=None):
    """Pick the newest revision of each form; overrides (form -> file name) win."""
    overrides = overrides or {}
    by_form = {}
    for f in files: by_form.setdefault(f["form"], []).append(f)
    chosen = {}
    for form, group in by_form.items():
        pinned = next((f for f in group if f["filename"] == overrides.get(form)), None)
        usable = [f for f in group if f["kind"] in ("form", "fillable form")]
        pool = usable or [f for f in group if f["kind"] in ("instructions", "brochure", "poster", "buckslip")] or group
        best = pinned or max(pool, key=rank)
        picks = {best["kind"]: best}
        for k in ("form", "fillable form", "instructions", "brochure"):
            if k in picks: continue
            same = [f for f in group if f["kind"] == k and f["rev"] == best["rev"]]
            if k == "instructions" and not same: same = [f for f in group if f["kind"] == k]
            if same: picks[k] = max(same, key=rank)
        chosen[form] = {"picks": picks, "files": group, "revision": best["rev"], "confirmed": bool(pinned)}
    return chosen
