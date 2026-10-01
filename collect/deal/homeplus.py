"""홈플러스 주간 전단: GET /leaf/getLeafletCache.json(현재 전단번호·기간·카테고리) + /leaf/item.json(상품, 20개씩).
카드할인가는 '해당 카드 결제 시' 가격이라 promo를 '카드할인'으로 구분해서 표시한다."""
import time
from dealcommon import make_deal
from common import DELAY, http_json

BASE = "https://mfront.homeplus.co.kr"


def collect():
    meta = http_json(BASE + "/leaf/getLeafletCache.json")["data"]
    no, period = meta["leafletNo"], f'{meta["dispStartDt"]} ~ {meta["dispEndDt"]}'
    cats = {c["cateNo"]: c["cateNm"] for c in meta["categoryList"] if c["cateNm"] != "전체"}
    out, seen = [], set()
    for cno, cname in cats.items():
        offset = 0
        while offset < 3000:
            rows = http_json(f"{BASE}/leaf/item.json?categoryId={cno}&leafletNo={no}&limit=20&offset={offset}&sort=RANK")["data"]["dataList"]
            if not rows:
                break
            for it in rows:
                if it["itemNo"] in seen:
                    continue
                seen.add(it["itemNo"])
                sale, dc = it.get("salePrice"), it.get("dcPrice")
                card = "CARD" in (it.get("dcType") or "")
                promo = "카드할인" if card else ("상품할인" if dc and sale and dc < sale else "전단가")
                size = None
                if it.get("unitDispYn") == "Y" and it.get("unitPrice"):
                    size = f'{it.get("unitQty")}{it.get("unitMeasure")}당 {int(round(it["unitPrice"])):,}원'
                out.append(make_deal(
                    "홈플러스", "mart", f'homeplus-{it["itemNo"]}', it["itemNm"], promo, list_price=sale, pay_price=dc if dc else sale,
                    image=f'https://image.homeplus.kr/td/{it["itemNo"]}' if False else None, category=cname,
                    source_url=f'{BASE}/item?itemNo={it["itemNo"]}&storeType=HYPER', period=period,
                    extra={"size_unit": size, "grade": it.get("grade"), "review_cnt": it.get("reviewCnt"),
                           "label": " / ".join(it.get("labelList") or []) or None, "per_store_note": "점포별 가격·취급상품이 다를 수 있음"}))
            offset += 20
            time.sleep(DELAY)
    return out


if __name__ == "__main__":
    import sys
    from collections import Counter
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), Counter(d["promo"] for d in r)); print(r[0])
