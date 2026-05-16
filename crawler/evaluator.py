"""
카드뉴스 적합도 평가기 (Phase 3 수정: 공통 항목 통일)

[공통 5개 항목 - 국내/글로벌 동일한 이름, 다른 기준]
 1. 시의성    (20점) - 얼마나 최신/시즌 맞는 소식인가
 2. 대중성    (20점) - 타깃 독자가 흥미롭게 읽을 수 있는가
 3. 콘텐츠화  (20점) - 카드뉴스로 시각화하기 좋은가
 4. 산업가치  (20점) - 업계 내 중요도/브랜드/데이터 가치
 5. SNS화제성 (20점) - 공유·저장·댓글 유발 가능성
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

THRESHOLD_SCORE = 30
PRIORITY_SCORE = 80


def _is_global_article(article: dict) -> bool:
    return article.get("collector") == "rss_global"


def _evaluate_kr_batch(batch: list[dict]) -> list[dict]:
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
아래 기사들이 인스타그램 카드뉴스 콘텐츠로 얼마나 적합한지 5개 항목으로 평가해주세요.

━━━ 평가 기준 (총 100점) ━━━

① 시의성 (20점)
 - 20점: 신제품 출시 직후, D-7 이내 행사 등 지금 당장 올려야 할 소식
 - 12점: 이번 달 안에 올리면 좋을 소식
 - 4점: 시기와 무관하거나 오래된 소식

② 대중성 (20점)
 - 20점: 전통주 모르는 일반인도 "오 신기하다!" 할 소식
 - 12점: 전통주 관심층이라면 흥미로울 소식
 - 4점: 업계 전문가만 관심 가질 소식

③ 콘텐츠화 (20점)
 - 20점: 이미지+짧은 카피로 임팩트 있게 제작 가능
 - 12점: 카드뉴스로 만들 수 있지만 임팩트 약함
 - 4점: 텍스트 많거나 시각화 어려운 내용

④ 산업가치 (20점)
 - 20점: 특색 있는 양조장·명인·신제품 스토리 / 시장 데이터 포함
 - 12점: 일반적인 브랜드 소식
 - 4점: 산업적 가치 낮음

⑤ SNS화제성 (20점)
 - 20점: 공유·저장·댓글 유발 가능성 높음
 - 12점: 관심층 내에서 화제될 수 있음
 - 4점: 화제성 낮음

━━━ 기사 목록 ━━━
{articles_text}

반드시 아래 JSON 형식으로만 답하세요:
[
  {{
    "index": 1,
    "score_timeliness": 20점 만점,
    "score_popularity": 20점 만점,
    "score_content": 20점 만점,
    "score_industry": 20점 만점,
    "score_sns": 20점 만점,
    "total_score": 100점 만점 합계,
    "score_reason": "총점 이유 한 줄 (30자 이내)",
    "tags": ["#태그1", "#태그2", "#태그3", "#태그4"],
    "card_summary": "카드뉴스용 한 줄 요약 (40자 이내)"
  }}
]"""
    return _parse_evaluation(batch, prompt, eval_type="국내")


def _evaluate_global_batch(batch: list[dict]) -> list[dict]:
    articles_text = ""
    for idx, article in enumerate(batch):
        articles_text += f"""
[{idx + 1}]
Title: {article.get('title', '')}
Summary: {article.get('description', article.get('summary', ''))[:120]}
Category: {article.get('category', '')}
Source: {article.get('source', '')}
"""
    prompt = f"""You are an expert editor for a global spirits and wine SNS channel targeting Korean audiences.
Evaluate using the same 5 criteria as domestic Korean articles for easy comparison.

━━━ Scoring Criteria (100 points total) ━━━

① 시의성 / Timeliness (20pts)
 - 20pts: Latest release, award season, limited edition right now
 - 12pts: Relevant news for this month
 - 4pts: Old or evergreen content

② 대중성 / Popularity (20pts)
 - 20pts: Korean spirits consumers would find very interesting
 - 12pts: Of interest to spirits enthusiasts
 - 4pts: Only industry professionals would care

③ 콘텐츠화 / Content Fit (20pts)
 - 20pts: Easily visualized as impactful card news
 - 12pts: Possible but weak impact
 - 4pts: Too text-heavy or hard to visualize

④ 산업가치 / Industry Value (20pts)
 - 20pts: Major global brand, significant market data, export/regulation news
 - 12pts: General brand or industry news
 - 4pts: Low industry significance

⑤ SNS화제성 / Virality (20pts)
 - 20pts: High potential for shares, saves, comments
 - 12pts: Moderate engagement potential
 - 4pts: Low virality potential

━━━ Articles ━━━
{articles_text}

Reply ONLY in this JSON format:
[
  {{
    "index": 1,
    "score_timeliness": score out of 20,
    "score_popularity": score out of 20,
    "score_content": score out of 20,
    "score_industry": score out of 20,
    "score_sns": score out of 20,
    "total_score": total out of 100,
    "score_reason": "one-line reason in Korean (within 30 chars)",
    "tags": ["#태그1", "#태그2", "#태그3", "#태그4"],
    "card_summary": "one-line summary in Korean for card news (within 40 chars)"
  }}
]"""
    return _parse_evaluation(batch, prompt, eval_type="글로벌")


def _parse_evaluation(batch: list[dict], prompt: str, eval_type: str) -> list[dict]:
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
                article["score_content"] = item.get("score_content", 0)
                article["score_industry"] = item.get("score_industry", 0)
                article["score_sns"] = item.get("score_sns", 0)
                article["score_reason"] = item.get("score_reason", "")
                article["tags"] = item.get("tags", [])
                article["card_summary"] = item.get("card_summary", article.get("title", "")[:40])
                article["eval_type"] = eval_type
                result.append(article)
        return result

    except Exception as e:
        print(f"  ⚠️ {eval_type} 평가 오류: {e}")
        for article in batch:
            article["score"] = 0
            article["score_timeliness"] = 0
            article["score_popularity"] = 0
            article["score_content"] = 0
            article["score_industry"] = 0
            article["score_sns"] = 0
            article["score_reason"] = "평가 실패"
            article["tags"] = []
            article["card_summary"] = article.get("title", "")[:40]
            article["eval_type"] = eval_type
        return batch


def evaluate_articles(articles: list[dict]) -> list[dict]:
    if not articles:
        return []

    print(f"\n⭐ 카드뉴스 적합도 평가 중... ({len(articles)}건)")
    print("  📊 공통 평가 항목: 시의성 · 대중성 · 콘텐츠화 · 산업가치 · SNS화제성 (각 20점)")

    kr_articles = [(i, a) for i, a in enumerate(articles) if not _is_global_article(a)]
    global_articles = [(i, a) for i, a in enumerate(articles) if _is_global_article(a)]

    print(f"  📰 국내 전통주: {len(kr_articles)}건")
    print(f"  🌍 글로벌 주류: {len(global_articles)}건")

    result = list(articles)
    batch_size = 5

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

    result.sort(key=lambda x: x.get("score", 0), reverse=True)

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
    return [a for a in evaluated if a.get("score", 0) >= threshold]
