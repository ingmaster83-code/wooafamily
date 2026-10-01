"""정규화된 plans.json 에 카테고리 키를 부여하는 규칙. 사이트 생성기와 분포 리포트가 함께 쓴다."""


def data_bucket(p):
    if p["data_unlimited"]:
        return "unlimited"
    g = p["data_gb"]
    if g is None:
        return None
    if g <= 1:
        return "~1gb"
    if g <= 5:
        return "1-5gb"
    if g <= 10:
        return "5-10gb"
    if g <= 30:
        return "10-30gb"
    return "30gb+"


def price_bucket(p):
    v = p["price_after"] if p["price_after"] is not None else p["price_now"]  # 장기 요금 기준
    if v is None:
        return None
    if v <= 10000:
        return "under-10k"
    if v <= 20000:
        return "10-20k"
    if v <= 30000:
        return "20-30k"
    return "30k+"


def voice_bucket(p):
    if p["voice_unlimited"]:
        return "unlimited"
    m = p["voice_min"]
    if m is None:
        return None
    if m == 0:
        return "none"
    return "~100m" if m <= 100 else "~300m" if m <= 300 else "300m+"


def qos_bucket(p):
    q = p["qos"]
    return q.lower() if q else "none"


def assign(p):
    return {
        "carrier": p["carrier"],
        "network": p["network"],
        "gen": p["gen"],
        "data": data_bucket(p),
        "price": price_bucket(p),
        "voice": voice_bucket(p),
        "qos": qos_bucket(p),
        "discount": p["discount_type"],
    }
