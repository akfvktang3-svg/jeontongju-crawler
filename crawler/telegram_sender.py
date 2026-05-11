"""
텔레그램 발송기 (Phase 4: 출력 개선)

변경사항:
- 헤더에 국내/글로벌 건수 구분 표시
- 공통 5개 항목 점수 표시 (시의성·대중성·콘텐츠화·산업가치·SNS)
- 80점↑ 최우선 기사 ⭐⭐ 표시
- 글로벌 카테고리 이모지 추가
- 국내🇰🇷 / 글로벌🌍 구분 표시
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

# 카테고리별 이모지 (국내 + 글로벌)
CATEGORY_EMOJI = {
    # 국내 전통주
    "신제품 출시":  "🆕",
    "행사 소식":   "🎪",
    "주류 트렌드":  "📈",
    "브랜드 이야기": "🏷️",
    # 글로벌 주류
    "위스키":      "🥃",
    "와인":        "🍷",
    "스피릿":      "🍸",
    "글로벌 트렌드": "🌍",
    # 공통
    "기타":        "📌",
}

PRIORITY_SCORE = 80  # 이 점수 이상 → ⭐⭐ 최우선


def send_top_articles(articles: list[dict]) -> int:
    """평가 통과 기사들을 텔레그램으로 발송. 반환: 발송 성공 건수"""
    if not articles:
        print("  ℹ️ 발송할 기사가 없어요.")
        return 0

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  ⚠️ 텔레그램 설정이 없어요. .env에 BOT_TOKEN과 CHAT_ID를 추가해주세요.")
        return 0

    print(f"\n📱 텔레그램 발송 중... ({len(articles)}건)")

    # 헤더 메시지 먼저 발송
    _send_header(articles)

    success = 0
    for i, article in enumerate(articles):
        message = _format_message(article, rank=i + 1)
        if _send_message(message):
            success += 1
        else:
            print(f"  ⚠️ {i+1}번 기사 발송 실패")

    print(f"  ✅ 텔레그램 발송 완료: {success}/{len(articles)}건")
    return success


def _send_header(articles: list[dict]):
    """일일 리포트 헤더 - 국내/글로벌 건수 구분 표시"""
    from datetime import datetime
    today = datetime.now().strftime("%Y년 %m월 %d일")

    # 국내/글로벌 건수 분리
    kr_count = sum(1 for a in articles if a.get("eval_type") == "국내")
    global_count = sum(1 for a in articles if a.get("eval_type") == "글로벌")
    priority_count = sum(1 for a in articles if a.get("score", 0) >= PRIORITY_SCORE)

    message = (
        f"🍶 *주류 인텔리전스 리포트*\n"
        f"📅 {today}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 총 *{len(articles)}건* 선정\n"
        f"  🇰🇷 국내 전통주: *{kr_count}건*\n"
        f"  🌍 글로벌 주류: *{global_count}건*\n"
    )
    if priority_count:
        message += f"  ⭐ 최우선 ({PRIORITY_SCORE}점↑): *{priority_count}건*\n"

    message += f"\n아래 기사를 확인하고 제작할 콘텐츠를 골라주세요 👇"
    _send_message(message)


def _format_message(article: dict, rank: int) -> str:
    """텔레그램 메시지 포맷 - Phase 4 개선"""
    category  = article.get("category", "기타")
    emoji     = CATEGORY_EMOJI.get(category, "📌")
    eval_type = article.get("eval_type", "")
    flag      = "🇰🇷" if eval_type == "국내" else "🌍"
    title     = article.get("title", "")
    summary   = article.get("card_summary", article.get("one_line", ""))
    tags      = " ".join(article.get("tags", []))
    score     = article.get("score", 0)
    reason    = article.get("score_reason", "")
    url       = article.get("link", article.get("url", ""))
    source    = article.get("source", "")

    # 점수별 강조 표시
    star = "⭐⭐" if score >= PRIORITY_SCORE else "⭐"

    # 공통 5개 항목 점수
    s_time    = article.get("score_timeliness", 0)
    s_pop     = article.get("score_popularity", 0)
    s_content = article.get("score_content", 0)
    s_ind     = article.get("score_industry", 0)
    s_sns     = article.get("score_sns", 0)

    message = (
        f"{star} *{rank}위* {flag} {emoji} {category}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📰 *{title}*\n\n"
        f"📝 {summary}\n\n"
        f"🏷️ {tags}\n\n"
        f"⭐ *{score}점* | {reason}\n"
        f"└ 시의성{s_time} · 대중성{s_pop} · 콘텐츠화{s_content} · 산업가치{s_ind} · SNS{s_sns}\n\n"
        f"📌 출처: {source}\n"
        f"🔗 [원문 보기]({url})"
    )
    return message


def _send_message(text: str) -> bool:
    """텔레그램 메시지 전송"""
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
