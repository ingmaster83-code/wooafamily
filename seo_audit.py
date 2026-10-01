"""생성된 site/ 의 SEO 점검: 제목·설명 길이/중복/누락, H1 개수, canonical, og, JSON-LD, 이미지 alt."""
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
files = [f for f in glob.glob(os.path.join(ROOT, "**", "index.html"), recursive=True)]
rows = []
for f in files:
    h = open(f, encoding="utf-8").read()
    g = lambda p: (re.search(p, h, re.S) or [None, None])[1]
    rows.append({
        "path": "/" + os.path.relpath(f, ROOT).replace("\\", "/").replace("index.html", ""),
        "title": g(r"<title>(.*?)</title>"), "desc": g(r'<meta name="description" content="(.*?)">'),
        "canon": g(r'<link rel="canonical" href="(.*?)">'), "ogt": g(r'<meta property="og:title" content="(.*?)">'),
        "ogi": g(r'<meta property="og:image" content="(.*?)">'), "tw": g(r'<meta name="twitter:card" content="(.*?)">'),
        "h1": len(re.findall(r"<h1[ >]", h)), "ld": len(re.findall(r"application/ld\+json", h)),
        "img_noalt": len(re.findall(r"<img(?![^>]*\balt=\"[^\"]+\")[^>]*>", h)),
    })


def kind(p):
    if p.startswith("/phone/plans/"):
        return "요금제 상세"
    if p.startswith("/deal/event"):
        return "이벤트"
    if p.startswith("/deal/"):
        return "행사"
    if p.startswith("/phone/calculator"):
        return "계산기"
    if p.startswith("/phone/"):
        return "알뜰폰 목록"
    return "기타"


by = defaultdict(list)
for r in rows:
    by[kind(r["path"])].append(r)
print(f"총 {len(rows)} 페이지\n")
for k, lst in by.items():
    tl = [len(r["title"] or "") for r in lst]
    dl = [len(r["desc"] or "") for r in lst]
    print(f"[{k}] {len(lst)}개 | 제목 길이 평균 {sum(tl)//len(tl)} (최대 {max(tl)}) | 설명 평균 {sum(dl)//len(dl)} (최대 {max(dl)}) | "
          f"h1≠1: {sum(1 for r in lst if r['h1'] != 1)} | og:image 없음: {sum(1 for r in lst if not r['ogi'])} | "
          f"twitter 없음: {sum(1 for r in lst if not r['tw'])} | alt 없는 img 있는 페이지: {sum(1 for r in lst if r['img_noalt'])} | JSON-LD 없음: {sum(1 for r in lst if not r['ld'])}")
for field in ("title", "desc"):
    c = Counter(r[field] for r in rows if r[field])
    d = {k: v for k, v in c.items() if v > 1}
    print(f"\n중복 {field}: {len(d)}종 / {sum(d.values())}페이지")
    for k, v in sorted(d.items(), key=lambda x: -x[1])[:5]:
        print(f"   {v}x  {k[:80]}")
print("\n제목 60자 초과:", sum(1 for r in rows if len(r["title"] or "") > 60), "| 설명 120자 초과:", sum(1 for r in rows if len(r["desc"] or "") > 120), "| 설명 70자 미만:", sum(1 for r in rows if len(r["desc"] or "") < 70))
print("\n샘플")
for k in by:
    r = by[k][len(by[k]) // 3]
    print(f"[{k}] {r['path']}\n   T: {r['title']}\n   D: {r['desc']}")
