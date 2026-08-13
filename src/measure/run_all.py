"""측정 엔트리포인트: `uv run python -m src.measure.run_all`

1. config 로드
2. (쿼리 × 채널) LLM 측정 → data/results/measure_{restaurant}_{date}.json
3. 검색 스냅샷 → data/results/search_{restaurant}_{date}.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from src.config import (
    RESULTS_DIR,
    get_mode,
    load_llm_channels,
    load_queries,
    load_restaurants,
)
from src.measure.query_runner import run_measurements
from src.measure.search_snapshot import snapshot_all


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AEO/GEO 측정 실행")
    parser.add_argument("--mode", choices=["mock", "live"], default=None,
                        help="기본값은 AEO_MODE 환경변수 (미설정 시 mock)")
    parser.add_argument("--date", default=None, help="결과 파일 날짜 (YYYY-MM-DD, 기본 오늘)")
    parser.add_argument("--skip-search", action="store_true", help="검색 스냅샷 생략")
    args = parser.parse_args(argv)

    mode = args.mode or get_mode()
    run_date = args.date or date.today().isoformat()

    restaurants = load_restaurants()
    queries = load_queries()
    channels = load_llm_channels()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"mode={mode}  date={run_date}  restaurants={len(restaurants)}  "
          f"queries={len(queries)}  channels={len(channels)}", file=sys.stderr)

    for restaurant in restaurants:
        records = run_measurements(restaurant, queries, channels, mode=mode)
        measure_path = RESULTS_DIR / f"measure_{restaurant.id}_{run_date}.json"
        measure_path.write_text(
            json.dumps(
                {
                    "date": run_date,
                    "mode": mode,
                    "restaurant_id": restaurant.id,
                    "restaurant_name": restaurant.name,
                    "results": [r.to_dict() for r in records],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        mentioned = sum(1 for r in records if r.mentioned)
        print(f"[{restaurant.id}] LLM 측정 {len(records)}건 중 언급 {mentioned}건 → {measure_path}",
              file=sys.stderr)

        if not args.skip_search:
            snapshots = snapshot_all(queries, restaurant, mode)
            search_path = RESULTS_DIR / f"search_{restaurant.id}_{run_date}.json"
            search_path.write_text(
                json.dumps(
                    {
                        "date": run_date,
                        "mode": mode,
                        "restaurant_id": restaurant.id,
                        "snapshots": [s.to_dict() for s in snapshots],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(f"[{restaurant.id}] 검색 스냅샷 {len(snapshots)}건 → {search_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
