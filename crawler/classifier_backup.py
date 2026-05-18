"""
Claude 분류기
수집된 뉴스를 Claude API로 자동 분류하고 카드뉴스 추천도를 평가합니다.
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 카테고리 정의
CATEGORIES = {
    "신제품 출시":   "🆕 새로운 전통주 출시, 리뉴얼, 신상품 등 시장에 새 제품이 등장한 소식",
    "행사 소식":     "🎪 드링크서울, 주류박람회, 시음회, 바쇼 등 주류 관련 오프라인 행사",
    "주류 트렌드":   "📈 국내 주류 소비량/판매량 변화, 수입/수출 동향, 맥주·위스키·와인 포함 주류 전반 트렌드",
    "브랜드 이야기": "🏷️ 특정 양조장·브랜드의 헤리티지, 투어, 방문기, 브랜드 스토리 소개",
    "기타":          "📌 위 네 가지에 해당하지 않는 기타 소식",
}

# 카테고리별 핵심 키워드 (Claude 오류시 보조 분류용)
CATEGORY_KEYWORDS = {
    "신제품 출시":   ["신제품", "출시", "신상품", "새로운", "리뉴얼", "선보", "한정판", "새 제품"],
    "행사 소식":     ["행사", "시음회", "출품", "주류박람회", "바쇼", "드링크서울", "박람회", "개최", "참가", "페스티벌", "팝업"],
    "주류 트렌드":   ["판매량", "매출", "소비량", "수입", "수출", "트렌드", "성장", "통계", "점유율", "MZ", "위스키", "와인"],
    "브랜드 이야기": ["양조장", "브랜드", "증류소", "투어", "기행", "방문기", "헤리티지", "장인", "스토리"],
}


def classify_articles(articles: list[dict]) -> list[dict]:
    """수집된 기사들을 Claude로 분류"""
    print("\n🤖 Claude가 기사 분류 중...")

    classified = []
    batch_size = 5

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(articles) + batch_size - 1) // batch_size
        print(f"  📋 배치 {batch_num}/{total_batches} 처리 중...")
        classified.extend(_classify_batch(batch))

    print(f"\n  ✅ 분류 완료: {len(classified)}건")
    return classified


def _classify_batch(batch: list[dict]) -> list[dict]:
    """배치 단위로 Claude에게 분류 요청"""

    articles_text = ""
    for idx, article in enumerate(batch):
        articles_text += f"\n[{idx+1}]\n제목: {article['title']}\n요약: {article['summary']}\n출처: {article['source']}\n"

    prompt = f"""당신은 전통주 및 주류 전문 미디어 편집자입니다.
아래 기사들을 읽고 반드시 아래 5개 카테고리 중 하나로만 분류해주세요.

━━━ 카테고리 정의 ━━━

1. 신제품 출시
   - 새로운 전통주·주류 제품이 시장에 나온 소식
   - 기존 제품의 리뉴얼, 패키지 변경, 한정판 출시 포함
   - 관련 단어: 신제품, 출시, 신상품, 새로운, 리뉴얼, 선보, 한정판

2. 행사 소식
   - 대한민국에서 열리는 주류 관련 오프라인 행사
   - 드링크서울, 주류박람회, 시음회, 바쇼, 페스티벌, 팝업 등
   - 관련 단어: 행사, 시음회, 출품, 박람회, 바쇼, 드링크서울, 개최, 참가

3. 주류 트렌드
   - 대한민국 주류 시장의 변화와 동향 (전통주 포함 맥주, 위스키, 와인 등 모두 포함)
   - 소비량/판매량/매출 변화, 수입·수출 현황, MZ세대 주류 문화 등
   - 관련 단어: 판매량, 매출, 소비량, 수입, 수출, 트렌드, 성장, 인기

4. 브랜드 이야기
   - 특정 양조장이나 브랜드 하나를 깊이 소개하는 기사
   - 양조장 투어, 방문기, 브랜드 헤리티지, 창업자 이야기 등
   - 관련 단어: 양조장, 증류소, 투어, 방문기, 기행, 헤리티지, 스토리, 장인

5. 기타
   - 위 4가지 카테고리 어디에도 해당하지 않는 소식

━━━ 카드뉴스 추천도 기준 ━━━
- 상: 일반 대중도 흥미롭게 읽을 만한 시의성 높은 소식
- 중: 주류·전통주 관심층이 관심 가질 만한 소식
- 하: 전문적이거나 대중 관심도가 낮은 소식

━━━ 기사 목록 ━━━
{articles_text}

반드시 아래 JSON 배열 형식으로만 답하세요. 다른 텍스트는 절대 포함하지 마세요:
[
  {{
    "index": 1,
    "category": "신제품 출시/행사 소식/주류 트렌드/브랜드 이야기/기타 중 정확히 하나",
    "reason": "분류 이유 한 줄 (20자 이내)",
    "one_line": "핵심 내용 한 줄 요약 (30자 이내)",
    "recommend": "상/중/하"
  }}
]"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        classifications = json.loads(raw)

        result = []
        for item in classifications:
            idx = item["index"] - 1
            if idx < len(batch):
                article = batch[idx].copy()
                category = item.get("category", "기타")
                if category not in CATEGORIES:
                    category = "기타"
                article["category"]  = category
                article["reason"]    = item.get("reason", "")
                article["one_line"]  = item.get("one_line", article["title"][:30])
                article["recommend"] = item.get("recommend", "하")
                result.append(article)
        return result

    except Exception as e:
        print(f"  ⚠️  분류 오류: {e}")
        return _fallback_classify(batch)


def _fallback_classify(batch: list[dict]) -> list[dict]:
    """Claude 오류 시 키워드 기반 기본 분류"""
    for article in batch:
        text = article.get("title", "") + " " + article.get("summary", "")
        category = "기타"
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                category = cat
                break
        article["category"]  = category
        article["reason"]    = "키워드 자동 분류"
        article["one_line"]  = article.get("title", "")[:30]
        article["recommend"] = "중"
    return batch
