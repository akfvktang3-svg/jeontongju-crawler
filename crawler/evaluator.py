"""
카드뉴스 적합도 평가기 (Phase 3: 국내/글로벌 분리 평가)

변경사항 (Phase 3):
- 국내 전통주 기사 → 전통주 전용 5개 항목으로 평가
- 글로벌 주류 기사 → 글로벌 전용 5개 항목으로 평가
- 둘 다 100점 만점, 60점 이상 카드뉴스 후보

[국내 전통주 평가 항목]
 1. 시의성        (20점) - 얼마나 최신/시즌 맞는 소식인가
 2. 대중성        (20점) - 일반인도 흥미롭게 읽을 수 있는가
 3. 카드뉴스 적합성 (20점) - 시각화/카드 형식에 맞는가
 4. 브랜드/스토리  (20점) - 양조장, 명인, 제품 스토리 있는가
 5. 시의성        (20점) - 지금 이 시점에 올리기 딱 맞는가

[글로벌 주류 평가 항목]
 1. 글로벌 브랜드  (20점) - 유명 브랜드/증류소 관련 여부
 2. 산업 트렌드    (20점) - 글로벌 주류 시장 흐름 반영
 3. 시장/수출/관세 (20점) - 수치, 통계, 정책 포함 여부
 4. 한국 콘텐츠화  (20점) - 한국 독자 관심도/콘텐츠화 가능성
 5. SNS 화제성    (20점) - 바이럴/공유 가능성
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 기준 점수 (이 점수 이상이면 텔레그램 발송)
THRESHOLD_SCORE = 60
PRIORITY_SCORE = 80  # 이 점수 이상이면 최우선 발송 ⭐


def _is_global_article(article: dict) -> bool:
    """RSS 수집기에서 온 글로벌 기사 여부"""
    return article.get("collector") == "rss_global"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 국내 전통주 평가
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _evaluate_kr_batch(batch: list[dict]) -> list[dict]:
    """국내 전통주 기사 평가 (5개 항목 × 20점)"""

    articles_text = ""
    for idx, article in enumerate(batch):
        articles_text += f"""
[{idx + 1}]
제목: {article.get('title', '')}
요약: {article.get('description', article.get('summary', ''))[:120]}
카테고리: {article.get('category', '')}
출처: {article.get('source', '')}
"""

    prompt = f"""당신은 전통주/우리술 전문 SNS 카드뉴스 편집장입니다.
아래 기사들이 인스타그램 카드뉴스 콘텐츠로 얼마나 적합한지 평가해주세요.

━━━ 평가 기준 (총 100점) ━━━

① 시의성 (20점)
 - 20점: 지금 당장 올려야 할 핫한 소식 (출시 직후, D-7 이내 행사)
 - 12점: 이번 달 안에 올리면 좋을 소식
 - 4점: 시기와 무관하거나 오래된 소식

② 대중성 (20점)
 - 20점: 전통주 모르는 일반인도 "오 신기하다!" 할 소식
 - 12점: 전통주 관심층이라면 흥미로울 소식
 - 4점: 업계 전문가만 관심 가질 소식

③ 카드뉴스 적합성 (20점)
 - 20점: 이미지+짧은 카피로 임팩트 있게 전달 가능
 - 12점: 카드뉴스로 만들 수 있지만 임팩트 약함
 - 4점: 텍스트가 너무 많거나 시각화 어려움

④ 브랜드/스토리 가치 (20점)
 - 20점: 특색 있는 양조장, 명인, 신제품 스토리 있음
 - 12점: 일반적인 브랜드 소식
 - 4점: 브랜드/스토리 요소 없음

⑤ SNS 화제성 (20점)
 - 20점: 공유·저장·댓글 유발 가능성 높음
 - 12점: 관심층 내에서 화제될 수 있음
 - 4점: 화제성 낮음

━━━ 태그 생성 규칙 ━━━
SNS 해시태그 4개를 만들어주세요. 예: #전통주, #막걸리신제품, #우리술

━━━ 기사 목록 ━━━
{articles_text}

반드시 아래 JSON 형식으로만 답하세요:
[
  {{
    "index": 1,
    "score_timeliness": 20점 만점 점수,
    "score_popularity": 20점 만점 점수,
    "score_card_fit": 20점 만점 점수,
    "score_brand": 20점 만점 점수,
    "score_sns": 20점 만점 점수,
    "total_score": 100점 만점 합계,
    "score_reason": "총점 이유 한 줄 (30자 이내)",
    "tags": ["#태그1", "#태그2", "#태그3", "#태그4"],
    "card_summary": "카드뉴스용 한 줄 요약 (40자 이내, 임팩트 있게)"
  }}
]"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

        evaluations = json.loads(raw)
        result = []
        for item in evaluations:
            idx = item["index"] - 1
            if idx < len(batch):
                article = batch[idx].copy()
                article["score"] = item.get("total_score", 0)
                article["score_timeliness"] = item.get("score_timeliness", 0)
                article["score_popularity"] = item.get("score_popularity", 0)
                article["score_card_fit"] = item.get("score_card_fit", 0)
                article["score_brand"] = item.get("score_brand", 0)
                article["score_sns"] = item.get("score_sns", 0)
                article["score_reason"] = item.get("score_reason", "")
                article["tags"] = item.get("tags", [])
                article["card_summary"] = item.get("card_summary", article.get("title", "")[:40])
                article["eval_type"] = "국내"
                result.append(article)
        return result

    except Exception as e:
        print(f"  ⚠️ 국내 평가 오류: {e}")
        for article in batch:
            article["score"] = 0
            article["score_reason"] = "평가 실패"
            article["tags"] = []
            article["card_summary"] = article.get("title", "")[:40]
            article["eval_type"] = "국내"
        return batch


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 글로벌 주류 평가
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _evaluate_global_batch(batch: list[dict]) -> list[dict]:
    """글로벌 주류 기사 평가 (5개 항목 × 20점)"""

    articles_text = ""
    for idx, article in enumerate(batch):
        articles_text += f"""
[{idx + 1}]
Title: {article.get('title', '')}
Summary: {article.get('description', article.get('summary', ''))[:120]}
Category: {article.get('category', '')}
Source: {article.get('source', '')}
"""

    prompt = f"""You are an expert editor for a global spirits and wine industry SNS channel targeting Korean audiences.
Evaluate how suitable each article is for Instagram card news content.

━━━ Scoring Criteria (100 points total) ━━━

① Global Brand Value (20pts)
 - 20pts: Major global brand/distillery news (Macallan, Penfolds, Diageo etc.)
 - 12pts: Known regional brand news
 - 4pts: Unknown or niche brand

② Industry Trend (20pts)
 - 20pts: Reflects major global spirits/wine market trend
 - 12pts: Relevant industry movement
 - 4pts: No significant trend value

③ Market/Data Value (20pts)
 - 20pts: Includes specific stats, export data, regulations, awards
 - 12pts: Some market context
 - 4pts: No data or market relevance

④ Korea Content Potential (20pts)
 - 20pts: Korean audiences would find it very interesting or relatable
 - 12pts: Some interest for Korean spirits enthusiasts
 - 4pts: Little relevance to Korean market

⑤ SNS Virality (20pts)
 - 20pts: High potential for shares, saves, comments
 - 12pts: Moderate engagement potential
 - 4pts: Low virality potential

━━━ Tag Rules ━━━
Create 4 hashtags in Korean. Example: #위스키, #글로벌주류, #와인트렌드

━━━ Articles ━━━
{articles_text}

Reply ONLY in this JSON format:
[
  {{
    "index": 1,
    "score_brand": score out of 20,
    "score_trend": score out of 20,
    "score_market": score out of 20,
    "score_korea": score out of 20,
    "score_sns": score out of 20,
    "total_score": total out of 100,
    "score_reason": "one-line reason in Korean (within 30 chars)",
    "tags": ["#태그1", "#태그2", "#태그3", "#태그4"],
    "card_summary": "one-line summary in Korean for card news (within 40 chars)"
  }}
]"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

        evaluations = json.loads(raw)
        result = []
        for item in evaluations:
            idx = item["index"] - 1
            if idx < len(batch):
                article = batch[idx].copy()
                article["score"] = item.get("total_score", 0)
                article["score_brand"] = item.get("score_brand", 0)
                article["score_trend"] = item.get("score_trend", 0)
                article["score_market"] = item.get("score_market", 0)
                article["score_korea"] = item.get("score_korea", 0)
                article["score_sns"] = item.get("score_sns", 0)
                article["score_reason"] = item.get("score_reason", "")
                article["tags"] = item.get("tags", [])
                article["card_summary"] = item.get("card_summary", article.get("title", "")[:40])
                article["eval_type"] = "글로벌"
                result.append(article)
        return result

    except Exception as e:
        print(f"  ⚠️ 글로벌 평가 오류: {e}")
        for article in batch:
            article["score"] = 0
            article["score_reason"] = "평가 실패"
            article["tags"] = []
            article["card_summary"] = article.get("title", "")[:40]
            article["eval_type"] = "글로벌"
        return batch


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 통합 실행 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def evaluate_articles(articles: list[dict]) -> list[dict]:
    """
    기사들을 평가하고 점수를 부여합니다.
    - 국내 전통주 기사 → 국내 기준으로 평가
    - 글로벌 주류 기사 → 글로벌 기준으로 평가
    반환: 점수가 추가된 기사 목록 (점수 높은 순 정렬)
    """
    if not articles:
        return []

    print(f"\n⭐ 카드뉴스 적합도 평가 중... ({len(articles)}건)")

    # 국내/글로벌 분리
    kr_articles = [(i, a) for i, a in enumerate(articles) if not _is_global_article(a)]
    global_articles = [(i, a) for i, a in enumerate(articles) if _is_global_article(a)]

    print(f"  📰 국내 전통주: {len(kr_articles)}건")
    print(f"  🌍 글로벌 주류: {len(global_articles)}건")

    result = list(articles)
    batch_size = 5

    # 국내 기사 평가
    if kr_articles:
        print(f"\n  🍶 국내 전통주 평가 시작...")
        for i in range(0, len(kr_articles), batch_size):
            chunk_indices = kr_articles[i:i + batch_size]
            chunk = [a for _, a in chunk_indices]
            batch_num = i // batch_size + 1
            total = (len(kr_articles) + batch_size - 1) // batch_size
            print(f"  📊 국내 배치 {batch_num}/{total} 처리 중...")
            evaluated = _evaluate_kr_batch(chunk)
            for j, (orig_idx, _) in enumerate(chunk_indices):
                result[orig_idx] = evaluated[j]

    # 글로벌 기사 평가
    if global_articles:
        print(f"\n  🥃 글로벌 주류 평가 시작...")
        for i in range(0, len(global_articles), batch_size):
            chunk_indices = global_articles[i:i + batch_size]
            chunk = [a for _, a in chunk_indices]
            batch_num = i // batch_size + 1
            total = (len(global_articles) + batch_size - 1) // batch_size
            print(f"  📊 글로벌 배치 {batch_num}/{total} 처리 중...")
            evaluated = _evaluate_global_batch(chunk)
            for j, (orig_idx, _) in enumerate(chunk_indices):
                result[orig_idx] = evaluated[j]

    # 점수 높은 순으로 정렬
    result.sort(key=lambda x: x.get("score", 0), reverse=True)

    # 결과 요약
    passed = [a for a in result if a.get("score", 0) >= THRESHOLD_SCORE]
    priority = [a for a in result if a.get("score", 0) >= PRIORITY_SCORE]

    kr_passed = [a for a in passed if a.get("eval_type") == "국내"]
    global_passed = [a for a in passed if a.get("eval_type") == "글로벌"]

    print(f"\n  ✅ 평가 완료: 총 {len(result)}건")
    print(f"  🎯 기준 통과 ({THRESHOLD_SCORE}점↑): {len(passed)}건")
    print(f"     └ 국내: {len(kr_passed)}건 / 글로벌: {len(global_passed)}건")
    print(f"  ⭐ 최우선 ({PRIORITY_SCORE}점↑): {len(priority)}건")

    return result


def get_top_articles(evaluated: list[dict], threshold: int = THRESHOLD_SCORE) -> list[dict]:
    """기준 점수 이상인 기사만 반환"""
    return [a for a in evaluated if a.get("score", 0) >= threshold]
