"""행사 수집 -> data/deals.json (+ 월별 이력 data/deal_history/YYYY-MM.json). 실패한 곳은 이전 데이터를 유지한다."""
import json
import os
import sys
import time
import traceback

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import cu, emart24, homeplus, seven  # noqa: E402

DATA = os.path.join(HERE, "..", "..", "data")
OUT = os.path.join(DATA, "deals.json")
STORES = {"CU": cu, "세븐일레븐": seven, "이마트24": emart24, "홈플러스": homeplus}


def main(only=None):
    os.makedirs(DATA, exist_ok=True)
    prev = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else []
    result, report = [], {}
    for name, mod in STORES.items():
        if only and name not in only:
            result += [d for d in prev if d["store"] == name]
            continue
        t = time.time()
        try:
            rows = mod.collect()
            prev_n = sum(1 for x in prev if x["store"] == name)
            if not rows or (prev_n and len(rows) < prev_n * 0.5):
                raise RuntimeError(f"급감/0건: {prev_n} -> {len(rows)}")
            report[name] = f"{len(rows)}개 ({time.time() - t:.0f}s)"
            result += rows
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            report[name] = "실패 - 이전 데이터 유지"
            result += [d for d in prev if d["store"] == name]
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 월별 이력(상품 키 + 행사유형 + 가격만 보관)
    if result:
        ym = max(d["fetched_at"] for d in result)[:7]
        hist_dir = os.path.join(DATA, "deal_history")
        os.makedirs(hist_dir, exist_ok=True)
        hp = os.path.join(hist_dir, f"{ym}.json")
        hist = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else {}
        for d in result:
            hist[d["key"]] = {"store": d["store"], "name": d["name"], "promo": d["promo"], "list_price": d["list_price"],
                              "unit_price": d["unit_price"], "last_seen": d["fetched_at"][:10], "first_seen": hist.get(d["key"], {}).get("first_seen", d["fetched_at"][:10])}
        json.dump(hist, open(hp, "w", encoding="utf-8"), ensure_ascii=False)
    for k, v in report.items():
        print(f"{k}: {v}")
    print("합계:", len(result))


if __name__ == "__main__":
    main(sys.argv[1:] or None)
