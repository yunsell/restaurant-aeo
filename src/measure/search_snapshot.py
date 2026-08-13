"""검색엔진 결과 스냅샷.

각 쿼리에 대해 상위 10개 검색 결과의 {title, url, snippet}을 저장하고,
매장 도메인이 몇 위에 나오는지 계산한다.

live 모드는 SerpAPI를 사용한다 (Bing Web Search v7는 2025-08 리타이어됨).
"""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import asdict, dataclass, field

import httpx

from src.config import Query, Restaurant


@dataclass
class SearchSnapshot:
    query_id: str
    query_text: str
    engine: str
    results: list[dict] = field(default_factory=list)  # [{title, url, snippet}]
    own_domain_rank: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _own_domain(restaurant: Restaurant) -> str:
    m = re.match(r"https?://([^/]+)", restaurant.website or "")
    return m.group(1).lower().removeprefix("www.") if m else ""


def _rank_of_domain(results: list[dict], domain: str) -> int | None:
    if not domain:
        return None
    for i, r in enumerate(results, start=1):
        if domain in (r.get("url") or "").lower():
            return i
    return None


def _mock_results(query: Query) -> list[dict]:
    h = int(hashlib.sha256(query.id.encode()).hexdigest(), 16)
    sites = [
        ("네이버 블로그", "https://blog.naver.com/food/22{}"),
        ("망고플레이트", "https://www.mangoplate.com/restaurants/{}"),
        ("식신", "https://www.siksinhot.com/P/{}"),
        ("다이닝코드", "https://www.diningcode.com/profile.php?rid={}"),
        ("트립어드바이저", "https://www.tripadvisor.com/Restaurant-{}"),
        ("인스타그램", "https://www.instagram.com/p/{}"),
        ("유튜브", "https://www.youtube.com/watch?v={}"),
        ("티스토리", "https://food.tistory.com/{}"),
        ("네이버 플레이스", "https://map.naver.com/p/entry/place/{}"),
        ("카카오맵", "https://place.map.kakao.com/{}"),
    ]
    return [
        {
            "title": f"{query.text_ko} — {name} 추천 글 {i + 1}",
            "url": tmpl.format((h + i) % 100000),
            "snippet": f"{query.text_ko}에 대한 {name} 정리 글입니다.",
        }
        for i, (name, tmpl) in enumerate(sites)
    ]


def _serpapi_results(query: Query, engine: str = "google") -> list[dict]:
    api_key = os.environ["SERPAPI_API_KEY"]
    r = httpx.get(
        "https://serpapi.com/search",
        params={"engine": engine, "q": query.text_ko, "num": 10, "api_key": api_key,
                "hl": "ko", "gl": "kr"},
        timeout=60,
    )
    r.raise_for_status()
    organic = r.json().get("organic_results", [])[:10]
    return [
        {"title": o.get("title", ""), "url": o.get("link", ""), "snippet": o.get("snippet", "")}
        for o in organic
    ]


def snapshot_query(query: Query, restaurant: Restaurant, mode: str, engine: str = "google") -> SearchSnapshot:
    if mode == "mock":
        results = _mock_results(query)
        engine = "mock"
    else:
        results = _serpapi_results(query, engine)
    return SearchSnapshot(
        query_id=query.id,
        query_text=query.text_ko,
        engine=engine,
        results=results,
        own_domain_rank=_rank_of_domain(results, _own_domain(restaurant)),
    )


def snapshot_all(queries: list[Query], restaurant: Restaurant, mode: str) -> list[SearchSnapshot]:
    return [snapshot_query(q, restaurant, mode) for q in queries]
