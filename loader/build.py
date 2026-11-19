"""Turns loader/raw/site.json into knowledge base files in knowledge-base/build/.

    python3 loader/build.py            members and the public only
    python3 loader/build.py --all      providers and agency pages too

Files are already split by section: create the knowledge base with no
chunking, or Bedrock will re-split them.
"""
import json, re, shutil, sys
from urllib.parse import quote
from collections import Counter, defaultdict
from pathlib import Path

from forms import describe_files, current_versions

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "site.json"
OUT = HERE.parent / "knowledge-base" / "build"
OVERRIDES = HERE.parent / "knowledge-base" / "forms-overrides.json"
ANSWERS = HERE.parent / "knowledge-base" / "answers"
SITE = "https://medquest.hawaii.gov"

# Who each part of the site is for. Only member and public pages load without --all.
AUDIENCE = [
    ("/en/plans-providers", "providers"),
    ("/en/resources/reports", "agency"), ("/en/resources/solicitations-contract", "agency"),
    ("/en/resources/rules-and-policy", "agency"), ("/en/resources/quality-strategy", "agency"),
    ("/en/resources/community-partners", "agency"), ("/en/resources/hawaii-health-analytics-program", "agency"),
    ("/en/about/state-plan-1115", "agency"), ("/en/about/Med-QUEST", "agency"),
    ("/en/page/logout", "skip"),
    ("/en/members-applicants/already-covered/going-home-plus/GHP-test", "skip"),
]
SKIP_BLOCKS = {"divider", "breadcrumb", "navigationList", "mediaBlock", "youtube", "formBlock", "subNavbar", "slide",
               "story", "imagecarousel", "providerDirectory", "formularySearch", "displayPosts", "news", "documentList",
               "languagehelp", "banner", "select", "textarea", "phone", "email", "date", "number", "state", "upload", "radio"}
TOPICS = {
    "apply": r"\bappl(y|ying|ication)\b|\bdhs ?1100\b",
    "renew": r"\brenew",
    "report-a-change": r"change of circumstance|report (a |any )?change|update (your )?information|\b1179a?\b",
    "health-plans": r"health plan|alohacare|\bhmsa\b|kaiser|ohana|unitedhealthcare",
    "benefits": r"covered (benefit|service)|benefits?\b|coverage includes",
    "dental": r"dental|dentist",
    "transportation": r"transportation|\bnemt\b|\bride\b|handi-?van",
    "prescriptions": r"prescription|pharmac|drug",
    "behavioral-health": r"behavioral|mental health|psychiatr|substance",
    "long-term-care": r"long[- ]term (care|services)|\bltss\b|nursing (home|facility)",
    "eligibility": r"eligib|qualif|income|poverty level|\bfpl\b",
    "appeals": r"appeal|grievance|hearing",
    "contact": r"\boffice\b|call center|1-800-316-8005|\bfax\b",
    "forms": r"\bform\b|\bdhs ?\d{3,4}",
    "coverage-ended": r"coverage (ended|ends|stop)|no longer (covered|qualify)|terminat",
    "privacy": r"privacy|hipaa|confidential",
}
FORM_REF = re.compile(r"\bDHS[ _-]?(\d{3,4}[A-Z]?(?:-\d(?!\d))?)\b", re.I)


def audience_of(path):
    return next((a for prefix, a in AUDIENCE if path.startswith(prefix)), "members")


def page_path(page):
    crumbs = page.get("breadcrumbs") or []
    return crumbs[-1]["url"] if crumbs and crumbs[-1].get("url") else "/en/" + page["slug"]


def safe(url):
    """Encode spaces and brackets, which would end a Markdown link early."""
    return url.replace(" ", "%20").replace("(", "%28").replace(")", "%29") if url else url


def absolute(url, page_url):
    if not url: return None
    url = url.strip()
    if url.startswith("#"): return safe(page_url + url)
    if url.startswith("/"): return safe(SITE + url)
    if url.startswith("http://medquest.hawaii.gov"): return safe("https" + url[4:])
    return safe(url)


class Renderer:
    """Converts the site's Lexical rich text to heading and Markdown items."""

    def __init__(self, page_url):
        self.page_url = page_url
        self.links = []          # (text, url) for every link on the page

    def link_url(self, node):
        f = node.get("fields") or {}
        if f.get("linkType") == "internal" and isinstance(f.get("doc"), dict):
            value = f["doc"].get("value")
            if isinstance(value, dict):
                if f["doc"].get("relationTo") == "media": return absolute(value.get("url"), self.page_url)
                crumbs = value.get("breadcrumbs") or []
                path = crumbs[-1].get("url") if crumbs else ("/en/" + value["slug"] if value.get("slug") else None)
                return absolute(path, self.page_url)
            return None
        return absolute(f.get("url"), self.page_url)

    def inline(self, nodes):
        out = []
        for n in nodes or []:
            t = n.get("type")
            if t == "text":
                text = n.get("text", "")
                out.append(f"**{text.strip()}** " if n.get("format", 0) & 1 and text.strip() else text)
            elif t in ("link", "autolink"):
                text = self.inline(n.get("children")).strip()
                url = self.link_url(n)
                if url and text:
                    self.links.append((re.sub(r"\*\*", "", text), url))
                    out.append(f"[{text}]({url})")
                else:
                    out.append(text)
            elif t == "linebreak":
                out.append("\n")
            elif t == "tab":
                out.append(" ")
            else:
                out.append(self.inline(n.get("children")))
        return "".join(out)

    def is_bold_line(self, node):
        texts = [c for c in node.get("children") or [] if c.get("type") == "text" and c.get("text", "").strip()]
        whole = "".join(c["text"] for c in texts).strip()
        return (texts and all(c.get("format", 0) & 1 for c in texts) and len(whole) < 90
                and not whole.endswith((".", ":")) and len(texts) == len([c for c in node.get("children") or [] if c.get("type") != "linebreak"]))

    def blocks(self, nodes, depth=0):
        items = []
        for n in nodes or []:
            t = n.get("type")
            if t == "heading":
                text = self.inline(n.get("children")).replace("**", "").strip()
                if text: items.append(("heading", text, None))
            elif t == "paragraph" or t == "largeBody":
                if self.is_bold_line(n):
                    items.append(("heading", self.inline(n.get("children")).replace("**", "").strip(), None))
                else:
                    text = self.inline(n.get("children")).strip()
                    if text: items.append(("text", text))
            elif t == "list":
                lines = []
                for i, li in enumerate(n.get("children") or [], 1):
                    nested = [c for c in li.get("children") or [] if c.get("type") == "list"]
                    own = [c for c in li.get("children") or [] if c.get("type") != "list"]
                    text = self.inline(own).strip()
                    bullet = f"{i}." if n.get("listType") == "number" else "-"
                    if text: lines.append("  " * depth + f"{bullet} {text}")
                    for sub in nested:
                        lines += [x[1] for x in self.blocks([sub], depth + 1) if x[0] == "text"]
                if lines: items.append(("text", "\n".join(lines)))
            elif t == "table":
                rows = []
                for r in n.get("children") or []:
                    cells = [self.inline(c.get("children") and [x for p in c["children"] for x in (p.get("children") or [])]).strip().replace("\n", " ")
                             for c in r.get("children") or []]
                    if any(cells): rows.append("| " + " | ".join(cells) + " |")
                if rows:
                    rows.insert(1, "|" + "---|" * rows[0].count(" | ") + "---|")
                    items.append(("text", "\n".join(rows)))
            elif t == "quote":
                items.append(("text", "> " + self.inline(n.get("children")).strip()))
            elif n.get("children"):
                items += self.blocks(n["children"], depth)
        return items

    def rich(self, value):
        if isinstance(value, dict) and isinstance(value.get("root"), dict):
            return self.blocks(value["root"].get("children"))
        if isinstance(value, str) and value.strip():
            return [("text", value.strip())]
        return []

    def layout(self, blocks):
        items = []
        for b in blocks or []:
            kind = b.get("blockType")
            if kind in SKIP_BLOCKS: continue
            if kind == "text":
                body = self.rich(b.get("content"))
                if b.get("anchorId") and body:
                    lead = re.match(r"\*\*(.+?)\*\* ?", body[0][1]) if body[0][0] == "text" else None
                    if body[0][0] == "heading": body[0] = ("heading", body[0][1], b["anchorId"])
                    elif lead:   # a bold title run into the first paragraph
                        body[0:1] = [("heading", lead.group(1).strip(), b["anchorId"]), ("text", body[0][1][lead.end():].strip())]
                    else: body.insert(0, ("heading", None, b["anchorId"]))
                items += body
            elif kind == "content":
                for c in b.get("columns") or []:
                    items += self.rich(c.get("richText")) + self.layout(c.get("blocks"))
            elif kind == "accordion":
                items += [("heading", (b.get("title") or "").strip(), None)] + self.rich(b.get("content"))
            elif kind == "tabs":
                for tab in b.get("tabs") or []:
                    items.append(("heading", (tab.get("label") or "").strip(), None))
                    for c in tab.get("columns") or []:
                        items += self.rich(c.get("richText")) + self.layout(c.get("blocks"))
            elif kind == "columnBlock":
                for c in b.get("columns") or []: items += self.layout(c.get("blocks"))
            elif kind == "threeColumn":
                for k in ("column1", "column2", "column3"): items += self.layout(b.get(k))
            elif kind == "card":
                for card in b.get("cards") or []:
                    items += [("heading", (card.get("title") or "").strip(), None)] + self.rich(card.get("content"))
                    items += self.button(card.get("link"))
            elif kind == "message":
                items += self.rich(b.get("message"))
            elif kind == "button":
                items += self.button(b.get("link"))
            elif kind == "faq":
                for topic in b.get("topics") or []:
                    for q in topic.get("questions") or []:
                        items += [("heading", (q.get("question") or "").strip(), None)] + self.rich(q.get("answer"))
            else:
                # An unfamiliar block: keep any rich text inside it.
                for v in b.values():
                    if isinstance(v, (dict, list)): items += self.rich(v) if isinstance(v, dict) else self.layout([x for x in v if isinstance(x, dict) and x.get("blockType")])
        return items

    def button(self, link):
        if not isinstance(link, dict) or not link.get("label"): return []
        if link.get("type") == "reference" and isinstance(link.get("reference"), dict):
            value = link["reference"].get("value")
            crumbs = (value.get("breadcrumbs") if isinstance(value, dict) else None) or []
            url = absolute(crumbs[-1].get("url") if crumbs else None, self.page_url)
        else:
            url = absolute(link.get("url"), self.page_url)
        if not url: return []
        self.links.append((link["label"], url))
        return [("text", f"[{link['label'].strip()}]({url})")]


def sections(items, title):
    """Group items under headings, merge tiny sections and split long ones."""
    out = []
    for item in items:
        if item[0] == "heading":
            if out and not out[-1]["body"] and (out[-1]["heading"] or "") and not out[-1]["anchor"]:
                out[-1]["heading"] = " – ".join(x for x in (out[-1]["heading"], item[1]) if x)
                out[-1]["anchor"] = out[-1]["anchor"] or item[2]
            else:
                out.append({"heading": item[1], "anchor": item[2], "body": []})
        else:
            if not out: out.append({"heading": None, "anchor": None, "body": []})
            out[-1]["body"].append(item[1])
    out = [s for s in out if s["body"]]
    words = lambda s: sum(len(b.split()) for b in s["body"])
    merged = []
    for s in out:
        # Merge tiny sections into the previous one unless they have their own anchor.
        if merged and words(s) < 40 and words(merged[-1]) < 450 and not s["anchor"]:
            merged[-1]["body"].append(f"**{s['heading']}**" if s["heading"] else "")
            merged[-1]["body"] += s["body"]
        else:
            merged.append(s)
    final = []
    for s in merged:
        chunk, count = [], 0
        for b in s["body"]:
            if count > 450 and chunk:
                final.append({**s, "body": chunk}); chunk, count = [], 0
                s = {**s, "heading": (s["heading"] or title) + " (continued)"}
            chunk.append(b); count += len(b.split())
        if chunk: final.append({**s, "body": chunk})
    return final


def write_label(path, attributes):
    """Write the .metadata.json for a knowledge base file.

    Bedrock rejects empty values and labels over 1 KB, so trim to fit."""
    a = {k: v for k, v in attributes.items() if v not in ("", None, [])}
    if a.get("page_url") == a.get("url"): a.pop("page_url", None)
    text = lambda: json.dumps({"metadataAttributes": a}, separators=(",", ":"), ensure_ascii=False)
    while len(text().encode()) > 1000 and len(a.get("form_numbers", [])) > 1:
        a["form_numbers"] = a["form_numbers"][:-1]
    while len(text().encode()) > 1000 and len(a.get("topics", [])) > 1:
        a["topics"] = a["topics"][:-1]
    if len(text().encode()) > 1000: a.pop("section", None)
    assert len(text().encode()) <= 1000, path
    Path(str(path) + ".metadata.json").write_text(text())


def topics_of(text):
    hits = Counter({t: len(re.findall(rx, text, re.I)) for t, rx in TOPICS.items()})
    return [t for t, n in hits.most_common(4) if n]


def main():
    include_all = "--all" in sys.argv
    site = json.loads(RAW.read_text())
    overrides = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}
    if OUT.exists(): shutil.rmtree(OUT)
    (OUT / "pages").mkdir(parents=True); (OUT / "forms").mkdir()

    report = {"skipped": [], "empty": [], "pages": 0, "sections": 0, "words": 0}
    resources = {"pulled": site["pulled"], "pages": [], "forms": []}
    link_texts = defaultdict(Counter)      # file url -> the words pages use for it
    mentions = defaultdict(list)           # form number -> pages that mention it

    for path, entries in site["linked"].items():
        for x in entries:
            if x["text"]: link_texts[SITE + "/api/media/file/" + quote(x["file"])][x["text"]] += 1

    # Replace links to old copies of a form with the current one (listed in the report).
    files = describe_files(site)
    chosen = current_versions(files, overrides)
    current_url = {}
    for form, c in chosen.items():
        p = c["picks"]; main_file = p.get("fillable form") or p.get("form") or next(iter(p.values()))
        current_url[form] = safe(SITE + main_file["url"])
    report["replaced"] = []

    def fix_links(body, page_url):
        def swap(m):
            text, url = m.group(1), m.group(2)
            # The form number is in the link text or just before it on the same line.
            before = m.string[:m.start()].rsplit("\n", 1)[-1][-120:]
            forms = ["DHS " + f.upper() for f in FORM_REF.findall(text) or FORM_REF.findall(before)[-1:]]
            if not forms or not url.lower().split("?")[0].endswith(".pdf") or forms[0] not in current_url: return m.group(0)
            if "instruction" in text.lower(): return m.group(0)
            new = current_url[forms[0]]
            if new == url: return m.group(0)
            report["replaced"].append((page_url, forms[0], url))
            return f"[{text}]({new})"
        return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", swap, body)

    # Keep sections repeated on many pages only once, so copies don't crowd searches.
    seen_bodies = {}
    report["repeats"] = 0

    for page in sorted(site["pages"], key=page_path):
        path = page_path(page)
        audience = audience_of(path)
        if audience == "skip" or (audience in ("providers", "agency") and not include_all):
            report["skipped"].append((path, audience)); continue
        page_url = SITE + path
        r = Renderer(page_url)
        secs = sections(r.rich((page.get("hero") or {}).get("richText")) + r.layout(page.get("layout")), page["title"])
        for text, url in r.links: link_texts[url][text] += 1
        if not secs:
            report["empty"].append(path); continue
        report["pages"] += 1
        meta = page.get("meta") or {}
        description = (meta.get("description") or "").strip()
        anchors = []
        slug = path.strip("/").replace("/", "__") or "home"
        for i, s in enumerate(secs, 1):
            heading = s["heading"] or page["title"]
            url = page_url + (f"#{s['anchor']}" if s["anchor"] else "")
            if s["anchor"]: anchors.append({"label": heading, "url": url})
            body = fix_links("\n\n".join(b for b in s["body"] if b), page_url)
            key = re.sub(r"\s+", " ", body).strip().lower()
            if len(key) > 80 and key in seen_bodies:
                report["repeats"] += 1; continue
            seen_bodies[key] = page_url
            forms = sorted({"DHS " + m.upper() for m in FORM_REF.findall(body)})
            for f in forms: mentions[f].append({"title": page["title"], "url": url})
            text = f"# {page['title']}" + (f": {heading}" if heading != page["title"] else "") + f"\n\nPage: {url}\n\n{body}\n"
            name = f"{slug}--{i:02d}.md"
            (OUT / "pages" / name).write_text(text)
            write_label(OUT / "pages" / name, {
                "type": "page", "title": page["title"], "section": heading, "url": url, "page_url": page_url,
                "audience": audience, "topics": topics_of(path + " " + heading + " " + body) or ["general"],
                "form_numbers": forms or ["none"], "updated": (page.get("updatedAt") or "")[:10]})
            report["sections"] += 1; report["words"] += len(body.split())
        resources["pages"].append({"title": page["title"], "url": page_url, "description": description,
                                   "audience": audience, "topics": topics_of(path + " " + page["title"] + " " + description),
                                   "sections": anchors})

    # Form cards: member forms and every form a loaded page mentions.
    wanted = {f["form"] for f in files if f["member_page"]} | set(mentions)
    if include_all: wanted = set(chosen)
    month = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    report["forms"] = 0; report["unnamed"] = []
    for form in sorted(wanted & set(chosen), key=lambda f: (int(re.search(r"\d+", f).group()), f)):
        c = chosen[form]; picks = c["picks"]
        names = Counter()
        # The site's title for the file, then the words pages link it with.
        for f in sorted(c["picks"].values(), key=lambda f: f["kind"] != "form"):
            if f.get("title"): names[f["title"]] += 100
        for f in c["files"]:
            for text, n in link_texts.get(SITE + f["url"], {}).items():
                clean = re.sub(r"\(?rev[^)]*\)?|fillable|pdf|instructions?|form\b|\bDHS[ _-]?\d{3,4}[A-Z]?(-\d)?|[“”\"']", " ", text, flags=re.I)
                clean = re.sub(r"\s+", " ", clean).strip(" -–:")
                if len(clean) > 6: names[clean] += n
        name = names.most_common(1)[0][0] if names else None
        if name:   # "DHS 1179A Change of ... Form (Rev. 02/2023)" -> "Change of ... Form"
            name = re.sub(r"\bDHS[ _-]?\d{3,4}[A-Z]?(-\d)?\b|\(?\brev(ised)?\b[^)]*\)?|,? ?revised \w+ \d{4}", " ", name, flags=re.I)
            name = re.sub(r"^(form|fillable)\b[ ,]*", "", re.sub(r"\s+", " ", name).strip(" ,-–:"), flags=re.I).strip(" ,-–:") or None
        if not name: report["unnamed"].append(form)
        title = f"Form {form}" + (f": {name}" if name else "")
        rev = c["revision"]
        rev_text = f"{month[rev[1]]} {rev[0]}".strip() if rev else "not in the file name"
        main_file = picks.get("fillable form") or picks.get("form") or next(iter(picks.values()))
        purpose = re.split(r"(?<=\.)\s", (main_file.get("description") or "").strip())[0]
        lines = [f"# {title}", "", f"Form number: {form}", f"Current revision: {rev_text}"]
        if purpose: lines.append(f"What it is for: {purpose}")
        lines.append("")
        for k, label in (("fillable form", "Fillable form (fill in on a computer)"), ("form", "Form to print"),
                         ("instructions", "Instructions"), ("brochure", "Brochure")):
            if k in picks: lines.append(f"- {label}: [{picks[k]['filename']}]({safe(SITE + picks[k]['url'])})")
        where = {m["url"]: m["title"] for m in mentions.get(form, [])}
        if where:
            lines += ["", "Explained on: " + "; ".join(f"[{t}]({u})" for u, t in list(where.items())[:4])]
        lines += ["", "The site also has older versions of this form; use the files above."]
        key = form.replace(" ", "-")
        (OUT / "forms" / f"{key}.md").write_text("\n".join(lines) + "\n")
        page_url = next(iter(where), SITE + "/en/members-applicants/member-forms")
        audience = "members" if any(f["member_page"] for f in c["files"]) or form in mentions else "providers"
        write_label(OUT / "forms" / f"{key}.md", {
            "type": "form", "title": title, "section": "", "url": safe(SITE + main_file["url"]), "page_url": page_url,
            "audience": audience, "topics": ["forms"] + [t for t in topics_of(title + " " + purpose) if t != "forms"][:3],
            "form_numbers": [form], "revision": f"{rev[0]}-{rev[1]:02d}" if rev else "unknown",
            "confirmed": c["confirmed"]})
        resources["forms"].append({"number": form, "name": name, "revision": rev_text, "confirmed": c["confirmed"],
            "download": safe(SITE + main_file["url"]),
            **{k.split()[0]: safe(SITE + picks[k]["url"]) for k in ("form", "fillable form", "instructions") if k in picks},
            "pages": [{"title": t, "url": u} for u, t in where.items()]})
        report["forms"] += 1

    # Hand-written answers (header between --- lines). Each "also_asked" phrasing
    # becomes a small card; long answers match poorly when searched whole.
    # The Lambda swaps a matching card for the full text from answers.json.
    (OUT / "answers").mkdir()
    full_answers = {}
    report["answers"] = {"draft": 0, "approved": 0}
    for path in sorted(ANSWERS.glob("*.md")):
        head, body = path.read_text().split("\n---\n", 1)
        h = dict(line.split(": ", 1) for line in head.strip("-\n").splitlines() if ": " in line)
        split = lambda v: [x.strip() for x in re.split(r"[,|]", v or "") if x.strip()]
        body = body.strip()
        title_line, rest = body.split("\n", 1)
        text = f"{title_line}\n\nAlso asked as: {'; '.join(split(h.get('also_asked')))}\n{rest}\n"
        (OUT / "answers" / path.name).write_text(text)
        full_answers[path.stem] = text
        status = h.get("status", "draft").strip()
        report["answers"][status if status in report["answers"] else "draft"] += 1
        write_label(OUT / "answers" / path.name, {
            "type": "answer", "title": h["question"], "section": "", "url": h["link"], "page_url": h["link"],
            "audience": "members", "topics": split(h.get("topics")) or ["general"],
            "form_numbers": split(h.get("forms")) or ["none"], "status": status, "answer_id": path.stem})
        asked = [h["question"]] + [q for q in (x.strip() for x in (h.get("also_asked") or "").split("|")) if q]
        for i, q in enumerate(asked, 1):
            card = OUT / "answers" / f"{path.stem}--q{i:02d}.md"
            card.write_text(q + "\n")
            write_label(card, {"type": "answer", "title": h["question"], "url": h["link"], "audience": "members",
                               "topics": split(h.get("topics")) or ["general"], "status": status,
                               "form_numbers": split(h.get("forms")) or ["none"], "answer_id": path.stem, "card": True})

    (OUT / "resources.json").write_text(json.dumps(resources, indent=1))
    (OUT / "answers.json").write_text(json.dumps(full_answers, indent=1))

    # The same content for the Lambda's keyword search (lambda/v2/bm25.py).
    docs = []
    for folder in ("pages", "forms", "answers"):
        for md in sorted((OUT / folder).glob("*.md")):
            if "--q" in md.stem: continue
            label = json.loads(Path(str(md) + ".metadata.json").read_text())["metadataAttributes"]
            docs.append({"text": md.read_text(), "title": label.get("title", ""), "section": label.get("section", ""),
                         "type": label.get("type", "page"), "url": label.get("url", ""), "page_url": label.get("page_url", label.get("url", "")),
                         "form_numbers": label.get("form_numbers", []), "answer_id": label.get("answer_id", "")})
    (OUT / "search-docs.json").write_text(json.dumps(docs, ensure_ascii=False))
    lines = [f"# Knowledge base build", "", f"Site pulled {site['pulled'][:16].replace('T', ' ')} UTC. "
             f"{'All audiences' if include_all else 'Members and the public only (phase 1)'}.", "",
             f"- Pages loaded: {report['pages']}, in {report['sections']} sections ({report['words']:,} words)",
             f"- Answers: {report['answers']['approved']} approved, {report['answers']['draft']} drafts",
             f"- Form cards: {report['forms']} ({sum(1 for f in resources['forms'] if f['confirmed'])} confirmed by a person, the rest best guesses)",
             f"- Pages left out: {len(report['skipped'])}; pages with no text: {len(report['empty'])}; repeated sections dropped: {report['repeats']}", "",
             "## Links to old copies of forms, replaced with the current one", "",
             *[f"- {p}: {f} was {u}" for p, f, u in report["replaced"]], "",
             "## Pages with no text", "", *[f"- {p}" for p in report["empty"]], "",
             "## Forms with no name found on the site", "", *[f"- {f}" for f in report["unnamed"]], "",
             "## Pages left out", "", *[f"- {p} ({a})" for p, a in report["skipped"]], ""]
    (OUT / "report.md").write_text("\n".join(lines))
    print("\n".join(lines[:8]))


if __name__ == "__main__":
    main()
