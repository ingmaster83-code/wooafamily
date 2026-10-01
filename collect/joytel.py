"""조이텔 / 시월모바일: 같은 솔루션(rate_plan.do). 목록 카드에 이름·데이터·통화·문자·가격·평생 표기가 모두 있다."""
import re
from bs4 import BeautifulSoup
from common import http, is_5g_name, make_plan, won

SITES = [("조이텔", "https://joytel.co.kr"), ("시월모바일", "https://siwolmobile.com")]
FIXED_NET = {"시월모바일": "LGU+"}  # 시월은 LGU+ 공용유심 전용(목록에 망 배지 없음)
NET = {"SKT": "SKT", "KT": "KT", "LGT": "LGU+", "LG": "LGU+", "LGU": "LGU+"}


def parse_card(carrier, base, li):
    a = li.select_one("a.card_rate_link")
    m = re.search(r"no=(\d+)", a["href"]) if a else None
    if not m:
        return None
    pid = m.group(1)
    badges = [b.get_text(strip=True) for b in li.select(".badge_wrap .badge")]
    net = FIXED_NET.get(carrier) or next((NET[b.replace("+", "")] for b in badges if b.replace("+", "") in NET), None)
    name_txt = title_text = (li.select_one("p.title") or li).get_text(strip=True)
    gen = "5G" if ("5G" in badges or is_5g_name(name_txt)) else "LTE" if ("LTE" in badges or carrier in FIXED_NET) else None
    title = li.select_one("p.title")
    if not title:
        return None
    desc = li.select("ul.desc li")
    data_raw = re.sub(r"\s+", " ", desc[0].get_text(" ", strip=True)) if desc else ""
    voice = sms = ""
    for d in desc[1:]:
        t = re.sub(r"\s+", " ", d.get_text(" ", strip=True))
        if t.startswith("통화"):
            voice = t[2:].strip()
        elif t.startswith("문자"):
            sms = t[2:].strip()
    li_text = re.sub(r"\s+", " ", li.get_text(" ", strip=True))
    details = {}
    tm = re.search(r"테더링\s*(\d+(?:\.\d+)?\s*(?:GB|MB)|무제한|불가)", li_text)
    if tm:
        details["테더링"] = tm.group(1).replace(" ", "") + "까지" if tm.group(1) not in ("무제한", "불가") else tm.group(1)
    sm = re.search(r"(\d+(?:\.\d+)?\s*(?:Mbps|Kbps))\s*(?:데이터\s*)?무제한", li_text)
    if sm:
        details["소진 후"] = f"최대 {sm.group(1).replace(' ', '')} 속도로 무제한"
    price_el = li.select_one(".price")
    ptxt = price_el.get_text(" ", strip=True) if price_el else ""
    ref = li.select_one(".price .ref")
    ref_txt = ref.get_text(strip=True) if ref else ""
    now = won(re.sub(r"\*.*", "", ptxt))
    months = None
    pm = re.search(r"(\d+)\s*개월\s*차\s*부터\s*([\d,]+)\s*원", ref_txt)
    pm2 = re.search(r"(\d+)\s*개월\s*이후\s*([\d,]+)\s*원", ref_txt)
    if "평생" in ref_txt:
        dtype, after = "lifetime", now
    elif pm:
        dtype, months, after = "period", int(pm.group(1)) - 1, won(pm.group(2))
    elif pm2:
        dtype, months, after = "period", int(pm2.group(1)), won(pm2.group(2))
    elif ref_txt:
        dtype, after = "period", None
    else:
        dtype, after = "none", now
    badge_txt = " ".join(badges)
    if dtype == "none":  # 가격 문구엔 없고 배지에만 할인 표기가 있는 경우(시월 등)
        bm = re.search(r"(\d+)\s*개월\s*할인", badge_txt)
        if "평생" in badge_txt or "평생" in title.get_text():
            dtype, after = "lifetime", now
        elif bm:
            dtype, months = "period", int(bm.group(1))
    return make_plan(carrier, pid, title.get_text(strip=True), net, f"{base}/rateplan_view.do?no={pid}",
                     gen=gen, data_raw=data_raw, voice_raw=voice, sms_raw=sms,
                     list_price=None, price_now=now, price_after=after, discount_type=dtype, discount_months=months,
                     extra={"details": details or None, "label": " ".join(b for b in badges if b not in ("SKT", "KT", "LGT", "LGU+", "LTE", "5G")) or None,
                            "price_note": ref_txt or None})


def collect():
    out = []
    for carrier, base in SITES:
        soup = BeautifulSoup(http(base + "/rate_plan.do"), "lxml")
        seen = set()
        for li in soup.select("li.card_list_item"):
            p = parse_card(carrier, base, li)
            if p and p["plan_id"] not in seen:
                seen.add(p["plan_id"])
                out.append(p)
    return out


if __name__ == "__main__":
    r = collect()
    print(len(r), r[0])
