"""공통 유틸 + 정규화 스키마. 수집기는 이 모듈의 make_plan()으로 통일된 dict를 만든다."""
import html, json, re, time, urllib.request
from datetime import datetime, timezone, timedelta

UA = {"User-Agent": "Mozilla/5.0 (compatible; WooaFamilyBot/0.1; +https://wooafamily.com)"}
KST = timezone(timedelta(hours=9))
DELAY = 0.4


def now_kst():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M")


def http(url, data=None, headers=None, retries=2):
    h = dict(UA)
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    err = None
    for _ in range(retries + 1):
        try:
            return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(1.5)
    raise err


def http_json(url, body=None):
    if body is not None:
        raw = http(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json; charset=utf-8"})
    else:
        raw = http(url)
    return json.loads(raw)


def won(s):
    """'27,500원' / '월 3,000원' / '2400' -> int, 없으면 None."""
    if s is None:
        return None
    m = re.search(r"(\d[\d,]*)", str(s))
    return int(m.group(1).replace(",", "")) if m else None


def num(s):
    m = re.search(r"\d+(?:\.\d+)?", str(s or ""))
    return float(m.group()) if m else None


def is_5g_name(name):
    """요금제명에서 5G(세대) 판정. '5GB'·'15G' 같은 데이터량 표기는 제외."""
    return bool(re.search(r"(?<![0-9A-Za-z])5G(?![A-Za-z0-9])", name or ""))


def parse_overage(text):
    """원문 안내에서 초과 요금(음성·영상·문자·데이터)을 뽑아 사람이 읽는 한 줄로 만든다."""
    parts = []
    m = re.search(r"음성통화는?\s*1초당\s*([\d.]+)원", text)
    if m:
        parts.append(f"음성 {m.group(1)}원/초")
    m = re.search(r"영상통화는?\s*1초당\s*([\d.]+)원", text)
    if m:
        parts.append(f"영상 {m.group(1)}원/초")
    m = re.search(r"SMS[^:：]{0,30}[:：]\s*([\d.]+)원", text)
    if m:
        parts.append(f"문자(SMS) {m.group(1)}원")
    m = re.search(r"LMS[^:：]{0,30}[:：]\s*([\d.]+)원", text)
    if m:
        parts.append(f"LMS {m.group(1)}원")
    m = re.search(r"1MB당\s*([\d.]+)원", text)
    if m:
        parts.append(f"데이터 {m.group(1)}원/MB")
    return " · ".join(parts) or None


def parse_data(raw):
    """데이터 문구 -> (월 기본 GB, 일 GB, 무제한 여부, 소진 후 속도)."""
    raw = raw or ""
    qos = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(Kbps|Mbps)", raw, re.I)
    if m:
        qos = f"{m.group(1)}{m.group(2).capitalize()}"
    daily = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*GB\s*/\s*일|매일\s*(\d+(?:\.\d+)?)\s*GB|일\s*(\d+(?:\.\d+)?)\s*GB", raw, re.I)
    if m:
        daily = float(next(g for g in m.groups() if g))
    scrub = re.sub(r"\d+(?:\.\d+)?\s*GB\s*/\s*일|매일\s*\d+(?:\.\d+)?\s*GB|일\s*\d+(?:\.\d+)?\s*GB", " ", raw, flags=re.I)
    monthly = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(GB|MB|TB|G|M)(?![A-Za-z가-힣])", scrub, re.I)
    if m:
        v = float(m.group(1))
        unit = m.group(2).upper()
        unit = unit if unit.endswith("B") else unit + "B"
        monthly = v / 1024 if unit == "MB" else v * 1024 if unit == "TB" else v
    unlimited = False
    if monthly is None and daily is None and "무제한" in raw:
        unlimited = True
    if monthly is None and daily is not None:
        monthly = round(daily * 30, 1)  # 일 데이터형은 월 환산
    return monthly, daily, unlimited, qos


def parse_voice(raw):
    raw = raw or ""
    unlimited = bool(re.search(r"무제한|기본\s*제공|^기본$", raw.strip())) or raw.strip() == "기본"
    m = re.search(r"(\d+)\s*분", raw)
    minutes = int(m.group(1)) if m and not unlimited else (int(m.group(1)) if m else None)
    if unlimited and re.search(r"기본\s*제공", raw) and m:
        # '기본제공 + 영상/부가통화 300분' 형태: 일반통화 무제한, 부가통화량 별도
        minutes = None
    return minutes, unlimited


def make_plan(carrier, plan_id, name, network, source_url, *, gen=None, data_raw="", voice_raw="", sms_raw="",
              list_price=None, price_now=None, price_after=None, discount_type="unknown",
              discount_months=None, extra=None):
    dgb, ddaily, dunl, qos = parse_data(data_raw)
    vmin, vunl = parse_voice(voice_raw)
    return {
        "carrier": carrier,
        "plan_id": str(plan_id),
        "name": re.sub(r"\s+", " ", html.unescape(name or "")).strip(),
        "network": network,          # SKT / KT / LGU+
        "gen": gen,                  # LTE / 5G
        "data_raw": data_raw.strip(),
        "voice_raw": voice_raw.strip(),
        "sms_raw": sms_raw.strip(),
        "data_gb": dgb,
        "data_daily_gb": ddaily,
        "data_unlimited": dunl,
        "qos": qos,
        "voice_min": vmin,
        "voice_unlimited": vunl,
        "list_price": list_price,    # 정가(할인 전)
        "price_now": price_now,      # 지금 가입하면 내는 월 요금
        "price_after": price_after,  # 기간 할인 종료 후 월 요금(평생이면 price_now와 동일)
        "discount_type": discount_type,  # lifetime / period / none / unknown
        "discount_months": discount_months,
        "source_url": source_url,
        "fetched_at": now_kst(),
        **(extra or {}),
    }
