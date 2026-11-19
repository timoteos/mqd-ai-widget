"""Keyword search (BM25) over the knowledge base.

Catches exact strings that meaning-based search can miss, such as form
numbers and program names. Reads search-docs.json from loader/build.py.
"""
import json
import math
import re
from collections import Counter
from pathlib import Path

STOP = set("""a an and are as at be by can do does for from get how i if in is it me my of on or our so that the
their them there these this to us was we what when where which who why will with you your med quest medquest
medicaid hawaii please tell know""".split())


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower().replace("ʻ", "").replace("'", "")) if len(t) > 1 and t not in STOP]


class Index:
    def __init__(self, path, k1=1.2, b=0.75):
        self.docs = json.loads(Path(path).read_text())
        self.k1, self.b = k1, b
        self.tf = [Counter(tokens(d["title"] + " " + d.get("section", "") + " " + d["text"])) for d in self.docs]
        self.length = [sum(c.values()) for c in self.tf]
        self.avg = sum(self.length) / max(1, len(self.length))
        df = Counter(t for c in self.tf for t in c)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query, k=3):
        q = set(tokens(query))
        scored = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for t in q:
                f = tf.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.length[i] / self.avg))
            if s > 0: scored.append((s, i))
        scored.sort(reverse=True)
        return [(s, self.docs[i]) for s, i in scored[:k]]
