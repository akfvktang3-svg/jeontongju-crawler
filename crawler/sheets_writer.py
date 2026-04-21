"""
구글 시트 저장기
분류된 뉴스를 구글 시트에 자동으로 기록합니다.
탭 구성: 전체수집함 / 카테고리현황 / 카드뉴스후보 / 쇼핑신제품 / 카드뉴스선정
"""

import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID   = os.getenv("SPREADSHEET_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./google_credentials.json")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CATEGORY_EMOJI = {
    "신제품 출시":   "🆕",
    "행사 소식":     "🎪",
    "주류 트렌드":   "📈",
    "브랜드 이야기": "🏷️",
    "기타":          "📌",
}

# 카테고리별 전용 탭 이름
CATEGORY_SHEET_NAMES = {
    "신제품 출시":   "🆕 신제품출시",
    "행사 소식":     "🎪 행사소식",
    "주류 트렌드":   "📈 주류트렌드",
    "브랜드 이야기": "🏷️ 브랜드이야기",
    "기타":          "📌 기타",
}


def get_sheet_client():
    """구글 시트 클라이언트 연결"""
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def setup_sheets(client) -> dict:
    """시트 탭 초기 설정 (없으면 생성)"""
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    existing = [ws.title for ws in spreadsheet.worksheets()]
    sheets = {}

    # 탭 1: 전체 수집함
    if "📥 전체수집함" not in existing:
        ws = spreadsheet.add_worksheet("📥 전체수집함", rows=1000, cols=12)
        ws.append_row([
            "수집일시", "제목", "카드뉴스 요약", "카테고리",
            "총점", "시의성", "대중성", "적합성", "연관성",
            "태그", "출처", "원문링크"
        ])
        _format_header(ws)
        print("  ✅ '전체수집함' 탭 생성")
    else:
        ws = spreadsheet.worksheet("📥 전체수집함")
    sheets["전체"] = ws

    # 탭 2: 카테고리별 현황 (하이퍼링크 포함)
    if "🗂️ 카테고리현황" not in existing:
        ws = spreadsheet.add_worksheet("🗂️ 카테고리현황", rows=100, cols=5)
        ws.append_row(["카테고리", "총 수집건수", "이번 실행 수집", "최근 업데이트", "바로가기"])
        _format_header(ws)
        for cat in ["신제품 출시", "행사 소식", "주류 트렌드", "브랜드 이야기", "기타"]:
            emoji = CATEGORY_EMOJI.get(cat, "")
            sheet_name = CATEGORY_SHEET_NAMES.get(cat, cat)
            ws.append_row([f"{emoji} {cat}", 0, 0, "-", f"→ {sheet_name} 탭 확인"])
        print("  ✅ '카테고리현황' 탭 생성")
    else:
        ws = spreadsheet.worksheet("🗂️ 카테고리현황")
    sheets["카테고리"] = ws

    # 탭 3: 카드뉴스 후보
    if "⭐ 카드뉴스후보" not in existing:
        ws = spreadsheet.add_worksheet("⭐ 카드뉴스후보", rows=200, cols=8)
        ws.append_row(["추천도", "카테고리", "제목", "카드뉴스 요약", "출처", "수집일", "원문링크", "제작여부"])
        _format_header(ws)
        print("  ✅ '카드뉴스후보' 탭 생성")
    else:
        ws = spreadsheet.worksheet("⭐ 카드뉴스후보")
    sheets["후보"] = ws

    # 탭 4: 쇼핑 신제품
    if "🛒 쇼핑신제품" not in existing:
        ws = spreadsheet.add_worksheet("🛒 쇼핑신제품", rows=500, cols=10)
        ws.append_row(["수집일시", "상품명", "브랜드", "주종", "가격", "출처", "상품링크", "이미지링크"])
        _format_header(ws)
        print("  ✅ '쇼핑신제품' 탭 생성")
    else:
        ws = spreadsheet.worksheet("🛒 쇼핑신제품")
    sheets["쇼핑"] = ws

    # 탭 5: 카드뉴스 선정 (제2저장소 - 60점 이상)
    if "🎯 카드뉴스선정" not in existing:
        ws = spreadsheet.add_worksheet("🎯 카드뉴스선정", rows=200, cols=12)
        ws.append_row([
            "수집일시", "제목", "카드뉴스 요약", "카테고리",
            "총점", "시의성", "대중성", "적합성", "연관성",
            "태그", "출처", "원문링크"
        ])
        _format_header(ws)
        print("  ✅ '카드뉴스선정' 탭 생성")
    else:
        ws = spreadsheet.worksheet("🎯 카드뉴스선정")
    sheets["선정"] = ws

    # 탭 6~10: 카테고리별 전용 탭 (기타 포함 5개)
    for cat, tab_name in CATEGORY_SHEET_NAMES.items():
        if tab_name not in existing:
            ws = spreadsheet.add_worksheet(tab_name, rows=500, cols=12)
            ws.append_row([
                "수집일시", "제목", "카드뉴스 요약",
                "총점", "시의성", "대중성", "적합성", "연관성",
                "태그", "출처", "원문링크"
            ])
            _format_header(ws)
            print(f"  ✅ '{tab_name}' 탭 생성")
        else:
            ws = spreadsheet.worksheet(tab_name)
        sheets[cat] = ws

    return sheets


def save_to_sheets(articles: list):
    """분류된 기사들을 전체수집함 + 카테고리별 탭에 저장"""
    print("\n📊 구글 시트에 저장 중...")
    try:
        client = get_sheet_client()
        sheets = setup_sheets(client)

        # 전체수집함 중복 체크
        existing_urls = _get_existing_urls_col(sheets["전체"], col=12)
        new_articles = [a for a in articles if a.get("url") not in existing_urls]
        print(f"  📌 신규 기사: {len(new_articles)}건 (중복 제외)")

        if not new_articles:
            print("  ℹ️  새로운 기사가 없어요.")
            return

        # 1. 전체수집함에 저장 (기타 포함 모든 기사)
        _save_to_main_sheet(sheets["전체"], new_articles)

        # 2. 카테고리별 탭에 저장 (기타 포함)
        _save_to_category_sheets(sheets, new_articles)

        # 3. 카테고리 현황 업데이트
        _update_category_sheet(sheets["카테고리"], new_articles)

        # 4. 카드뉴스 후보 탭 (추천도 '상'인 것)
        top_articles = [a for a in new_articles if a.get("recommend") == "상"]
        if top_articles:
            _save_to_candidate_sheet(sheets["후보"], top_articles)
            print(f"  ⭐ 카드뉴스 후보 {len(top_articles)}건 추가")

        print("  ✅ 구글 시트 저장 완료!")

    except Exception as e:
        print(f"  ❌ 구글 시트 저장 오류: {e}")
        raise


def save_selected_to_sheets(articles: list):
    """평가 통과 기사를 제2저장소(카드뉴스선정 탭)에 저장"""
    if not articles:
        return

    print("\n🎯 카드뉴스 선정 기사 저장 중...")
    try:
        client = get_sheet_client()
        sheets = setup_sheets(client)
        ws = sheets["선정"]

        existing_urls = _get_existing_urls_col(ws, col=12)
        new_items = [a for a in articles if a.get("url") not in existing_urls]

        if not new_items:
            print("  ℹ️  새로운 선정 기사가 없어요.")
            return

        rows = []
        for a in new_items:
            emoji = CATEGORY_EMOJI.get(a.get("category", "기타"), "📌")
            tags  = " ".join(a.get("tags", []))
            rows.append([
                a.get("collected_at", ""),
                a.get("title", ""),
                a.get("card_summary", ""),
                f"{emoji} {a.get('category', '기타')}",
                a.get("score", 0),
                a.get("score_timeliness", 0),
                a.get("score_popularity", 0),
                a.get("score_card_fit", 0),
                a.get("score_relevance", 0),
                tags,
                a.get("source", ""),
                a.get("url", ""),
            ])
        ws.append_rows(rows)
        print(f"  💾 카드뉴스 선정: {len(rows)}건 추가")

    except Exception as e:
        print(f"  ❌ 선정 저장 오류: {e}")


def save_shopping_to_sheets(items: list):
    """쇼핑 신제품을 별도 탭에 저장"""
    if not items:
        return

    print("\n🛒 쇼핑 신제품 시트 저장 중...")
    try:
        client = get_sheet_client()
        sheets = setup_sheets(client)
        ws = sheets["쇼핑"]

        existing_urls = _get_existing_urls_col(ws, col=7)
        new_items = [i for i in items if i.get("url") not in existing_urls]

        if not new_items:
            print("  ℹ️  새로운 쇼핑 상품이 없어요.")
            return

        rows = []
        for item in new_items:
            price = item.get("price", "-")
            price_str = price + "원" if price and price != "-" else "-"
            rows.append([
                item.get("collected_at", ""),
                item.get("title", ""),
                item.get("brand", "-"),
                item.get("product_category", "기타"),
                price_str,
                item.get("source", ""),
                item.get("url", ""),
                item.get("image_url", ""),
            ])
        ws.append_rows(rows)
        print(f"  💾 쇼핑 신제품 {len(rows)}건 추가")

    except Exception as e:
        print(f"  ❌ 쇼핑 시트 저장 오류: {e}")


# ── 내부 함수 ─────────────────────────────────────────────────

def _save_to_main_sheet(ws, articles: list):
    """전체 수집함에 모든 기사 저장 (기타 포함)"""
    rows = []
    for a in articles:
        emoji = CATEGORY_EMOJI.get(a.get("category", "기타"), "📌")
        tags  = " ".join(a.get("tags", []))
        rows.append([
            a.get("collected_at", ""),
            a.get("title", ""),
            a.get("card_summary", a.get("one_line", "")),
            f"{emoji} {a.get('category', '기타')}",
            a.get("score", 0),
            a.get("score_timeliness", 0),
            a.get("score_popularity", 0),
            a.get("score_card_fit", 0),
            a.get("score_relevance", 0),
            tags,
            a.get("source", ""),
            a.get("url", ""),
        ])
    ws.append_rows(rows)
    print(f"  💾 전체수집함: {len(rows)}건 추가")


def _save_to_category_sheets(sheets: dict, articles: list):
    """카테고리별 전용 탭에 저장 (기타 포함)"""
    from collections import defaultdict
    grouped = defaultdict(list)
    for a in articles:
        cat = a.get("category", "기타")
        if cat not in CATEGORY_SHEET_NAMES:
            cat = "기타"
        grouped[cat].append(a)

    for cat, cat_articles in grouped.items():
        ws = sheets.get(cat)
        if not ws:
            continue
        rows = []
        for a in cat_articles:
            tags = " ".join(a.get("tags", []))
            rows.append([
                a.get("collected_at", ""),
                a.get("title", ""),
                a.get("card_summary", a.get("one_line", "")),
                a.get("score", 0),
                a.get("score_timeliness", 0),
                a.get("score_popularity", 0),
                a.get("score_card_fit", 0),
                a.get("score_relevance", 0),
                tags,
                a.get("source", ""),
                a.get("url", ""),
            ])
        if rows:
            ws.append_rows(rows)
            print(f"  💾 {CATEGORY_SHEET_NAMES[cat]}: {len(rows)}건 추가")


def _update_category_sheet(ws, articles: list):
    """카테고리 현황 탭 업데이트"""
    from collections import Counter
    counts = Counter(a.get("category", "기타") for a in articles)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    categories = ["신제품 출시", "행사 소식", "주류 트렌드", "브랜드 이야기", "기타"]
    for i, cat in enumerate(categories, start=2):
        row = ws.row_values(i)
        prev_total = int(row[1]) if len(row) > 1 and str(row[1]).isdigit() else 0
        new_count  = counts.get(cat, 0)
        ws.update(f"B{i}:D{i}", [[prev_total + new_count, new_count, now]])


def _save_to_candidate_sheet(ws, articles: list):
    """카드뉴스 후보 탭에 저장"""
    rows = []
    for a in articles:
        emoji = CATEGORY_EMOJI.get(a.get("category", "기타"), "📌")
        rows.append([
            "⭐ 상",
            f"{emoji} {a.get('category', '기타')}",
            a.get("title", ""),
            a.get("card_summary", a.get("one_line", "")),
            a.get("source", ""),
            a.get("collected_at", ""),
            a.get("url", ""),
            "☐ 대기중",
        ])
    ws.append_rows(rows)


def _get_existing_urls_col(ws, col: int = 8) -> set:
    """지정 열에서 URL 목록 가져오기 (중복 방지)"""
    try:
        all_values = ws.col_values(col)
        return set(all_values[1:])
    except Exception:
        return set()


def _format_header(ws):
    """헤더 행 굵게 설정"""
    try:
        ws.format("1:1", {"textFormat": {"bold": True}})
    except Exception:
        pass
