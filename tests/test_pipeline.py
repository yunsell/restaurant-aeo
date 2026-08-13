"""mock 모드 파이프라인 통합 테스트 (LLM 클라이언트 / 캐시 / 러너 / 검색 스냅샷)."""
import json

from src.config import LLMChannel
from src.measure.llm_clients import LLMResponse, MockClient, extract_domains, get_client
from src.measure.query_runner import run_measurements
from src.measure.search_snapshot import snapshot_all, snapshot_query
from src.utils.cache import DiskCache


def test_mock_client_deterministic(channels, restaurant):
    c = MockClient(channels[0], target_names=restaurant.all_names)
    r1 = c.ask("홍대 맛집 추천")
    r2 = c.ask("홍대 맛집 추천")
    assert r1.text == r2.text
    assert r1.model_version.startswith("mock-")


def test_mock_client_search_returns_sources(channels, restaurant):
    with_search = MockClient(channels[0], target_names=restaurant.all_names).ask("q")
    without = MockClient(channels[1], target_names=restaurant.all_names).ask("q")
    assert with_search.sources
    assert not without.sources


def test_get_client_mock_mode(channels):
    client = get_client(channels[0], mode="mock")
    assert isinstance(client, MockClient)


def test_extract_domains():
    urls = ["https://www.naver.com/a", "http://blog.naver.com/b", "not-a-url", "https://naver.com/c"]
    assert extract_domains(urls) == ["naver.com", "blog.naver.com"]


def test_disk_cache_roundtrip(tmp_path):
    cache = DiskCache(cache_dir=tmp_path, ttl_hours=1)
    assert cache.get("ns", "key") is None
    cache.set("ns", "key", {"text": "hello"})
    assert cache.get("ns", "key") == {"text": "hello"}


def test_disk_cache_expiry(tmp_path):
    cache = DiskCache(cache_dir=tmp_path, ttl_hours=0)  # 즉시 만료
    cache.set("ns", "key", {"text": "hello"})
    assert cache.get("ns", "key") is None


def test_llm_response_serde():
    r = LLMResponse(text="hi", sources=["https://a.com"], latency_ms=10, model_version="m")
    assert LLMResponse.from_dict(r.to_dict()) == r


def test_run_measurements_mock(restaurant, queries, channels, tmp_path):
    cache = DiskCache(cache_dir=tmp_path, ttl_hours=1)
    records = run_measurements(restaurant, queries, channels, mode="mock", cache=cache, progress=False)
    assert len(records) == len(queries) * len(channels)
    # 결정적 정렬: 쿼리 순 → 채널 순
    assert [r.query_id for r in records] == ["q1", "q1", "q2", "q2"]
    for r in records:
        assert r.error == ""
        assert r.response_text
    # JSON 직렬화 가능해야 한다
    json.dumps([r.to_dict() for r in records], ensure_ascii=False)


def test_run_measurements_uses_cache(restaurant, queries, channels, tmp_path):
    cache = DiskCache(cache_dir=tmp_path, ttl_hours=1)
    first = run_measurements(restaurant, queries, channels, mode="mock", cache=cache, progress=False)
    second = run_measurements(restaurant, queries, channels, mode="mock", cache=cache, progress=False)
    assert [r.response_text for r in first] == [r.response_text for r in second]
    # 캐시 파일이 생성되어 있어야 한다
    assert list(tmp_path.glob("*.json"))


def test_search_snapshot_mock(queries, restaurant):
    snap = snapshot_query(queries[0], restaurant, mode="mock")
    assert snap.engine == "mock"
    assert len(snap.results) == 10
    assert all({"title", "url", "snippet"} <= set(r) for r in snap.results)
    # 매장 웹사이트 도메인은 mock 결과에 없으므로 순위 None
    assert snap.own_domain_rank is None


def test_search_snapshot_own_domain_rank(queries):
    from src.config import Restaurant
    from src.measure.search_snapshot import _rank_of_domain

    results = [
        {"title": "t", "url": "https://blog.naver.com/x", "snippet": ""},
        {"title": "t", "url": "https://www.hongdae-a.example.com/menu", "snippet": ""},
    ]
    assert _rank_of_domain(results, "hongdae-a.example.com") == 2
    assert _rank_of_domain(results, "absent.com") is None


def test_snapshot_all(queries, restaurant):
    snaps = snapshot_all(queries, restaurant, mode="mock")
    assert [s.query_id for s in snaps] == ["q1", "q2"]


def test_unknown_provider_raises():
    ch = LLMChannel(id="x", provider="unknown", model="m")
    try:
        get_client(ch, mode="live")
        raised = False
    except ValueError:
        raised = True
    assert raised
