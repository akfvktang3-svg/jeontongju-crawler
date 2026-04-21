"""
텔레그램 발송기
평가 기준을 통과한 기사를 텔레그램으로 전송합니다.

발송 형식:
  🍶 [카테고리] 제목
  📝 카드뉴스 요약
  🏷️ #태그1 #태그2 #태그3 #태그4
  ⭐ 점수: 85점 (시의성20 대중성22 적합성25 연관성18)
  🔗 원문 링크
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

# 카테고리별 이모지
CATEGORY_EMOJI = {
    "신제품 출시":   "🆕",
    "행사 소식":     "🎪",
    "주류 트렌드":   "📈",
    "브랜드 이야기": "🏷️",
    "기타":          "📌",
}


def send_top_articles(articles: list[dict]) -> int:
    """
    평가 통과 기사들을 텔레그램으로 발송
    반환: 발송 성공 건수
    """
    if not articles:
        print("  ℹ️  발송할 기사가 없어요.")
        return 0

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  ⚠️  텔레그램 설정이 없어요. .env에 BOT_TOKEN과 CHAT_ID를 추가해주세요.")
        return 0

    print(f"\n📱 텔레그램 발송 중... ({len(articles)}건)")

    # 헤더 메시지 먼저 발송
    _send_header(len(articles))

    success = 0
    for i, article in enumerate(articles):
        message = _format_message(article, rank=i + 1)
        if _send_message(message):
            success += 1
        else:
            print(f"  ⚠️  {i+1}번 기사 발송 실패")

    print(f"  ✅ 텔레그램 발송 완료: {success}/{len(articles)}건")
    return success


def _send_header(count: int):
    """일일 리포트 헤더 메시지"""
    from datetime import datetime
    today = datetime.now().strftime("%Y년 %m월 %d일")

    message = (
        f"🍶 *전통주 카드뉴스 후보 리포트*\n"
        f"📅 {today}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"총 *{count}건*의 카드뉴스 후보가 선정되었어요!\n"
        f"아래 기사들을 확인하고 제작할 콘텐츠를 골라주세요 👇"
    )
    _send_message(message)


def _format_message(article: dict, rank: int) -> str:
    """텔레그램 메시지 포맷"""
    category     = article.get("category", "기타")
    emoji        = CATEGORY_EMOJI.get(category, "📌")
    title        = article.get("title", "")
    card_summary = article.get("card_summary", article.get("one_line", ""))
    tags         = " ".join(article.get("tags", []))
    score        = article.get("score", 0)
    t_score      = article.get("score_timeliness", 0)
    p_score      = article.get("score_popularity", 0)
    c_score      = article.get("score_card_fit", 0)
    r_score      = article.get("score_relevance", 0)
    reason       = article.get("score_reason", "")
    url          = article.get("url", "")
    source       = article.get("source", "")

    message = (
        f"*{rank}위* {emoji} {category}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📰 *{title}*\n\n"
        f"📝 {card_summary}\n\n"
        f"🏷️ {tags}\n\n"
        f"⭐ *{score}점* | {reason}\n"
        f"└ 시의성 {t_score} · 대중성 {p_score} · 적합성 {c_score} · 연관성 {r_score}\n\n"
        f"📌 출처: {source}\n"
        f"🔗 [원문 보기]({url})"
    )
    return message


def _send_message(text: str) -> bool:
    """텔레그램 메시지 전송"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"  ❌ 텔레그램 오류: {e}")
        return False


def test_connection() -> bool:
    """텔레그램 연결 테스트"""
    print("📱 텔레그램 연결 테스트 중...")
    result = _send_message(
        "✅ 전통주 크롤러 텔레그램 연결 성공!\n"
        "앞으로 카드뉴스 후보 기사를 이 채널로 받아보실 수 있어요 🍶"
    )
    if result:
        print("  ✅ 연결 성공!")
    else:
        print("  ❌ 연결 실패. BOT_TOKEN과 CHAT_ID를 확인해주세요.")
    return result
