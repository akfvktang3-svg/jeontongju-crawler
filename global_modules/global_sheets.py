"""
글로벌 주류 구글 시트 저장기
"""

import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_client():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON 없음")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def save_to_sheets(articles: list[dict]):
    if not articles:
        return

    print("\n구글 시트 저장 중...")
    try:
        gc = _get_client()
        sh = gc.open_by_key(SPREADSHEET_ID)

        try:
            ws = sh.worksheet("글로벌주류수집함")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet("글로벌주류수집함", rows=1000, cols=15)
            ws.append_row([
                "수집일시", "제목", "요약", "카테고리", "출처",
                "점수", "시의성", "대중성", "콘텐츠화", "산업가치", "SNS화제성",
                "태그", "카드요약", "URL"
            ])

        existing = ws.col_values(2)[1:]
        new_rows = []
        for a in articles:
            if a.get("title", "") in existing:
                continue
            new_rows.append([
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                a.get("title", ""),
                a.get("summary", "")[:200],
                a.get("category", "기타"),
                a.get("source", ""),
                a.get("score", 0),
                a.get("score_timeliness", 0),
                a.get("score_popularity", 0),
                a.get("score_content", 0),
                a.get("score_industry", 0),
                a.get("score_sns", 0),
                " ".join(a.get("tags", [])),
                a.get("card_summary", ""),
                a.get("url", ""),
            ])

        if new_rows:
            ws.append_rows(new_rows)
            print(f"  글로벌주류수집함: {len(new_rows)}건 추가")
        else:
            print("  새로운 기사 없음")

    except Exception as e:
        print(f"  ERROR: 시트 저장 실패: {e}")
