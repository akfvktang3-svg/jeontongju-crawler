"""
Claude API로 P.D.A 프레임워크 기반 카드뉴스 카피 생성
앵글: Problem / Desire / Action / 트렌드 / 스토리
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


SYSTEM_PROMPT = """당신은 전통주 브랜드의 SNS 카드뉴스 카피라이터입니다.
P.D.A 프레임워크(Problem/Desire/Action)와 트렌드·스토리 앵글로 임팩트 있는 카피를 씁니다.

규칙:
- 헤드라인: 20자 이내, 강렬하고 궁금증을 유발하는 한 문장
- 본문 슬라이드: 슬라이드당 50자 이내 (읽기 쉽게 핵심만)
- CTA: 행동을 유도하는 20자 이내 문구
- 해시태그: 5개, #전통주 포함
- MZ세대가 공감하는 감성적 어조
- 반드시 유효한 JSON만 출력"""


def determine_card_count(text: str) -> int:
    """뉴스 분량에 따라 카드 장수 자동 결정 (3/5/7)"""
    length = len(text.strip())
    if length < 300:
        return 3
    elif length < 700:
        return 5
    else:
        return 7


def generate_copies(article: dict) -> tuple[list[dict], int]:
    """
    5가지 앵글의 카드뉴스 카피 생성
    반환: (copies 리스트, 카드 장수)
    """
    title = article.get("title", "")
    summary = article.get("card_summary", article.get("summary", article.get("one_line", "")))
    body = article.get("body", summary)
    category = article.get("category", "")

    card_count = determine_card_count(body or summary)
    content_slides = card_count - 2  # cover + cta 제외

    slide_spec = _build_slide_spec(card_count, content_slides)

    prompt = f"""다음 전통주 뉴스를 바탕으로 {card_count}장 카드뉴스 카피를 5가지 앵글로 작성해주세요.

뉴스 제목: {title}
카테고리: {category}
내용 요약: {summary}

─────────────────────────────
5가지 앵글 정의:
• Problem  - 독자가 공감할 문제/불편/놀라운 사실로 시작
• Desire   - 독자가 원하는 욕망·로망을 자극
• Action   - 구체적인 행동을 즉시 유도
• 트렌드   - 최신 트렌드·데이터로 관심 유도
• 스토리   - 감성적인 이야기·서사로 몰입 유도
─────────────────────────────

각 앵글 카드 구성 ({card_count}장):
{slide_spec}

아래 JSON 배열 형식으로만 응답하세요 (마크다운 코드블록 제외):
[
  {{
    "angle": "Problem",
    "headline": "커버 헤드라인 (20자 이내)",
    "slides": [
      {{"slide": 1, "type": "cover", "title": "헤드라인 (20자)", "subtitle": "서브타이틀 (30자)"}},
      {{"slide": 2, "type": "content", "title": "소제목 (15자)", "body": "본문 내용 (50자 이내)"}},
      ...content slides...
      {{"slide": {card_count}, "type": "cta", "action": "행동 촉구 문구 (20자)", "hashtags": ["#전통주", "#태그2", "#태그3", "#태그4", "#태그5"]}}
    ]
  }},
  {{ "angle": "Desire", ... }},
  {{ "angle": "Action", ... }},
  {{ "angle": "트렌드", ... }},
  {{ "angle": "스토리", ... }}
]"""

    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    copies = _parse_json(raw)
    return copies, card_count


def _build_slide_spec(card_count: int, content_slides: int) -> str:
    lines = ["- 슬라이드 1: 커버 (헤드라인 + 서브타이틀)"]
    for i in range(content_slides):
        lines.append(f"- 슬라이드 {i+2}: 본문 {i+1} (소제목 + 본문)")
    lines.append(f"- 슬라이드 {card_count}: CTA (행동 촉구 + 해시태그 5개)")
    return "\n".join(lines)


def _parse_json(raw: str) -> list[dict]:
    """Claude 응답에서 JSON 배열 추출"""
    # 코드블록 제거
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except json.JSONDecodeError:
                continue

    # 직접 파싱 시도
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # [ ] 범위 추출
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
        raise ValueError(f"JSON 파싱 실패:\n{raw[:300]}")
