"""
카드뉴스 적합도 평가기
수집된 뉴스를 100점 만점으로 평가하고,
기준 점수(기본 60점) 이상인 뉴스를 선별합니다.

평가 항목 (총 100점):
  1. 시의성       (25점) - 얼마나 최신/시즌 맞는 소식인가
  2. 대중성       (25점) - 일반인도 흥미롭게 읽을 수 있는가
  3. 카드뉴스 적합성 (25점) - 시각화/카드 형식에 맞는가
  4. 전통주 연관성 (25점) - 전통주/우리술과 얼마나 직접 관련인가
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 기준 점수 (이 점수 이상이면 제2저장소 + 텔레그램 발송)
THRESHOLD_SCORE = 60


def evaluate_articles(articles: list[dict]) -> list[dict]:
    """
    기사들을 평가하고 점수를 부여합니다.
    반환: 점수가 추가된 기사 목록 (점수 높은 순 정렬)
    """
    if not articles:
        return []

    print(f"\n⭐ 카드뉴스 적합도 평가 중... ({len(articles)}건)")
    evaluated = []
    batch_size = 5

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        batch_num = i // batch_size + 1
        total = (len(articles) + batch_size - 1) // batch_size
        print(f"  📊 평가 배치 {batch_num}/{total} 처리 중...")
        evaluated.extend(_evaluate_batch(batch))

    # 점수 높은 순으로 정렬
    evaluated.sort(key=lambda x: x.get("score", 0), reverse=True)

    # 결과 요약
    passed = [a for a in evaluated if a.get("score", 0) >= THRESHOLD_SCORE]
    print(f"\n  ✅ 평가 완료: 총 {len(evaluated)}건")
    print(f"  🎯 기준 통과 ({THRESHOLD_SCORE}점↑): {len(passed)}건")

    return evaluated


def _evaluate_batch(batch: list[dict]) -> list[dict]:
    """배치 단위로 Claude에게 평가 요청"""

    articles_text = ""
    for idx, article in enumerate(batch):
        articles_text += f"""
[{idx + 1}]
제목: {article.get('title', '')}
요약: {article.get('summary', '')[:100]}
카테고리: {article.get('category', '')}
출처: {article.get('source', '')}
"""

    prompt = f"""당신은 전통주 전문 SNS 카드뉴스 편집장입니다.
아래 기사들이 인스타그램/카카오 카드뉴스 콘텐츠로 얼마나 적합한지 평가해주세요.

━━━ 평가 기준 (총 100점) ━━━

① 시의성 (25점)
  - 25점: 지금 당장 올려야 할 핫한 소식 (신제품 출시 직후, D-7 이내 행사 등)
  - 15점: 이번 달 안에 올리면 좋을 소식
  - 5점:  시기와 무관하거나 오래된 소식

② 대중성 (25점)
  - 25점: 전통주 모르는 일반인도 "오 신기하다!" 할 소식
  - 15점: 전통주 관심 있는 사람이라면 흥미로울 소식
  - 5점:  업계 관계자나 전문가만 관심 가질 소식

③ 카드뉴스 적합성 (25점)
  - 25점: 이미지+짧은 카피로 임팩트 있게 전달 가능 (신제품, 행사, 순위, 트렌드)
  - 15점: 카드뉴스로 만들 수 있지만 임팩트가 약함
  - 5점:  텍스트가 너무 많거나 시각화하기 어려운 내용

④ 전통주 연관성 (25점)
  - 25점: 전통주/우리술이 핵심 주제인 소식
  - 15점: 전통주가 포함되지만 주류 전반 소식
  - 5점:  전통주와 간접적으로만 연관

━━━ 태그 생성 규칙 ━━━
기사 내용을 보고 SNS에서 쓸 해시태그 4개를 만들어주세요.
예: #전통주, #막걸리신제품, #드링크서울, #우리술

━━━ 기사 목록 ━━━
{articles_text}

반드시 아래 JSON 형식으로만 답하세요:
[
  {{
    "index": 1,
    "score_timeliness": 25점 만점 점수,
    "score_popularity": 25점 만점 점수,
    "score_card_fit": 25점 만점 점수,
    "score_relevance": 25점 만점 점수,
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
                article["score"]             = item.get("total_score", 0)
                article["score_timeliness"]  = item.get("score_timeliness", 0)
                article["score_popularity"]  = item.get("score_popularity", 0)
                article["score_card_fit"]    = item.get("score_card_fit", 0)
                article["score_relevance"]   = item.get("score_relevance", 0)
                article["score_reason"]      = item.get("score_reason", "")
                article["tags"]              = item.get("tags", [])
                article["card_summary"]      = item.get("card_summary", article.get("one_line", ""))
                result.append(article)

        return result

    except Exception as e:
        print(f"  ⚠️  평가 오류: {e}")
        # 오류 시 기본값 부여
        for article in batch:
            article["score"]        = 0
            article["score_reason"] = "평가 실패"
            article["tags"]         = []
            article["card_summary"] = article.get("title", "")[:40]
        return batch


def get_top_articles(evaluated: list[dict], threshold: int = THRESHOLD_SCORE) -> list[dict]:
    """기준 점수 이상인 기사만 반환"""
    return [a for a in evaluated if a.get("score", 0) >= threshold]
