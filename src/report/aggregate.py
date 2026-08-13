"""data/results/*.json 로드 + 리포트용 집계."""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from src.config import RESULTS_DIR


def _dates_for(prefix: str, restaurant_id: str, results_dir: Path) -> list[str]:
    pattern = re.compile(rf"{prefix}_{re.escape(restaurant_id)}_(\d{{4}}-\d{{2}}-\d{{2}})\.json")
    dates = []
    for p in results_dir.glob(f"{prefix}_{restaurant_id}_*.json"):
        m = pattern.fullmatch(p.name)
        if m:
            dates.append(m.group(1))
    return sorted(dates)


def list_measure_dates(restaurant_id: str, results_dir: Path | None = None) -> list[str]:
    return _dates_for("measure", restaurant_id, results_dir or RESULTS_DIR)


def load_measure(restaurant_id: str, run_date: str, results_dir: Path | None = None) -> dict:
    path = (results_dir or RESULTS_DIR) / f"measure_{restaurant_id}_{run_date}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_search(restaurant_id: str, run_date: str, results_dir: Path | None = None) -> dict | None:
    path = (results_dir or RESULTS_DIR) / f"search_{restaurant_id}_{run_date}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class Summary:
    date: str
    total: int = 0
    mentioned: int = 0
    by_channel: dict[str, dict] = field(default_factory=dict)  # {channel: {total, mentioned, ranks}}
    mentioned_query_ids: set[str] = field(default_factory=set)
    top_domains: Counter = field(default_factory=Counter)
    sentiments: Counter = field(default_factory=Counter)
    errors: int = 0

    @property
    def mention_rate(self) -> float:
        return self.mentioned / self.total if self.total else 0.0


def summarize(measure: dict) -> Summary:
    s = Summary(date=measure["date"])
    for r in measure["results"]:
        s.total += 1
        ch = s.by_channel.setdefault(r["channel_id"], {"total": 0, "mentioned": 0, "ranks": []})
        ch["total"] += 1
        if r.get("error"):
            s.errors += 1
        if r["mentioned"]:
            s.mentioned += 1
            ch["mentioned"] += 1
            if r.get("rank"):
                ch["ranks"].append(r["rank"])
            s.mentioned_query_ids.add(r["query_id"])
            s.sentiments[r.get("sentiment", "neutral")] += 1
        for domain in r.get("sources_used", []):
            s.top_domains[domain] += 1
    return s


def search_rank_table(search: dict | None) -> dict[str, int | None]:
    """{query_id: own_domain_rank}"""
    if not search:
        return {}
    return {snap["query_id"]: snap.get("own_domain_rank") for snap in search["snapshots"]}


def next_actions(summary: Summary, search_ranks: dict[str, int | None]) -> list[str]:
    """측정 결과에서 자동으로 도출하는 P0 개선 액션."""
    actions: list[str] = []
    if summary.mention_rate == 0:
        actions.append("**P0**: 어느 LLM에서도 언급되지 않음 — Schema.org 랜딩 페이지 배포 + "
                       "검색엔진(Google Search Console, Bing Webmaster) 제출부터 시작")
    if search_ranks and all(rank is None for rank in search_ranks.values()):
        actions.append("**P0**: 검색 상위 10위 안에 매장 도메인이 전혀 없음 — 랜딩 페이지 SEO "
                       "(title/H1에 '지역+카테고리 맛집' 키워드) 보강 필요")
    zero_channels = [c for c, v in summary.by_channel.items() if v["mentioned"] == 0]
    if zero_channels and summary.mentioned > 0:
        actions.append(f"**P1**: 언급 0회 채널 공략: {', '.join(zero_channels)} — 해당 모델이 "
                       "인용하는 소스(아래 TOP 도메인)에 매장 정보 등록/리뷰 확보")
    if summary.top_domains:
        top3 = ", ".join(d for d, _ in summary.top_domains.most_common(3))
        actions.append(f"**P1**: LLM들이 인용하는 상위 소스({top3})에 매장 콘텐츠 확보")
    if not actions:
        actions.append("현재 지표 유지 — 주간 측정으로 순위 변동 모니터링")
    return actions[:5]
