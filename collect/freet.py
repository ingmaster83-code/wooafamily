"""프리티: GET api.freet.co.kr/plan/v1/list (JSON, 페이지당 20개)."""
import time
from common import DELAY, http_json, make_plan, won

NET = {"freeS": "SKT", "freeC": "KT", "freeT": "LGU+"}  # freeT=LGU+ / freeC=KT 로 실측 확인
API = "https://api.freet.co.kr/plan/v1/list?rowSize=20&pageNo={p}&onlineAuth=Y"


def collect():
    items, page = [], 1
    while True:
        r = http_json(API.format(p=page))["data"]
        lst = r.get("ratePlans") or []
        items += lst
        if not lst or len(items) >= r["totalCount"]:
            break
        page += 1
        time.sleep(DELAY)
    out = []
    for p in items:
        base = won(p["basicFee"])
        now = won(p.get("monthlyFee"))
        months = int(p.get("periodDiscMonth") or 0)
        forever = int(p.get("foreverDiscAmt") or 0)
        after = base - forever if base is not None else None
        if months > 0:
            dtype = "period"
        elif forever > 0:
            dtype = "lifetime"
        else:
            dtype = "none"
        if now is None:
            now = after if months == 0 else None
        out.append(make_plan(
            "프리티모바일", p["svcCd"], p["svcName"], NET.get(p.get("comType")),
            f"https://www.freet.co.kr/plan/ratePlan/detail?svcCd={p['svcCd']}",
            gen=p.get("genCd"),
            data_raw=" ".join(x for x in [p.get("freeData"), p.get("qos")] if x),
            voice_raw=p.get("freeVoice") or "", sms_raw=p.get("freeSms") or "",
            list_price=base, price_now=now, price_after=after,
            discount_type=dtype, discount_months=months or None,
            extra={"prepaid": p.get("svcType") == "선불"},
        ))
    return out


if __name__ == "__main__":
    r = collect()
    print(len(r), r[0])
