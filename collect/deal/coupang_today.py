"""쿠팡 카테고리별 베스트(생활필수품) -> data/today.json. 파트너스 Open API(GET /products/bestcategories/{id})가 파트너스 링크·가격·이미지를 준다.
'오늘의 생활 특가' 섹션(/today/)의 카테고리별 인기 상품 목록용. 순위는 쿠팡 카테고리 베스트 기준이다."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coupang_links as cl  # noqa: E402
from coupang_phones import final_image  # noqa: E402
from dealcommon import now_kst  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
# (쿠팡 카테고리 id, slug, 이름)
CATS = [(1012, "food", "식품·장보기"), (1014, "living", "생활용품"), (1013, "kitchen", "주방용품"), (1016, "digital", "가전·디지털"),
        (1011, "baby", "출산·유아동"), (1024, "health", "건강식품"), (1029, "pet", "반려동물"), (1010, "beauty", "뷰티")]


def main():
    cl._load_env()
    if "COUPANG_ACCESS_KEY" not in os.environ:
        print("API 키 없음 - 건너뜀")
        return
    out = []
    for cid, slug, name in CATS:
        try:
            rows = cl._call("GET", cl.BASE + f"/products/bestcategories/{cid}", "limit=10").get("data", [])
        except Exception as e:  # noqa: BLE001
            print("실패", name, str(e)[:80])
            continue
        items = [{"rank": i + 1, "name": p["productName"], "price": int(p["productPrice"]), "image": final_image(p.get("productImage")),
                  "url": p["productUrl"], "rocket": bool(p.get("isRocket"))} for i, p in enumerate(rows)]
        if len(items) >= 5:
            out.append({"id": cid, "slug": slug, "name": name, "items": items})
        print(name, len(items))
        time.sleep(0.6)
    if len(out) < 4:
        print("결과 부족 - 이전 데이터 유지")
        return
    json.dump({"fetched_at": now_kst(), "cats": out}, open(os.path.join(DATA, "today.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(out), "개 카테고리 저장")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
