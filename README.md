# restaurant-aeo

**AEO/GEO 측정 툴킷** — 특정 음식점이 ChatGPT · Claude · Gemini · Perplexity 답변에 얼마나 노출되는지 **측정 → 최적화 → 재측정** 사이클을 자동화합니다.

- 표준 프롬프트 세트를 여러 LLM에 던지고 **매장 언급 여부 · 순위 · 인용 소스**를 추출
- Schema.org `Restaurant` JSON-LD가 포함된 **정적 랜딩 페이지** 생성 (GitHub Pages 배포 가능)
- **주 1회 자동 측정** + 전주 대비 변동 markdown 리포트 (GitHub Actions)

매장 정보는 전부 `config/`의 YAML로 파라미터화되어 있어 어떤 매장으로든 재사용할 수 있습니다.

## 5분 셋업

```bash
git clone <this-repo> && cd restaurant-aeo

# 1. 의존성 설치 (uv)
uv sync --all-extras

# 2. 환경변수
cp .env.example .env      # 키 입력. AEO_MODE=mock 이면 키 없이도 전체 파이프라인 실행 가능

# 3. 측정 대상 설정
#    config/restaurants.yaml  ← 매장 이름/주소/별칭
#    config/queries.yaml      ← 측정 프롬프트 목록
#    config/llms.yaml         ← 사용할 모델/채널

# 4. 측정 실행 (mock 모드는 API 비용 0원)
uv run python -m src.measure.run_all

# 5. 리포트 생성
uv run python -m src.report.baseline_report   # 첫 측정 후 1회
uv run python -m src.report.weekly_report     # 이후 매주

# 6. 랜딩 페이지 생성 → site/
uv run python -m src.landing.build_site
```

## 폴더 구조

```
config/          측정 대상 매장·프롬프트·모델 설정 (YAML)
src/measure/     LLM 클라이언트, 쿼리 실행, 언급 파서, 검색 스냅샷
src/report/      baseline / 주간 markdown 리포트 + 차트
src/landing/     Schema.org JSON-LD + Jinja2 랜딩 페이지 빌더
data/results/    측정 원본 JSON (커밋 대상)
reports/         생성된 markdown 리포트
site/            생성된 랜딩 페이지 (GitHub Pages 소스)
tests/           pytest
```

## 모드

| 모드 | 설명 |
|---|---|
| `AEO_MODE=mock` | 모든 LLM/검색 호출을 canned 응답으로 대체. 파이프라인 개발·테스트용, 비용 0 |
| `AEO_MODE=live` | 실제 API 호출. `.env`에 키 필요. 응답은 24h 디스크 캐시 |

## 테스트

```bash
uv run pytest --cov=src
```

## GitHub Actions

- `weekly-measure.yml` — 매주 월요일 03:00 UTC에 측정 + 주간 리포트 커밋. 저장소 Secrets에 API 키 등록 필요
- `deploy-site.yml` — `site/` 변경 시 GitHub Pages 배포

## 라이선스

MIT
