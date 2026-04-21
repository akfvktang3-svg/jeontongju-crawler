"""
카드뉴스 카피 구글 시트 기입 + 승인 감지
탭: ✏️ 카드뉴스카피
"""

import os
import json
import time
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID   = os.getenv("SPREADSHEET_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./google_credentials.json")
COPY_SHEET_NAME  = "✏️ 카드뉴스카피"
CANDIDATE_SHEET  = "⭐ 카드뉴스후보"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COPY_HEADERS = [
    "생성일시", "뉴스제목", "뉴스URL",
    "앵글", "헤드라인", "슬라이드데이터(JSON)",
    "승인여부", "승인일시", "카드장수",
]

# 승인으로 인식할 값들
APPROVAL_VALUES = {"승인", "✅", "✅승인", "approve", "ok", "OK"}


def _get_client():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def _open_spreadsheet():
    return _get_client().open_by_key(SPREADSHEET_ID)


def _ensure_copy_sheet(spreadsheet) -> gspread.Worksheet:
    existing = [ws.title for ws in spreadsheet.worksheets()]
    if COPY_SHEET_NAME not in existing:
        ws = spreadsheet.add_worksheet(COPY_SHEET_NAME, rows=500, cols=len(COPY_HEADERS))
        ws.append_row(COPY_HEADERS)
        ws.format("1:1", {"textFormat": {"bold": True}})
    return spreadsheet.worksheet(COPY_SHEET_NAME)


# ── 공개 API ──────────────────────────────────────────────────


def write_copies(article: dict, copies: list[dict], card_count: int) -> int:
    """
    5가지 카피를 시트에 기입
    반환: 첫 번째 카피가 기록된 행 번호 (1-based)
    """
    spreadsheet = _open_spreadsheet()
    ws = _ensure_copy_sheet(spreadsheet)

    now   = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = article.get("title", "")
    url   = article.get("url", "")

    rows = [
        [
            now,
            title,
            url,
            copy.get("angle", ""),
            copy.get("headline", ""),
            json.dumps(copy.get("slides", []), ensure_ascii=False),
            "대기중",
            "",
            card_count,
        ]
        for copy in copies
    ]

    all_values = ws.get_all_values()
    start_row  = len(all_values) + 1   # 헤더 포함 → 다음 빈 행

    ws.append_rows(rows)
    print(f"  ✏️  카피 {len(rows)}개를 시트 {start_row}행부터 기입했어요.")
    return start_row


def wait_for_approval(
    start_row: int,
    timeout_minutes: int = 60,
    poll_interval: int   = 30,
) -> dict | None:
    """
    승인된 카피를 폴링으로 감지
    반환: 승인된 카피 dict (angle/headline/slides/card_count/title/url) 또는 None
    """
    spreadsheet = _open_spreadsheet()
    ws = spreadsheet.worksheet(COPY_SHEET_NAME)

    end_time = time.time() + timeout_minutes * 60
    print(f"  ⏳ 승인 대기 중 (최대 {timeout_minutes}분, {poll_interval}초마다 확인)...")

    while time.time() < end_time:
        try:
            # 5개 앵글 행 읽기
            end_row  = start_row + 4
            raw_rows = ws.get(f"A{start_row}:I{end_row}")

            for i, row in enumerate(raw_rows):
                if len(row) < 7:
                    continue
                status = row[6].strip()
                if status in APPROVAL_VALUES:
                    # 승인 시각 기록
                    ws.update_cell(start_row + i, 8, datetime.now().strftime("%Y-%m-%d %H:%M"))

                    slides     = json.loads(row[5]) if len(row) > 5 and row[5] else []
                    card_count = int(row[8]) if len(row) > 8 and row[8].strip().isdigit() else len(slides)

                    print(f"  ✅ '{row[3]}' 앵글 승인 감지!")
                    return {
                        "angle":      row[3],
                        "headline":   row[4],
                        "slides":     slides,
                        "card_count": card_count,
                        "title":      row[1],
                        "url":        row[2],
                    }
        except Exception as e:
            print(f"  ⚠️  폴링 오류: {e}")

        time.sleep(poll_interval)

    print("  ⏰ 승인 대기 시간 초과.")
    return None


def get_candidate_articles() -> list[dict]:
    """카드뉴스후보 탭에서 제작 대기 중인 기사 목록 반환"""
    try:
        spreadsheet = _open_spreadsheet()
        ws          = spreadsheet.worksheet(CANDIDATE_SHEET)
    except gspread.WorksheetNotFound:
        print(f"  ⚠️  '{CANDIDATE_SHEET}' 탭을 찾을 수 없어요. 크롤러를 먼저 실행해주세요.")
        return []

    all_rows   = ws.get_all_records()
    candidates = []
    for i, row in enumerate(all_rows, start=2):   # 2: 헤더 다음 행부터
        status = str(row.get("제작여부", "")).strip()
        if status in ("☐ 대기중", "", "대기중"):
            candidates.append({
                "row":          i,
                "title":        row.get("제목", ""),
                "category":     row.get("카테고리", ""),
                "card_summary": row.get("카드뉴스 요약", ""),
                "url":          row.get("원문링크", ""),
                "source":       row.get("출처", ""),
                "collected_at": row.get("수집일", ""),
            })
    return candidates


def mark_article_in_progress(row: int):
    """카드뉴스후보 탭에서 해당 행을 '🔄 제작중'으로 표시"""
    _update_candidate_status(row, "🔄 제작중")


def mark_article_done(row: int):
    """카드뉴스후보 탭에서 해당 행을 '✅ 완료'로 표시"""
    _update_candidate_status(row, "✅ 완료")


def _update_candidate_status(row: int, status: str):
    try:
        spreadsheet = _open_spreadsheet()
        ws = spreadsheet.worksheet(CANDIDATE_SHEET)
        ws.update_cell(row, 8, status)   # H열: 제작여부
    except Exception as e:
        print(f"  ⚠️  상태 업데이트 오류: {e}")
