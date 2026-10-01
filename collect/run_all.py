"""전체 수집 -> data/plans.json. 한 통신사가 실패해도 나머지는 계속, 실패 통신사는 이전 데이터를 유지한다."""
import json
import os
import sys
import time
import traceback

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
import amobile, cards, eyes, freet, joytel, sk7  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
OUT = os.path.join(DATA, "plans.json")
COLLECTORS = {"에이모바일": amobile, "프리티모바일": freet, "아이즈모바일": eyes, "SK7모바일": sk7, "조이텔·시월": joytel}


def main(only=None):
    os.makedirs(DATA, exist_ok=True)
    prev = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else []
    result, report = [], {}
    for key, mod in COLLECTORS.items():
        names = {"조이텔·시월": ("조이텔", "시월모바일")}.get(key, (key,))
        if only and key not in only:
            result += [p for p in prev if p["carrier"] in names]  # 건너뛴 통신사는 이전 데이터 유지
            continue
        t = time.time()
        try:
            rows = mod.collect()
            prev_n = sum(1 for p in prev if p["carrier"] in names)
            if prev_n and len(rows) < prev_n * 0.5:
                raise RuntimeError(f"급감: {prev_n} -> {len(rows)}")
            report[key] = f"{len(rows)}개 ({time.time() - t:.0f}s)"
            result += rows
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            report[key] = "실패/급감 - 이전 데이터 유지"
            result += [p for p in prev if p["carrier"] in names]
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not only or "카드" in only:
        try:
            cs = cards.collect()
            json.dump(cs, open(os.path.join(DATA, "cards.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            report["제휴카드"] = f"{len(cs)}개"
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            report["제휴카드"] = "실패 - 이전 데이터 유지"
    for k, v in report.items():
        print(f"{k}: {v}")
    print("합계:", len(result))


if __name__ == "__main__":
    main(sys.argv[1:] or None)
