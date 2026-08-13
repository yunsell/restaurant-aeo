"""주간 리포트 — 직전 측정 대비 변동을 강조.

실행: `uv run python -m src.report.weekly_report`
출력: reports/weekly_{restaurant}_{date}.md (+ 추이 차트)
"""
from __future__ import annotations

import argparse
import sys

from src.config import REPORTS_DIR, load_restaurants
from src.report.aggregate import (
    Summary,
    list_measure_dates,
    load_measure,
    load_search,
    search_rank_table,
    summarize,
)
from src.report.charts import trend_chart


def _delta(new: int, old: int) -> str:
    diff = new - old
    if diff > 0:
        return f"▲{diff}"
    if diff < 0:
        return f"▼{abs(diff)}"
    return "―"


def _channel_delta_table(cur: Summary, prev: Summary) -> str:
    lines = ["| 채널 | 이번 주 | 지난 주 | 변동 |", "|---|---|---|---|"]
    for ch in sorted(set(cur.by_channel) | set(prev.by_channel)):
        c = cur.by_channel.get(ch, {}).get("mentioned", 0)
        p = prev.by_channel.get(ch, {}).get("mentioned", 0)
        lines.append(f"| {ch} | {c} | {p} | {_delta(c, p)} |")
    return "\n".join(lines)


def _search_delta_table(cur: dict[str, int | None], prev: dict[str, int | None]) -> str:
    if not cur and not prev:
        return "_검색 스냅샷 없음_"
    lines = ["| 쿼리 | 이번 주 순위 | 지난 주 순위 | 변동 |", "|---|---|---|---|"]
    for qid in sorted(set(cur) | set(prev)):
        c, p = cur.get(qid), prev.get(qid)
        if c is not None and p is not None:
            arrow = _delta(p, c)  # 순위는 낮을수록 좋음 → 부호 반전
        elif c is not None and p is None:
            arrow = "NEW"
        elif c is None and p is not None:
            arrow = "OUT"
        else:
            arrow = "―"
        lines.append(f"| {qid} | {c or '-'} | {p or '-'} | {arrow} |")
    return "\n".join(lines)


def build_report(restaurant_id: str, cur_date: str, prev_date: str) -> str:
    cur = summarize(load_measure(restaurant_id, cur_date))
    prev = summarize(load_measure(restaurant_id, prev_date))
    cur_ranks = search_rank_table(load_search(restaurant_id, cur_date))
    prev_ranks = search_rank_table(load_search(restaurant_id, prev_date))

    new_domains = sorted(set(cur.top_domains) - set(prev.top_domains))
    lost_domains = sorted(set(prev.top_domains) - set(cur.top_domains))
    new_queries = sorted(cur.mentioned_query_ids - prev.mentioned_query_ids)
    lost_queries = sorted(prev.mentioned_query_ids - cur.mentioned_query_ids)

    dates = list_measure_dates(restaurant_id)
    summaries = [summarize(load_measure(restaurant_id, d)) for d in dates]
    chart_name = f"trend_{restaurant_id}_{cur_date}.png"
    trend_chart(summaries, REPORTS_DIR / "charts" / chart_name)

    first_mention_block = (
        "\n".join(f"- 🎉 **{q}** — 이번 주 처음 언급됨" for q in new_queries)
        if new_queries
        else "_새로 언급된 프롬프트 없음_"
    )

    return f"""# 주간 리포트 ({cur_date}, 비교 기준: {prev_date})

## 요약
- 총 언급: **{cur.mentioned}회** (지난 주 {prev.mentioned}회, {_delta(cur.mentioned, prev.mentioned)})
- 언급률: {cur.mention_rate * 100:.1f}% (지난 주 {prev.mention_rate * 100:.1f}%)
- 언급된 프롬프트 수: {len(cur.mentioned_query_ids)} (지난 주 {len(prev.mentioned_query_ids)})

![trend](charts/{chart_name})

## 처음 언급된 프롬프트
{first_mention_block}
{"" if not lost_queries else chr(10) + "언급이 사라진 프롬프트: " + ", ".join(lost_queries)}

## 채널별 언급 변동
{_channel_delta_table(cur, prev)}

## 검색 순위 변동 (자기 매장 도메인)
{_search_delta_table(cur_ranks, prev_ranks)}

## 인용 소스 변화
- 새로 등장한 도메인: {", ".join(new_domains) if new_domains else "없음"}
- 사라진 도메인: {", ".join(lost_domains) if lost_domains else "없음"}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="주간 리포트 생성")
    parser.add_argument("--date", default=None, help="이번 주 측정 날짜 (기본: 가장 최근)")
    args = parser.parse_args(argv)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for restaurant in load_restaurants():
        dates = list_measure_dates(restaurant.id)
        if len(dates) < 2:
            print(f"[{restaurant.id}] 비교할 이전 측정이 없음 (측정 {len(dates)}회) — "
                  f"baseline_report를 사용하세요", file=sys.stderr)
            continue
        cur_date = args.date or dates[-1]
        prev_date = [d for d in dates if d < cur_date][-1]
        report = build_report(restaurant.id, cur_date, prev_date)
        out = REPORTS_DIR / f"weekly_{restaurant.id}_{cur_date}.md"
        out.write_text(report, encoding="utf-8")
        print(f"[{restaurant.id}] 주간 리포트 → {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
