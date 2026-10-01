"""이마트24 행사상품: /goods/event?page=N 서버 렌더링(페이지당 20개). 혜택 태그 1+1/2+1/3+1/세일/골라담기."""
import re
import time
from bs4 import BeautifulSoup
from dealcommon import make_deal
from common import DELAY, http, won

URL = "https://emart24.co.kr/goods/event?search=&category_seq=&align=&page={p}"
REF = "https://emart24.co.kr/goods/event"


def collect():
    out, seen = [], set()
    for page in range(1, 300):
        soup = BeautifulSoup(http(URL.format(p=page)), "lxml")
        wraps = soup.select("div.itemWrap")
        fresh = 0
        for w in wraps:
            tag = w.select_one(".itemTit span.floatR")
            title = w.select_one(".itemtitle a")
            if not (tag and title):
                continue
            promo = re.sub(r"\s+", "", tag.get_text())
            nm = title.get_text(strip=True)
            off, on = w.select_one("a.priceOff"), w.select_one("a.price")
            p_off, p_on = won(off.get_text()) if off else None, won(on.get_text()) if on else None
            img = w.select_one(".itemSpImg img")
            src = img.get("src") if img else None
            bc = re.search(r"/(\d{8,14})\.", src or "")
            k = (nm, promo, p_on, p_off)
            if k in seen or p_on is None:
                continue
            seen.add(k)
            fresh += 1
            key = f"emart24-{bc.group(1) if bc else len(out)}-{promo}"
            if promo in ("1+1", "2+1", "3+1"):
                d = make_deal("이마트24", "cvs", key, nm, promo, list_price=p_on, image=src, barcode=bc.group(1) if bc else None, source_url=REF)
            elif promo == "세일":
                d = make_deal("이마트24", "cvs", key, nm, "세일", list_price=p_off or p_on, pay_price=p_on, image=src,
                              barcode=bc.group(1) if bc else None, source_url=REF)
            else:  # 골라담기 등: 묶음 조건을 알 수 없어 개당가는 계산하지 않음
                d = make_deal("이마트24", "cvs", key, nm, promo, list_price=p_on, image=src, barcode=bc.group(1) if bc else None, source_url=REF)
                d["unit_price"], d["discount_rate"] = None, None
            out.append(d)
        if not wraps or fresh == 0:
            break
        time.sleep(DELAY)
    return out


if __name__ == "__main__":
    import sys
    from collections import Counter
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), Counter(d["promo"] for d in r)); print(r[0])
