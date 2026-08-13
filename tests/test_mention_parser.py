from src.measure.mention_parser import parse_mention


def test_not_mentioned(restaurant):
    text = "1. 연남 소문난 국밥\n2. 합정 옛날손칼국수"
    r = parse_mention(text, restaurant)
    assert r.mentioned is False
    assert r.rank is None
    assert r.context == ""


def test_exact_korean_mention_with_rank(restaurant):
    text = "홍대 맛집 추천입니다.\n1. 연남 소문난 국밥 — 든든합니다.\n2. 홍대 A식당 — 국물이 진해요.\n3. 망원 김치찜"
    r = parse_mention(text, restaurant)
    assert r.mentioned is True
    assert r.rank == 2
    assert "홍대 A식당" in r.context


def test_alias_mention(restaurant):
    text = "요즘 핫한 곳은 A식당 홍대점입니다. 웨이팅이 좀 있어요."
    r = parse_mention(text, restaurant)
    assert r.mentioned is True
    assert r.rank is None


def test_korean_spacing_insensitive(restaurant):
    # 공백이 달라도 한글 이름은 매칭되어야 한다
    text = "추천: 홍대A식당 이 근처에서 유명합니다."
    r = parse_mention(text, restaurant)
    assert r.mentioned is True


def test_english_fuzzy_mention(restaurant):
    text = "1. Hongdae A Restaurant - famous for its rich gukbap broth."
    r = parse_mention(text, restaurant)
    assert r.mentioned is True
    assert r.rank == 1


def test_english_no_false_positive(restaurant):
    text = "1. Mapo Grill House\n2. Yeonnam Noodle Bar"
    r = parse_mention(text, restaurant)
    assert r.mentioned is False


def test_sentiment_positive(restaurant):
    text = "홍대 A식당은 국물이 진하고 정말 맛있어요. 추천합니다."
    r = parse_mention(text, restaurant)
    assert r.sentiment == "positive"


def test_sentiment_negative(restaurant):
    text = "홍대 A식당은 기대보다 별로였고 가격도 비싸요. 실망했습니다."
    r = parse_mention(text, restaurant)
    assert r.sentiment == "negative"


def test_sources_domains(restaurant):
    text = "홍대 A식당 추천!"
    sources = [
        "https://www.mangoplate.com/restaurants/abc",
        "https://blog.naver.com/xyz/123",
        "https://www.mangoplate.com/restaurants/def",  # 중복 도메인
    ]
    r = parse_mention(text, restaurant, sources)
    assert r.sources_used == ["mangoplate.com", "blog.naver.com"]


def test_empty_text(restaurant):
    r = parse_mention("", restaurant)
    assert r.mentioned is False


def test_numbered_list_with_parenthesis(restaurant):
    text = "1) 연남 소문난 국밥\n2) 홍대 A식당"
    r = parse_mention(text, restaurant)
    assert r.rank == 2


def test_markdown_bold_list(restaurant):
    text = "- **1. 연남 소문난 국밥**\n- **2. 홍대 A식당** — 국밥 맛집"
    r = parse_mention(text, restaurant)
    assert r.mentioned is True
    assert r.rank == 2
