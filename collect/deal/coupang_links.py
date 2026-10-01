"""행사 상품 -> 쿠팡 검색결과 페이지의 파트너스 단축링크 매핑 (data/coupang_links.json: {deal key: 링크}).

방식: 상품명을 쿠팡 검색 URL(https://www.coupang.com/np/search?q=...)로 만들고, 딥링크 API(POST /deeplink, 여러 URL 일괄)로
수수료가 귀속되는 link.coupang.com 단축 URL로 변환한다. 개별 상품을 추정해서 연결하지 않으므로 엉뚱한 상품으로 연결될 위험이 없다.

키는 환경변수 COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY 또는 wooafamily/.env.local 에서만 읽는다(저장소에 올리지 말 것).
링크를 쓰는 페이지에는 '파트너스 활동을 통해 일정액의 수수료를 제공받을 수 있음' 문구가 있어야 한다(API 응답에도 안내됨)."""
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HOST = "https://api-gateway.coupang.com"
BASE = "/v2/providers/affiliate_open_api/apis/openapi/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "data")
BATCH = 20
# 쿠팡 파트너스에 맞지 않거나 검색 결과가 무의미한 품목(주류·담배·상품권 등)은 링크를 만들지 않는다
SKIP = re.compile(r"위스키|와인|소주|맥주|막걸리|사케|보드카|담배|전자담배|상품권|기프트|교통카드|복권|수입맥주|하이볼|리큐르|칵테일")
PREFIX = re.compile(r"^[가-힣A-Za-z0-9&\.]{1,8}\)")  # '농심)' 같은 제조사 표기


def _load_env():
    """wooafamily/.env.local 의 KEY=VALUE 를 환경변수로 읽는다(이미 설정돼 있으면 유지)."""
    p = os.path.join(HERE, "..", "..", ".env.local")
    if not os.path.exists(p):
        return
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip())


def _auth(method, path, query=""):
    ak, sk = os.environ["COUPANG_ACCESS_KEY"], os.environ["COUPANG_SECRET_KEY"]
    signed = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")
    sig = hmac.new(sk.encode(), (signed + method + path + query).encode(), hashlib.sha256).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={ak}, signed-date={signed}, signature={sig}"


def _call(method, path, query="", body=None):
    url = HOST + path + (("?" + query) if query else "")
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": _auth(method, path, query), "Content-Type": "application/json;charset=UTF-8"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))


def keyword_of(name):
    """'농심)멘토스레인보우' -> '농심 멘토스레인보우'. 제조사 접두어는 공백으로 풀고 (New)·(특) 같은 매장 표기는 제거."""
    n = re.sub(r"\((?:New|NEW|특|신|증|행사|BIG|PB|종료)[^)]*\)", " ", name)
    m = PREFIX.match(n)
    if m:
        n = m.group(0)[:-1] + " " + n[m.end():]
    n = re.sub(r"[^\w\s가-힣.+%&]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def search_url(keyword):
    return "https://www.coupang.com/np/search?q=" + urllib.parse.quote(keyword)


def convert(urls):
    """URL 리스트 -> {원본URL: 단축URL}"""
    r = _call("POST", BASE + "/deeplink", "", {"coupangUrls": urls})
    return {d["originalUrl"]: d["shortenUrl"] for d in r.get("data", []) if d.get("shortenUrl")}


def main(limit=None):
    _load_env()
    if "COUPANG_ACCESS_KEY" not in os.environ:
        print("API 키 없음 - 건너뜀 (.env.local 설정 후 실행)")
        return
    deals = json.load(open(os.path.join(DATA, "deals.json"), encoding="utf-8"))
    cache_path = os.path.join(DATA, "coupang_cache.json")  # 키워드 -> 단축URL (재사용)
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}
    kw_of = {}
    for d in deals:
        if SKIP.search(d["name"]):
            continue
        k = keyword_of(d["name"])
        if len(k) >= 2:
            kw_of[d["key"]] = k
    todo = sorted({k for k in kw_of.values() if k not in cache})
    if limit:
        todo = todo[:limit]
    print(f"상품 {len(kw_of)}개 / 고유 키워드 {len(set(kw_of.values()))}개 / 새로 변환 {len(todo)}개")
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        urls = [search_url(k) for k in chunk]
        try:
            got = convert(urls)
        except urllib.error.HTTPError as e:
            print("HTTP", e.code, e.read().decode("utf-8", "ignore")[:200])
            time.sleep(5)
            continue
        except Exception as e:  # noqa: BLE001
            print("ERR", type(e).__name__, str(e)[:120])
            time.sleep(3)
            continue
        for k, u in zip(chunk, urls):
            # 응답의 originalUrl 은 인코딩 형태가 다를 수 있어 순서/정규화 둘 다 대응
            s = got.get(u) or next((v for o, v in got.items() if urllib.parse.unquote(o) == urllib.parse.unquote(u)), None)
            if s:
                cache[k] = s
        time.sleep(0.5)
        if (i // BATCH) % 10 == 0:
            json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
    links = {key: cache[k] for key, k in kw_of.items() if k in cache}
    json.dump(links, open(os.path.join(DATA, "coupang_links.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"링크 {len(links)}개 연결 (키워드 캐시 {len(cache)}개)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
