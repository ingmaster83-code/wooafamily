"""CU 행사상품: POST /event/plusAjax.do (HTML 조각, 페이지당 40개). 상품 이미지 파일명이 바코드."""
import re
import time
import urllib.parse
from bs4 import BeautifulSoup
from dealcommon import make_deal
from common import DELAY, http

URL = "https://cu.bgfretail.com/event/plusAjax.do"
REF = "https://cu.bgfretail.com/event/plus.do?category=event&depth2=1&sf=N"


def collect():
    out, seen = [], set()
    for page in range(1, 200):
        body = urllib.parse.urlencode({"pageIndex": page, "listType": 0, "searchCondition": "", "user_id": ""}).encode()
        html = http(URL, data=body, headers={"Referer": REF, "Content-Type": "application/x-www-form-urlencoded"})
        lis = BeautifulSoup(html, "lxml").select("li.prod_list")
        fresh = 0
        for li in lis:
            name = li.select_one(".name")
            price = li.select_one(".price strong")
            badge = li.select_one(".badge span")
            img = li.select_one("img.prod_img")
            if not (name and price and badge):
                continue
            promo = badge.get_text(strip=True)
            nm = name.get_text(strip=True)
            src = img.get("src", "") if img else ""
            bc = re.search(r"/(\d{8,14})\.", src)
            k = (nm, promo, price.get_text(strip=True))
            if k in seen:
                continue
            seen.add(k)
            fresh += 1
            out.append(make_deal("CU", "cvs", f"cu-{bc.group(1) if bc else len(out)}-{promo}", nm, promo,
                                 list_price=int(price.get_text(strip=True).replace(",", "")),
                                 image=("https:" + src) if src.startswith("//") else src, barcode=bc.group(1) if bc else None,
                                 source_url=REF))
        if not lis or fresh == 0:
            break
        time.sleep(DELAY)
    return out


if __name__ == "__main__":
    import sys
    from collections import Counter
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), Counter(d["promo"] for d in r)); print(r[0])
