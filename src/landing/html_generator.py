"""Jinja2로 매장 랜딩 페이지 HTML을 렌더링한다."""
from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.config import Restaurant
from src.landing.schema_builder import _price_range, jsonld_script

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _guess_area(address: str) -> str:
    """주소에서 동네 키워드 추출 (예: '서울 마포구 홍익로 XX' → '홍대')."""
    # 홍익로/홍대 인근이면 홍대로. 그 외에는 구 이름 사용.
    if re.search(r"홍익로|홍대", address):
        return "홍대"
    m = re.search(r"([가-힣]+구)", address)
    return m.group(1) if m else "우리 동네"


def render_restaurant_page(restaurant: Restaurant, area: str | None = None) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("restaurant.html")
    return template.render(
        r=restaurant,
        area=area or _guess_area(restaurant.address),
        jsonld=jsonld_script(restaurant),
        price_display=_price_range(restaurant.price_range),
    )
