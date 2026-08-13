"""site/ 정적 사이트 빌드 엔트리포인트.

실행: `uv run python -m src.landing.build_site`
출력: site/index.html (매장 1개) 또는 site/{restaurant_id}/index.html (여러 개) + site/index.html 목록
"""
from __future__ import annotations

import sys

from src.config import SITE_DIR, load_restaurants
from src.landing.html_generator import render_restaurant_page


def main() -> int:
    restaurants = load_restaurants()
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    if len(restaurants) == 1:
        html = render_restaurant_page(restaurants[0])
        out = SITE_DIR / "index.html"
        out.write_text(html, encoding="utf-8")
        print(f"[{restaurants[0].id}] 랜딩 페이지 → {out}", file=sys.stderr)
        return 0

    links = []
    for r in restaurants:
        page_dir = SITE_DIR / r.id
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(render_restaurant_page(r), encoding="utf-8")
        links.append(f'<li><a href="{r.id}/">{r.name}</a></li>')
        print(f"[{r.id}] 랜딩 페이지 → {page_dir / 'index.html'}", file=sys.stderr)

    index = (
        "<!DOCTYPE html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
        "<title>매장 목록</title></head><body><h1>매장 목록</h1><ul>"
        + "".join(links)
        + "</ul></body></html>"
    )
    (SITE_DIR / "index.html").write_text(index, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
