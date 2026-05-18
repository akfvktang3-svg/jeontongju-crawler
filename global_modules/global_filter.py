"""
글로벌 주류 Claude 필터
키워드 필터 없이 Claude API로만 판단
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def filter_articles(articles: list[dict]) -> list[dict]:
    if not articles:
        return []

    print(f"\nClaude 필터링 중... ({len(articles)}건)")
    passed = []
    batch_size = 10

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        results = _filter_batch(batch)
        passed.extend(results)

    removed = len(articles) - len(passed)
    print(f"필터 완료: {len(passed)}건 통과 / {removed}건 제거")
    return passed


def _filter_batch(batch: list[dict]) -> list[dict]:
    items_text = "\n".join(
        f"[{i+1}] Title: {a.get('title', '')[:80]}\n"
        f"    Summary: {a.get('summary', '')[:100]}\n"
        f"    Source: {a.get('source', '')}"
        for i, a in enumerate(batch)
    )

    prompt = f"""You are an expert editor for a global liquor industry media channel targeting Korean audiences.

Evaluate each article and decide if it has genuine news value about the global spirits/wine/whisky industry.

PASS criteria:
- New product releases or limited editions
- Distillery/winery news and innovations
- Market trends, sales data, export news
- Awards and competitions
- Industry policy and regulations
- Notable brand or company news

REJECT criteria:
- Generic lifestyle content with no news value
- Low-quality SEO or promotional articles
- Unrelated food/beverage content

Articles:
{items_text}

Reply ONLY in this JSON format:
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
        passed = []
        for r in results:
            idx = r["index"] - 1
            if 0 <= idx < len(batch) and r.get("pass"):
                passed.append(batch[idx])
        return passed

    except Exception as e:
        print(f"  WARNING: Claude 필터 오류: {e} -> 전체 통과")
        return batch
