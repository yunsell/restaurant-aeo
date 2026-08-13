"""config/ 아래 YAML 설정을 dataclass로 로드한다."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = DATA_DIR / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"
SITE_DIR = PROJECT_ROOT / "site"
CACHE_DIR = PROJECT_ROOT / ".cache"


@dataclass
class Review:
    author: str
    rating: int
    text: str


@dataclass
class Restaurant:
    id: str
    name: str
    category: str
    address: str
    name_en: str = ""
    subcategory: str = ""
    coordinates: tuple[float, float] | None = None
    phone: str = ""
    hours: str = ""
    price_range: str = ""
    website: str = ""
    aliases: list[str] = field(default_factory=list)
    reviews: list[Review] = field(default_factory=list)
    aggregate_rating: dict | None = None

    @property
    def all_names(self) -> list[str]:
        names = [self.name] + self.aliases
        if self.name_en:
            names.append(self.name_en)
        return names


@dataclass
class Query:
    id: str
    text_ko: str
    intent: str
    weight: float = 1.0
    text_en: str = ""


@dataclass
class LLMChannel:
    id: str
    provider: str
    model: str
    use_search: bool = False


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_restaurants(path: Path | None = None) -> list[Restaurant]:
    raw = _load_yaml(path or CONFIG_DIR / "restaurants.yaml")
    out = []
    for r in raw["restaurants"]:
        coords = r.get("coordinates")
        out.append(
            Restaurant(
                id=r["id"],
                name=r["name"],
                name_en=r.get("name_en", ""),
                category=r["category"],
                subcategory=r.get("subcategory", ""),
                address=r["address"],
                coordinates=tuple(coords) if coords else None,
                phone=r.get("phone", ""),
                hours=r.get("hours", ""),
                price_range=r.get("price_range", ""),
                website=r.get("website", ""),
                aliases=r.get("aliases", []),
                reviews=[Review(**rv) for rv in r.get("reviews", [])],
                aggregate_rating=r.get("aggregate_rating"),
            )
        )
    return out


def load_queries(path: Path | None = None) -> list[Query]:
    raw = _load_yaml(path or CONFIG_DIR / "queries.yaml")
    return [
        Query(
            id=q["id"],
            text_ko=q["text_ko"],
            text_en=q.get("text_en", ""),
            intent=q["intent"],
            weight=float(q.get("weight", 1.0)),
        )
        for q in raw["queries"]
    ]


def load_llm_channels(path: Path | None = None) -> list[LLMChannel]:
    raw = _load_yaml(path or CONFIG_DIR / "llms.yaml")
    return [
        LLMChannel(
            id=c["id"],
            provider=c["provider"],
            model=c["model"],
            use_search=bool(c.get("use_search", False)),
        )
        for c in raw["llms"]
    ]


def get_mode() -> str:
    """"mock" 또는 "live". 기본은 mock — 키 없이도 파이프라인이 돈다."""
    return os.environ.get("AEO_MODE", "mock").lower()


def get_cache_ttl_hours() -> float:
    return float(os.environ.get("AEO_CACHE_TTL_HOURS", "24"))
