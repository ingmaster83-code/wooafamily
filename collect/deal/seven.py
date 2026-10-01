"""세븐일레븐 행사상품: POST listMoreAjax.asp (pTab 1=1+1, 2=2+1, 4=할인). 페이지당 약 9개."""
import re
import time
import urllib.parse
from bs4 import BeautifulSoup
from dealcommon import make_deal
from common import DELAY, http

BASE = "https://www.7-eleven.co.kr"
REF = BASE + "/product/presentList.asp"
TABS = {"1": "1+1", "2": "2+1", "4": "할인"}


def parse(html, promo_default):
    """바깥 li(직계 ul.tag_list_01을 가진 것)만 상품으로 본다."""
    out = []
    for li in BeautifulSoup(html, "lxml").select("li"):
        tag_ul = li.find("ul", class_="tag_list_01", recursive=False)
        pp = li.find("div", class_="pic_product")
        if not tag_ul or not pp:
            continue
        nm = pp.select_one(".name")
        nums = [int(re.sub(r"[^\d]", "", x.get_text())) for x in pp.select(".price span") if re.search(r"\d", x.get_text())]
        if not nm or not nums:
            continue
        tags = [t.get_text(strip=True) for t in tag_ul.select("li")]
        promo = next((t for t in tags if t in ("1+1", "2+1", "3+1")), promo_default)
        img = pp.find("img")
        gv = re.search(r"fncGoView\('(\d+)'\)", str(li))
        out.append((promo, nm.get_text(strip=True), nums, img.get("src") if img else None, gv.group(1) if gv else None))
    return out


def fetch_page(tab, page):
    body = urllib.parse.urlencode({"intPageSize": 5, "intCurrPage": page, "cateCd1": "", "cateCd2": "", "cateCd3": "", "pTab": tab}).encode()
    html = http(BASE + "/product/listMoreAjax.asp", data=body,
                headers={"Referer": REF, "Content-Type": "application/x-www-form-urlencoded"})
    return parse(html, TABS[tab])


def to_deal(label, promo, name, nums, img, gv, n):
    image = (BASE + img) if img and img.startswith("/") else img
    key = f"seven-{gv or n}-{promo if label != '할인' else label}"
    if label == "할인":
        if len(nums) >= 2:
            return make_deal("세븐일레븐", "cvs", key, name, "할인", list_price=max(nums), pay_price=min(nums), image=image, source_url=REF)
        return make_deal("세븐일레븐", "cvs", key, name, "할인", list_price=nums[0], image=image, source_url=REF)
    return make_deal("세븐일레븐", "cvs", key, name, promo, list_price=nums[0], image=image, source_url=REF)


def collect():
    from concurrent.futures import ThreadPoolExecutor
    deals, seen = [], set()
    with ThreadPoolExecutor(max_workers=4) as ex:
        for tab, label in TABS.items():
            page = 1
            while page < 400:
                batch = list(ex.map(lambda p: fetch_page(tab, p), range(page, page + 4)))
                got = 0
                for rows in batch:
                    for promo, name, nums, img, gv in rows:
                        k = (tab, name, tuple(nums))
                        if k in seen:
                            continue
                        seen.add(k)
                        got += 1
                        deals.append(to_deal(label, promo, name, nums, img, gv, len(deals)))
                if got == 0:
                    break
                page += 4
                time.sleep(DELAY)
    return deals


if __name__ == "__main__":
    import sys
    from collections import Counter
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), Counter(d["promo"] for d in r)); print(r[0]); print([d for d in r if d["promo"] == "할인"][:2])
