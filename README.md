# 우아패밀리 (wooafamily.com)

우아하게 절약하자 — 알뜰폰 요금제, 편의점·마트 행사 비교 사이트.

- `collect/` : 통신사·편의점·마트 공식 페이지 수집기 (`run_all.py`, `deal/run_deals.py`)
- `build.py`, `build_deal.py` : 수집 데이터 -> 정적 사이트(`site/`) 생성
- `data/` : 수집 결과(자동 갱신)
- `.github/workflows/update.yml` : 하루 2회 수집·빌드·배포

API 키는 저장소에 올리지 않는다. 로컬은 `.env.local`, 배포는 GitHub Secrets(`COUPANG_ACCESS_KEY`, `COUPANG_SECRET_KEY`)를 쓴다.
