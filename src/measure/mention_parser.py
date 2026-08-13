"""LLM 응답 텍스트에서 대상 매장의 언급 여부·순위·문맥·감성을 추출한다.

매칭 규칙:
- 한글 이름/별칭: 공백 무시 완전 일치
- 영문/변형: rapidfuzz partial_ratio >= 85
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from rapidfuzz import fuzz

from src.config import Restaurant
from src.measure.llm_clients import extract_domains

FUZZY_THRESHOLD = 85
CONTEXT_CHARS = 100

_POSITIVE_WORDS = [
    "맛있", "추천", "훌륭", "최고", "인기", "유명", "가성비", "친절", "깔끔", "진하", "만족",
    "delicious", "best", "great", "excellent", "popular", "recommend", "must-try", "famous",
]
_NEGATIVE_WORDS = [
    "별로", "실망", "비싸", "불친절", "아쉽", "그저 그", "웨이팅이 길", "맛없",
    "disappointing", "overpriced", "bad", "avoid", "mediocre", "rude",
]

# "1. 이름", "1) 이름", "① 이름", "**1. 이름**" 류의 리스트 항목
_LIST_ITEM_RE = re.compile(r"^\s*(?:[*#>\-\s]*)?(?:(\d+)[.)]|[①②③④⑤⑥⑦⑧⑨⑩])\s*(.+)$")
_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"


@dataclass
class MentionResult:
    mentioned: bool = False
    rank: int | None = None
    context: str = ""
    sentiment: str = "neutral"
    sources_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _is_korean(s: str) -> bool:
    return bool(re.search(r"[가-힣]", s))


def _find_name(text: str, name: str) -> int:
    """텍스트에서 name의 시작 인덱스, 없으면 -1.

    한글 이름은 양쪽 공백을 제거한 형태끼리 비교(공백 무시 완전 일치),
    그 외에는 fuzzy 매칭으로 위치를 찾는다.
    """
    if not name:
        return -1
    if _is_korean(name):
        squeezed_name = name.replace(" ", "")
        squeezed_text = text.replace(" ", "")
        idx = squeezed_text.find(squeezed_name)
        if idx < 0:
            return -1
        # 원본 텍스트에서의 대략적 위치 복원: 공백 제거 전 인덱스로 역매핑
        count = 0
        for i, ch in enumerate(text):
            if ch != " ":
                if count == idx:
                    return i
                count += 1
        return 0
    # 영문/변형: 슬라이딩 없이 fuzzy alignment 사용
    lowered = text.lower()
    target = name.lower()
    idx = lowered.find(target)
    if idx >= 0:
        return idx
    if fuzz.partial_ratio(target, lowered) >= FUZZY_THRESHOLD:
        # 위치는 근사값으로: 첫 토큰 검색
        first_token = target.split()[0]
        pos = lowered.find(first_token)
        return pos if pos >= 0 else 0
    return -1


def _matched_in(text: str, restaurant: Restaurant) -> tuple[int, str] | None:
    """(위치, 매칭된 이름) 또는 None."""
    best: tuple[int, str] | None = None
    for name in restaurant.all_names:
        pos = _find_name(text, name)
        if pos >= 0 and (best is None or pos < best[0]):
            best = (pos, name)
    return best


def _detect_rank(text: str, restaurant: Restaurant) -> int | None:
    """번호 매겨진 리스트에서 매장이 몇 번째 항목에 등장하는지."""
    for line in text.splitlines():
        m = _LIST_ITEM_RE.match(line)
        if not m:
            continue
        if m.group(1):
            num = int(m.group(1))
        else:
            circled = next((c for c in line if c in _CIRCLED), None)
            num = _CIRCLED.index(circled) + 1 if circled else None
        if num is None:
            continue
        item_text = m.group(2)
        if _matched_in(item_text, restaurant):
            return num
    return None


def _detect_sentiment(context: str) -> str:
    pos = sum(1 for w in _POSITIVE_WORDS if w in context or w in context.lower())
    neg = sum(1 for w in _NEGATIVE_WORDS if w in context or w in context.lower())
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def parse_mention(text: str, restaurant: Restaurant, sources: list[str] | None = None) -> MentionResult:
    result = MentionResult(sources_used=extract_domains(sources or []))
    if not text:
        return result

    match = _matched_in(text, restaurant)
    if not match:
        return result

    pos, _name = match
    result.mentioned = True
    result.rank = _detect_rank(text, restaurant)
    start = max(0, pos - CONTEXT_CHARS // 2)
    result.context = text[start : pos + CONTEXT_CHARS].strip()
    result.sentiment = _detect_sentiment(result.context)
    return result
