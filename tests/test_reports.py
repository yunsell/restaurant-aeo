"""리포트 집계/생성 테스트 (fixture JSON 기반)."""
import json

import pytest

from src.report.aggregate import (
    list_measure_dates,
    load_measure,
    next_actions,
    search_rank_table,
    summarize,
)


def _record(query_id, channel_id, mentioned=False, rank=None, sources=None, sentiment="neutral", error=""):
    return {
        "restaurant_id": "hongdae_a",
        "query_id": query_id,
        "channel_id": channel_id,
        "mentioned": mentioned,
        "rank": rank,
        "context": "ctx" if mentioned else "",
        "sentiment": sentiment,
        "sources_used": sources or [],
        "latency_ms": 100,
        "model_version": "mock",
        "error": error,
        "response_text": "...",
    }


@pytest.fixture
def measure_doc():
    return {
        "date": "2026-08-14",
        "mode": "mock",
        "restaurant_id": "hongdae_a",
        "restaurant_name": "홍대 A식당",
        "results": [
            _record("q1", "ch_a", mentioned=True, rank=2, sources=["mangoplate.com"], sentiment="positive"),
            _record("q1", "ch_b"),
            _record("q2", "ch_a", mentioned=True, rank=1, sources=["mangoplate.com", "blog.naver.com"]),
            _record("q2", "ch_b", error="timeout"),
        ],
    }


def test_summarize(measure_doc):
    s = summarize(measure_doc)
    assert s.total == 4
    assert s.mentioned == 2
    assert s.mention_rate == 0.5
    assert s.by_channel["ch_a"]["mentioned"] == 2
    assert s.by_channel["ch_a"]["ranks"] == [2, 1]
    assert s.by_channel["ch_b"]["mentioned"] == 0
    assert s.mentioned_query_ids == {"q1", "q2"}
    assert s.top_domains["mangoplate.com"] == 2
    assert s.errors == 1
    assert s.sentiments["positive"] == 1


def test_search_rank_table():
    search = {"snapshots": [{"query_id": "q1", "own_domain_rank": 3}, {"query_id": "q2", "own_domain_rank": None}]}
    assert search_rank_table(search) == {"q1": 3, "q2": None}
    assert search_rank_table(None) == {}


def test_next_actions_zero_mentions(measure_doc):
    for r in measure_doc["results"]:
        r["mentioned"] = False
        r["sources_used"] = []
    s = summarize(measure_doc)
    actions = next_actions(s, {"q1": None})
    assert any("P0" in a for a in actions)


def test_next_actions_zero_channel(measure_doc):
    s = summarize(measure_doc)
    actions = next_actions(s, {"q1": 3})
    assert any("ch_b" in a for a in actions)


def test_list_and_load_measure(tmp_path, measure_doc):
    p = tmp_path / "measure_hongdae_a_2026-08-14.json"
    p.write_text(json.dumps(measure_doc, ensure_ascii=False), encoding="utf-8")
    assert list_measure_dates("hongdae_a", tmp_path) == ["2026-08-14"]
    assert load_measure("hongdae_a", "2026-08-14", tmp_path)["date"] == "2026-08-14"


def test_weekly_delta_formatting():
    from src.report.weekly_report import _delta

    assert _delta(5, 3) == "▲2"
    assert _delta(3, 5) == "▼2"
    assert _delta(3, 3) == "―"


def test_charts(tmp_path, measure_doc):
    from src.report.charts import channel_mention_chart, trend_chart

    s = summarize(measure_doc)
    out1 = channel_mention_chart(s, tmp_path / "c.png")
    out2 = trend_chart([s, s], tmp_path / "t.png")
    assert out1.exists() and out1.stat().st_size > 0
    assert out2.exists() and out2.stat().st_size > 0
