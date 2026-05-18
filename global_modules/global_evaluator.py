"""
글로벌 주류 점수 평가기
공통 5개 항목으로 평가 (글로벌 기준 적용)
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

THRESHOLD_SCORE = 30
PRIORITY_SCORE = 80


def evaluate_articles(articles: list[dict]) -> list[dict]:
    if not articles:
        return []

    print(f"\n점수 평가 중... ({len(articles)}건)")
    result = list(articles)
    batch_size = 5

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        evaluated = _evaluate_batch(batch)
        for j, article in enumerate(evaluated):
            result[i + j] = article

    result.sort(key=lambda x: x.get("score", 0), reverse=True)

    passed = [a for a in result if a.get("score", 0) >= THRESHOLD_SCORE]
    priority = [a for a in result if a.get("score", 0) >= PRIORITY_SCORE]
    print(f"  평가 완료: {len(result)}건")
    print(f"  기준 통과 ({THRESHOLD_SCORE}점↑): {len(passed)}건")
    print(f"  최우선 ({PRIORITY_SCORE}점↑): {len(priority)}건")

    return result


def _evaluate_batch(batch: list[dict]) -> list[dict]:
    articles_text = ""
    for idx, a in enumerate(batch):
        articles_text += (
            f"\n[{idx+1}]\n"
            f"Title: {a.get('title', '')}\n"
            f"Summary: {a.get('summary', '')[:150]}\n"
            f"Source: {a.get('source', '')}\n"
            f"Category: {a.get('category', '')}\n"
        )

    prompt = f"""You are an expert editor for a global spirits/wine SNS channel targeting Korean audiences.
Score each article using 5 criteria (100 points total).

Scoring criteria:
1. Timeliness (20pts): Is this breaking news or a timely release?
2. Popularity (20pts): Would Korean spirits/wine lovers find this interesting?
3. Content Fit (20pts): Easy to make into visual card news?
4. Industry Value (20pts): Major brand, market data, or significant industry news?
5. Virality (20pts): High potential for shares/saves/comments?

Articles:
{articles_text}

Reply ONLY in this JSON format:
[
  {{
    "index": 1,
    "score_timeliness": 15,
    "score_popularity": 18,
    "score_content": 16,
    "score_industry": 17,
    "score_sns": 14,
    "total_score": 80,
    "score_reason": "한 줄 이유 (30자 이내)",
    "tags": ["#위스키", "#글로벌주류", "#신제품", "#하이볼"],
    "card_summary": "카드뉴스용 한 줄 한국어 요약 (40자 이내)"
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
            if 0 <= idx < len(batch):
                article = batch[idx].copy()
                article["score"] = item.get("total_score", 0)
                article["score_timeliness"] = item.get("score_timeliness", 0)
                article["score_popularity"] = item.get("score_popularity", 0)
                article["score_content"] = item.get("score_content", 0)
                article["score_industry"] = item.get("score_industry", 0)
                article["score_sns"] = item.get("score_sns", 0)
                article["score_reason"] = item.get("score_reason", "")
                article["tags"] = item.get("tags", [])
                article["card_summary"] = item.get("card_summary", article.get("title", "")[:40])
                result.append(article)
        return result

    except Exception as e:
        print(f"  WARNING: 평가 오류: {e}")
        for article in batch:
            article["score"] = 0
            article["score_reason"] = "평가 실패"
            article["tags"] = []
            article["card_summary"] = article.get("title", "")[:40]
        return batch


def get_top_articles(evaluated: list[dict], threshold: int = THRESHOLD_SCORE) -> list[dict]:
    return [a for a in evaluated if a.get("score", 0) >= threshold]
