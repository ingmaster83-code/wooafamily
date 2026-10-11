"""KT엠모바일: 카테고리 목록(getCtgXmlAllListAjax) -> 카테고리별 요금제(rateContentAjax) JSON. 목록엔 프로모션 요금만 있고 적용 기간 표기는 없다.
이 환경의 파이썬 SSL이 서버와 맞지 않아 curl(쿠키 유지)로 호출한다."""
import json
import os
import re
import subprocess
import tempfile
import time
from common import DELAY, is_5g_name, make_plan, won

BASE = "https://www.ktmmobile.com"
JAR = os.path.join(tempfile.gettempdir(), "ktm_cookies.txt")


def _curl(path, post=None):
    c = ["curl", "-sL", "-m", "40", "-A", "Mozilla/5.0 (compatible; WooaFamilyBot/0.1; +https://wooafamily.com)", "-c", JAR, "-b", JAR,
         "-H", "X-Requested-With: XMLHttpRequest", "-e", BASE + "/rate/rateList.do", BASE + path]
    if post is not None:
        c += ["-d", post]
    for _ in range(3):
        out = subprocess.run(c, capture_output=True).stdout.decode("utf-8", "ignore")
        if out.strip():
            return out
        time.sleep(2)
    raise RuntimeError("KT엠모바일 응답 없음: " + path)


def collect():
    _curl("/rate/rateList.do")
    ctg = json.loads(_curl("/rate/getCtgXmlAllListAjax.do", "rateAdsvcDivCd=RATE"))
    out, seen = [], set()
    for c in ctg:
        if c.get("depthKey") != 2 or not c.get("relCnt"):
            continue
        time.sleep(DELAY)
        try:
            items = json.loads(_curl("/rate/rateContentAjax.do", "rateAdsvcCtgCd=" + str(c["rateAdsvcCtgCd"])))
        except Exception:  # noqa: BLE001
            continue
        for o in items:
            code = o.get("rateAdsvcCd")
            name = (o.get("rateAdsvcNm") or "").strip()
            if not code or code in seen or not name or o.get("useYn") not in (None, "Y"):
                continue
            base, promo = won(o.get("mmBasAmtVatDesc")), won(o.get("promotionAmtVatDesc"))
            if base is None:
                continue
            seen.add(code)
            data = re.sub(r"\s*\+\s*최대\s*", " + ", (o.get("bnfitData") or "").strip())
            voice = (o.get("bnfitVoice") or "").strip()
            sms = (o.get("bnfitSms") or "").strip()
            voice, sms = ("무제한" if voice == "기본제공" else voice), ("무제한" if sms == "기본제공" else sms)
            now = promo if promo is not None and promo < base else base
            if now < base:
                dtype, after, months, note = "period", base, None, "프로모션 요금 · 적용 기간은 KT엠모바일 공식 페이지에서 확인"
            else:
                dtype, after, months, note = "none", base, None, None
            teth = None
            out.append(make_plan("KT엠모바일", code, name, "KT", BASE + "/rate/rateList.do", gen="5G" if is_5g_name(name) else "LTE",
                                 data_raw=data, voice_raw=voice, sms_raw=sms, list_price=base, price_now=now, price_after=after,
                                 discount_type=dtype, discount_months=months, extra={"details": teth, "label": None, "price_note": note}))
    return out


if __name__ == "__main__":
    import sys, collections
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), collections.Counter(x["discount_type"] for x in r), collections.Counter(x["gen"] for x in r))
    for x in r[:4]:
        print({k: x[k] for k in ("name", "data_raw", "voice_raw", "sms_raw", "list_price", "price_now", "price_after", "discount_type")})
    print([x["name"] for x in r if not x["data_raw"]][:5])
