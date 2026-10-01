"""쿠팡 골드박스(오늘의 특가) -> data/goldbox.json. 파트너스 Open API(GET /products/goldbox)가 파트너스 링크와 가격·이미지를 준다.
행사 페이지 하단에 우리 HTML로 직접 보여주기 위한 데이터(외부 위젯은 광고 차단·도메인 등록 문제로 비는 경우가 있음)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coupang_links as cl  # noqa: E402
from coupang_phones import final_image  # noqa: E402
from dealcommon import now_kst  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")


def main(limit=24):
    cl._load_env()
    if "COUPANG_ACCESS_KEY" not in os.environ:
        print("API 키 없음 - 건너뜀")
        return
    rows = cl._call("GET", cl.BASE + "/products/goldbox", "").get("data", [])
    items = []
    for p in rows[:limit]:
        items.append({"name": p["productName"], "price": int(p["productPrice"]), "image": final_image(p.get("productImage")),
                      "url": p["productUrl"], "rocket": bool(p.get("isRocket")), "category": p.get("categoryName")})
    if len(items) < 6:
        print("결과 부족:", len(items), "- 이전 데이터 유지")
        return
    json.dump({"fetched_at": now_kst(), "items": items}, open(os.path.join(DATA, "goldbox.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(items), "개 저장")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
