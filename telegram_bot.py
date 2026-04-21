"""
텔레그램 봇 - 카드뉴스 선택 / 승인 대기 / PNG 발송
명령어: /목록  /상태  /도움말  /start
"""

import os
import asyncio
import logging
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)
from dotenv import load_dotenv

import copy_agent
import image_renderer
import sheet_writer

load_dotenv()

BOT_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID     = os.getenv("TELEGRAM_CHAT_ID")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
SHEET_URL      = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# chat_id → 진행 중인 작업 정보
_active_jobs: dict[int, dict] = {}


# ── 명령어 핸들러 ──────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🍶 *전통주 카드뉴스 자동화 봇*\n\n"
        "/list — 카드뉴스 후보 기사 목록\n"
        "/status — 진행 중인 작업 확인\n"
        "/help — 사용법 안내",
        parse_mode="Markdown",
    )


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("📋 구글 시트에서 후보 목록을 가져오는 중...")

    articles = await asyncio.get_event_loop().run_in_executor(
        None, sheet_writer.get_candidate_articles
    )

    if not articles:
        await msg.edit_text(
            "⚠️ 카드뉴스 후보가 없어요.\n"
            "크롤러를 먼저 실행해주세요:\n`python crawler.py`",
            parse_mode="Markdown",
        )
        return

    articles = articles[:10]   # 최대 10개
    context.user_data["articles"] = articles

    keyboard = [
        [InlineKeyboardButton(
            f"{i+1}. {a['title'][:28]}{'…' if len(a['title']) > 28 else ''}",
            callback_data=f"sel_{i}",
        )]
        for i, a in enumerate(articles)
    ]

    await msg.edit_text(
        f"📰 *카드뉴스 후보 {len(articles)}건*\n"
        f"제작할 기사를 선택하세요:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid in _active_jobs:
        job = _active_jobs[cid]
        title = job["article"]["title"][:35]
        await update.message.reply_text(
            f"🔄 진행 중: *{title}*\n"
            f"구글 시트에서 승인을 기다리는 중이에요.\n\n"
            f"📊 [시트 열기]({SHEET_URL})",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    else:
        await update.message.reply_text("✅ 현재 진행 중인 작업이 없습니다.\n/list 로 기사를 선택하세요.")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *카드뉴스 자동화 사용법*\n\n"
        "1️⃣ `/list` — 카드뉴스 후보 목록 불러오기\n"
        "2️⃣ 기사 선택 → AI가 5가지 앵글 카피 자동 생성\n"
        "3️⃣ 구글 시트 *'✏️ 카드뉴스카피'* 탭에서\n"
        "    G열(승인여부)에 `승인` 입력\n"
        "4️⃣ PNG 카드뉴스 자동 생성 → 채널 발송!\n\n"
        "🃏 *카드 장수 기준*\n"
        "  • ~300자 기사 → 3장\n"
        "  • 300~700자 → 5장\n"
        "  • 700자+ → 7장\n\n"
        "⏳ 승인 대기: 최대 60분",
        parse_mode="Markdown",
    )


# ── 인라인 버튼 콜백 ───────────────────────────────────────────

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx      = int(query.data.split("_")[1])
    articles = context.user_data.get("articles", [])
    chat_id  = query.message.chat_id

    if idx >= len(articles):
        await query.edit_message_text("❌ 유효하지 않은 선택입니다.")
        return

    article = articles[idx]
    title   = article["title"][:40]

    if chat_id in _active_jobs:
        await query.edit_message_text(
            "⚠️ 이미 진행 중인 작업이 있어요. `/상태`로 확인하세요.",
            parse_mode="Markdown",
        )
        return

    await query.edit_message_text(
        f"✅ 선택: *{title}*\n\n"
        f"🤖 Claude AI가 P.D.A 프레임워크로 카피를 생성 중...\n"
        f"잠시만 기다려주세요 (10~30초).",
        parse_mode="Markdown",
    )

    # 카피 생성 (동기 블로킹 → 스레드풀 실행)
    loop = asyncio.get_event_loop()
    try:
        copies, card_count = await loop.run_in_executor(
            None, copy_agent.generate_copies, article
        )
    except Exception as e:
        logger.exception("카피 생성 오류")
        await context.bot.send_message(chat_id, f"❌ 카피 생성 오류: {e}")
        return

    # 구글 시트 기입
    try:
        start_row = await loop.run_in_executor(
            None, lambda: sheet_writer.write_copies(article, copies, card_count)
        )
        await loop.run_in_executor(
            None, lambda: sheet_writer.mark_article_in_progress(article["row"])
        )
    except Exception as e:
        logger.exception("시트 저장 오류")
        await context.bot.send_message(chat_id, f"❌ 시트 저장 오류: {e}")
        return

    # 생성된 카피 미리보기 발송
    preview_lines = [
        f"✏️ *카피 생성 완료!* (카드 {card_count}장 기준)\n"
    ]
    for copy in copies:
        angle    = copy.get("angle", "")
        headline = copy.get("headline", "")
        preview_lines.append(f"• *[{angle}]* {headline}")

    preview_lines += [
        f"\n📊 구글 시트에서 원하는 앵글을 승인해주세요:",
        f"[✏️ 카드뉴스카피 탭 열기]({SHEET_URL})",
        f"\n→ G열(승인여부)에 `승인` 입력",
    ]

    await context.bot.send_message(
        chat_id,
        "\n".join(preview_lines),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )

    # 승인 폴링 태스크 시작
    _active_jobs[chat_id] = {
        "article":    article,
        "start_row":  start_row,
        "card_count": card_count,
    }
    asyncio.create_task(
        _poll_and_render(context.bot, chat_id, article, start_row, card_count)
    )


# ── 백그라운드 폴링 + 렌더링 + 발송 ──────────────────────────

async def _poll_and_render(
    bot,
    chat_id:   int,
    article:   dict,
    start_row: int,
    card_count: int,
):
    """승인 감지 → PNG 렌더링 → 채널 발송"""
    loop = asyncio.get_event_loop()

    await bot.send_message(chat_id, "⏳ 승인 대기 중... (최대 60분, 30초 간격 확인)")

    try:
        approved = await loop.run_in_executor(
            None,
            lambda: sheet_writer.wait_for_approval(start_row, timeout_minutes=60, poll_interval=30),
        )
    except Exception as e:
        logger.exception("폴링 오류")
        await bot.send_message(chat_id, f"❌ 폴링 중 오류 발생: {e}")
        _active_jobs.pop(chat_id, None)
        return

    if approved is None:
        await bot.send_message(chat_id, "⏰ 60분 내에 승인이 없어 작업을 종료합니다.")
        _active_jobs.pop(chat_id, None)
        return

    angle = approved.get("angle", "")
    await bot.send_message(
        chat_id,
        f"✅ *[{angle}]* 앵글 승인!\n🎨 PNG 카드뉴스 생성 중...",
        parse_mode="Markdown",
    )

    # 이미지 렌더링
    try:
        config = image_renderer.load_config()
        paths: list[Path] = await loop.run_in_executor(
            None, lambda: image_renderer.render_cards(approved, config)
        )
    except Exception as e:
        logger.exception("이미지 렌더링 오류")
        await bot.send_message(chat_id, f"❌ 이미지 생성 오류: {e}")
        _active_jobs.pop(chat_id, None)
        return

    await bot.send_message(
        chat_id,
        f"🖼️ *{len(paths)}장 생성 완료!* 채널로 발송 중...",
        parse_mode="Markdown",
    )

    # 채널 발송
    title_short = article.get("title", "")[:40]
    for i, path in enumerate(paths):
        caption = f"🍶 {title_short}" if i == 0 else None
        with open(path, "rb") as f:
            await bot.send_photo(CHANNEL_ID, f, caption=caption)

    # 완료 처리
    try:
        await loop.run_in_executor(
            None, lambda: sheet_writer.mark_article_done(article["row"])
        )
    except Exception:
        pass

    _active_jobs.pop(chat_id, None)

    await bot.send_message(
        chat_id,
        f"🎉 *카드뉴스 발송 완료!*\n"
        f"총 {len(paths)}장이 채널에 올라갔어요.",
        parse_mode="Markdown",
    )


# ── 봇 실행 ───────────────────────────────────────────────────

def run_bot():
    if not BOT_TOKEN:
        raise ValueError(".env에 TELEGRAM_BOT_TOKEN이 없어요.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("list",   cmd_list))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CallbackQueryHandler(handle_selection, pattern=r"^sel_\d+$"))

    logger.info("🤖 텔레그램 봇 시작!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run_bot()
