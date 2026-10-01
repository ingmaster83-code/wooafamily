"""data/plans.json -> site/ 정적 HTML 생성. 사용: python build.py
구조: 우아패밀리 = 절약 통합 포털. 알뜰폰 요금제는 /phone/ 섹션(향후 다른 절약 섹션이 형제로 추가됨)."""
import html
import json
import os
import re
import shutil
import statistics
import sys
from collections import Counter, defaultdict
from itertools import combinations

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "collect"))
import config as C  # noqa: E402
from categories import assign  # noqa: E402

OUT = os.path.join(HERE, "site")
esc = html.escape
SEC = "/phone"  # 알뜰폰 섹션 접두사

CARRIER_SLUG = {"아이즈모바일": "eyes", "프리티모바일": "freet", "에이모바일": "amobile",
                "조이텔": "joytel", "시월모바일": "siwol", "SK7모바일": "sk7"}
NET_SLUG = {"SKT": "skt", "KT": "kt", "LGU+": "lgu"}
LABELS = {
    "network": {"SKT": "SKT망", "KT": "KT망", "LGU+": "LG U+망"},
    "gen": {"LTE": "LTE", "5G": "5G", "3G": "3G"},
    "data": {"unlimited": "데이터 무제한", "~1gb": "데이터 1GB 이하", "1-5gb": "데이터 1~5GB",
             "5-10gb": "데이터 5~10GB", "10-30gb": "데이터 10~30GB", "30gb+": "데이터 30GB 이상"},
    "price": {"under-10k": "월 1만원 이하", "10-20k": "월 1~2만원대", "20-30k": "월 2~3만원대", "30k+": "월 3만원 이상"},
    "voice": {"unlimited": "통화 무제한", "none": "통화 없음", "~100m": "통화 100분 이하",
              "~300m": "통화 300분 이하", "300m+": "통화 300분 초과"},
    "qos": {"none": "소진 후 속도 미제공", "400kbps": "소진 후 400Kbps", "1mbps": "소진 후 1Mbps",
            "3mbps": "소진 후 3Mbps", "5mbps": "소진 후 5Mbps", "10mbps": "소진 후 10Mbps"},
    "discount": {"lifetime": "평생 할인", "period": "기간 할인", "none": "정가(할인 없음)"},
    "carrier": {k: k for k in CARRIER_SLUG},
}
AXIS_TITLE = {"carrier": "통신사", "network": "통신망", "gen": "세대", "data": "데이터량", "price": "월 요금",
              "voice": "통화", "qos": "소진 후 속도", "discount": "할인 유형"}
AXIS_DESC = {"carrier": "알뜰폰 통신사별 요금제", "network": "SKT·KT·LG U+ 통신망별 요금제",
             "data": "데이터 제공량 구간별 요금제", "price": "월 요금대별 요금제",
             "voice": "통화 제공량별 요금제", "discount": "평생 할인·기간 할인·정가 요금제"}
AXES = ["carrier", "network", "gen", "data", "price", "voice", "qos", "discount"]
TABS = ["carrier", "network", "data", "price", "voice", "discount"]  # 섹션 상단 탭 + 축 인덱스 페이지
SLUG_OF = {"carrier": CARRIER_SLUG, "network": NET_SLUG}

# 포털 서비스 목록: live=True 만 링크. 나머지는 '준비 중' 로드맵 카드(내용은 자유롭게 교체)
SERVICES = [
    {"key": "phone", "icon": "📱", "name": "통신비", "title": "알뜰폰 요금제 비교", "url": SEC + "/", "live": True,
     "desc": "통신사 공식 정보 기준으로 요금제를 한눈에 비교"},
    {"key": "deal", "icon": "🏪", "name": "장보기", "title": "편의점·마트 행사 모음", "url": "/deal/", "live": True,
     "desc": "1+1·2+1을 정가와 개당 가격으로 비교"},
    {"key": "move", "icon": "⛽", "name": "교통비", "title": "주유소 최저가·정기권 비교", "url": "#", "live": False,
     "desc": "기름값과 대중교통비를 줄이는 방법"},
    {"key": "energy", "icon": "💡", "name": "공과금", "title": "전기·가스 요금 계산", "url": "#", "live": False,
     "desc": "고정비를 줄이는 계산기와 감면 안내"},
]


def vslug(axis, v):
    return SLUG_OF.get(axis, {}).get(v, re.sub(r"[^a-z0-9-]", "", v.replace("~", "u").replace("+", "p")))


def won(v):
    return "-" if v is None else f"{v:,}원"


def eff(p):
    """장기 월 요금(할인 종료 후, 평생이면 현재가)."""
    return p["price_after"] if p["price_after"] is not None else p["price_now"]


def year_avg(p):
    """첫 12개월 월평균 실질 요금."""
    m = p["discount_months"]
    if p["discount_type"] != "period" or not m or p["price_now"] is None or p["price_after"] is None:
        return eff(p)
    k = min(m, 12)
    return round((p["price_now"] * k + p["price_after"] * (12 - k)) / 12)


def data_label(p, qos=True):
    g, d = p["data_gb"], p["data_daily_gb"]
    if p["data_unlimited"]:
        s = "무제한"
    elif g is None:
        s = "-"
    elif d and not re.search(r"\d\s*GB", re.sub(r"\d+(?:\.\d+)?\s*GB\s*/\s*일|매일\s*\d+(?:\.\d+)?\s*GB|일\s*\d+(?:\.\d+)?\s*GB", "", p["data_raw"], flags=re.I)):
        s = f"매일 {d:g}GB"
    else:
        s = f"{g:g}GB" if g >= 1 else f"{round(g * 1024)}MB"
        if d:
            s += f" + 매일 {d:g}GB"
    if qos and p["qos"]:
        s += f" (소진 후 {p['qos']})"
    return s


def voice_label(p):
    if p["voice_unlimited"]:
        return "무제한(일반통화)"
    if p["voice_min"] is None:
        return "-"
    return "없음" if p["voice_min"] == 0 else f"{p['voice_min']}분"


def sms_label(p):
    s = p["sms_raw"] or "-"
    return "기본제공" if s in ("기본", "기본제공") else s


def discount_label(p):
    t, m = p["discount_type"], p["discount_months"]
    if t == "lifetime":
        return "평생 할인"
    if t == "period":
        return f"{m}개월 할인" if m else "기간 할인"
    return "정가"


def price_story(p):
    t = p["discount_type"]
    if t == "lifetime":
        return f"가입 후 계속 월 {won(p['price_now'])}"
    if t == "period" and p["discount_months"] and p["price_after"] is not None:
        return f"처음 {p['discount_months']}개월 월 {won(p['price_now'])} → 이후 월 {won(p['price_after'])}"
    if t == "period":
        return f"할인 기간 월 {won(p['price_now'])}(종료 후 요금은 통신사 안내 확인)"
    return f"월 {won(p['price_now'])}"


def plan_url(p):
    pid = re.sub(r"[^a-z0-9]+", "-", p["plan_id"].lower()).strip("-")
    return f"{SEC}/plans/{CARRIER_SLUG[p['carrier']]}-{pid}/"


def cat_url(axis, v):
    return f"{SEC}/{axis}/{vslug(axis, v)}/"


def combo_url(a, va, b, vb):
    return f"{SEC}/{a}/{vslug(a, va)}/{b}/{vslug(b, vb)}/"


# ---------------------------------------------------------------- HTML 조각
def head(title, desc, path, ld=None, noindex=False):
    url = C.DOMAIN + path
    ga = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={C.GA_ID}"></script>'
          f'<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}'
          f'gtag("js",new Date());gtag("config","{C.GA_ID}");</script>') if C.GA_ID else ""
    ads = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={C.ADSENSE_CLIENT}" '
           f'crossorigin="anonymous"></script>') if C.ADSENSE_CLIENT else ""
    ldj = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in (ld or []))
    robots = '<meta name="robots" content="noindex,follow">' if noindex else ""
    verify = f'<meta name="naver-site-verification" content="{C.NAVER_SITE_VERIFICATION}">' if getattr(C, "NAVER_SITE_VERIFICATION", "") else ""
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">'
            f'<link rel="canonical" href="{url}">{robots}{verify}'
            f'<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}">'
            f'<meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{url}">'
            f'<meta property="og:site_name" content="{C.SITE_NAME}"><meta property="og:locale" content="ko_KR">'
            f'<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">'
            f'<link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/density.css"><link rel="stylesheet" href="/deal.css">{ga}{ads}{ldj}</head><body>')


def header(active=""):
    menu = "".join(
        (f'<a class="mi" href="{s["url"]}"><span class="mi-ic">{s["icon"]}</span><span><b>{s["name"]}</b>'
         f'<em>{esc(s["title"])}</em></span></a>') if s["live"] else
        (f'<span class="mi off"><span class="mi-ic">{s["icon"]}</span><span><b>{s["name"]}</b>'
         f'<em>{esc(s["title"])} · 준비 중</em></span></span>') for s in SERVICES)
    return (f'<header class="gh"><div class="wrap gh-in"><a class="logo" href="/"><i>우</i>{C.SITE_NAME}</a>'
            f'<nav class="gnav"><div class="dd"><button type="button" class="dd-b">전체 서비스 <span>▾</span></button>'
            f'<div class="dd-m">{menu}</div></div>'
            f'<a href="{SEC}/" class="{"on" if active == "phone" else ""}">알뜰폰 요금제</a>'
            f'<a href="/deal/" class="{"on" if active == "deal" else ""}">편의점·마트 행사</a>'
            f'<a href="/about/">소개</a></nav></div></header>')


def subnav(active_axis=None):
    tabs = [(f"{SEC}/", "알뜰폰 홈", "home")] + [(f"{SEC}/{a}/", AXIS_TITLE[a] + "별", a) for a in TABS]
    t = "".join(f'<a href="{u}" class="{"on" if k == active_axis else ""}">{n}</a>' for u, n, k in tabs)
    return f'<div class="sub"><div class="wrap sub-in">{t}</div></div>'


def crumbs(items):
    out = '<span class="sep">/</span>'.join(f'<a href="{u}">{esc(t)}</a>' if u else f"<span>{esc(t)}</span>" for u, t in items)
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": t, **({"item": C.DOMAIN + u} if u else {})}
        for i, (u, t) in enumerate(items)]}
    return f'<nav class="crumbs">{out}</nav>', ld


def coupang_generic():
    if not C.COUPANG_ENABLED:
        return ""
    return ('<section class="card coupang"><h2>함께 보면 좋은 쿠팡 추천 상품</h2>'
            '<p class="muted">관심 상품을 기반으로 한 쿠팡 추천입니다.</p>'
            '<script src="https://ads-partners.coupang.com/g.js"></script>'
            f'<script>new PartnersCoupang.G({{"id":{C.COUPANG_ID},"trackingCode":"{C.COUPANG_TRACKING}",'
            '"subId":"wooafamily","template":"carousel","width":"680","height":"140"});</script>'
            '<p class="fine">이 페이지는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p></section>')


def footer(stamp, finder_js=False):
    contact = f'<p>정정 요청: {esc(C.CONTACT_EMAIL)}</p>' if C.CONTACT_EMAIL else ""
    live = "".join(f'<a href="{s["url"]}">{s["name"]} · {esc(s["title"])}</a>' for s in SERVICES if s["live"])
    soon = "".join(f'<span>{s["name"]} <em>준비 중</em></span>' for s in SERVICES if not s["live"])
    return (f'<footer class="gf"><div class="wrap"><div class="gf-grid">'
            f'<div><div class="logo sm"><i>우</i>{C.SITE_NAME}</div><p class="muted">{C.TAGLINE}.<br>'
            f'생활비를 줄여주는 정보를 한곳에 모았어요.</p></div>'
            f'<div><h4>서비스</h4>{live}{soon}</div>'
            f'<div><h4>안내</h4><a href="/about/">서비스 소개·수집 정책</a><a href="/privacy/">개인정보처리방침</a></div></div>'
            f'<div class="gf-note"><p>요금 정보는 각 통신사 공식 홈페이지를 기준으로 하루 여러 번 확인해 갱신합니다(최근 확인: {stamp}). '
            f'실제 가입 조건과 요금은 반드시 통신사 화면에서 다시 확인하세요. 우아패밀리는 통신사의 대리·중개 사이트가 아닙니다.</p>{contact}'
            f'<p>© 2026 {C.SITE_NAME}</p></div></div></footer>{'<script src="/finder.js"></script>' if finder_js else ''}</body></html>')


def qos_kbps(p):
    m = re.match(r"([\d.]+)\s*(Kbps|Mbps)", p["qos"] or "", re.I)
    return int(float(m.group(1)) * (1000 if m.group(2).lower() == "mbps" else 1)) if m else 0


NETCLS = {"SKT": "skt", "KT": "kt", "LGU+": "lgu"}


def is_unl(p):
    """데이터 무제한: 순수 무제한이거나, 기본 데이터 소진 후에도 속도제한으로 계속 쓸 수 있는 요금제."""
    return bool(p["data_unlimited"] or qos_kbps(p) > 0)


def after_html(p):
    t = p["discount_type"]
    if t == "period" and p["discount_months"] and p["price_after"] is not None:
        return f'<span class="af warn">{p["discount_months"]}개월 후 {p["price_after"]:,}원</span>'
    if t == "lifetime":
        return '<span class="af good">평생 유지</span>'
    if t == "period":
        return '<span class="af warn">기간 한정 할인</span>'
    return '<span class="af">정가</span>'


def plan_row(p):
    c = p["_cat"]
    sub = []
    if p["qos"]:
        sub.append(f"+{p['qos']}")
    sub.append("통화 " + ("무제한" if p["voice_unlimited"] else voice_label(p)))
    sub.append("문자 " + sms_label(p).replace("기본제공", "무제한"))
    tags = "".join(f'<span class="tg">{t}</span>' for t in ([p["gen"]] if p["gen"] == "5G" else []))
    if is_unl(p):
        tags += '<span class="tg unl">소진 후 무제한</span>'
    return (f'<a class="row" href="{plan_url(p)}" data-net="{c["network"]}" data-gen="{p["gen"] or ""}" data-data="{c["data"] or ""}" '
            f'data-price="{c["price"] or ""}" data-voice="{"u" if p["voice_unlimited"] else "m"}" data-qos="{qos_kbps(p)}" '
            f'data-disc="{p["discount_type"]}" data-car="{CARRIER_SLUG[p["carrier"]]}" data-gb="{9999 if p["data_unlimited"] else (p["data_gb"] or 0)}" '
            f'data-unl="{1 if is_unl(p) else 0}" data-now="{p["price_now"] or 0}" data-eff="{eff(p) or 0}">'
            f'<div class="r-main"><div class="r-top"><span class="net {NETCLS[p["network"]]}">{esc(p["network"])}</span>'
            f'<span class="car">{esc(p["carrier"])}</span></div><b class="r-name">{esc(p["name"])}</b>'
            f'<div class="r-spec"><span class="r-data">{esc(data_label(p, False))}</span>'
            f'<span class="r-sub">{esc(" · ".join(sub))}</span></div>'
            f'<div class="r-tags">{tags}<span class="tag {p["discount_type"]}">{esc(discount_label(p))}</span></div></div>'
            f'<div class="r-price"><b>{p["price_now"]:,}원</b>{after_html(p)}</div><span class="chev">›</span></a>')


def plan_rows(plans):
    return f'<div class="list static">{"".join(plan_row(p) for p in plans)}</div>'


def seg(k, opts):
    btns = "".join(f'<button type="button" data-v="{v}" class="{"on" if i == 0 else ""}">{esc(t)}</button>'
                   for i, (v, t) in enumerate([("", "전체")] + opts))
    return f'<div class="seg" data-k="{k}">{btns}</div>'


def filter_panel(carriers):
    net = seg("net", [("SKT", "SKT"), ("KT", "KT"), ("LGU+", "LG U+")])
    qos = seg("qos", [("5", "5Mbps↑"), ("3", "3Mbps"), ("1", "1Mbps↓"), ("0", "없음")])
    data = seg("data", [(v, LABELS["data"][v].replace("데이터 ", "")) for v in ["~1gb", "1-5gb", "5-10gb", "10-30gb", "30gb+", "unlimited"]])
    price = seg("price", [(v, LABELS["price"][v].replace("월 ", "")) for v in ["under-10k", "10-20k", "20-30k", "30k+"]])
    disc = seg("disc", [("lifetime", "평생"), ("period", "기간"), ("none", "정가")])
    cars = "".join(f'<label class="carchk"><input type="checkbox" value="{CARRIER_SLUG[c]}"><span>{esc(c)}</span></label>' for c in carriers)
    return ('<aside class="filters" id="filters"><div class="f-head"><b>필터</b><button type="button" id="resetf" class="lnk">초기화</button>'
            '<button type="button" class="closef x" aria-label="닫기">✕</button></div>'
            f'<div class="f-g"><h4>통신망</h4>{net}</div><div class="f-g"><h4>소진 후 속도</h4>{qos}</div>'
            '<div class="f-g"><h4>빠른 필터</h4><div class="tgls"><button type="button" class="tgl" data-k="voice">통화 무제한</button>'
            '<button type="button" class="tgl" data-k="g5">5G</button><button type="button" class="tgl" data-k="life">평생 할인</button></div></div>'
            f'<div class="f-g"><h4>데이터량</h4>{data}</div><div class="f-g"><h4>월 요금대</h4>{price}</div>'
            f'<div class="f-g"><h4>할인 유형</h4>{disc}</div><div class="f-g"><h4>통신사</h4><div class="cars">{cars}</div></div>'
            '<button type="button" class="closef apply"><span id="fcnt">0</span>개 결과 보기</button></aside><div class="backdrop closef"></div>')


def finder(plans, asof, carriers):
    net = seg("net", [("SKT", "SKT"), ("KT", "KT"), ("LGU+", "LG U+")])
    return ('<div class="finder">' + filter_panel(carriers) +
            f'<section class="results"><div class="mbar">{net}<button type="button" id="openf" class="fbtn">필터</button></div>'
            f'<div class="res-head"><div class="rh-l"><span><b id="cnt">{len(plans)}</b>개</span>'
            '<button type="button" class="sortb on" data-s="eff">낮은 가격순</button>'
            '<button type="button" class="sortb" data-s="now">지금 가격순</button>'
            '<button type="button" class="sortb" data-s="gb">데이터 많은순</button></div>'
            f'<span class="asof">{asof} 기준</span></div>'
            f'<div class="list" id="list">{"".join(plan_row(p) for p in plans)}</div>'
            '<p id="empty" class="empty" hidden>조건에 맞는 요금제가 없어요. 필터를 줄여 보세요.</p>'
            '<button type="button" id="more" class="morebtn" hidden>더 보기</button></section></div>')


def plan_cards(plans):
    out = []
    for p in plans:
        out.append(f'<a class="pc" href="{plan_url(p)}"><span class="tag {p["discount_type"]}">{esc(discount_label(p))}</span>'
                   f'<b class="pc-n">{esc(p["name"])}</b><span class="sm">{esc(p["carrier"])} · {esc(p["network"])} · {esc(data_label(p).split(" (")[0])}</span>'
                   f'<span class="pc-p">월 <strong>{p["price_now"]:,}</strong>원</span><span class="sm">{esc(price_story(p))}</span></a>')
    return f'<div class="pcs">{"".join(out)}</div>'


CARDS = []
PHONES = {}


def phone_carousel():
    items = PHONES.get("items") or []
    if not items:
        return ""
    slides = "".join(
        f'<a class="pcar-s" href="{esc(p["url"])}" rel="nofollow sponsored noopener" target="_blank">'
        f'{("<img class=pcar-img referrerpolicy=no-referrer src=" + chr(34) + esc(p["image"]) + chr(34) + " alt=>") if p.get("image") else "<span class=pcar-img></span>"}'
        f'<span class="pcar-m"><span class="pcar-rank">인기 {p["rank"]}위</span><b>{esc(p["name"])}</b>'
        f'<span class="pcar-p">{p["price"]:,}원{" <i>로켓배송</i>" if p.get("rocket") else ""}</span>'
        f'<span class="pcar-go">온라인 가격비교 ↗</span></span></a>' for p in items)
    dots = "".join(f'<button type="button" class="pcar-dot{" on" if k == 0 else ""}" aria-label="{k + 1}번째"></button>' for k in range(len(items)))
    return ('<h2 class="sh">알뜰폰과 함께 쓰는 자급제폰</h2>'
            f'<div class="card tight pcar" id="pcar"><div class="pcar-track">{slides}</div>'
            f'<button type="button" class="pcar-arrow pcar-prev" aria-label="이전">‹</button>'
            f'<button type="button" class="pcar-arrow pcar-next" aria-label="다음">›</button>'
            f'<div class="pcar-dots">{dots}</div></div>'
            f'<p class="fine">쿠팡 검색 랭킹 기준(판매량 순위가 아님) · {esc(PHONES.get("fetched_at", "")[:10])} 확인 · '
            '‘온라인 가격비교’ 링크는 쿠팡 파트너스 활동의 일환으로 일정액의 수수료를 제공받을 수 있습니다.</p>')


def phone_rank_box():
    items = PHONES.get("items") or []
    if not items:
        return ""
    rows = "".join(
        f'<a class="pr" href="{esc(p["url"])}" rel="nofollow sponsored noopener" target="_blank">'
        f'<span class="pr-n n{p["rank"]}">{p["rank"]}</span>'
        f'{("<img class=pr-img referrerpolicy=no-referrer src=" + chr(34) + esc(p["image"]) + chr(34) + " alt=>") if p.get("image") else "<span class=pr-img></span>"}'
        f'<span class="pr-m"><b>{esc(p["name"])}</b><span class="pr-p">{p["price"]:,}원{" <i>로켓배송</i>" if p.get("rocket") else ""}</span></span>'
        f'<span class="pr-go">온라인 가격비교 ↗</span></a>' for p in items)
    return ('<section class="card phones"><h2>알뜰폰과 함께 쓰는 자급제폰 TOP 10</h2>'
            f'<p class="muted sm">쿠팡 검색 랭킹 기준 인기 자급제폰입니다(판매량 순위가 아님). {esc(PHONES.get("fetched_at", "")[:16])} 확인 · 가격은 수시로 바뀔 수 있어요.</p>'
            f'<div class="prs">{rows}</div>'
            '<p class="fine">‘온라인 가격비교’ 링크는 쿠팡 파트너스 활동의 일환으로, 이를 통해 구매가 이루어지면 일정액의 수수료를 제공받을 수 있습니다.</p></section>')


def coupang():
    return phone_rank_box() or coupang_generic()




def cards_for(carrier=None, network=None):
    out = []
    for c in CARDS:
        if carrier and c["carrier"] != carrier:
            continue
        if network and c["networks"] and network not in c["networks"]:
            continue
        if network and not carrier and not c["networks"]:
            continue
        out.append(c)
    return out


def card_html(c, price=None, compact=False):
    fee = "<br>".join(esc(x) for x in c["annual_fee"]) if c["annual_fee"] else "원문 확인"
    if c["tiers"]:
        rows = "".join(f'<tr><td>전월 {t["spend_won"] // 10000}만원 이상</td><td><b>최대 {t["discount"]:,}원</b></td></tr>' for t in c["tiers"])
        ben = f'<table class="tiers"><tbody>{rows}</tbody></table>'
    else:
        ben = f'<p class="cb-b">{esc(c["benefit"])}</p>'
    nets = " · ".join(c["networks"]) + "망" if c["networks"] else "적용 망은 원문 확인"
    est = ""
    if price and c["tiers"] and not compact:
        t0 = min(c["tiers"], key=lambda t: t["spend_won"])
        tm = max(c["tiers"], key=lambda t: t["discount"])
        left = price - t0["discount"]
        if left <= 0:
            msg = f'전월 {t0["spend_won"] // 10000}만원 이상 쓰면 이 요금제의 통신요금 대부분을 할인으로 상쇄할 수 있어요.'
        else:
            msg = f'전월 {t0["spend_won"] // 10000}만원 이상 쓰면 이 요금제는 월 <b>{left:,}원</b> 수준까지 내려갈 수 있어요.'
        if len(c["tiers"]) > 1:
            msg += f' (최대 {tm["discount"]:,}원 구간은 전월 {tm["spend_won"] // 10000}만원 이상)'
        est = f'<p class="cb-est">{msg}<span class="fine">연회비와 월 한도·자동이체 등 조건에 따라 실제 혜택은 달라질 수 있어요.</span></p>'
    return (f'<div class="cb"><div class="cb-h"><b>{esc(c["name"])}</b><span class="tag">{esc(c["carrier"])} 제휴</span></div>'
            f'<div class="cb-m"><span>연회비 {fee}</span><span>{esc(nets)}</span>'
            f'{"<span>" + str(c["months"]) + "개월" + "</span>" if c["months"] else ""}</div>{ben}{est}'
            f'<a class="cb-l" href="{esc(c["source_url"])}" rel="nofollow noopener" target="_blank">{esc(c["carrier"])} 안내 원문 ↗</a></div>')


def card_section(cs, title, price=None, compact=False):
    if not cs:
        return ""
    return (f'<section class="card"><h2>{esc(title)}</h2><p class="muted sm">통신요금 자동이체 등 조건을 채우면 받을 수 있는 할인입니다. '
            f'전월 실적·월 한도·적용 요금제는 카드마다 다르니 신청 전 통신사 안내를 꼭 확인하세요.</p>'
            f'<div class="cbs">{"".join(card_html(c, price, compact) for c in cs)}</div></section>')


def stat_boxes(items):
    return '<div class="stats">' + "".join(f'<div><span>{k}</span><b>{v}</b></div>' for k, v in items) + "</div>"


# ---------------------------------------------------------------- 페이지 생성
pages = []


def write(path, content):
    fp = os.path.join(OUT, path.strip("/"), "index.html") if path != "/" else os.path.join(OUT, "index.html")
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, "w", encoding="utf-8").write(content)
    pages.append(path)


def stats_text(plans, label):
    n = len(plans)
    effs = [eff(p) for p in plans if eff(p) is not None]
    cheapest = min(plans, key=lambda p: (eff(p) if eff(p) is not None else 10 ** 9))
    life = sum(1 for p in plans if p["discount_type"] == "lifetime")
    top = ", ".join(f"{c} {k}개" for c, k in Counter(p["carrier"] for p in plans).most_common(3))
    med = int(statistics.median(effs)) if effs else None
    return (f"{label} 조건에 맞는 알뜰폰 요금제는 현재 총 {n}개입니다. 장기 월 요금 기준 가장 저렴한 요금제는 "
            f"{cheapest['carrier']} '{cheapest['name']}'로 월 {won(eff(cheapest))}이고, 중간값은 월 {won(med)}입니다. "
            f"평생 할인 요금제는 {life}개이며, 통신사별로는 {top} 순으로 많습니다.")


def build():
    plans = json.load(open(os.path.join(HERE, "data", "plans.json"), encoding="utf-8"))
    plans = [p for p in plans if p["network"] and p["price_now"] is not None]
    for p in plans:
        p["_cat"] = assign(p)
        p["_cat"]["carrier"] = p["carrier"]
    stamp = max(p["fetched_at"] for p in plans)
    ymd = stamp[:10]
    ym = f"{int(ymd[:4])}년 {int(ymd[5:7])}월"
    pp = os.path.join(HERE, "data", "phones.json")
    PHONES.clear()
    if os.path.exists(pp):
        PHONES.update(json.load(open(pp, encoding="utf-8")))
    cp = os.path.join(HERE, "data", "cards.json")
    CARDS[:] = [c for c in json.load(open(cp, encoding="utf-8"))] if os.path.exists(cp) else []
    n_carrier = len(set(p["carrier"] for p in plans))
    carriers = sorted(set(p["carrier"] for p in plans), key=lambda c: -sum(1 for p in plans if p["carrier"] == c))

    os.makedirs(OUT, exist_ok=True)
    for name in os.listdir(OUT):  # 폴더 자체는 유지(미리보기 서버가 잡고 있을 수 있음)
        fp = os.path.join(OUT, name)
        shutil.rmtree(fp, ignore_errors=True) if os.path.isdir(fp) else os.remove(fp)
    open(os.path.join(OUT, "CNAME"), "w", encoding="utf-8").write(C.DOMAIN.replace("https://", "") + "\n")
    for f in ("style.css", "density.css", "deal.css", "deal.js", "finder.js", "pcar.js"):
        shutil.copy(os.path.join(HERE, "static", f), os.path.join(OUT, f))

    by_axis = {a: defaultdict(list) for a in AXES}
    for p in plans:
        for a in AXES:
            if p["_cat"][a]:
                by_axis[a][p["_cat"][a]].append(p)
    for p in plans:  # '데이터 무제한' 구간은 기본 GB 구간과 별개로, 소진 후 속도제한 무제한 요금제까지 포함
        if is_unl(p) and p["_cat"]["data"] != "unlimited":
            by_axis["data"]["unlimited"].append(p)
    for a in AXES:
        for v in by_axis[a]:
            by_axis[a][v].sort(key=lambda p: (eff(p) if eff(p) is not None else 10 ** 9, p["name"]))

    # --- 요금제 상세
    for p in plans:
        path = plan_url(p)
        c = p["_cat"]
        db = by_axis["data"].get(c["data"], [])
        rank = db.index(p) + 1 if p in db else None
        alts = [q for q in db if q is not p and q["_cat"]["voice"] == c["voice"] and eff(q) is not None
                and eff(p) is not None and eff(q) <= eff(p) and q["carrier"] != p["carrier"]][:5]
        title = f"{p['name']} 요금 · 데이터 · 할인 조건 | {p['carrier']} 알뜰폰"
        desc = (f"{p['carrier']} {p['name']} 요금제: {price_story(p)}. 데이터 {data_label(p)}, 통화 {voice_label(p)}, "
                f"문자 {sms_label(p)}. {ym} 기준 통신사 공식 정보.")
        bc, bld = crumbs([("/", "홈"), (SEC + "/", "알뜰폰 요금제"), (cat_url("carrier", p["carrier"]), p["carrier"]), (None, p["name"])])
        spec = [("통신사", p["carrier"]), ("통신망", p["network"]), ("세대", p["gen"] or "-"),
                ("데이터", data_label(p)), ("통화", voice_label(p)), ("문자", sms_label(p)),
                ("정가", won(p["list_price"]) if p["list_price"] else "통신사 화면 확인")]
        if p["discount_type"] == "period":
            spec.append(("첫 12개월 월평균", won(year_avg(p))))
        grid = "".join(f"<div><span>{k}</span><b>{esc(str(v))}</b></div>" for k, v in spec)
        chips = "".join(f'<a class="chip" href="{cat_url(a, c[a])}">{esc(LABELS[a][c[a]])}</a>'
                        for a in ["network", "gen", "data", "price", "voice", "discount"] if c.get(a))
        if p["discount_type"] == "period" and p["discount_months"] and p["price_after"] is not None:
            flow = (f'<div class="flow"><div><span>처음 {p["discount_months"]}개월</span><b>월 {won(p["price_now"])}</b></div>'
                    f'<i>→</i><div class="after"><span>그 이후</span><b>월 {won(p["price_after"])}</b></div></div>')
        elif p["discount_type"] == "lifetime":
            flow = f'<div class="flow"><div class="after"><span>평생 할인 요금</span><b>월 {won(p["price_now"])}</b></div></div>'
        else:
            flow = f'<div class="flow"><div class="after"><span>월 요금</span><b>{won(p["price_now"])}</b></div></div>'
        rank_txt = (f"<p class='note'>같은 데이터 구간({esc(LABELS['data'][c['data']])}) 요금제 {len(db)}개 중 "
                    f"장기 월 요금 기준 <b>{rank}번째</b>로 저렴합니다.</p>") if rank else ""
        alt_html = ("<section class='card'><h2>비슷한 조건의 더 저렴한 요금제</h2><p class='muted'>같은 데이터 구간·통화 조건에서 "
                    "장기 월 요금이 같거나 낮은 다른 통신사 요금제입니다.</p>" + plan_rows(alts) + "</section>") if alts else ""
        pc = cards_for(carrier=p["carrier"], network=p["network"]) if (eff(p) or 0) >= 8000 else []
        card_html_box = card_section(pc, f"{p['carrier']} 제휴카드로 통신비 더 줄이기", eff(p))
        faq = [
            (f"{p['name']} 요금은 계속 같은가요?",
             {"lifetime": "통신사가 평생(가입 유지 시 계속) 할인으로 안내한 요금제입니다. 단, 조건(사용 실적, 요금제 변경 등)은 통신사 안내를 꼭 확인하세요.",
              "period": f"아니요. {price_story(p)}처럼 할인 기간이 끝나면 요금이 달라집니다.",
              "none": "별도 기간 할인 없이 표시된 요금이 계속 적용되는 정가형 요금제로 안내되어 있습니다."}[p["discount_type"]]),
            ("이 요금은 어디서 확인한 건가요?",
             f"{p['carrier']} 공식 홈페이지의 요금제 안내를 {p['fetched_at']}에 확인한 내용입니다. 원문 링크에서 직접 비교해 보세요."),
            ("가입하면 요금이 바로 적용되나요?",
             "가입 시점·번호이동 여부·제휴 혜택에 따라 실제 청구액은 달라질 수 있어요. 최종 조건은 가입 화면에서 확인하세요."),
        ]
        faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq)
        ld = [bld, {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}]
        body = (head(title, desc, path, ld) + header("phone") + subnav() + '<main class="wrap">' + bc +
                f'<div class="pp"><div class="pp-main"><section class="card hero-card"><div class="hc-top"><span class="tag {p["discount_type"]}">{esc(discount_label(p))}</span>'
                f'<span class="muted">{esc(p["carrier"])} · {esc(p["network"])}{" · " + p["gen"] if p["gen"] else ""}</span></div>'
                f'<h1>{esc(p["name"])}</h1>{flow}<div class="chips">{chips}</div>'
                f'<a class="btn" href="{esc(p["source_url"])}" rel="nofollow noopener" target="_blank">{esc(p["carrier"])} 공식 페이지에서 확인 ↗</a>'
                f'<p class="fine">확인 시각 {esc(p["fetched_at"])} · 가입 전 반드시 통신사 화면에서 최종 요금을 확인하세요.</p></section>'
                f'<section class="card"><h2>요금제 상세</h2><div class="grid">{grid}</div>{rank_txt}</section>'
                f'{card_html_box}{alt_html}<section class="card"><h2>자주 묻는 질문</h2>{faq_html}</section></div>'
                f'<aside class="pp-side"><section class="card side-sum"><h3>이 요금제와 비슷한 조건 보기</h3><div class="chips">{chips}</div>'
                f'<a class="lnk-b" href="{SEC}/">전체 요금제 비교하기 →</a></section>{coupang()}</aside></div></main>' + footer(stamp))
        write(path, body)

    # --- 카테고리 페이지 (단일 + 조합)
    combo_set, combo_defs = set(), []
    for a, b in combinations(AXES, 2):
        cnt = defaultdict(list)
        for p in plans:
            va, vb = p["_cat"][a], p["_cat"][b]
            if va and vb:
                cnt[(va, vb)].append(p)
        for (va, vb), sel in cnt.items():
            if len(sel) < C.MIN_COMBO or len(sel) == len(by_axis[a][va]) or len(sel) == len(by_axis[b][vb]):
                continue  # 얇거나 부모와 동일 집합이면 생성 안 함
            u = combo_url(a, va, b, vb)
            combo_set.add(u)
            combo_defs.append((a, va, b, vb, sel, u))

    def cat_page(path, label, sel, parents, crumb_items, active_axis):
        sel = sorted(sel, key=lambda p: (eff(p) if eff(p) is not None else 10 ** 9, p["name"]))
        n = len(sel)
        effs = [eff(p) for p in sel if eff(p) is not None]
        title = f"{label} 알뜰폰 요금제 비교 ({n}개) | {C.SITE_NAME}"
        desc = f"{label} 알뜰폰 요금제 {n}개를 장기 월 요금 낮은 순으로 비교. {min(effs):,}원부터. {ym} 기준 통신사 공식 정보."
        bc, bld = crumbs(crumb_items)
        refine = []
        cur_axes = {a for a, _ in parents}
        for a in AXES:
            if a in cur_axes or len(parents) != 1:
                continue
            cnt = Counter(p["_cat"][a] for p in sel if p["_cat"][a])
            links = []
            for v, k in cnt.most_common():
                if k < C.MIN_COMBO or k == n:
                    continue
                pa, pv = parents[0]
                f1, f2 = sorted([(pa, pv), (a, v)], key=lambda t: AXES.index(t[0]))
                u = combo_url(f1[0], f1[1], f2[0], f2[1])
                if u in combo_set:
                    links.append(f'<a class="chip" href="{u}">{esc(LABELS[a][v])} <i>{k}</i></a>')
            if links:
                refine.append(f"<div class='rf'><b>{AXIS_TITLE[a]}</b><div class='chips'>{''.join(links)}</div></div>")
        itemlist = {"@context": "https://schema.org", "@type": "ItemList", "numberOfItems": n, "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": C.DOMAIN + plan_url(p), "name": p["name"]} for i, p in enumerate(sel[:20])]}
        life = sum(1 for p in sel if p["discount_type"] == "lifetime")
        cat_cards = ""
        if len(parents) == 1 and parents[0][0] in ("carrier", "network"):
            ax, vv = parents[0]
            cs = cards_for(carrier=vv) if ax == "carrier" else cards_for(network=vv)
            cat_cards = card_section(cs, f"{LABELS[ax][vv]}에서 쓸 수 있는 제휴카드", compact=True)
        body = (head(title, desc, path, [bld, itemlist]) + header("phone") + subnav(active_axis) + '<main class="wrap">' + bc +
                f'<div class="ph-row"><h1 class="ph">{esc(label)} 알뜰폰 요금제</h1>'
                f'<p class="muted">요금제 {n}개 · 최저 장기 월 {won(min(effs))} · 평생 할인 {life}개</p></div>'
                + finder(sel, f"{int(ymd[5:7])}/{int(ymd[8:10])} {stamp[11:]}", carriers)
                + (f'<section class="card"><h2>조건 좁히기</h2>{"".join(refine)}</section>' if refine else "")
                + cat_cards
                + f'<section class="card"><h2>{esc(label)} 요금제 한눈에 보기</h2><p class="prose-p">{esc(stats_text(sel, label))}</p>'
                f'<p class="fine">장기 월 요금은 할인 종료 후(평생 할인이면 지금과 동일) 월 요금이며, 순서의 기준입니다.</p></section>'
                f'{coupang()}</main>' + footer(stamp, True))
        write(path, body)

    for a in AXES:
        for v, sel in by_axis[a].items():
            if len(sel) >= C.MIN_COMBO:
                cat_page(cat_url(a, v), LABELS[a][v], sel, [(a, v)],
                         [("/", "홈"), (SEC + "/", "알뜰폰 요금제"), (f"{SEC}/{a}/" if a in TABS else None, AXIS_TITLE[a] + "별"),
                          (None, LABELS[a][v])], a if a in TABS else None)
    for a, va, b, vb, sel, u in combo_defs:
        cat_page(u, f"{LABELS[a][va]} {LABELS[b][vb]}", sel, [(a, va), (b, vb)],
                 [("/", "홈"), (SEC + "/", "알뜰폰 요금제"), (cat_url(a, va), LABELS[a][va]), (None, LABELS[b][vb])],
                 a if a in TABS else None)

    # --- 축 인덱스 (/phone/carrier/ 등)
    for a in TABS:
        cards = []
        for v, sel in sorted(by_axis[a].items(), key=lambda t: -len(t[1])):
            if len(sel) < C.MIN_COMBO:
                continue
            effs = [eff(p) for p in sel if eff(p) is not None]
            cards.append(f'<a class="idx" href="{cat_url(a, v)}"><b>{esc(LABELS[a][v])}</b>'
                         f'<span class="muted">요금제 {len(sel)}개</span><span class="sm">최저 월 {won(min(effs))}</span></a>')
        bc, bld = crumbs([("/", "홈"), (SEC + "/", "알뜰폰 요금제"), (None, AXIS_TITLE[a] + "별")])
        t = f"{AXIS_TITLE[a]}별 알뜰폰 요금제 | {C.SITE_NAME}"
        write(f"{SEC}/{a}/", head(t, f"{AXIS_DESC[a]}를 한눈에 확인하세요. {ym} 기준 통신사 공식 정보.", f"{SEC}/{a}/", [bld])
              + header("phone") + subnav(a) + '<main class="wrap">' + bc
              + f'<h1 class="ph">{AXIS_TITLE[a]}별 알뜰폰 요금제</h1><p class="muted">{AXIS_DESC[a]}</p><div class="idxs">{"".join(cards)}</div>'
              + coupang() + "</main>" + footer(stamp))

    # --- 알뜰폰 섹션 홈
    life_top = sorted([p for p in plans if p["discount_type"] == "lifetime"], key=lambda p: eff(p))[:9]
    quick = []
    for a in ["network", "data", "price", "discount"]:
        chips = "".join(f'<a class="chip" href="{cat_url(a, v)}">{esc(LABELS[a][v])} <i>{len(s)}</i></a>'
                        for v, s in sorted(by_axis[a].items(), key=lambda t: -len(t[1])) if len(s) >= C.MIN_COMBO)
        quick.append(f"<div class='rf'><b>{AXIS_TITLE[a]}</b><div class='chips'>{chips}</div></div>")
    car_cards = "".join(
        f'<a class="idx" href="{cat_url("carrier", c)}"><b>{esc(c)}</b><span class="muted">요금제 {len(s)}개</span>'
        f'<span class="sm">최저 월 {won(min(eff(p) for p in s))}</span></a>' for c, s in sorted(by_axis["carrier"].items(), key=lambda t: -len(t[1])))
    sec_title = f"알뜰폰 요금제 비교 — 통신사·데이터·요금대별 {len(plans)}개 | {C.SITE_NAME}"
    sec_desc = (f"알뜰폰 {n_carrier}개 통신사의 요금제 {len(plans)}개를 통신망·데이터량·요금대·할인 유형별로 비교하세요. "
                f"{ym} 기준 통신사 공식 정보.")
    bc, bld = crumbs([("/", "홈"), (None, "알뜰폰 요금제")])
    all_sorted = sorted(plans, key=lambda p: (eff(p) if eff(p) is not None else 10 ** 9, p["name"]))
    write(SEC + "/", head(sec_title, sec_desc, SEC + "/", [bld]) + header("phone") + subnav("home") + '<main class="wrap">' + bc +
          f'<div class="ph-row"><h1 class="ph">알뜰폰 요금제 비교</h1>'
          f'<p class="muted">{n_carrier}개 통신사 · 요금제 {len(plans)}개 · 통신사 공식 정보 기준</p></div>'
          + finder(all_sorted, f"{int(ymd[5:7])}/{int(ymd[8:10])} {stamp[11:]}", carriers)
          + f'<section class="card"><h2>조건으로 바로가기</h2>{"".join(quick)}</section>'
          f'<section><h2 class="sh">통신사별로 보기</h2><div class="idxs">{car_cards}</div></section>{coupang()}</main>' + footer(stamp, True))

    # --- 포털 홈 (정보 밀도 높은 구성)
    n_life = sum(1 for p in plans if p["discount_type"] == "lifetime")
    min_eff = min(eff(p) for p in plans if eff(p) is not None)
    stats = [("등록 요금제", f"{len(plans)}개"), ("알뜰폰 통신사", f"{n_carrier}곳"), ("평생 할인", f"{n_life}개"), ("최저 월 요금", won(min_eff))]
    svc_cards = []
    for sv in SERVICES:
        if sv["live"]:
            svc_cards.append(f'<a class="svc c" href="{sv["url"]}"><span class="svc-ic">{sv["icon"]}</span><span class="svc-b"><b>{esc(sv["title"])}</b>'
                             f'<span class="muted">{esc(sv["desc"])}</span></span><span class="svc-go">→</span></a>')
        else:
            svc_cards.append(f'<div class="svc c off"><span class="svc-ic">{sv["icon"]}</span><span class="svc-b"><b>{esc(sv["title"])}</b>'
                             f'<span class="muted">{esc(sv["desc"])}</span></span><span class="soon">준비 중</span></div>')
    hq = []
    for ax in ["network", "data", "price", "voice", "discount"]:
        ch = "".join(f'<a class="chip" href="{cat_url(ax, v)}">{esc(LABELS[ax][v])} <i>{len(ss)}</i></a>'
                     for v, ss in sorted(by_axis[ax].items(), key=lambda t: -len(t[1])) if len(ss) >= C.MIN_COMBO)
        hq.append(f"<div class='rf'><b>{AXIS_TITLE[ax]}</b><div class='chips'>{ch}</div></div>")
    car_list = "".join(
        f'<a class="cl" href="{cat_url("carrier", c)}"><b>{esc(c)}</b><span>{len(ss)}개</span><span class="sm">최저 {won(min(eff(p) for p in ss))}</span></a>'
        for c, ss in sorted(by_axis["carrier"].items(), key=lambda t: -len(t[1])))
    hld = {"@context": "https://schema.org", "@type": "WebSite", "name": C.SITE_NAME, "url": C.DOMAIN}
    home_title = f"{C.SITE_NAME} — {C.TAGLINE} | 생활비 절약 정보 모음"
    home_desc = "통신비·공과금·교통비·생활물가까지, 생활비를 줄여주는 정보를 한곳에 모았습니다. 지금은 알뜰폰 요금제 비교를 제공합니다."
    write("/", head(home_title, home_desc, "/", [hld]) + header() + '<main class="wrap home">'
          f'<section class="hero mini"><div class="hm-l"><span class="eyebrow">{C.TAGLINE}</span><h1>생활비, 우아하게 줄여요</h1>'
          f'<p>통신비부터 하나씩. 광고에 흔들리지 않는 비교 정보로 매달 나가는 돈을 줄이세요.</p>'
          f'<a class="btn sm" href="{SEC}/">알뜰폰 요금제 비교하기</a></div>'
          f'<div class="hm-r">{"".join(f"<div><span>{k}</span><b>{v}</b></div>" for k, v in stats)}</div></section>'
          f'<section><h2 class="sh">절약 서비스</h2><div class="svcs c">{"".join(svc_cards)}</div></section>'
          f'<div class="cols"><section class="col-l"><h2 class="sh">평생 할인 최저가 TOP 8</h2><div class="hl">{plan_rows(life_top[:8])}</div>'
          f'<p class="more"><a href="{SEC}/discount/lifetime/">평생 할인 요금제 {n_life}개 전체 보기 →</a></p></section>'
          f'<section class="col-r"><h2 class="sh">조건으로 찾기</h2><div class="card tight">{"".join(hq)}</div>'
          f'{phone_carousel()}<h2 class="sh">통신사별 요금제</h2><div class="card tight cls">{car_list}</div></section></div>'
          f'<section class="trust c"><div><b>공식 정보만</b><p>통신사 공식 홈페이지 정보만 수집하고 원문 링크·확인 시각을 표시해요.</p></div>'
          f'<div><b>순서는 요금 기준</b><p>광고·제휴와 무관하게 장기 월 요금 낮은 순으로 정렬해요.</p></div>'
          f'<div><b>하루 여러 번 갱신</b><p>자동으로 다시 확인해 바뀐 요금을 빠르게 반영해요.</p></div></section></main>' + footer(stamp).replace("</body>", '<script src="/pcar.js"></script></body>'))

    # --- 소개 / 개인정보
    about = ('<main class="wrap narrow"><h1 class="ph">서비스 소개 · 수집 정책</h1><section class="card prose">'
             f"<p>{C.SITE_NAME}은 {C.TAGLINE}는 목표로 생활비를 줄여주는 정보를 모으는 사이트입니다. 현재는 알뜰폰 요금제를 "
             "통신사·통신망·데이터량·요금대·할인 유형별로 비교할 수 있게 정리하고 있으며, 앞으로 다른 절약 주제를 차례로 추가할 예정입니다. "
             "특정 통신사의 대리점이나 중개 서비스가 아니며, 가입은 각 통신사 공식 화면에서 이루어집니다.</p>"
             "<h2>데이터 수집 방식</h2><ul><li>각 알뜰폰 통신사의 공식 홈페이지에 공개된 요금제 정보만 수집합니다.</li>"
             "<li>robots.txt를 준수하고, 로그인이 필요한 화면이나 개인정보는 수집하지 않습니다.</li>"
             "<li>다른 비교 사이트의 값을 가져오지 않으며, 항목마다 원문 링크와 확인 시각을 함께 표시합니다.</li>"
             "<li>하루 여러 번 자동으로 다시 확인하고, 가격이 비정상적으로 바뀐 항목은 검증 전까지 게시를 보류합니다.</li></ul>"
             "<h2>요금 표기 기준</h2><ul><li><b>지금 월 요금</b>: 지금 가입했을 때 처음 내는 월 요금</li>"
             "<li><b>장기 월 요금</b>: 기간 할인이 끝난 뒤(평생 할인이면 지금과 동일)의 월 요금. 순위와 정렬의 기본 기준입니다.</li>"
             "<li><b>평생 할인</b>은 통신사가 그렇게 안내한 요금제만 표시하며, 사용 실적 등 유지 조건은 통신사 안내를 확인해야 합니다.</li></ul>"
             "<h2>광고·제휴 안내</h2><p>일부 페이지 하단의 자급제폰 목록은 쿠팡 파트너스 활동의 일환으로 제공되며, 이에 따른 일정액의 수수료를 제공받습니다. "
             "요금제 순서는 광고·제휴와 무관하게 요금 기준으로 정렬됩니다.</p>"
             + (f"<h2>정정 요청</h2><p>표시된 내용이 통신사 화면과 다르면 {esc(C.CONTACT_EMAIL)}로 알려주세요.</p>" if C.CONTACT_EMAIL else "")
             + "</section></main>")
    write("/about/", head(f"서비스 소개 · 수집 정책 | {C.SITE_NAME}", "우아패밀리의 데이터 수집 방식과 요금 표기 기준 안내", "/about/")
          + header() + about + footer(stamp))
    priv = ('<main class="wrap narrow"><h1 class="ph">개인정보처리방침</h1><section class="card prose">'
            "<p>우아패밀리는 회원가입·로그인 기능이 없으며 이름, 연락처 등 개인정보를 직접 수집하지 않습니다.</p>"
            "<h2>자동 수집 정보</h2><p>서비스 개선을 위해 Google Analytics가 쿠키·접속 로그(방문 페이지, 기기·브라우저 정보 등 비식별 정보)를 수집할 수 있습니다. "
            "브라우저 설정에서 쿠키를 거부할 수 있습니다.</p>"
            "<h2>제3자 광고·제휴</h2><p>쿠팡 파트너스 배너 등 외부 서비스가 자체 쿠키를 사용할 수 있으며, 해당 서비스의 개인정보 처리 정책이 적용됩니다.</p><p>이 사이트는 Google 애드센스 등 제3자 광고 서비스를 이용할 수 있습니다. Google을 포함한 제3자 광고 사업자는 쿠키를 사용하여 이용자가 이 사이트나 다른 사이트를 방문한 기록을 바탕으로 광고를 게재할 수 있습니다. 이용자는 <a href=\"https://adssettings.google.com\" rel=\"noopener\" target=\"_blank\">Google 광고 설정</a>에서 맞춤 광고를 해제할 수 있습니다.</p>"
            "</section></main>")
    write("/privacy/", head(f"개인정보처리방침 | {C.SITE_NAME}", "우아패밀리 개인정보처리방침", "/privacy/") + header() + priv + footer(stamp))

    # --- 편의점·마트 행사 섹션
    import build_deal
    build_deal.build_deals({"esc": esc, "C": C, "write": write, "head": head, "header": header, "footer": footer,
                            "crumbs": crumbs, "coupang": coupang_generic, "HERE": HERE, "OUT": OUT, "stamp": stamp, "ymd": ymd})

    # --- sitemap / robots / 404
    urls = "".join(f"<url><loc>{C.DOMAIN}{u}</loc><lastmod>{ymd}</lastmod></url>" for u in pages)
    open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    if C.ADSENSE_CLIENT:  # 애드센스 ads.txt (표준 형식)
        pub = C.ADSENSE_CLIENT.replace("ca-pub-", "pub-")
        open(os.path.join(OUT, "ads.txt"), "w", encoding="utf-8").write(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")
    open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {C.DOMAIN}/sitemap.xml\n")
    open(os.path.join(OUT, "404.html"), "w", encoding="utf-8").write(
        head("페이지를 찾을 수 없어요 | " + C.SITE_NAME, "페이지를 찾을 수 없습니다", "/404.html", noindex=True) + header()
        + '<main class="wrap narrow"><h1 class="ph">페이지를 찾을 수 없어요</h1><p><a href="/">홈으로 가기</a></p></main>' + footer(stamp))
    print(f"요금제 상세 {len(plans)} / 조합 {len(combo_defs)} / 총 {len(pages)} 페이지")


if __name__ == "__main__":
    build()
