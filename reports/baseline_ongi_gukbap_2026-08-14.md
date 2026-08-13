# Baseline 리포트 (2026-08-14)

## 측정 대상
- 매장: 온기국밥 홍대점 (한식/돼지국밥)
- 프롬프트: 20개
- 채널: 2개 (LLM × 검색 on/off)
- 모드: live

## 결과 요약
- **총 40 조합 중 매장 언급: 0회 (0.0%)**
- 언급된 프롬프트: 0/20개
- 감성 분포: -
- 오류: 0건

![channel chart](charts/baseline_ongi_gukbap_2026-08-14.png)

## 채널별 상세
| 채널 | 언급 | 측정 | 언급률 | 언급 시 평균 순위 |
|---|---|---|---|---|
| gpt5_search | 0 | 20 | 0.0% | - |
| gpt5_no_search | 0 | 20 | 0.0% | - |

## 검색 순위 (자기 매장 도메인)
| 쿼리 | 매장 도메인 순위 |
|---|---|
| q_hongdae_general | 10위권 밖 |
| q_hongdae_top | 10위권 밖 |
| q_hongdae_korean | 10위권 밖 |
| q_hongdae_gukbap | 10위권 밖 |
| q_hongdae_gukbap_en | 10위권 밖 |
| q_hongdae_date | 10위권 밖 |
| q_hongdae_solo | 10위권 밖 |
| q_hongdae_group | 10위권 밖 |
| q_hongdae_cheap | 10위권 밖 |
| q_hongdae_late | 10위권 밖 |
| q_hongdae_local_pick | 10위권 밖 |
| q_hongdae_lunch | 10위권 밖 |
| q_hongdae_traditional | 10위권 밖 |
| q_hongdae_soup | 10위권 밖 |
| q_hongdae_tourist_en | 10위권 밖 |
| q_hongdae_hangover | 10위권 밖 |
| q_mapo_gukbap | 10위권 밖 |
| q_hongdae_family | 10위권 밖 |
| q_hongdae_rainy | 10위권 밖 |
| q_hongdae_best_overall | 10위권 밖 |

## 인용된 소스 도메인 TOP 10
| 도메인 | 인용 횟수 |
|---|---|
| diningcode.com | 9 |
| guide.michelin.com | 8 |
| siksinhot.com | 7 |
| gajaseoul.com | 5 |
| english.visitseoul.net | 4 |
| tabling.co.kr | 4 |
| english.visitkorea.or.kr | 4 |
| hongdaedak.com | 2 |
| lovejejus.tistory.com | 2 |
| autoreserve.com | 2 |

## 다음 액션
- **P0**: 어느 LLM에서도 언급되지 않음 — Schema.org 랜딩 페이지 배포 + 검색엔진(Google Search Console, Bing Webmaster) 제출부터 시작
- **P0**: 검색 상위 10위 안에 매장 도메인이 전혀 없음 — 랜딩 페이지 SEO (title/H1에 '지역+카테고리 맛집' 키워드) 보강 필요
- **P1**: LLM들이 인용하는 상위 소스(diningcode.com, guide.michelin.com, siksinhot.com)에 매장 콘텐츠 확보
