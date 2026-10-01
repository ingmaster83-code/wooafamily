"""알뜰폰 통신사 제휴카드 수집: 에이모바일(/card), 아이즈모바일(/payplan/alliance 중 카드 항목).
서비스 종료 카드는 제외하고, 혜택 문구는 원문 그대로 보관한다(계산은 확실한 숫자만)."""
import re
from bs4 import BeautifulSoup
from common import http, now_kst

AM_URL = "https://amobile.co.kr/card"
EY_URL = "https://eyes.co.kr/payplan/alliance"


def kr_won(s):
    """'1만 2천원', '1만7천원', '2만원', '20,000원', '5,000원' -> int"""
    s = s.replace(" ", "").replace(",", "")
    m = re.fullmatch(r"(?:(\d+)만)?(?:(\d+)천)?(\d+)?원?", s)
    if not m or not any(m.groups()):
        return None
    man, cheon, rest = (int(x) if x else 0 for x in m.groups())
    return man * 10000 + cheon * 1000 + rest


AMT = r"(\d+만\s*\d*천?원|\d+천원|\d{1,3}(?:,\d{3})+원|\d+원)"


def parse_tiers(text):
    """'30만원 이상 1만 2천원', '전월 70만원 이상 시 최대 21,000원' -> [{spend_won, discount}]"""
    tiers = []
    for m in re.finditer(r"(?:전월\s*)?(\d+)만원\s*이상(?:\s*시)?\s*(?:최대\s*)?" + AMT, text):
        d = kr_won(m.group(2))
        if d:
            tiers.append({"spend_won": int(m.group(1)) * 10000, "discount": d})
    return tiers


def networks_of(text):
    if re.search(r"SKT망[^.]*미적용", text):
        return ["KT", "LGU+"]
    if re.search(r"KT[·,]\s*(?:LGU\+|LG U\+|U\+)", text):
        return ["KT", "LGU+"]
    if re.search(r"(?:LGU\+|LG U\+|U\+)\s*(?:망|알뜰폰)", text) and "KT" not in text:
        return ["LGU+"]
    if re.search(r"KT\s*(?:망|마이알뜰폰)", text) and not re.search(r"U\+", text):
        return ["KT"]
    return None  # 조건 불명 -> 모든 망에 노출하지 않고 통신사 단위로만 표시


def amobile_cards():
    soup = BeautifulSoup(http(AM_URL), "lxml")
    out = []
    for li in soup.select("li"):
        h3, h6 = li.find("h3"), li.find("h6")
        if not (h3 and h6 and "연회비" in li.get_text()):
            continue
        txt = li.get_text("\n", strip=True)
        if "서비스종료" in txt:
            continue
        a = li.select_one("a.card_cont_btn")
        fee, benefit = [], ""
        for p in li.find_all("p"):
            label = p.find("strong")
            body = re.sub(r"\s*\n\s*", " / ", p.get_text("\n", strip=True))
            if not label:
                continue
            if "연회비" in label.get_text():
                fee.append(re.sub(r"^[^/]*연회비\s*/\s*", "", body).strip(" /"))
            elif "혜택" in label.get_text():
                benefit = re.sub(r"^혜택안내\s*/?\s*", "", body)
        tiers = parse_tiers(benefit)
        out.append({
            "carrier": "에이모바일", "issuer": h6.get_text(strip=True), "name": h3.get_text(strip=True),
            "annual_fee": fee, "benefit": benefit, "tiers": tiers,
            "max_discount": max([t["discount"] for t in tiers], default=None),
            "networks": networks_of(h3.get_text(strip=True) + " " + benefit), "months": (int(m.group(1)) if (m := re.search(r"총\s*(\d+)\s*회", benefit)) else None),
            "source_url": ("https://amobile.co.kr" + a["href"]) if a else AM_URL, "fetched_at": now_kst(),
        })
    return out


def eyes_cards():
    soup = BeautifulSoup(http(EY_URL), "lxml")
    out = []
    for li in soup.select("div.event-list-3 li"):
        title, date = li.select_one("p.title"), li.select_one("p.date")
        a = li.find("a")
        if not (title and date and "카드" in title.get_text()):
            continue
        name, benefit = title.get_text(strip=True), date.get_text(strip=True)
        m = re.search(r"최대\s*" + AMT, benefit)
        mx = kr_won(m.group(1)) if m else None
        mm = re.search(r"(\d+)개월간", benefit)
        out.append({
            "carrier": "아이즈모바일", "issuer": name.split()[0] if name else "", "name": name,
            "annual_fee": [], "benefit": benefit, "tiers": [], "max_discount": mx,
            "networks": networks_of(name + " " + benefit), "months": int(mm.group(1)) if mm else None,
            "source_url": "https://eyes.co.kr/payplan/" + a["href"] if a and a.get("href") else EY_URL, "fetched_at": now_kst(),
        })
    return out


def collect():
    cards = amobile_cards() + eyes_cards()
    for i, c in enumerate(cards, 1):
        c["id"] = f"{'amobile' if c['carrier'] == '에이모바일' else 'eyes'}-{i}"
    return cards


if __name__ == "__main__":
    import json
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    r = collect()
    print(len(r), "cards")
    for c in r:
        print(c["carrier"], "|", c["name"], "|", c["networks"], "| max", c["max_discount"], "|", c["tiers"], "|", c["benefit"][:70])
