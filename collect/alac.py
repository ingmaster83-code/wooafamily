"""알닷(uplusmvno.com, LG U+ 알뜰폰 허브): 사이트 화면이 쓰는 공개 목록 API(POST /umah/fo/chrg/v1/chrgeInfo) 한 번으로 LG U+망 제휴 사업자 1,100여 개 요금제가 온다.
직접 수집하는 통신사와 겹치는 곳은 제외하고, 공식 사이트 수집이 어려운 사업자(모나·찬스·토스·헬로·U+유모바일 등)만 쓴다. 상세 링크는 알닷 요금제 페이지."""
import html
import json
import re
from common import http, make_plan, won

API = "https://api.uplusmvno.com/umah/fo/chrg/v1/chrgeInfo"
SITE = "https://www.uplusmvno.com"
# 이미 공식 사이트에서 직접 수집하는 사업자(알닷 값은 쓰지 않는다)
OWN = {"이야기모바일", "KG모바일", "시월모바일", "스마텔", "A모바일", "인스모바일", "아이즈모바일", "슈가모바일", "티플러스", "프리티"}
CARRIER = {"WELL": "웰(WELL)", "모빙(mobing)": "모빙", "에스원안심모바일": "안심모바일"}


def collect():
    raw = http(API, data=b"{}", headers={"Content-Type": "application/json", "Accept": "application/json", "Origin": SITE, "Referer": SITE + "/plan/plan-list"})
    rows = json.loads(raw).get("alphaChrgListOutVo") or []
    out, seen = [], set()
    for x in rows:
        carrier = html.unescape(x.get("ptnCmpyNm") or "").strip()
        carrier = CARRIER.get(carrier, carrier)
        if not carrier or carrier in OWN or x.get("mvnopPpEnprKdCd") != "MVNO" or x["mvnopPpId"] in seen:
            continue
        seen.add(x["mvnopPpId"])
        name = html.unescape(x.get("mvnopPpNm") or "")
        name = re.sub(r"★.*$", "", name)
        tags = re.findall(r"\[([^\]]+)\]", name)
        name = re.sub(r"\s+", " ", re.sub(r"\[[^\]]+\]", " ", name)).strip()
        if not name:
            continue
        data = re.sub(r"^월\s*", "", (x.get("dataVolume") or "").strip())
        call = "무제한" if x.get("callVolume") == "기본제공" else (x.get("callVolume") or "")
        sms = "무제한" if x.get("messageVolume") == "기본제공" else (x.get("messageVolume") or "")
        mm = int(x.get("evetDichAplyMmct") or 0)
        now_p, after_p, base_p = won(x.get("evetDcntAmt")), won(x.get("evetEndLtrAmt")), won(x.get("monthFixedAmt"))
        if mm and mm != 999 and now_p is not None and after_p and after_p > now_p:
            dtype, now, after, months = "period", now_p, after_p, mm
        else:
            price = now_p if now_p is not None else base_p
            if price is None:
                continue
            dtype, now, after, months = "none", price, price, None
            if any("평생" in t for t in tags) or "평생" in name:  # 이름 머리말에 '[평생할인]'이 있는 요금제
                dtype = "lifetime"
        det = f"{SITE}/plan/plan-list/detail?mvnopPpId={x['mvnopPpId']}&mvnopPtnId={x.get('mvnopPtnId')}"
        out.append(make_plan(carrier, x["mvnopPpId"], name, "LGU+", det, gen="5G" if x.get("ppCommSkil") == "5G" else "LTE",
                             data_raw=data, voice_raw=call, sms_raw=sms, list_price=None, price_now=now, price_after=after,
                             discount_type=dtype, discount_months=months,
                             extra={"details": None, "label": " ".join(tags) or None, "price_note": "출처: 알닷(LG U+ 알뜰폰 허브)"}))
    return out


if __name__ == "__main__":
    import sys, collections
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), collections.Counter(x["carrier"] for x in r).most_common(), collections.Counter(x["discount_type"] for x in r))
    for x in r[:3]:
        print({k: x[k] for k in ("carrier", "name", "data_raw", "voice_raw", "sms_raw", "price_now", "price_after", "discount_months", "discount_type", "label")})
    print("zero/odd price:", sum(1 for x in r if not x["price_now"] or x["price_now"] < 100))
