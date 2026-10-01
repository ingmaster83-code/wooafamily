"""편의점·마트 진행 중 이벤트/기획전 목록 수집 -> {store, title, period, image, url}.
제목·기간·썸네일·원문 링크만 가져오고, 본문은 가져오지 않는다(원문은 각 매장 페이지에서 보게 연결)."""
import re
from bs4 import BeautifulSoup
import dealcommon  # noqa: F401  (collect/ 경로 등록)
from common import http, now_kst
import emarteveryday

PERIOD = re.compile(r"(20\d\d[-.]\d\d[-.]\d\d)\s*~\s*(20\d\d[-.]\d\d[-.]\d\d)")


def seven():
    base = "https://www.7-eleven.co.kr"
    soup = BeautifulSoup(http(base + "/event/eventList.asp"), "lxml")
    out = []
    for li in soup.select("li"):
        img = li.select_one("a.event_img img")
        pm = PERIOD.search(li.get_text(" ", strip=True))
        if not (img and pm and img.get("alt")):
            continue
        out.append({"store": "세븐일레븐", "title": img["alt"].strip(), "period": f"{pm.group(1)} ~ {pm.group(2)}",
                    "image": None, "url": base + "/event/eventList.asp"})  # 세븐 이미지는 핫링크가 막혀 있어 쓰지 않음
    return out


def emart24():
    base = "https://emart24.co.kr"
    soup = BeautifulSoup(http(base + "/event/ing"), "lxml")
    out = []
    for a in soup.select("a.eventWrap"):
        pm = PERIOD.search(a.get_text(" ", strip=True))
        p = a.select_one("p")
        if not (pm and p):
            continue
        title = re.sub(r"\s+", " ", PERIOD.sub("", p.get_text(" ", strip=True))).strip()
        img = a.select_one("img")
        out.append({"store": "이마트24", "title": title, "period": f"{pm.group(1)} ~ {pm.group(2)}",
                    "image": img.get("src") if img else None, "url": base + a["href"]})
    return out


def everyday():
    out = []
    for ex in emarteveryday.exhibitions():
        title = re.sub(r"\s*\d{2}-\d{2}-\d{2}\s*~\s*\d{2}-\d{2}-\d{2}\s*$", "", ex["title"]).strip()
        out.append({"store": "이마트에브리데이", "title": title, "period": ex["period"], "image": None, "url": ex["url"]})
    return out


def collect():
    rows = []
    for fn in (seven, emart24, everyday):
        try:
            rows += fn()
        except Exception as e:  # noqa: BLE001
            print("events skip", fn.__name__, str(e)[:100])
    out = []
    for r in rows:
        r["period"] = (r["period"] or "").replace(".", "-")
        pm = PERIOD.search(r["period"])
        if pm:  # 상시 진행형(기간이 62일 초과)은 이벤트로 보지 않는다
            from datetime import date
            a, b = (date.fromisoformat(pm.group(i)) for i in (1, 2))
            if (b - a).days > 62:
                continue
        r["fetched_at"] = now_kst()
        out.append(r)
    return out


if __name__ == "__main__":
    import sys
    from collections import Counter
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), Counter(x["store"] for x in r))
    for x in r[:2] + r[8:10] + r[-2:]:
        print(x["store"], "|", x["title"][:40], "|", x["period"], "|", (x["image"] or "")[:50])
