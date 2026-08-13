import json

from src.config import Restaurant, Review
from src.landing.html_generator import _guess_area, render_restaurant_page
from src.landing.schema_builder import (
    _opening_hours,
    _price_range,
    build_restaurant_jsonld,
    jsonld_script,
)


def _full_restaurant() -> Restaurant:
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
        aliases=["홍대 A"],
        reviews=[Review(author="김OO", rating=5, text="국물이 진해요 & 맛있어요")],
        aggregate_rating={"value": 4.5, "count": 128},
    )


def test_jsonld_required_fields():
    data = build_restaurant_jsonld(_full_restaurant())
    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "Restaurant"
    assert data["name"] == "홍대 A식당"
    assert data["address"]["@type"] == "PostalAddress"
    assert data["geo"] == {"@type": "GeoCoordinates", "latitude": 37.5563, "longitude": 126.9236}
    assert data["telephone"] == "02-123-4567"
    assert data["servesCuisine"] == "한식"


def test_jsonld_optional_fields():
    data = build_restaurant_jsonld(_full_restaurant())
    assert data["aggregateRating"]["ratingValue"] == 4.5
    assert data["aggregateRating"]["reviewCount"] == 128
    assert data["review"][0]["reviewRating"]["ratingValue"] == 5
    assert data["menu"] == "https://hongdae-a.example.com/menu"
    assert "map.naver.com" in data["hasMap"]


def test_jsonld_minimal_restaurant_omits_empty():
    r = Restaurant(id="x", name="가게", category="한식", address="서울 어딘가")
    data = build_restaurant_jsonld(r)
    for absent in ("geo", "telephone", "openingHoursSpecification", "aggregateRating", "review", "url"):
        assert absent not in data


def test_opening_hours_parse():
    spec = _opening_hours("11:00-22:00")
    assert spec[0]["opens"] == "11:00"
    assert spec[0]["closes"] == "22:00"
    assert len(spec[0]["dayOfWeek"]) == 7
    assert _opening_hours("항상 영업") is None
    assert _opening_hours("") is None


def test_price_range_format():
    assert _price_range("10000-20000") == "₩10,000-₩20,000"
    assert _price_range("") is None
    assert _price_range("$$") == "$$"


def test_jsonld_script_is_valid_json():
    script = jsonld_script(_full_restaurant())
    # </ 이스케이프 후에도 JSON으로 파싱 가능해야 한다
    assert json.loads(script.replace("<\\/", "</"))
    assert "</script>" not in script


def test_render_restaurant_page():
    html = render_restaurant_page(_full_restaurant())
    assert "<!DOCTYPE html>" in html
    # SEO: title/H1에 "지역 카테고리 맛집" 키워드
    assert "홍대 국밥 맛집" in html
    assert '<script type="application/ld+json">' in html
    assert '"@type": "Restaurant"' in html
    assert 'property="og:title"' in html
    assert 'name="twitter:card"' in html
    # 리뷰 인용
    assert "김OO" in html


def test_render_page_jsonld_not_escaped():
    html = render_restaurant_page(_full_restaurant())
    # autoescape가 JSON-LD를 망가뜨리지 않아야 한다
    assert "&#34;" not in html.split("application/ld+json")[1].split("</script>")[0]


def test_guess_area():
    assert _guess_area("서울 마포구 홍익로 12") == "홍대"
    assert _guess_area("서울 강남구 테헤란로 1") == "강남구"
    assert _guess_area("어딘가") == "우리 동네"
