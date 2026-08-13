"""Baseline 리포트 — 실험 시작 시점의 노출 현황 스냅샷.

실행: `uv run python -m src.report.baseline_report [--date YYYY-MM-DD]`
출력: reports/baseline_{restaurant}_{date}.md (+ 차트 PNG)
"""
from __future__ import annotations

import argparse
import sys

from src.config import REPORTS_DIR, load_llm_channels, load_queries, load_restaurants
from src.report.aggregate import (
    Summary,
    list_measure_dates,
    load_measure,
    load_search,
    next_actions,
    search_rank_table,
    summarize,
)
from src.report.charts import channel_mention_chart


def _channel_table(summary: Summary) -> str:
    lines = ["| 채널 | 언급 | 측정 | 언급률 | 언급 시 평균 순위 |", "|---|---|---|---|---|"]
    for ch, v in summary.by_channel.items():
        rate = v["mentioned"] / v["total"] * 100 if v["total"] else 0
        avg_rank = f"{sum(v['ranks']) / len(v['ranks']):.1f}" if v["ranks"] else "-"
        lines.append(f"| {ch} | {v['mentioned']} | {v['total']} | {rate:.1f}% | {avg_rank} |")
    return "\n".join(lines)


def _search_table(search_ranks: dict[str, int | None]) -> str:
    if not search_ranks:
        return "_검색 스냅샷 없음_"
    lines = ["| 쿼리 | 매장 도메인 순위 |", "|---|---|"]
    for qid, rank in search_ranks.items():
        lines.append(f"| {qid} | {rank if rank else '10위권 밖'} |")
    return "\n".join(lines)


def _domains_table(summary: Summary) -> str:
    if not summary.top_domains:
        return "_인용 소스 없음_"
    lines = ["| 도메인 | 인용 횟수 |", "|---|---|"]
    for domain, count in summary.top_domains.most_common(10):
        lines.append(f"| {domain} | {count} |")
    return "\n".join(lines)


def build_report(restaurant_id: str, run_date: str) -> str:
    measure = load_measure(restaurant_id, run_date)
    summary = summarize(measure)
    search_ranks = search_rank_table(load_search(restaurant_id, run_date))

    restaurants = {r.id: r for r in load_restaurants()}
    restaurant = restaurants.get(restaurant_id)
    n_queries = len(load_queries())
    n_channels = len(load_llm_channels())

    chart_path = REPORTS_DIR / "charts" / f"baseline_{restaurant_id}_{run_date}.png"
    channel_mention_chart(summary, chart_path)

    label = f"{restaurant.name} ({restaurant.category}/{restaurant.subcategory})" if restaurant else restaurant_id
    actions = "\n".join(f"- {a}" for a in next_actions(summary, search_ranks))
    sentiment = ", ".join(f"{k} {v}" for k, v in summary.sentiments.items()) or "-"

    return f"""# Baseline 리포트 ({run_date})

## 측정 대상
- 매장: {label}
- 프롬프트: {n_queries}개
- 채널: {n_channels}개 (LLM × 검색 on/off)
- 모드: {measure.get('mode', '?')}

## 결과 요약
- **총 {summary.total} 조합 중 매장 언급: {summary.mentioned}회 ({summary.mention_rate * 100:.1f}%)**
- 언급된 프롬프트: {len(summary.mentioned_query_ids)}/{n_queries}개
- 감성 분포: {sentiment}
- 오류: {summary.errors}건

![channel chart](charts/baseline_{restaurant_id}_{run_date}.png)

## 채널별 상세
{_channel_table(summary)}

## 검색 순위 (자기 매장 도메인)
{_search_table(search_ranks)}

## 인용된 소스 도메인 TOP 10
{_domains_table(summary)}

## 다음 액션
{actions}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Baseline 리포트 생성")
    parser.add_argument("--date", default=None, help="측정 날짜 (기본: 가장 최근 결과)")
    args = parser.parse_args(argv)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for restaurant in load_restaurants():
        dates = list_measure_dates(restaurant.id)
        if not dates:
            print(f"[{restaurant.id}] 측정 결과 없음 — 먼저 run_all을 실행하세요", file=sys.stderr)
            continue
        run_date = args.date or dates[-1]
        report = build_report(restaurant.id, run_date)
        out = REPORTS_DIR / f"baseline_{restaurant.id}_{run_date}.md"
        out.write_text(report, encoding="utf-8")
        print(f"[{restaurant.id}] baseline 리포트 → {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
