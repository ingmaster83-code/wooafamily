"""인스모바일: 조이텔·시월과 같은 목록 구조(rate_plan.do)지만 목록 가격엔 할인 후 금액만 있어, 상세(rateplan_view.do)에서 할인 종료 후 요금을 읽는다."""
import re
import time
from bs4 import BeautifulSoup
import joytel
from common import DELAY, http, won

BASE = "https://www.insmobile.co.kr"
NETS = {"SKT": "SKT", "KT": "KT", "LGU+": "LGU+", "LGT": "LGU+", "LG U+": "LGU+"}


def collect():
    soup = BeautifulSoup(http(BASE + "/rate_plan.do"), "lxml")
    out, seen = [], set()
    for li in soup.select("li.card_list_item"):
        p = joytel.parse_card("인스모바일", BASE, li)
        if not p or p["plan_id"] in seen:
            continue
        seen.add(p["plan_id"])
        net_el = li.select_one("p.title .text_light_color")
        p["network"] = NETS.get(net_el.get_text(strip=True)) if net_el else None
        p["name"] = re.sub(r"^(?:LGU\+|KT|SKT)\s*", "", p["name"])
        try:
            d = BeautifulSoup(http(f"{BASE}/rateplan_view.do?no={p['plan_id']}"), "lxml").get_text(" ", strip=True)
        except Exception:  # noqa: BLE001
            d = ""
        d = re.sub(r"\s+", " ", d)
        m = re.search(r"월\s*([\d,]+)\s*원\s*\*?\s*(\d+)\s*개월\s*이후\s*([\d,]+)\s*원", d)
        base = re.search(r"기본료\s*\(VAT포함\)[^\d]*([\d,]+)", d)
        now_m = re.search(r"월\s*([\d,]+)\s*원", d)
        if m:
            p["price_now"], p["discount_months"], p["price_after"], p["discount_type"] = won(m.group(1)), int(m.group(2)), won(m.group(3)), "period"
        elif now_m:
            p["price_now"] = won(now_m.group(1))
            p["price_after"], p["discount_type"], p["discount_months"] = p["price_now"], "none", None
        if base:
            p["list_price"] = won(base.group(1))
        tm = re.search(r"핫스팟 제공량은 ([\d.]+\s*(?:GB|MB))", d)
        if tm:
            p["details"] = {**(p.get("details") or {}), "테더링": tm.group(1).replace(" ", "") + "까지"}
        out.append(p)
        time.sleep(DELAY)
    return [p for p in out if p["network"] and p["price_now"] is not None and p["price_after"] is not None]


if __name__ == "__main__":
    import sys, collections
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), collections.Counter(x["network"] for x in r), collections.Counter(x["discount_type"] for x in r))
    for x in r[:4]:
        print({k: x[k] for k in ("name", "network", "gen", "data_raw", "price_now", "price_after", "discount_months", "discount_type", "list_price")})
