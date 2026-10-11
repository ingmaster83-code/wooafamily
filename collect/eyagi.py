"""이야기모바일: 목록 AJAX(json_proc.php, mode=comm_list_view)가 요금제 필드를 배열로 돌려준다. page_seq 1~4 × 태그별로 합쳐 후불 요금제만 쓴다."""
import json
import re
import urllib.parse
from common import http, make_plan, won

BASE = "https://www.eyagi.co.kr/shop"
NET = {"skt": "SKT", "kt": "KT", "lgt": "LGU+"}
TAGS = [[], ["20"], ["21"], ["22"], ["30"], ["31"], ["34"]]


def _post(page, tags):
    pairs = [("page_seq", page), ("keyword", ""), ("search_mindata", ""), ("search_maxdata", ""), ("search_qos", ""), ("search_pchip", ""),
             ("search_select_chip", ""), ("search_callgride", ""), ("search_networkgride", ""), ("search_carrierSelect", ""),
             ("search_planSort", ""), ("mode", "comm_list_view")] + [("tab_seq[]", t) for t in tags]
    raw = http(BASE + "/plan/json_proc.php", data=urllib.parse.urlencode(pairs).encode(),
               headers={"Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest", "Referer": BASE + "/plan/list.php"})
    return json.loads(raw).get("data")


def collect():
    rows = {}
    for page in ("1", "2", "3", "4"):
        for tags in TAGS:
            d = _post(page, tags)
            if not d:
                continue
            for i, code in enumerate(d["comm_code"]):
                rows[(code, d["agent_code"][i])] = {k: (v[i] if isinstance(v, list) and i < len(v) else None) for k, v in d.items() if k != "coupon_name"}
    out, seen = [], set()
    for (code, agent), r in rows.items():
        if r.get("pay_type") != "2" or r.get("mno_gubun") not in NET:
            continue
        base, now, after = won(r.get("base_fee")), won(r.get("selling_price")), won(r.get("restoration_fee"))
        if now is None:
            continue
        months = won(r.get("terms"))
        name = re.sub(r"\s+", " ", r["comm_name"]).strip()
        label = None
        m = re.match(r"\[([^\]]+)\]\s*(.*)", name)
        if m:
            label, name = f"{m.group(1)} 제휴", m.group(2)
        life = "life" in (r.get("terms_str") or "") or str(r.get("terms")) == "life"
        if life:
            dtype, after, months = "lifetime", now, None
        elif after is not None and after != now and months:
            dtype = "period"
        else:
            dtype, after, months = "none", now, None
        data = r.get("free_data_str") or ""
        if r.get("qos") and r.get("unlimit_data_yn") == "Y":
            data += f" + {r['qos']}Mbps"
        call = "무제한" if r.get("call_str") == "기본제공" else (r.get("call_str") or "")
        sms = "무제한" if r.get("sms_str") == "기본제공" else (r.get("sms_str") or "")
        if "주유편의점" in name or data.startswith("0MB"):  # 주유소·편의점 전용 채널 상품
            continue
        key = (NET[r["mno_gubun"]], name, data, now, after, call)
        if key in seen:
            continue
        seen.add(key)
        out.append(make_plan("이야기모바일", f"{code}-{agent}", name, NET[r["mno_gubun"]],
                             f"{BASE}/plan/detail.php?comm_code={code}&agent_code={agent}",
                             gen="5G" if r.get("is_5g_yn") == "5G" else "LTE", data_raw=data, voice_raw=call, sms_raw=sms,
                             list_price=base, price_now=now, price_after=after, discount_type=dtype, discount_months=months,
                             extra={"details": ({"테더링": r["tethering_str"]} if r.get("tethering_str") else None), "label": label, "price_note": None}))
    return out


if __name__ == "__main__":
    import sys, collections
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), collections.Counter(x["network"] for x in r), collections.Counter(x["discount_type"] for x in r))
    for x in r[:3] + r[-2:]:
        print({k: x[k] for k in ("name", "network", "gen", "data_raw", "voice_raw", "sms_raw", "list_price", "price_now", "price_after", "discount_months", "discount_type", "label")})
