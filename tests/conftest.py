import pytest

from src.config import LLMChannel, Query, Restaurant


@pytest.fixture
def restaurant() -> Restaurant:
    return Restaurant(
        id="hongdae_a",
        name="홍대 A식당",
        name_en="Hongdae A Restaurant",
        category="한식",
        subcategory="국밥",
        address="서울 마포구 홍익로 12",
        coordinates=(37.5563, 126.9236),
        phone="02-123-4567",
        hours="11:00-22:00",
        price_range="10000-20000",
        website="https://hongdae-a.example.com",
        aliases=["홍대 A", "A식당 홍대점"],
    )


@pytest.fixture
def queries() -> list[Query]:
    return [
        Query(id="q1", text_ko="홍대 근처 맛집 5곳 추천해줘", intent="generic_local_list", weight=1.0),
        Query(id="q2", text_ko="홍대 국밥 맛집 어디가 좋아?", intent="category_local", weight=1.5),
    ]


@pytest.fixture
def channels() -> list[LLMChannel]:
    return [
        LLMChannel(id="mock_search", provider="openai", model="gpt-5", use_search=True),
        LLMChannel(id="mock_no_search", provider="anthropic", model="claude-opus-5", use_search=False),
    ]
