"""편의점·마트 행사 섹션(/deal/) 생성. build.py에서 ctx(공통 헬퍼)를 받아 호출한다.
표시 원칙: 정가를 먼저, 그다음 실질 개당 가격. 전체 상품은 /deal/data.json 으로 내려 JS가 검색·필터, 페이지에는 상위 목록만 HTML로 넣는다."""
import json
import os
import re
from collections import Counter, defaultdict

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "collect", "deal"))
from classify import ORDER as CAT_ORDER, SLUG_NAME as CAT_NAME, classify  # noqa: E402

SEC = "/deal"
STORE_SLUG = {"CU": "cu", "세븐일레븐": "seven", "이마트24": "emart24", "홈플러스": "homeplus", "이마트에브리데이": "everyday"}
STORE_KIND = {"CU": "편의점", "세븐일레븐": "편의점", "이마트24": "편의점", "홈플러스": "마트", "이마트에브리데이": "마트"}
GROUP = {"1+1": "1+1", "2+1": "2+1", "3+1": "3+1", "세일": "세일·할인", "할인": "세일·할인", "상품할인": "세일·할인",
         "카드할인": "카드할인", "전단가": "전단 특가", "골라담기": "골라담기"}
GROUP_SLUG = {"1+1": "1plus1", "2+1": "2plus1", "3+1": "3plus1", "세일·할인": "sale", "카드할인": "card", "전단 특가": "flyer", "골라담기": "pick"}
SHOW_IMAGES = True   # 타사 CDN 이미지를 그대로 불러온다. 이용 약관이 걱정되면 False
STATIC_N = 40        # 페이지당 HTML로 넣는 상위 행 수


def won(v):
    return "-" if v is None else f"{v:,}원"


def short(d, link=None):
    """JSON용 압축 레코드"""
    g = GROUP.get(d["promo"], d["promo"])
    return {"s": STORE_SLUG[d["store"]], "g": GROUP_SLUG.get(g, "etc"), "p": d["promo"], "n": d["name"], "l": d["list_price"],
            "u": d["unit_price"], "r": d["discount_rate"] or 0, "i": d["image"] if (SHOW_IMAGES and d["store"] != "세븐일레븐") else None, "x": d["source_url"],
            "z": d.get("size_unit"), "e": d.get("period"), "k": d["key"], "c": d["cat"], "b": link}


def row_html(d, links, esc):
    st, g = STORE_SLUG[d["store"]], GROUP.get(d["promo"], d["promo"])
    img = (f'<img class="d-img" loading="lazy" referrerpolicy="no-referrer" src="{esc(d["image"])}" alt="{esc(d["name"])}">' if d.get("image") and SHOW_IMAGES and d["store"] != "세븐일레븐" else '<span class="d-img ph"></span>')
    lp, up = d["list_price"], d["unit_price"]
    if d["promo"] in ("1+1", "2+1", "3+1"):
        price = (f'<span class="d-list">정가 {won(lp)}</span><b class="d-unit">개당 {won(up)}</b>'
                 f'<span class="d-rate">{d["discount_rate"]}%↓</span>')
    elif d["promo"] in ("세일", "할인", "상품할인", "카드할인") and up is not None and lp and up < lp:
        price = (f'<span class="d-list">정가 {won(lp)}</span><b class="d-unit">{won(up)}</b>'
                 f'<span class="d-rate">{d["discount_rate"]}%↓</span>')
    elif d["promo"] == "골라담기":
        price = f'<b class="d-unit">{won(lp)}</b><span class="d-note">골라담기 가격·조건은 매장 확인</span>'
    else:
        price = f'<b class="d-unit">{won(up if up is not None else lp)}</b>'
    extra = f'<span class="d-note">{esc(d["size_unit"])}</span>' if d.get("size_unit") else ""
    link = links.get(d["key"])
    btn = (f'<a class="d-buy" href="{esc(link)}" rel="nofollow sponsored noopener" target="_blank">온라인 가격비교 ↗</a>' if link else "")
    return (f'<div class="drow">{img}<div class="d-main"><div class="d-top"><span class="stb {st}">{esc(d["store"])}</span>'
            f'<span class="tag">{esc(g)}</span></div><b class="d-name">{esc(d["name"])}</b></div>'
            f'<div class="d-price">{price}{extra}{btn}</div></div>')


def build_deals(ctx):
    esc, C, write = ctx["esc"], ctx["C"], ctx["write"]
    head, header, footer, crumbs, coupang = ctx["head"], ctx["header"], ctx["footer"], ctx["crumbs"], ctx["coupang"]
    here = ctx["HERE"]
    dp = os.path.join(here, "data", "deals.json")
    if not os.path.exists(dp):
        return
    deals = [d for d in json.load(open(dp, encoding="utf-8")) if d["store"] in STORE_SLUG and d["list_price"] and "(종료)" not in d["name"] and not d["name"].startswith("종료)")]
    lp_path = os.path.join(here, "data", "coupang_links.json")
    links = json.load(open(lp_path, encoding="utf-8")) if os.path.exists(lp_path) else {}
    for d in deals:
        d["cat"] = classify(d["name"], d.get("category"))
    stamp, ymd = ctx["stamp"], ctx["ymd"]
    ym = f"{int(ymd[:4])}년 {int(ymd[5:7])}월"
    os.makedirs(os.path.join(ctx["OUT"], "deal"), exist_ok=True)
    json.dump([short(d, links.get(d["key"])) for d in deals], open(os.path.join(ctx["OUT"], "deal", "data.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))

    PRI = {"1+1": 0, "2+1": 1, "3+1": 2}

    def sort_key(d):
        return (PRI.get(d["promo"], 3), -(d["discount_rate"] or 0), d["unit_price"] if d["unit_price"] is not None else 10 ** 9, d["name"])

    def subnav(active):
        tabs = [(f"{SEC}/", "행사 홈", "home"), (f"{SEC}/store/cu/", "편의점·마트별", "store"), (f"{SEC}/promo/1plus1/", "행사 유형별", "promo"),
                (f"{SEC}/category/drink/", "분류별", "cat"), (f"{SEC}/event/", "이벤트", "event")]
        return '<div class="sub"><div class="wrap sub-in">' + "".join(
            f'<a href="{u}" class="{"on" if k == active else ""}">{n}</a>' for u, n, k in tabs) + "</div></div>"

    def chips(items):
        return "".join(f'<a class="chip{" on" if on else ""}" href="{u}">{esc(t)} <i>{n}</i></a>' for u, t, n, on in items)

    by_store, by_group, by_cat = defaultdict(list), defaultdict(list), defaultdict(list)
    for d in deals:
        by_cat[d["cat"]].append(d)
        by_store[d["store"]].append(d)
        by_group[GROUP.get(d["promo"], d["promo"])].append(d)

    def page(path, title_label, sel, store=None, group=None, crumb_items=None, active="home", intro="", cat=None):
        sel = sorted(sel, key=sort_key)
        n = len(sel)
        rates = [d["discount_rate"] for d in sel if d["discount_rate"]]
        if path == SEC + "/":
            title = f"편의점 1+1·2+1 행사 모음 {ym} — CU·세븐일레븐·이마트24 개당 가격 비교 {n}개 | {C.SITE_NAME}"
        else:
            title = f"{title_label} 행사 상품 {n}개 ({ym}) — 정가·개당 가격 비교 | {C.SITE_NAME}"
        desc = (f"{title_label} 행사상품 {n}개를 정가와 실질 개당 가격으로 비교하세요. "
                f"{ym} 기준 각 매장 공식 정보." + (f" 평균 {round(sum(rates) / len(rates))}% 할인." if rates else ""))
        bc, bld = crumbs(crumb_items or [("/", "홈"), (None, title_label)])
        store_chips = chips([(f"{SEC}/store/{STORE_SLUG[s]}/", s, len(v), s == store) for s, v in
                             sorted(by_store.items(), key=lambda t: -len(t[1]))])
        group_chips = chips([(f"{SEC}/promo/{GROUP_SLUG[g]}/", g, len(v), g == group) for g, v in
                             sorted(by_group.items(), key=lambda t: -len(t[1])) if g in GROUP_SLUG])
        cat_chips = chips([(f"{SEC}/category/{s_}/", CAT_NAME[s_], len(by_cat[s_]), s_ == cat) for s_ in CAT_ORDER if len(by_cat.get(s_, [])) >= 5])
        cnt_store = Counter(d["store"] for d in sel)
        summary = (f"{title_label} 조건의 행사 상품은 현재 {n}개입니다. "
                   + (f"평균 할인율은 {round(sum(rates) / len(rates))}%이고, " if rates else "")
                   + "매장별로는 " + ", ".join(f"{s} {k}개" for s, k in cnt_store.most_common(4)) + " 순으로 많습니다. "
                   "정가와 개당 실질 가격을 함께 표시하며, 행사 기간·재고는 매장마다 다를 수 있습니다.")
        itemlist = {"@context": "https://schema.org", "@type": "ItemList", "numberOfItems": n,
                    "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": d["name"]} for i, d in enumerate(sel[:20])]}
        rows = "".join(row_html(d, links, esc) for d in sel[:STATIC_N])
        ctl = (f'<div class="dctl" id="dctl" data-store="{STORE_SLUG[store] if store else ""}" data-group="{GROUP_SLUG[group] if group else ""}" data-cat="{cat or ""}">'
               '<input id="dq" type="search" placeholder="상품명 검색 (예: 라면, 콜라)" autocomplete="off">'
               '<div class="dcat" data-k="dcat"><button type="button" class="on" data-v="">전체</button>'
               + "".join(f'<button type="button" data-v="{s_}">{CAT_NAME[s_]}</button>' for s_ in CAT_ORDER if len(by_cat.get(s_, [])) >= 5) + '</div>'
               '<div class="seg" data-k="dstore"><button type="button" class="on" data-v="">전체</button>'
               '<button type="button" data-v="cu">CU</button><button type="button" data-v="seven">세븐</button>'
               '<button type="button" data-v="emart24">이마트24</button><button type="button" data-v="homeplus">홈플러스</button><button type="button" data-v="everyday">이마트EV</button></div>'
               '<div class="seg" data-k="dgroup"><button type="button" class="on" data-v="">전체</button>'
               '<button type="button" data-v="1plus1">1+1</button><button type="button" data-v="2plus1">2+1</button>'
               '<button type="button" data-v="sale">세일·할인</button><button type="button" data-v="flyer">전단</button></div>'
               '<div class="dsort"><button type="button" class="sortb on" data-s="rec">추천순</button><button type="button" class="sortb" data-s="rate">할인율순</button>'
               '<button type="button" class="sortb" data-s="unit">개당가 낮은순</button>'
               '<button type="button" class="sortb" data-s="list">정가 낮은순</button>'
               f'<span class="asof"><b id="dcnt">{n}</b>개 · {stamp[:10]} 기준</span></div></div>')
        body = (head(title, desc, path, [bld, itemlist]) + header("deal") + subnav(active) + '<main class="wrap">' + bc +
                f'<div class="ph-row"><h1 class="ph">{esc(title_label)} 행사 상품</h1>'
                f'<p class="muted">{esc(intro) if intro else f"{n}개 · 정가와 개당 가격을 함께 비교"}</p></div>'
                f'<section class="card tight"><div class="rf"><b>매장</b><div class="chips">{store_chips}</div></div>'
                f'<div class="rf"><b>행사</b><div class="chips">{group_chips}</div></div>'
                f'<div class="rf"><b>분류</b><div class="chips">{cat_chips}</div></div></section>'
                f'{ctl}<div class="dlist" id="dlist">{rows}</div>'
                '<p id="dempty" class="empty" hidden>조건에 맞는 상품이 없어요.</p>'
                '<button type="button" id="dmore" class="morebtn" hidden>더 보기</button>'
                f'<section class="card"><h2>{esc(title_label)} 행사 한눈에 보기</h2><p class="prose-p">{esc(summary)}</p>'
                '<p class="fine">1+1은 개당 정가의 1/2, 2+1은 2/3, 3+1은 3/4을 지불하는 것으로 환산한 개당 가격입니다. '
                '점포별로 행사 여부·재고·가격이 다를 수 있어요.</p></section>'
                f'{coupang()}</main>' + footer(stamp).replace("</body>", '<script src="/deal.js"></script></body>'))
        write(path, body)

    # 이벤트 페이지
    evp = os.path.join(here, "data", "events.json")
    events = json.load(open(evp, encoding="utf-8")) if os.path.exists(evp) else []
    if events:
        from datetime import date
        today = ymd
        events = [e for e in events if not e.get("period") or e["period"][-10:] >= today]
        events.sort(key=lambda e: (e["store"], e["period"][-10:]))
        by_ev = defaultdict(list)
        for e in events:
            by_ev[e["store"]].append(e)
        cards = []
        for s_, lst in by_ev.items():
            items = "".join(
                f'<a class="evc" href="{esc(e["url"])}" rel="nofollow noopener" target="_blank">'
                + (f'<img class="evc-img" loading="lazy" referrerpolicy="no-referrer" src="{esc(e["image"])}" alt="{esc(e["title"])}">' if e.get("image") else '<span class="evc-img ph"></span>')
                + f'<span class="evc-m"><b>{esc(e["title"])}</b><span class="muted sm">{esc(e["period"])}</span></span></a>' for e in lst)
            cards.append(f'<section class="card"><h2><span class="stb {STORE_SLUG[s_]}">{esc(s_)}</span> 진행 중 이벤트·기획전 {len(lst)}개</h2><div class="evcs">{items}</div></section>')
        bc, bld = crumbs([("/", "홈"), (SEC + "/", "편의점·마트 행사"), (None, "이벤트")])
        title = f"편의점·마트 이벤트·기획전 모음 — {ym} 진행 중 | {C.SITE_NAME}"
        desc = f"세븐일레븐·이마트24·이마트에브리데이의 {ym} 진행 중 이벤트와 기획전 {len(events)}개를 기간과 함께 모았습니다."
        write(SEC + "/event/", head(title, desc, SEC + "/event/", [bld]) + header("deal") + subnav("event") + '<main class="wrap">' + bc +
              f'<div class="ph-row"><h1 class="ph">편의점·마트 이벤트·기획전</h1><p class="muted">{len(events)}개 · 제목·기간만 모았고 자세한 내용은 각 매장 페이지에서 확인하세요</p></div>'
              + "".join(cards) + coupang() + "</main>" + footer(stamp))

    # 홈
    page(SEC + "/", "편의점·마트", deals, intro=f"{len(deals)}개 · CU·세븐일레븐·이마트24·홈플러스 · 정가와 개당 가격 비교",
         crumb_items=[("/", "홈"), (None, "편의점·마트 행사")])
    for s_ in CAT_ORDER:
        if len(by_cat.get(s_, [])) >= 5:
            page(f"{SEC}/category/{s_}/", CAT_NAME[s_], by_cat[s_], cat=s_, active="cat",
                 crumb_items=[("/", "홈"), (SEC + "/", "편의점·마트 행사"), (None, CAT_NAME[s_])])
    for s, v in by_store.items():
        page(f"{SEC}/store/{STORE_SLUG[s]}/", s, v, store=s, active="store",
             crumb_items=[("/", "홈"), (SEC + "/", "편의점·마트 행사"), (None, s)])
    for g, v in by_group.items():
        if g in GROUP_SLUG and len(v) >= 5:
            page(f"{SEC}/promo/{GROUP_SLUG[g]}/", g, v, group=g, active="promo",
                 crumb_items=[("/", "홈"), (SEC + "/", "편의점·마트 행사"), (None, g)])
    combos = defaultdict(list)
    for d in deals:
        combos[(d["store"], GROUP.get(d["promo"], d["promo"]))].append(d)
    for (s, g), v in combos.items():
        if g in GROUP_SLUG and len(v) >= 10 and len(v) < len(by_store[s]) and len(v) < len(by_group[g]):
            page(f"{SEC}/store/{STORE_SLUG[s]}/{GROUP_SLUG[g]}/", f"{s} {g}", v, store=s, group=g, active="store",
                 crumb_items=[("/", "홈"), (SEC + "/", "편의점·마트 행사"), (f"{SEC}/store/{STORE_SLUG[s]}/", s), (None, g)])
    return len(deals)
