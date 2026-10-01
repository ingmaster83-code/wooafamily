"""쿠팡 자급제폰 TOP 10 -> data/phones.json (쿠팡 파트너스 Open API 상품 검색, 파트너스 링크 포함).

순위 기준은 '쿠팡 검색 랭킹'이다(판매량 순위가 아님). 여러 검색어 결과를 합치고, 액세서리·리퍼·중고·중복 상품을 걸러 상위 10개를 남긴다.
키는 환경변수 COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY 또는 wooafamily/.env.local 에서만 읽는다."""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coupang_links as cl  # noqa: E402
from dealcommon import now_kst  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
QUERIES = ["삼성전자 갤럭시 자급제", "Apple 아이폰 자급제", "자급제폰", "자급제 스마트폰", "삼성전자 갤럭시 S26 자급제",
           "Apple 아이폰 17 자급제", "삼성전자 갤럭시 A 자급제", "삼성전자 갤럭시 Z 플립 자급제", "Apple 아이폰 자급제 256GB", "삼성전자 갤럭시 S25 자급제"]
POS = re.compile(r"자급제|SM-[A-Z]\d{2,4}[A-Z]?|아이폰\s?\d{2}|iPhone")
NEG = re.compile(r"케이스|필름|보호|충전|케이블|거치|스트랩|이어폰|버즈|워치|리퍼|공기계|중고|[SAB]급|언락|젤리|커버|강화유리|링|그립|스탠드|파우치|팝소켓|폴더폰|터치스크린")


def search(kw, limit=10):  # limit 10 초과 시 결과가 비어 오는 것을 확인함
    q = urllib.parse.urlencode({"keyword": kw, "limit": limit})
    return cl._call("GET", cl.BASE + "/products/search", q).get("data", {}).get("productData", [])


def final_image(url):
    """ads-partners.coupang.com 중간 주소는 광고 차단기에 걸리므로, 리다이렉트를 따라가 최종 이미지 CDN 주소를 쓴다."""
    if not url or "ads-partners" not in url:
        return url
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=15).geturl() or url
    except Exception:  # noqa: BLE001
        return url


def norm(name):
    return re.sub(r"[\s\-_/()]+", "", name).lower()


def main(top=10):
    cl._load_env()
    if "COUPANG_ACCESS_KEY" not in os.environ:
        print("API 키 없음 - 건너뜀")
        return
    lists = []
    for kw in QUERIES:
        try:
            lists.append([p for p in search(kw) if POS.search(p["productName"]) and not NEG.search(p["productName"])])
        except Exception as e:  # noqa: BLE001
            print("검색 실패", kw, str(e)[:80])
        time.sleep(0.6)
    out, seen_id, seen_name = [], set(), set()
    for i in range(max((len(x) for x in lists), default=0)):  # 검색어별 순위를 번갈아 합친다
        for lst in lists:
            if i >= len(lst):
                continue
            p = lst[i]
            if p["productId"] in seen_id or norm(p["productName"]) in seen_name:
                continue
            seen_id.add(p["productId"])
            seen_name.add(norm(p["productName"]))
            out.append({"name": p["productName"], "price": int(p["productPrice"]), "image": final_image(p.get("productImage")),
                        "url": p["productUrl"], "rocket": bool(p.get("isRocket"))})
    out = out[:top]
    for n, p in enumerate(out, 1):
        p["rank"] = n
    if len(out) < 5:  # 결과가 너무 적으면 이전 데이터를 유지
        print("결과 부족:", len(out), "- 이전 데이터 유지")
        return
    json.dump({"fetched_at": now_kst(), "basis": "쿠팡 검색 랭킹", "items": out},
              open(os.path.join(DATA, "phones.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(out), "개 저장")
    for p in out:
        print(p["rank"], p["name"][:44], p["price"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
