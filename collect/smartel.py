"""스마텔: Next.js 페이지의 서버 데이터(self.__next_f)에 전체 요금제(후불 약 188개) JSON이 들어 있어 한 번의 요청으로 수집한다."""
import json
import re
from common import http, make_plan

BASE = "https://www.smartel.kr"


def _plans():
    h = http(BASE + "/phoneplan")
    blob = "".join(json.loads('"' + c + '"') for c in re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', h, re.S))
    i = blob.find('"planCode"')
    j = blob.rfind("[{", 0, i)
    arr, _ = json.JSONDecoder().raw_decode(blob[j:])
    return arr


def _gb(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f"{f:g}"


def collect():
    out, seen = [], set()
    for a in _plans():
        uid = a.get("uuid_id")
        if not uid or uid in seen or a.get("disabled") or a.get("deletedAt") or a.get("prepaidPostpaid") != "postpaid":
            continue
        seen.add(uid)
        net = {"SKT": "SKT", "KT": "KT", "LGU+": "LGU+"}.get(a.get("mno"))
        orig, promo, dur = a.get("originalPrice"), a.get("promotionPrice"), a.get("promotionDuration") or 0
        if not net or not orig or promo is None:
            continue
        everyday, base, speed = _gb(a.get("dataEveryday")), _gb(a.get("dataDefault")), _gb(a.get("dataAdditionalSpeedLimit"))
        if everyday and float(everyday) > 0:
            data = f"매일 {everyday}GB"
        else:
            data = f"{base}GB" if base and float(base) > 0 else ""
        if speed:
            data += f" + {speed}Mbps"
        v = str(a.get("voiceDefault") or "")
        voice = "무제한" if v == "999" else (f"{v}분" if v not in ("", "0") else "")
        sms = (a.get("text") or "").strip()
        sms = "무제한" if sms == "기본제공" else sms
        if dur == 999 or (dur == 0 and promo == orig and False):
            dtype, after, months = "lifetime", promo, None
        elif dur and promo < orig:
            dtype, after, months = "period", orig, dur
        else:
            dtype, after, months = "none", promo, None
        teth = _gb(a.get("tethering"))
        details = {"테더링": f"{teth}GB까지"} if teth and float(teth) > 0 else None
        sub = (a.get("subName") or "").strip()
        name = a["name"] + (f" {sub}" if sub else "")
        out.append(make_plan("스마텔", uid, name, net, f"{BASE}/phoneplan/{uid}",
                             gen="5G" if a.get("networkType") == "5G" else "LTE", data_raw=data, voice_raw=voice, sms_raw=sms,
                             list_price=orig, price_now=promo, price_after=after, discount_type=dtype, discount_months=months,
                             extra={"details": details, "label": None, "price_note": None}))
    return out


if __name__ == "__main__":
    import sys, collections
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), collections.Counter(x["network"] for x in r), collections.Counter(x["discount_type"] for x in r))
    for x in r[:3] + r[-2:]:
        print({k: x[k] for k in ("name", "network", "gen", "data_raw", "voice_raw", "sms_raw", "price_now", "price_after", "discount_months", "discount_type")})
