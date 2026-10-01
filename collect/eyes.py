"""아이즈모바일: /payplan/all_plan?page=N 로 ID 수집 -> /payplan/plan_info/{id}/C01 상세 파싱."""
import re
import time
from bs4 import BeautifulSoup
from common import DELAY, http, is_5g_name, make_plan, won

BASE = "https://eyes.co.kr"
NET = {"skt": "SKT", "kt": "KT", "lg": "LGU+"}


def list_ids():
    ids, page = [], 1
    while page < 40:
        h = http(f"{BASE}/payplan/all_plan?page={page}")
        new = [x for x in dict.fromkeys(re.findall(r"plan_info/(\d+/C\d+)", h)) if x not in ids]
        if not new:
            break
        ids += new
        page += 1
        time.sleep(DELAY)
    return ids


def parse(pid, h):
    soup = BeautifulSoup(h, "lxml")
    marker = soup.find("h2", class_="blind", string=re.compile("요금제 정보"))
    if not marker:
        return None
    sec = marker.find_parent("section") or marker.find_parent("div")
    badge = sec.select_one("span.badge")
    net = next((v for k, v in NET.items() if badge and k in badge.get("class", [])), None)
    period_badge = sec.select_one("span.badge.period")
    name_el = sec.select_one("p.body_medium.sb")
    org = sec.select_one("p.org_p")
    cur = sec.select_one("p.current_p")
    per = sec.select_one("p.body_medium.sb.period")
    if not name_el:
        return None
    name = name_el.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", sec.get_text(" ", strip=True))
    org_txt = org.get_text(strip=True) if org else ""
    cur_txt = cur.get_text(" ", strip=True) if cur else ""
    # 요금제명 ~ 정가(없으면 현재가) 사이 = 데이터/음성/문자 원문
    i = text.find(name) + len(name)
    bound = org_txt or cur_txt
    j = text.find(bound, i) if bound else -1
    raw = text[i:j].strip() if j > i else ""
    sms = re.search(r"(\d+\s*건|기본제공|무제한)$", raw)
    sms_raw = sms.group(1) if sms else ""
    raw = raw[: sms.start()].strip() if sms else raw
    voice = re.search(r"(기본제공\s*\+\s*영상/부가통화\s*\d+\s*분|\d+\s*분|기본제공|무제한)$", raw)
    voice_raw = voice.group(1) if voice else ""
    data_raw = raw[: voice.start()].strip() if voice else raw
    now = won(cur_txt)
    list_price = won(org_txt) if org_txt else now
    per_txt = per.get_text(strip=True) if per else ""
    badge_txt = period_badge.get_text(strip=True) if period_badge else ""
    months = None
    if "평생" in per_txt or "평생" in badge_txt:
        dtype, after = "lifetime", now
    else:
        m = re.search(r"(\d+)\s*개월", per_txt + badge_txt)
        if m:
            dtype, months, after = "period", int(m.group(1)), list_price
        else:
            dtype, after = "none", list_price
    if dtype == "none" and now is None:
        now = list_price
    if dtype == "none" and list_price is None:
        return None
    gen = "5G" if is_5g_name(name) else "LTE"
    return make_plan("아이즈모바일", pid.split("/")[0], name, net, f"{BASE}/payplan/plan_info/{pid}",
                     gen=gen, data_raw=data_raw, voice_raw=voice_raw, sms_raw=sms_raw,
                     list_price=list_price, price_now=now, price_after=after,
                     discount_type=dtype, discount_months=months,
                     extra={"label": badge_txt or None})


def collect():
    out = []
    for pid in list_ids():
        try:
            p = parse(pid, http(f"{BASE}/payplan/plan_info/{pid}"))
        except Exception as e:  # noqa: BLE001
            print("eyes fail", pid, e)
            p = None
        if p:
            out.append(p)
        time.sleep(DELAY)
    return out


if __name__ == "__main__":
    r = collect()
    print(len(r), r[0])
