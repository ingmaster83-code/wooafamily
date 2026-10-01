"""행사 정보 공통 스키마. 편의점·마트 수집기가 make_deal()로 같은 형태의 dict를 만든다.
표시 원칙: 정가(list_price)를 먼저, 그다음 실질 개당 가격(unit_price)을 따로 보여준다."""
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common import now_kst  # noqa: E402,F401

# 증정형 행사별 (낸 개수, 받는 개수)
MULTI = {"1+1": (1, 2), "2+1": (2, 3), "3+1": (3, 4)}


def unit_price_of(promo, price):
    """n+1 행사의 실질 개당 가격(원, 반올림). 계산 불가면 None."""
    if promo in MULTI and price:
        pay, get = MULTI[promo]
        return round(price * pay / get)
    return None


def make_deal(store, kind, key, name, promo, *, list_price=None, pay_price=None, image=None, source_url=None,
              category=None, barcode=None, period=None, extra=None):
    """list_price: 정가(개당) / pay_price: 행사 적용 시 지불 가격.
    n+1 행사는 list_price=개당 판매가, pay_price는 비워 둠(개당 실질가는 unit_price)."""
    unit = unit_price_of(promo, list_price)
    if unit is None and pay_price is not None:
        unit = pay_price  # 세일·할인: 지불가가 곧 개당 가격
    rate = None
    if list_price and unit is not None and unit < list_price:
        rate = round((1 - unit / list_price) * 100)
    return {
        "store": store, "kind": kind, "key": str(key), "name": re.sub(r"\s+", " ", name or "").strip(),
        "promo": promo, "list_price": list_price, "pay_price": pay_price, "unit_price": unit, "discount_rate": rate,
        "image": image, "category": category, "barcode": barcode, "source_url": source_url,
        "period": period, "fetched_at": now_kst(), **(extra or {}),
    }
