"""Schema.org Restaurant JSON-LD 빌더.

Google Rich Results Test를 통과하도록 필수/권장 필드를 채운다.
값이 없는 선택 필드는 아예 넣지 않는다 (빈 값은 검증 실패 원인).
"""
from __future__ import annotations

import json
import re

from src.config import Restaurant

_ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _opening_hours(hours: str) -> list[dict] | None:
    """"11:00-22:00" → openingHoursSpecification (매일 동일 영업으로 가정)."""
    m = re.fullmatch(r"\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*", hours or "")
    if not m:
        return None
    return [
        {
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": _ALL_DAYS,
            "opens": m.group(1),
            "closes": m.group(2),
        }
    ]


def _price_range(raw: str) -> str | None:
    """"10000-20000" → "₩10,000-₩20,000"."""
    m = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", raw or "")
    if not m:
        return raw or None
    lo, hi = (int(g) for g in m.groups())
    return f"₩{lo:,}-₩{hi:,}"


def build_restaurant_jsonld(restaurant: Restaurant) -> dict:
    data: dict = {
        "@context": "https://schema.org",
        "@type": "Restaurant",
        "name": restaurant.name,
        "servesCuisine": restaurant.category,
        "address": {
            "@type": "PostalAddress",
            "streetAddress": restaurant.address,
            "addressLocality": "서울",
            "addressCountry": "KR",
        },
    }
    if restaurant.name_en:
        data["alternateName"] = restaurant.name_en
    if restaurant.coordinates:
        lat, lng = restaurant.coordinates
        data["geo"] = {"@type": "GeoCoordinates", "latitude": lat, "longitude": lng}
    if restaurant.phone:
        data["telephone"] = restaurant.phone
    hours = _opening_hours(restaurant.hours)
    if hours:
        data["openingHoursSpecification"] = hours
    price = _price_range(restaurant.price_range)
    if price:
        data["priceRange"] = price
    if restaurant.website:
        data["url"] = restaurant.website
        data["menu"] = restaurant.website.rstrip("/") + "/menu"
    if restaurant.coordinates:
        lat, lng = restaurant.coordinates
        data["hasMap"] = f"https://map.naver.com/p?c={lng},{lat},17"
    if restaurant.aggregate_rating:
        data["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": restaurant.aggregate_rating["value"],
            "reviewCount": restaurant.aggregate_rating["count"],
        }
    if restaurant.reviews:
        data["review"] = [
            {
                "@type": "Review",
                "author": {"@type": "Person", "name": rv.author},
                "reviewRating": {"@type": "Rating", "ratingValue": rv.rating, "bestRating": 5},
                "reviewBody": rv.text,
            }
            for rv in restaurant.reviews
        ]
    return data


def jsonld_script(restaurant: Restaurant) -> str:
    # </script> 조기 종료 방지: JSON 문자열 안의 "</"를 "<\/"로 이스케이프
    raw = json.dumps(build_restaurant_jsonld(restaurant), ensure_ascii=False, indent=2)
    return raw.replace("</", "<\\/")
