"""KG모바일: 사이트(Vue SPA)가 쓰는 JSON API(/api/product/plan)를 그대로 호출한다. 목록엔 할인액이 비어 있어 상세(/plan/{번호})의 saleList에서
평생할인(ltSaleAmount)·기간할인(prSaleAmount)을 읽는다. 기간은 groupName('6개월 할인 / ...')과 안내문 '가입월 포함 N개월'에서 얻는다."""
import json
import re
import time
from common import DELAY, http, make_plan

BASE = "https://www.kgmobile.co.kr"
H = {"Accept": "application/json"}
NET = {"LGT": "LGU+", "SKT": "SKT", "KT": "KT"}


def _get(path):
    return json.loads(http(BASE + path, headers=H))["entity"]


def _qos(v):
    return v if v and v not in ("-", "0") else ""


def collect():
    plans, page = [], 1
    while True:
        e = _get(f"/api/product/plan?page={page}")
        plans += e["list"]
        if page >= e["pageInfo"]["totalPage"]:
            break
        page += 1
        time.sleep(DELAY / 2)
    out, seen = [], set()
    for x in plans:
        if x.get("useFlag") != "Y" or x["planCode"] in seen or x.get("telco") not in NET:
            continue
        base = x.get("basicAmount")
        if not base:
            continue
        seen.add(x["planCode"])
        try:
            d = _get(f"/api/product/plan/{x['planNo']}")
        except Exception:  # noqa: BLE001
            d = x
        sale = (d.get("saleList") or [{}])[0] if d.get("saleList") else {}
        lt, pr = sale.get("ltSaleAmount") or 0, sale.get("prSaleAmount") or 0
        txt = re.sub(r"<[^>]+>", " ", d.get("contents") or "")
        gm = re.match(r"(\d+)개월", x.get("groupName") or "") or re.search(r"가입월\s*포함\s*(\d+)\s*개월", txt) or re.search(r"(\d+)개월간 적용", txt)
        months = int(gm.group(1)) if gm else None
        life = lt > 0
        if life:
            dtype, now, after = "lifetime", max(base - lt, 0), max(base - lt, 0)
        elif pr > 0:
            dtype, now, after = "period", max(base - pr, 0), base
        else:
            dtype, now, after, months = "none", base, base, None
        m, du = x.get("basicMonthData"), x.get("basicMonthDataUnit") or "GB"
        daily = x.get("basicDayData")
        data = ""
        if daily and daily not in (-1, "-1", "0", 0):
            data = f"매일 {daily}{x.get('basicDayDataUnit') or 'GB'}"
        if m and m not in ("-1", "0", "-"):
            data = (data + " + " if data else "") + f"{m}{du}"
        if x.get("basicQos") and _qos(x["basicQos"]):
            data += f" + {x['basicQos']}"
        v, s = str(x.get("basicVoice")), str(x.get("basicSms"))
        voice = "무제한" if v == "-1" else (f"{v}분" if v.isdigit() and int(v) > 0 else "")
        sms = "무제한" if s == "-1" else (f"{s}건" if s.isdigit() and int(s) > 0 else "")
        name = re.sub(r"\s+", " ", x["planName"]).strip()
        teth = x.get("tetheringData")
        out.append(make_plan("KG모바일", x["planCode"], name, NET[x["telco"]], BASE + "/product/plan", gen="5G" if x.get("network") == "5G" else "LTE",
                             data_raw=data, voice_raw=voice, sms_raw=sms, list_price=base, price_now=now, price_after=after,
                             discount_type=dtype, discount_months=months,
                             extra={"details": ({"테더링": f"{teth}GB까지"} if teth else None), "label": x.get("groupName"), "price_note": None}))
        time.sleep(DELAY / 2)
    return out


if __name__ == "__main__":
    import sys, collections
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), collections.Counter(x["discount_type"] for x in r), collections.Counter(x["gen"] for x in r))
    for x in r[:2] + [y for y in r if y["discount_type"] == "lifetime"][:2] + [y for y in r if y["discount_type"] == "period"][:3]:
        print({k: x[k] for k in ("name", "data_raw", "voice_raw", "sms_raw", "list_price", "price_now", "price_after", "discount_months", "discount_type")})
    print("months None in period:", sum(1 for y in r if y["discount_type"] == "period" and y["discount_months"] is None))
