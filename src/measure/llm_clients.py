"""LLM provider 클라이언트.

공통 인터페이스 ``LLMClient.ask(query) -> LLMResponse``.
- ``AEO_MODE=mock`` 이면 ``MockClient`` 가 canned 응답을 돌려준다 (비용 0, 키 불필요).
- ``AEO_MODE=live`` 이면 provider별 실제 SDK/REST 호출.

구현 노트:
- OpenAI: Responses API + web_search 툴
- Anthropic: Messages API + web_search_20260209 서버 툴 (claude-opus-5는
  temperature 등 샘플링 파라미터를 받지 않으므로 보내지 않는다)
- Google: Gemini REST generateContent + google_search grounding
- Perplexity: REST chat/completions (sonar 모델은 항상 검색 기반)
"""
from __future__ import annotations

import hashlib
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import LLMChannel

_RETRYABLE = (httpx.HTTPError, ConnectionError, TimeoutError)


@dataclass
class LLMResponse:
    text: str
    sources: list[str] = field(default_factory=list)
    latency_ms: int = 0
    cost_usd: float = 0.0
    model_version: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LLMResponse":
        return cls(**d)


class LLMClient(ABC):
    def __init__(self, channel: LLMChannel):
        self.channel = channel

    @abstractmethod
    def _ask(self, query: str) -> LLMResponse:
        ...

    def ask(self, query: str) -> LLMResponse:
        start = time.monotonic()
        try:
            resp = self._ask_with_retry(query)
        except Exception as e:  # 마지막 재시도까지 실패 — 파이프라인은 계속 돈다
            resp = LLMResponse(text="", model_version=self.channel.model, error=f"{type(e).__name__}: {e}")
        resp.latency_ms = int((time.monotonic() - start) * 1000)
        return resp

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE),
        reraise=True,
    )
    def _ask_with_retry(self, query: str) -> LLMResponse:
        return self._ask(query)


# ── Mock ─────────────────────────────────────────────────────

_MOCK_COMPETITORS = ["연남 소문난 국밥", "홍대 돈부리집", "합정 옛날손칼국수", "상수 브런치하우스", "망원 김치찜"]
_MOCK_SOURCES = [
    "https://blog.naver.com/food_hongdae/223000001",
    "https://www.mangoplate.com/restaurants/abc123",
    "https://www.siksinhot.com/P/12345",
    "https://www.tripadvisor.com/Restaurant_Review-hongdae",
    "https://www.diningcode.com/profile.php?rid=xyz",
]


class MockClient(LLMClient):
    """결정적(deterministic) canned 응답.

    (채널 id, 쿼리) 해시로 대상 매장 언급 여부·순위를 정하므로
    같은 입력이면 언제나 같은 출력 → 테스트/개발에 사용.
    """

    def __init__(self, channel: LLMChannel, target_names: list[str] | None = None):
        super().__init__(channel)
        self.target_names = target_names or []

    def _ask(self, query: str) -> LLMResponse:
        h = int(hashlib.sha256(f"{self.channel.id}::{query}".encode()).hexdigest(), 16)
        mention = self.target_names and (h % 10 < 3)  # 약 30% 확률로 언급
        items = _MOCK_COMPETITORS[:4]
        if mention:
            rank = (h // 10) % 5  # 0~4위 자리에 삽입
            items = items[:rank] + [self.target_names[0]] + items[rank:]
        else:
            items = items + [_MOCK_COMPETITORS[4]]
        lines = [f"{i + 1}. {name} — 홍대 인근에서 평이 좋은 곳입니다." for i, name in enumerate(items)]
        text = "홍대 근처 추천 맛집입니다:\n" + "\n".join(lines)
        sources = _MOCK_SOURCES[: 3 if self.channel.use_search else 0]
        return LLMResponse(text=text, sources=sources, model_version=f"mock-{self.channel.model}")


# ── OpenAI (ChatGPT) ─────────────────────────────────────────


class OpenAIClient(LLMClient):
    def _ask(self, query: str) -> LLMResponse:
        from openai import OpenAI

        client = OpenAI()
        kwargs: dict = {"model": self.channel.model, "input": query}
        if self.channel.use_search:
            kwargs["tools"] = [{"type": "web_search"}]
        resp = client.responses.create(**kwargs)

        text = getattr(resp, "output_text", "") or ""
        sources: list[str] = []
        for item in getattr(resp, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                for ann in getattr(content, "annotations", []) or []:
                    url = getattr(ann, "url", None)
                    if url:
                        sources.append(url)
        return LLMResponse(text=text, sources=sources, model_version=getattr(resp, "model", self.channel.model))


# ── Anthropic (Claude) ───────────────────────────────────────


class AnthropicClient(LLMClient):
    def _ask(self, query: str) -> LLMResponse:
        import anthropic

        client = anthropic.Anthropic()
        kwargs: dict = {
            "model": self.channel.model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": query}],
        }
        if self.channel.use_search:
            kwargs["tools"] = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}]
        resp = client.messages.create(**kwargs)

        if resp.stop_reason == "refusal":
            return LLMResponse(text="", model_version=resp.model, error="refusal")

        text_parts: list[str] = []
        sources: list[str] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "web_search_tool_result":
                content = block.content
                if isinstance(content, list):
                    for result in content:
                        url = getattr(result, "url", None)
                        if url:
                            sources.append(url)
        return LLMResponse(text="\n".join(text_parts), sources=sources, model_version=resp.model)


# ── Google (Gemini) ──────────────────────────────────────────


class GeminiClient(LLMClient):
    def _ask(self, query: str) -> LLMResponse:
        api_key = os.environ["GEMINI_API_KEY"]
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.channel.model}:generateContent"
        )
        body: dict = {"contents": [{"parts": [{"text": query}]}]}
        if self.channel.use_search:
            body["tools"] = [{"google_search": {}}]
        r = httpx.post(url, json=body, headers={"x-goog-api-key": api_key}, timeout=120)
        r.raise_for_status()
        data = r.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return LLMResponse(text="", model_version=self.channel.model, error="no candidates")
        cand = candidates[0]
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        sources = [
            chunk["web"]["uri"]
            for chunk in cand.get("groundingMetadata", {}).get("groundingChunks", [])
            if chunk.get("web", {}).get("uri")
        ]
        return LLMResponse(text=text, sources=sources, model_version=data.get("modelVersion", self.channel.model))


# ── Perplexity ───────────────────────────────────────────────


class PerplexityClient(LLMClient):
    def _ask(self, query: str) -> LLMResponse:
        api_key = os.environ["PERPLEXITY_API_KEY"]
        r = httpx.post(
            "https://api.perplexity.ai/chat/completions",
            json={
                "model": self.channel.model,
                "messages": [{"role": "user", "content": query}],
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        sources = data.get("citations", []) or [
            s.get("url", "") for s in data.get("search_results", []) if s.get("url")
        ]
        return LLMResponse(text=text, sources=sources, model_version=data.get("model", self.channel.model))


# ── Factory ──────────────────────────────────────────────────

_PROVIDERS: dict[str, type[LLMClient]] = {
    "openai": OpenAIClient,
    "anthropic": AnthropicClient,
    "google": GeminiClient,
    "perplexity": PerplexityClient,
}


def get_client(channel: LLMChannel, mode: str, target_names: list[str] | None = None) -> LLMClient:
    if mode == "mock":
        return MockClient(channel, target_names=target_names)
    try:
        cls = _PROVIDERS[channel.provider]
    except KeyError:
        raise ValueError(f"unknown provider: {channel.provider}") from None
    return cls(channel)


def extract_domains(urls: list[str]) -> list[str]:
    """URL 리스트 → 중복 제거된 도메인 리스트 (등장 순서 유지)."""
    seen: list[str] = []
    for u in urls:
        m = re.match(r"https?://([^/]+)", u)
        if not m:
            continue
        domain = m.group(1).lower().removeprefix("www.")
        if domain not in seen:
            seen.append(domain)
    return seen
