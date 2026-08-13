"""(쿼리 × 채널) 조합을 병렬 실행하고 언급 파싱 결과를 모은다."""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from src.config import LLMChannel, Query, Restaurant, get_mode
from src.measure.llm_clients import LLMResponse, get_client
from src.measure.mention_parser import parse_mention
from src.utils.cache import DiskCache

MAX_WORKERS = 6


@dataclass
class MeasureRecord:
    restaurant_id: str
    query_id: str
    channel_id: str
    mentioned: bool
    rank: int | None
    context: str
    sentiment: str
    sources_used: list[str]
    latency_ms: int
    model_version: str
    error: str
    response_text: str

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _ask_cached(channel: LLMChannel, query_text: str, mode: str, cache: DiskCache,
                target_names: list[str]) -> LLMResponse:
    namespace = f"llm::{channel.id}::{mode}"
    cached = cache.get(namespace, query_text)
    if cached is not None:
        return LLMResponse.from_dict(cached)
    client = get_client(channel, mode, target_names=target_names)
    resp = client.ask(query_text)
    if not resp.error:  # 실패 응답은 캐시하지 않는다
        cache.set(namespace, query_text, resp.to_dict())
    return resp


def run_measurements(
    restaurant: Restaurant,
    queries: list[Query],
    channels: list[LLMChannel],
    mode: str | None = None,
    cache: DiskCache | None = None,
    progress: bool = True,
) -> list[MeasureRecord]:
    mode = mode or get_mode()
    cache = cache or DiskCache()
    jobs = [(q, c) for q in queries for c in channels]
    records: list[MeasureRecord] = []

    def _run(q: Query, c: LLMChannel) -> MeasureRecord:
        resp = _ask_cached(c, q.text_ko, mode, cache, restaurant.all_names)
        mention = parse_mention(resp.text, restaurant, resp.sources)
        return MeasureRecord(
            restaurant_id=restaurant.id,
            query_id=q.id,
            channel_id=c.id,
            mentioned=mention.mentioned,
            rank=mention.rank,
            context=mention.context,
            sentiment=mention.sentiment,
            sources_used=mention.sources_used,
            latency_ms=resp.latency_ms,
            model_version=resp.model_version,
            error=resp.error,
            response_text=resp.text,
        )

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_run, q, c): (q, c) for q, c in jobs}
        done = 0
        for fut in as_completed(futures):
            records.append(fut.result())
            done += 1
            if progress:
                q, c = futures[fut]
                print(f"[{done}/{len(jobs)}] {q.id} × {c.id}", file=sys.stderr)

    # 결정적 순서로 정렬 (쿼리 → 채널)
    order_q = {q.id: i for i, q in enumerate(queries)}
    order_c = {c.id: i for i, c in enumerate(channels)}
    records.sort(key=lambda r: (order_q[r.query_id], order_c[r.channel_id]))
    return records
