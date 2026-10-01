"""오늘의 생활 특가 섹션(/today/) 생성. 쿠팡 골드박스 + 카테고리별 베스트(data/today.json). build.py에서 ctx를 받아 호출한다."""
import json
import os

SEC = "/today"
FINE = '<p class="fine">이 페이지는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다. 가격·재고는 수시로 바뀌므로 구매 전 쿠팡에서 다시 확인하세요.</p>'


def card(p, esc, rank=True):
    img = (f'<img class="gd-img" width="96" height="96" loading="lazy" referrerpolicy="no-referrer" src="{esc(p["image"])}" alt="{esc(p["name"])}">'
           if p.get("image") else '<span class="gd-img"></span>')
    badge = f'<span class="gd-rank">{p["rank"]}</span>' if rank and p.get("rank") else ""
    return (f'<a class="gd" href="{esc(p["url"])}" rel="nofollow sponsored noopener" target="_blank">{badge}{img}'
            f'<span class="gd-n">{esc(p["name"])}</span><span class="gd-p">{p["price"]:,}원{" <i>로켓배송</i>" if p.get("rocket") else ""}</span>'
            f'<span class="gd-go">쿠팡 최저가 보기 ↗</span></a>')


def tabs(cats, active, esc):
    t = f'<a href="{SEC}/" class="{"on" if active is None else ""}">오늘의 특가</a>' + "".join(
        f'<a href="{SEC}/{c["slug"]}/" class="{"on" if c["slug"] == active else ""}">{esc(c["name"])}</a>' for c in cats)
    return f'<div class="sub"><div class="wrap sub-in">{t}</div></div>'


def build_today(ctx):
    esc, C, write, head, header, footer, crumbs = (ctx[k] for k in ("esc", "C", "write", "head", "header", "footer", "crumbs"))
    HERE, stamp, ymd = ctx["HERE"], ctx["stamp"], ctx["ymd"]
    gold = ctx["gold"]
    p = os.path.join(HERE, "data", "today.json")
    if not os.path.exists(p):
        return
    data = json.load(open(p, encoding="utf-8"))
    cats, when = data["cats"], data["fetched_at"][:16]
    ym = f"{int(ymd[:4])}년 {int(ymd[5:7])}월"
    gitems = (gold.get("items") or [])[:12]

    # 허브
    bc, bld = crumbs([("/", "홈"), (None, "오늘의 생활 특가")])
    title = f"오늘의 생활 특가 {ym} — 쿠팡 골드박스·카테고리별 인기 상품 | {C.SITE_NAME}"
    desc = f"쿠팡 골드박스 특가와 식품·생활용품·주방용품·가전 등 카테고리별 인기 상품을 하루 두 번 갱신해 모았어요. {ym} 기준 생활 특가."
    body = ""
    if gitems:
        body += (f'<section class="card gold"><h2>오늘의 쿠팡 골드박스 특가</h2><p class="muted sm">쿠팡이 오늘 내놓은 특가 상품 · {esc(gold.get("fetched_at", "")[:16])} 확인</p>'
                 f'<div class="golds">{"".join(card(g, esc, False) for g in gitems)}</div></section>')
    for c in cats:
        body += (f'<section class="card gold"><h2>{esc(c["name"])} 인기 상품</h2><p class="muted sm">쿠팡 {esc(c["name"])} 카테고리 베스트 상위 상품</p>'
                 f'<div class="golds">{"".join(card(x, esc) for x in c["items"][:6])}</div>'
                 f'<p class="more"><a href="{SEC}/{c["slug"]}/">{esc(c["name"])} 인기 상품 10개 전체 보기 →</a></p></section>')
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": "오늘의 생활 특가", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": g["name"]} for i, g in enumerate(gitems)]}
    write(SEC + "/", head(title, desc, SEC + "/", [bld, ld]) + header("today") + tabs(cats, None, esc) + '<main class="wrap">' + bc +
          f'<div class="ph-row"><h1 class="ph">오늘의 생활 특가</h1><p class="muted">쿠팡 골드박스 · 카테고리별 인기 상품 · {esc(when)} 확인</p></div>'
          + body + FINE + '</main>' + footer(stamp))

    # 카테고리
    for c in cats:
        bc, bld = crumbs([("/", "홈"), (SEC + "/", "오늘의 생활 특가"), (None, c["name"])])
        t = f'{c["name"]} 인기 상품 TOP 10 {ym} — 쿠팡 베스트 | {C.SITE_NAME}'
        top = "·".join(x["name"][:14] for x in c["items"][:3])
        d = f'쿠팡 {c["name"]} 카테고리 인기 상품 TOP 10과 가격을 모았어요. 1위 {c["items"][0]["name"][:30]} 등. {ym} 기준, 하루 두 번 갱신.'
        ld = {"@context": "https://schema.org", "@type": "ItemList", "name": f'{c["name"]} 인기 상품', "itemListElement": [
            {"@type": "ListItem", "position": x["rank"], "name": x["name"]} for x in c["items"]]}
        write(f'{SEC}/{c["slug"]}/', head(t, d, f'{SEC}/{c["slug"]}/', [bld, ld]) + header("today") + tabs(cats, c["slug"], esc) + '<main class="wrap">' + bc +
              f'<div class="ph-row"><h1 class="ph">{esc(c["name"])} 인기 상품 TOP 10</h1><p class="muted">쿠팡 카테고리 베스트 기준 · {esc(when)} 확인</p></div>'
              f'<section class="card gold"><div class="golds">{"".join(card(x, esc) for x in c["items"])}</div></section>' + FINE + '</main>' + footer(stamp))
