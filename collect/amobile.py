"""에이모바일: POST /planasync (JSON). 평생할인여부 필드 제공."""
import re
from common import http_json, make_plan, won

NET = {"S": "SKT", "K": "KT", "L": "LGU+"}
URL = "https://amobile.co.kr/planasync"


def _unit(v, unit):
    v = (v or "").strip()
    return f"{v}{unit}" if re.fullmatch(r"\d+", v) else v


def collect():
    d = http_json(URL, {"section": "plansearch", "keyword": "N", "telecom": "all", "sort": "price", "status": "Y"})
    out = []
    for p in d["planList"]:
        base, cut = won(p["기본료"]) or 0, won(p["알뜰할인"]) or 0
        now = won(p["할인요금"])
        months = int(p["추가할인개월수"] or 0)
        lifetime = p["평생할인여부"] == "Y"
        after = now if (lifetime or months == 0) else base - cut
        dtype = "lifetime" if lifetime else ("period" if months > 0 else "none")
        out.append(make_plan(
            "에이모바일", p["요금제구성ID"], p["요금제명"], NET.get(p["통신사"]),
            "https://amobile.co.kr/plannew",
            gen="5G" if p["망구분"] == "5G" else "LTE",
            data_raw=p["무료데이타"] or "", voice_raw=_unit(p["무료음성"], "분"), sms_raw=_unit(p["무료문자"], "건"),
            list_price=base, price_now=now, price_after=after,
            discount_type=dtype, discount_months=months or None,
            extra={"promo": p.get("프로모션") if p.get("프로모션") not in (None, "", "없음") else None},
        ))
    return out


if __name__ == "__main__":
    r = collect()
    print(len(r), r[0])
