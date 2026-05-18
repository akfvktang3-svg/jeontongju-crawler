"""
글로벌 주류 텔레그램 발송기
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PRIORITY_SCORE = 80

CATEGORY_EMOJI = {
    "위스키": "🥃",
    "와인": "🍷",
    "스피릿": "🍸",
    "맥주": "🍺",
    "기타": "🌍",
}


def send_top_articles(articles: list[dict]) -> int:
    if not articles:
        print("  발송할 기사가 없어요.")
        return 0

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  WARNING: 텔레그램 설정 없음")
        return 0

    print(f"\n텔레그램 발송 중... ({len(articles)}건)")
    _send_header(articles)

    success = 0
    for i, article in enumerate(articles):
        message = _format_message(article, rank=i + 1)
        if _send_message(message):
            success += 1

    print(f"  발송 완료: {success}/{len(articles)}건")
    return success


def _send_header(articles: list[dict]):
    today = datetime.now().strftime("%Y년 %m월 %d일")
    priority_count = sum(1 for a in articles if a.get("score", 0) >= PRIORITY_SCORE)

    from collections import Counter
    counts = Counter(a.get("category", "기타") for a in articles)
    category_lines = "\n".join(
        f"  {CATEGORY_EMOJI.get(cat, '🌍')} {cat}: *{cnt}건*"
        for cat, cnt in counts.most_common()
    )

    message = (
        f"🌍 *글로벌 주류 인텔리전스 리포트*\n"
        f"📅 {today}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 총 *{len(articles)}건* 선정\n"
        f"{category_lines}\n"
    )
    if priority_count:
        message += f"  ⭐ 최우선 ({PRIORITY_SCORE}점↑): *{priority_count}건*\n"
    message += "\n아래 기사를 확인하고 제작할 콘텐츠를 골라주세요 👇"
    _send_message(message)


def _format_message(article: dict, rank: int) -> str:
    category = article.get("category", "기타")
    emoji = CATEGORY_EMOJI.get(category, "🌍")
    score = article.get("score", 0)
    star = "⭐⭐" if score >= PRIORITY_SCORE else "⭐"
    title = article.get("title", "")
    summary = article.get("card_summary", article.get("summary", ""))
    tags = " ".join(article.get("tags", []))
    reason = article.get("score_reason", "")
    url = article.get("url", "")
    source = article.get("source", "")

    s_time = article.get("score_timeliness", 0)
    s_pop = article.get("score_popularity", 0)
    s_con = article.get("score_content", 0)
    s_ind = article.get("score_industry", 0)
    s_sns = article.get("score_sns", 0)

    return (
        f"{star} *{rank}위* {emoji} {category}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📰 *{title}*\n\n"
        f"📝 {summary}\n\n"
        f"🏷️ {tags}\n\n"
        f"⭐ *{score}점* | {reason}\n"
        f"└ 시의성{s_time} · 대중성{s_pop} · 콘텐츠화{s_con} · 산업가치{s_ind} · SNS{s_sns}\n\n"
        f"📌 출처: {source}\n"
        f"🔗 [원문 보기]({url})"
    )


def _send_message(text: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"  ERROR: 텔레그램 오류: {e}")
        return False


def test_connection() -> bool:
    print("텔레그램 연결 테스트 중...")
    result = _send_message(
        "✅ 글로벌 주류 크롤러 연결 성공!\n"
        "이 채널로 글로벌 위스키/와인 뉴스를 받아보실 수 있어요 🌍🥃🍷"
    )
    print("  연결 성공!" if result else "  연결 실패!")
    return result
