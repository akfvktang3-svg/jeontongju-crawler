"""
Claude 기반 2차 필터
키워드로 1차 필터링 후, Claude가 최종적으로
"이게 진짜 전통주/주류 관련인지" 판단합니다.

사용 위치:
  - 뉴스: 수집 후 → Claude 분류 전에 실행
  - 쇼핑: 수집 후 → 구글 시트 저장 전에 실행
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1차 필터: 키워드 기반 (빠름)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 뉴스 필터
NEWS_REQUIRED = [
    "전통주", "막걸리", "약주", "청주", "탁주", "동동주",
    "전통소주", "우리술", "한국술", "양조장", "증류소",
    "과실주", "민속주", "전통 술", "주류",
]
NEWS_EXCLUDE = [
    "술잔", "와인잔", "맥주잔", "안주", "술집",
    "칵테일", "일본술", "사케", "위스키", "와인",
    "맥주", "소맥", "보자기",
]

# 쇼핑 필터
SHOP_REQUIRED = [
    "막걸리", "전통주", "약주", "청주", "탁주", "동동주",
    "전통소주", "과실주", "민속주", "복분자주", "매실주",
    "소곡주", "법주", "안동소주", "문배주", "이강주",
    "진도홍주", "감홍로", "화요", "백세주", "산사춘",
]
SHOP_EXCLUDE = [
    "잔", "컵", "보자기", "포장지", "박스", "케이스",
    "안주", "오징어", "육포", "치즈", "과자",
    "책", "도서", "인형", "굿즈", "향수", "캔들",
    "호리병", "주전자", "병따개", "오프너",
    "술게임", "주사위", "카드게임",
]


def keyword_filter_news(articles: list[dict]) -> list[dict]:
    """뉴스 1차 키워드 필터"""
    result = []
    for a in articles:
        text = a.get("title", "") + " " + a.get("summary", "")
        if any(kw in text for kw in NEWS_EXCLUDE):
            continue
        if any(kw in text for kw in NEWS_REQUIRED):
            result.append(a)
    return result


def keyword_filter_shopping(items: list[dict]) -> list[dict]:
    """쇼핑 1차 키워드 필터"""
    result = []
    for item in items:
        name = item.get("title", "")
        if any(kw in name for kw in SHOP_EXCLUDE):
            continue
        if any(kw in name for kw in SHOP_REQUIRED):
            result.append(item)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2차 필터: Claude 기반 (정확함)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def claude_filter_news(articles: list[dict]) -> list[dict]:
    """
    Claude가 뉴스 기사를 읽고
    '이게 진짜 전통주/우리술 관련 뉴스인지' 최종 판단
    """
    if not articles:
        return []

    print(f"  🔍 Claude 뉴스 필터링 중... ({len(articles)}건)")
    passed = []
    batch_size = 10

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        filtered = _claude_filter_batch(batch, mode="news")
        passed.extend(filtered)

    removed = len(articles) - len(passed)
    print(f"  ✅ 뉴스 필터 완료: {len(passed)}건 통과 / {removed}건 제거")
    return passed


def claude_filter_shopping(items: list[dict]) -> list[dict]:
    """
    Claude가 쇼핑 상품명을 읽고
    '이게 진짜 전통주 술 제품인지' 최종 판단
    """
    if not items:
        return []

    print(f"  🔍 Claude 쇼핑 필터링 중... ({len(items)}건)")
    passed = []
    batch_size = 10

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        filtered = _claude_filter_batch(batch, mode="shopping")
        passed.extend(filtered)

    removed = len(items) - len(passed)
    print(f"  ✅ 쇼핑 필터 완료: {len(passed)}건 통과 / {removed}건 제거")
    return passed


def _claude_filter_batch(batch: list[dict], mode: str) -> list[dict]:
    """Claude에게 배치 단위로 필터링 요청"""

    if mode == "news":
        items_text = "\n".join(
            f"[{i+1}] 제목: {a.get('title','')} / 요약: {a.get('summary','')[:60]}"
            for i, a in enumerate(batch)
        )
        prompt = f"""당신은 전통주/우리술 전문 미디어 편집장입니다.
아래 뉴스 기사들을 읽고, 각 기사가 전통주·우리술과 직접 관련된 기사인지 판단해주세요.

통과 기준:
- 전통주, 막걸리, 약주, 청주, 우리술, 양조장 등 한국 전통 주류가 주제인 기사
- 전통주 시장, 산업, 행사, 신제품, 브랜드, 트렌드 관련 기사

탈락 기준:
- 전통주와 무관한 일반 뉴스 (경제, 정치, 연예 등)
- 단순히 "술"이라는 단어만 포함된 기사
- 위스키, 와인, 맥주, 사케 등 외국 주류만 다루는 기사
- 술잔, 안주, 주류 관련 용품만 다루는 기사

기사 목록:
{items_text}

반드시 아래 JSON 형식으로만 답하세요:
[{{"index": 1, "pass": true}}, {{"index": 2, "pass": false}}, ...]"""

    else:  # shopping
        items_text = "\n".join(
            f"[{i+1}] 상품명: {a.get('title','')}"
            for i, a in enumerate(batch)
        )
        prompt = f"""당신은 전통주 전문 쇼핑몰 MD입니다.
아래 상품들이 실제 전통주(마시는 술) 제품인지 판단해주세요.

통과 기준:
- 막걸리, 약주, 청주, 전통소주, 과실주, 증류주 등 마시는 전통주 자체
- 전통주 세트 상품 (술이 포함된 것)

탈락 기준:
- 술잔, 컵, 호리병, 주전자 등 음주 용품
- 보자기, 포장지, 박스 등 포장재
- 안주, 음식류
- 책, 도서, 굿즈, 인형
- 향수, 캔들 등 전혀 관련없는 상품
- 외국 주류 (위스키, 와인, 사케 등)

상품 목록:
{items_text}

반드시 아래 JSON 형식으로만 답하세요:
[{{"index": 1, "pass": true}}, {{"index": 2, "pass": false}}, ...]"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        results = json.loads(raw)
        passed_indices = {r["index"] - 1 for r in results if r.get("pass")}
        return [batch[i] for i in range(len(batch)) if i in passed_indices]

    except Exception as e:
        print(f"  ⚠️  Claude 필터 오류: {e} → 키워드 필터 결과 유지")
        return batch  # 오류 시 그냥 통과


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 통합 실행 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def filter_news(articles: list[dict]) -> list[dict]:
    """뉴스 2단계 필터 (키워드 → Claude)"""
    after_keyword = keyword_filter_news(articles)
    after_claude  = claude_filter_news(after_keyword)
    return after_claude


def filter_shopping(items: list[dict]) -> list[dict]:
    """쇼핑 2단계 필터 (키워드 → Claude)"""
    after_keyword = keyword_filter_shopping(items)
    after_claude  = claude_filter_shopping(after_keyword)
    return after_claude
