"""SK7모바일: callingPlanList.do?refCode=USIM 에서 ID -> callingPlanView.do 상세 텍스트 파싱.
SK7은 SKT망 알뜰폰. 프로모션 할인은 약관상 '해지 전까지 평생 적용'이므로 프로모션가가 있으면 lifetime."""
import re
import time
from bs4 import BeautifulSoup
from common import DELAY, http, make_plan, parse_overage, won

BASE = "https://www.sk7mobile.com"
LIST = BASE + "/prod/data/callingPlanList.do?refCode=USIM"
VIEW = BASE + "/prod/data/callingPlanView.do?refCode=USIM&prodCd={}"


def parse(pid, h):
    soup = BeautifulSoup(h, "lxml")
    for s in soup(["script", "style"]):
        s.decompose()
    t = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    head = re.search(r"상단으로 이동\s+(.*?)\s+데이터 제공량", t)
    name_blob = head.group(1) if head else ""
    nm = re.search(r"((?:LTE|5G|3G)\s*(?:USIM|유심)(?:\s*\([^)]*\))?(?:\s*표준)?)", name_blob)
    name = nm.group(1).strip() if nm else name_blob[:40]
    dm = re.search(r"데이터 제공량\s+(.+?)\s+음성 제공량\s+(.+?)\s+문자 제공량\s+(.+?)\s+기본료\s+([\d,]+)\s*원", t)
    if not dm:
        return None
    data_raw, voice_raw, sms_raw, base = dm.group(1), dm.group(2), dm.group(3), won(dm.group(4))
    pm = re.search(r"프로모션 할인 후 기본료\s+([\d,]+)\s*원", t)
    promo = won(pm.group(1)) if pm else None
    gen = "5G" if name.startswith("5G") else "3G" if name.startswith("3G") else "LTE"
    if promo is not None:
        dtype, now, after = "lifetime", promo, promo
    else:
        dtype, now, after = "none", base, base
    details = {}
    gi = t.find("기본 제공량 이용안내")
    if gi >= 0:
        seg = t[gi + len("기본 제공량 이용안내"):gi + 1800]
        m = re.search(r"데이터\s+(.*?)\s+통화\s+HD Voice", seg)
        if m:
            v = re.split(r"\s(?:\d+Mbps\s*:|\d+(?:Kbps|GB)\s+기본제공\s+추가)", m.group(1).strip())[0]
            details["데이터 안내"] = v.strip()[:140]
        m = re.search(r"통화\s+(HD Voice.*?)\s+문자\s", seg)
        if m:
            v = re.split(r"\s부가통화 1초|\s※", m.group(1).strip())[0]
            details["통화 안내"] = v.strip()[:140]
    ov = parse_overage(t)
    if ov:
        details["초과 요금"] = ov
    return make_plan("SK7모바일", pid, name or pid, "SKT", VIEW.format(pid), gen=gen,
                     data_raw=data_raw, voice_raw=voice_raw, sms_raw=sms_raw,
                     list_price=base, price_now=now, price_after=after, discount_type=dtype,
                     extra={"details": details or None})


def collect():
    ids = sorted(set(re.findall(r"PD\d{8}", http(LIST))))
    out = []
    for pid in ids:
        try:
            p = parse(pid, http(VIEW.format(pid)))
        except Exception as e:  # noqa: BLE001
            print("sk7 fail", pid, e)
            p = None
        if p:
            out.append(p)
        time.sleep(DELAY)
    return out


if __name__ == "__main__":
    r = collect()
    print(len(r), r[0])
