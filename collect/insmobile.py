"""인스모바일: 조이텔·시월과 같은 목록 구조(rate_plan.do)지만 목록 가격엔 할인 후 금액만 있어, 상세(rateplan_view.do)에서 할인 종료 후 요금을 읽는다."""
import re
import time
from bs4 import BeautifulSoup
import joytel
from common import DELAY, http, won

BASE = "https://www.insmobile.co.kr"
SITES = [("인스모바일", "https://www.insmobile.co.kr"), ("한패스모바일", "https://www.hanpassmobile.co.kr"), ("슈가모바일", "https://www.sugarmobile.co.kr"), ("도시락모바일", "https://dosirakmobile.com")]
PLAIN = {"도시락모바일"}  # 목록 카드 구조가 다르고 프로모션 없이 정가만 표기
NETS = {"SKT": "SKT", "KT": "KT", "LGU+": "LGU+", "LGT": "LGU+", "LG U+": "LGU+"}


def collect_site(carrier, BASE):
    soup = BeautifulSoup(http(BASE + "/rate_plan.do"), "lxml")
    out, seen = [], set()
    for li in soup.select("li.card_list_item"):
        p = joytel.parse_card(carrier, BASE, li)
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
            life = p["discount_type"] == "lifetime"  # 목록 배지·문구로 이미 평생할인 판정된 경우 유지
            p["price_after"], p["discount_type"], p["discount_months"] = p["price_now"], ("lifetime" if life else "none"), None
        if base:
            p["list_price"] = won(base.group(1))
        tm = re.search(r"핫스팟 제공량은 ([\d.]+\s*(?:GB|MB))", d)
        if tm:
            p["details"] = {**(p.get("details") or {}), "테더링": tm.group(1).replace(" ", "") + "까지"}
        out.append(p)
        time.sleep(DELAY)
    return [p for p in out if p["network"] and p["price_now"] is not None and p["price_after"] is not None]


def collect_plain(carrier, base):
    """도시락모바일: 카드(div.title)에 망·이름·데이터·통화·문자·월 요금이 모두 있고, 할인은 '평생할인' 배지로만 표시된다."""
    soup = BeautifulSoup(http(base + "/rate_plan.do"), "lxml")
    out, seen = [], set()
    for li in soup.select("li.card_list_item"):
        a = li.select_one("a.card_rate_link")
        m = re.search(r"no=(\d+)", a["href"]) if a else None
        t = li.select_one("div.title")
        if not m or not t or m.group(1) in seen:
            continue
        badges = [b.get_text(strip=True) for b in t.select(".badge")]
        net = next((NETS[b] for b in badges if b in NETS), None)
        name = re.sub(r"\s+", " ", t.get_text(" ", strip=True))
        for b in badges:
            name = name.replace(b, "", 1)
        name = name.strip()
        desc = li.select("ul.desc li")
        data = re.sub(r"\s+", " ", desc[0].get_text(" ", strip=True)) if desc else ""
        voice = sms = ""
        for d in desc[1:]:
            x = re.sub(r"\s+", " ", d.get_text(" ", strip=True))
            if x.startswith("통화"):
                voice = x[2:].strip()
            elif x.startswith("문자"):
                sms = x[2:].strip()
        price = won((li.select_one(".price") or li).get_text(" ", strip=True))
        if not net or price is None:
            continue
        seen.add(m.group(1))
        life = any("평생" in b for b in badges)
        from common import is_5g_name, make_plan
        out.append(make_plan(carrier, m.group(1), name, net, f"{base}/rateplan_view.do?no={m.group(1)}",
                             gen="5G" if ("5G" in badges or is_5g_name(name)) else "LTE", data_raw=data, voice_raw=voice, sms_raw=sms,
                             list_price=None, price_now=price, price_after=price, discount_type="lifetime" if life else "none", discount_months=None,
                             extra={"details": None, "label": " ".join(b for b in badges if b not in NETS and b != "5G" and "무제한" not in b) or None, "price_note": None}))
    return out


def collect():
    out = []
    for carrier, base in SITES:
        try:
            out += collect_plain(carrier, base) if carrier in PLAIN else collect_site(carrier, base)
        except Exception as e:  # noqa: BLE001  한 곳이 실패해도 나머지는 계속
            print(carrier, "실패:", str(e)[:80])
    return out


if __name__ == "__main__":
    import sys, collections
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), collections.Counter(x["network"] for x in r), collections.Counter(x["discount_type"] for x in r))
    for x in r[:4]:
        print({k: x[k] for k in ("name", "network", "gen", "data_raw", "price_now", "price_after", "discount_months", "discount_type", "list_price")})
