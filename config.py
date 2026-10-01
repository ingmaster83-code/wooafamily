"""wooafamily 사이트 설정. wooahouse 공통 지침과 분리된 별도 브랜드."""
SITE_NAME = "우아패밀리"
TAGLINE = "우아하게 절약하자"
DOMAIN = "https://wooafamily.com"
SECTION_NAME = "알뜰폰 요금제 비교"

GA_ID = "G-9ZGENFSXWC"          # 포트폴리오 공통 GA 속성(분리하려면 교체)
CONTACT_EMAIL = ""              # 비어 있으면 연락처 문구를 노출하지 않음 — 정정 신고용 이메일을 넣을 것

# 쿠팡 파트너스: 도메인 단위 등록 필요(wooafamily.com). 자급제폰 키워드형 캐러셀 배너를 새로 만들면 ID를 교체.
COUPANG_ID = 980427
COUPANG_TRACKING = "AF5600192"
COUPANG_ENABLED = True

# 애드센스는 승인 후 활성화
ADSENSE_CLIENT = "ca-pub-6464921081676309"   # 애드센스 퍼블리셔 ID (모든 페이지 head에 스크립트 삽입 + ads.txt 생성)
MIN_COMBO = 3                   # 카테고리 조합 페이지 최소 결과 수(얇은 페이지 방지)

# 네이버 서치어드바이저 사이트 소유 확인 (모든 페이지 head에 메타태그로 삽입)
NAVER_SITE_VERIFICATION = "dc74dcbb4b60d9d60833f375eab9cf3242b187f8"
