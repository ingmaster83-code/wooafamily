"""데이터 품질 + 카테고리 분포 리포트 (사이트 만들기 전 검증용)."""
import json
import os
import sys
from collections import Counter
from itertools import combinations

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from categories import assign  # noqa: E402

plans = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "plans.json"), encoding="utf-8"))
print("총", len(plans), "개\n")

print("== 통신사별 개수 / 품질 이상")
for c, n in Counter(p["carrier"] for p in plans).items():
    rows = [p for p in plans if p["carrier"] == c]
    bad = {
        "망없음": sum(1 for p in rows if not p["network"]),
        "가격없음": sum(1 for p in rows if p["price_now"] is None),
        "데이터불명": sum(1 for p in rows if p["data_gb"] is None and not p["data_unlimited"]),
        "통화불명": sum(1 for p in rows if p["voice_min"] is None and not p["voice_unlimited"]),
        "정가없음": sum(1 for p in rows if p["list_price"] is None),
    }
    print(f"  {c}: {n}  이상={ {k: v for k, v in bad.items() if v} }")

print("\n== 할인 유형")
print(" ", dict(Counter(p["discount_type"] for p in plans)))

cats = [assign(p) for p in plans]
axes = ["network", "gen", "data", "price", "voice", "qos", "discount"]
print("\n== 축별 분포")
for a in axes:
    print(f"  {a}:", dict(Counter(c[a] for c in cats).most_common()))

# 2축 조합 페이지 수(결과 3개 이상만 페이지 생성)
MIN = 3
print(f"\n== 2축 조합 중 결과 {MIN}개 이상(=생성 가능 페이지)")
total = 0
for a, b in combinations(axes, 2):
    cnt = Counter((c[a], c[b]) for c in cats if c[a] and c[b])
    ok = sum(1 for v in cnt.values() if v >= MIN)
    total += ok
    print(f"  {a} x {b}: {ok}/{len(cnt)}")
print("  합계(2축):", total)
single = sum(1 for a in axes for k, v in Counter(c[a] for c in cats).items() if k and v >= MIN)
print("  1축 페이지:", single, " 요금제 상세:", len(plans))
