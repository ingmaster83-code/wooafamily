"""티플러스: /BackBone/rate/rate_list 가 HTML 조각(20개씩, key로 다음 페이지)을 돌려준다. 이 환경의 파이썬 SSL로는 서버 핸드셰이크가 실패해 curl로 호출한다."""
import re
import subprocess
import time
import urllib.parse
from bs4 import BeautifulSoup
from common import DELAY, make_plan, won

BASE = "https://tplusmobile.com"
NET = {"skt": "SKT", "kt": "KT", "lg": "LGU+", "lgu": "LGU+", "lgt": "LGU+", "lgu+": "LGU+", "lg u+": "LGU+"}
FORM = dict(keyword="", seloptiontp="", selcompanytp="", recommendtp="", selplanstp="all_plans", filter_data_s=0, filter_data_e=30001,
            filter_voice_s=0, filter_voice_e=501, filter_price_s=0, filter_price_e=50001, selsorttp="", sel_companies="", sel_sms="",
            sel_network="", sel_qos="", sel_term="", sel_benefit_seqs="")


def _post(extra):
    body = urllib.parse.urlencode({**FORM, **extra})
    for _ in range(3):
        r = subprocess.run(["curl", "-s", "-m", "40", "-A", "Mozilla/5.0 (compatible; WooaFamilyBot/0.1; +https://wooafamily.com)",
                            "-H", "X-Requested-With: XMLHttpRequest", "-e", BASE + "/main/rate/join", "-d", body,
                            BASE + "/BackBone/rate/rate_list"], capture_output=True)
        parts = r.stdout.decode("utf-8", "ignore").strip().split("ㅹㆄ")
        if parts[0] == "TRUE" and len(parts) >= 7:
            return parts
        time.sleep(2)
    return None


def _cards(html):
    return BeautifulSoup(html, "lxml").select("div.cardArea")


def parse(card):
    a = card.select_one("a[href*=plan_details]")
    if not a:
        return None
    seq = re.search(r"seq=([0-9A-F]+)", a["href"]).group(1)
    badges = [b.get_text(strip=True) for b in card.select(".badgeArea .badge")]
    net = next((NET[b.lower()] for b in badges if b.lower() in NET), None)
    title_el = card.select_one("h4.title")
    if not net or not title_el:
        return None
    name = re.sub(r"\s+", " ", title_el.get_text(" ", strip=True)).replace("＋", "+")
    desc = card.select_one("p.desc20px700")
    data = re.sub(r"\s+", " ", desc.get_text(" ", strip=True)).replace("최대", "").strip() if desc else ""
    data = re.sub(r"\s+", " ", data)
    q = re.search(r"([\d.]+\s*[MK]bps)", data)
    if q:
        data = re.sub(r"\s*[\d.]+\s*[MK]bps", "", data).strip() + " + " + q.group(1).replace(" ", "")
    ico = {k: (card.select_one(f".ico.{k}").get_text(strip=True) if card.select_one(f".ico.{k}") else "") for k in ("call", "message")}
    call = "무제한" if ico["call"] == "기본제공" else ico["call"]
    sms = "무제한" if ico["message"] == "기본제공" else ico["message"]
    thr = card.select_one("p.throthDesc")
    base = won(thr.get_text()) if thr else None
    promo = card.select_one("p.desc16px700")
    ptxt = re.sub(r"\s+", "", promo.get_text()) if promo else ""
    bt = " ".join(badges)
    mp = re.search(r"(\d+)개월간월([\d,]+)원", ptxt)
    rd = " ".join(t.get_text(" ", strip=True) for t in card.select(".rateDetail .text"))
    after_m = re.search(r"(\d+)개월\s*후\s*월\s*([\d,]+)원", rd)
    if mp:
        now, months = won(mp.group(2)), int(mp.group(1))
        after = won(after_m.group(2)) if after_m else base
        dtype = "period"
    else:
        now = won(ptxt) if ptxt else base
        after, months = now, None
        dtype = "lifetime" if "평생" in bt or "평생" in ptxt else "none"
    if now is None:
        return None
    teth = re.search(r"테더링\s*([\d.]+\s*(?:GB|MB))", rd)
    return make_plan("티플러스", seq[:24], name, net, f"{BASE}{a['href']}", gen="5G" if is5g(name) else "LTE", data_raw=data, voice_raw=call, sms_raw=sms,
                     list_price=base, price_now=now, price_after=after, discount_type=dtype, discount_months=months,
                     extra={"details": ({"테더링": teth.group(1).replace(" ", "") + "까지"} if teth else None), "label": None, "price_note": None}), seq


def is5g(name):
    from common import is_5g_name
    return is_5g_name(name)


def collect():
    parts = _post({"tp": "F", "key": ""})
    if not parts:
        raise RuntimeError("티플러스 목록 응답 없음")
    total = int(parts[2])
    rows = []
    while True:
        rows += _cards(parts[1])
        if len(rows) >= total or int(parts[3]) == 0:
            break
        time.sleep(DELAY)
        parts = _post({"tp": "N", "key": parts[5], "nowcnt": parts[6]})
        if not parts:
            break
    out, seen = [], set()
    for c in rows:
        r = parse(c)
        if not r:
            continue
        p, seq = r
        k = (p["network"], re.sub(r"\(.*", "", p["name"]).strip(), p["data_raw"], p["price_now"], p["price_after"], p["voice_raw"])
        if k in seen:
            continue
        seen.add(k)
        out.append(p)
    return out


if __name__ == "__main__":
    import sys, collections
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), collections.Counter(x["network"] for x in r), collections.Counter(x["discount_type"] for x in r))
    for x in r[:3] + r[-2:]:
        print({k: x[k] for k in ("name", "network", "gen", "data_raw", "voice_raw", "sms_raw", "list_price", "price_now", "price_after", "discount_months", "discount_type")})
