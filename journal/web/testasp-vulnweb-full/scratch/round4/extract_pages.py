#!/usr/bin/env python3
"""Extract forms / fields / links / params / comments / scripts / metas from every downloaded page."""
import os, re, json, glob
from html.parser import HTMLParser

BASE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(BASE, "..", "pages")

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.forms = []          # dict per form
        self.cur = None
        self.links = []          # href with context
        self.imgs = []
        self.scripts = []        # {'src':..} or {'inline':text}
        self.styles = []
        self.metas = []
        self.comments = []
        self.titles = []
        self._intitle = False
        self._inscript = None
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self.cur = {"attrs": a, "fields": []}
            self.forms.append(self.cur)
        elif tag == "input":
            f = {"tag": "input", "name": a.get("name"), "type": a.get("type", "text"),
                 "value": a.get("value"), "id": a.get("id"), "class": a.get("class")}
            (self.cur["fields"] if self.cur else self.forms.setdefault("_noform", [])).append(f)
        elif tag in ("textarea", "select"):
            f = {"tag": tag, "name": a.get("name"), "type": tag, "value": a.get("value")}
            if isinstance(self.cur, dict): self.cur["fields"].append(f)
        elif tag == "a":
            self.links.append(a.get("href"))
        elif tag == "img":
            self.imgs.append(a.get("src"))
        elif tag == "script":
            if a.get("src"): self.scripts.append({"src": a.get("src")})
            else: self._inscript = {"inline": []}
        elif tag == "link":
            self.styles.append(a.get("href"))
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "title":
            self._intitle = True
    def handle_endtag(self, tag):
        if tag == "form": self.cur = None
        if tag == "script" and self._inscript is not None:
            self.scripts.append({"inline": "".join(self._inscript["inline"])})
            self._inscript = None
        if tag == "title": self._intitle = False
    def handle_data(self, d):
        if self._intitle: self.titles.append(d.strip())
        if self._inscript is not None: self._inscript["inline"].append(d)
    def handle_comment(self, c):
        self.comments.append(c.strip())

results = {}
for f in sorted(glob.glob(os.path.join(PAGES, "*.body"))):
    raw = open(f, "rb").read().decode("latin-1")
    p = P()
    try: p.feed(raw)
    except Exception as e: pass
    name = os.path.basename(f)[:-5]
    forms = []
    for fr in p.forms:
        if fr == "_noform": continue
        if isinstance(p.forms, dict) and not isinstance(fr, dict): continue
        forms.append({
            "method": fr["attrs"].get("method"),
            "action": fr["attrs"].get("action"),
            "name": fr["attrs"].get("name"),
            "enctype": fr["attrs"].get("enctype"),
            "fields": [x for x in fr["fields"]],
        })
    links = []
    for h in p.links:
        if h is None: continue
        q = h.split("?", 1)[1] if "?" in h else ""
        params = sorted(set(re.findall(r"[?&]([^=&]+)=", "?" + q))) if q else []
        asp = re.search(r"([A-Za-z0-9_\-]+\.asp)\b", h, re.I)
        links.append({"href": h, "asp": asp.group(1) if asp else None, "query_params": params})
    results[name] = {
        "bytes": len(raw),
        "title": " ".join(p.titles).strip(),
        "charset_meta": [m for m in p.metas],
        "forms": forms,
        "fields_without_form": p.forms.get("_noform", []) if isinstance(p.forms, dict) else [],
        "links": links,
        "link_count": len(links),
        "imgs": sorted(set(x for x in p.imgs if x)),
        "script_srcs": [s["src"] for s in p.scripts if "src" in s],
        "inline_scripts": [s["inline"] for s in p.scripts if "inline" in s],
        "css_links": [s for s in p.styles if s],
        "comments": p.comments,
    }

out = os.path.join(BASE, "page_extract.json")
json.dump(results, open(out, "w"), indent=1)

# compact console report
for name, d in results.items():
    print("=" * 70)
    print(f"{name}  ({d['bytes']}b)  title={d['title']!r}")
    print(f"  forms: {len(d['forms'])}")
    for fr in d["forms"]:
        print(f"   method={fr['method']} action={fr['action']!r} name={fr['name']} enctype={fr['enctype']}")
        for f in fr["fields"]:
            print(f"     - {f['tag']} name={f['name']} type={f['type']} value={f['value']}")
    print(f"  links({d['link_count']}):")
    for l in d["links"]:
        print(f"     {l['href']}   [asp={l['asp']} params={l['query_params']}]")
    print(f"  script_srcs={d['script_srcs']}  inline_script_count={len(d['inline_scripts'])}  css={d['css_links']}")
    print(f"  imgs={d['imgs']}")
    print("  comments:")
    for c in d["comments"]:
        print(f"     <!-- {' '.join(c.split())} -->")
