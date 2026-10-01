"""이마트 에브리데이 전단 기획전: /exhibition/ExhibitionList 에서 기획전 목록 -> 각 기획전 페이지(서버 렌더링)의 상품 파싱.
상품마다 상품명, 정가(actualPrice), 행사가(salePrice), 용량당 단가 문구, 바코드(skuCode), 이미지가 들어 있다."""
import re
import time
from bs4 import BeautifulSoup
from dealcommon import make_deal
from common import DELAY, http

BASE = "https://emile.emarteveryday.co.kr"
LIST = BASE + "/exhibition/ExhibitionList"


def exhibitions():
    soup = BeautifulSoup(http(LIST), "lxml")
    out, seen = [], set()
    for a in soup.select("a[href*='ExhibitionView']"):
        href = a.get("href", "")
        m = re.search(r"uid=([A-Za-z0-9]+)", href)
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        txt = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        pm = re.search(r"(\d{2}-\d{2}-\d{2})\s*~\s*(\d{2}-\d{2}-\d{2})", txt)
        out.append({"uid": m.group(1), "title": txt, "period": f"20{pm.group(1)} ~ 20{pm.group(2)}" if pm else None,
                    "url": BASE + "/exhibition/ExhibitionView?uid=" + m.group(1)})
    return out


def parse_goods(html, ex):
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for g in soup.select("div.goods"):
        title = g.select_one(".goods__title")
        inp = {i.get("id"): i.get("value") for i in g.select(".goods__price-info input")}
        if not title or not inp.get("salePrice"):
            continue
        sale, actual = int(inp["salePrice"]), int(inp.get("actualPrice") or inp["salePrice"])
        txt = re.sub(r"\s+", " ", g.get_text(" ", strip=True))
        if g.select_one(".thumbnail__sold-out") and "is-sold" in " ".join(g.get("class", [])):
            continue
        img = g.select_one("img")
        src = (img.get("data-src") or img.get("src") or "") if img else ""
        unit = re.search(r"((?:\d+\s*(?:g|kg|ml|L|개|매|롤|입)|\d+)당\s*[\d,]+원)", txt)
        mult = re.search(r"\b([123])\+1\b", txt)
        flags = [f.get_text(strip=True) for f in g.select(".goods__flag span")]
        out_kw = {"flags": ", ".join(flags) or None, "size_unit": unit.group(1) if unit else None}
        sku = inp.get("skuCode")
        key = f"everyday-{sku}"
        nm = title.get_text(strip=True)
        if mult:
            d = make_deal("이마트에브리데이", "mart", key, nm, f"{mult.group(1)}+1", list_price=sale, image=src if src.startswith("http") else None,
                          barcode=sku, source_url=ex["url"], period=ex["period"], extra=out_kw)
        elif sale < actual:
            d = make_deal("이마트에브리데이", "mart", key, nm, "세일", list_price=actual, pay_price=sale, image=src if src.startswith("http") else None,
                          barcode=sku, source_url=ex["url"], period=ex["period"], extra=out_kw)
        else:
            continue  # 할인 없이 가격만 실린 상품은 행사로 보지 않는다
        rows.append(d)
    return rows


def collect():
    out, seen = [], set()
    for ex in exhibitions():
        try:
            rows = parse_goods(http(ex["url"]), ex)
        except Exception as e:  # noqa: BLE001
            print("everyday skip", ex["uid"], str(e)[:80])
            continue
        for d in rows:
            if d["key"] in seen:
                continue
            seen.add(d["key"])
            out.append(d)
        time.sleep(DELAY)
    return out


if __name__ == "__main__":
    import sys
    from collections import Counter
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), Counter(d["promo"] for d in r))
    for d in r[:4]:
        print(d["name"], d["list_price"], d["pay_price"], d["unit_price"], d["discount_rate"], d.get("size_unit"), d["period"])
