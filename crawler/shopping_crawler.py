"""
전통주 신제품 크롤러
세 곳에서 신제품을 수집합니다:
  1. 네이버 쇼핑 (최신순)
  2. 술마켓 (soolmarket.com)
  3. 술담화 (sooldamhwa.com)
"""

import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID     = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# 주종 분류 키워드
JUJEONG_MAP = {
    "막걸리": ["막걸리", "탁주", "동동주", "동동", "누룩"],
    "약주":   ["약주", "법주", "소곡주", "백세주", "청명주", "한산"],
    "과실주": ["과실주", "복분자", "매실주", "산사춘", "오미자", "포도주", "블루베리", "딸기주", "체리"],
    "증류주": ["소주", "증류", "안동소주", "문배주", "이강주", "진도홍주", "화요", "일품진로", "감홍로"],
}

# 반드시 전통주여야 함 (이게 없으면 제외)
REQUIRED_KEYWORDS = [
    "막걸리", "전통주", "약주", "청주", "탁주", "동동주",
    "전통소주", "우리술", "과실주", "민속주", "복분자주",
    "매실주", "소곡주", "법주", "안동소주", "문배주",
    "이강주", "진도홍주", "감홍로", "화요",
]

# 제외 키워드
EXCLUDE_KEYWORDS = [
    "잔", "컵", "보자기", "포장지", "박스",
    "안주", "오징어", "육포", "책", "도서",
    "인형", "굿즈", "향수", "캔들",
]


# ── 1. 네이버 쇼핑 ─────────────────────────────────────────────

def fetch_naver_shopping(display: int = 20) -> list[dict]:
    """네이버 쇼핑 최신 전통주 상품 수집"""
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id":     NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query":   "전통주",
        "display": display,
        "sort":    "date",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        items = response.json().get("items", [])

        results = []
        for item in items:
            name  = _clean(item.get("title", ""))
            brand = item.get("brand", "") or item.get("maker", "") or "-"
            price = _format_price(item.get("lprice", "0"))
            link  = item.get("link", "")
            image = item.get("image", "")

            if not _is_valid_product(name):
                continue

            results.append(_make_product(
                name=name, brand=brand, price=price,
                link=link, image=image, source="네이버쇼핑"
            ))
        return results

    except Exception as e:
        print(f"  ⚠️  네이버 쇼핑 오류: {e}")
        return []


# ── 2. 술마켓 ──────────────────────────────────────────────────

def fetch_soolmarket(pages: int = 2) -> list[dict]:
    """술마켓 신상품 페이지 크롤링"""
    results = []
    base_url = "https://www.soolmarket.com/goods/goods_list.php"

    for page in range(1, pages + 1):
        try:
            params = {
                "cateCd":  "026",
                "sort":    "date",
                "pageNum": 10,
                "page":    page,
            }
            response = requests.get(base_url, params=params,
                                    headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # 상품 카드 파싱
            items = soup.select(".goods_list_item, .item_cont, li.item")
            if not items:
                items = soup.select("ul.goods_list li")

            for item in items:
                name_tag  = item.select_one(".goods_name, .item_name, a.name")
                price_tag = item.select_one(".goods_price, .item_price, .price")
                link_tag  = item.select_one("a[href]")
                img_tag   = item.select_one("img")

                if not name_tag:
                    continue

                name  = name_tag.get_text(strip=True)
                price = price_tag.get_text(strip=True) if price_tag else "-"
                price = re.sub(r"[^\d,]", "", price) or "-"
                link  = "https://www.soolmarket.com" + link_tag["href"] if link_tag else ""
                image = img_tag.get("src", "") if img_tag else ""

                if not _is_valid_product(name):
                    continue

                results.append(_make_product(
                    name=name, brand="-", price=price,
                    link=link, image=image, source="술마켓"
                ))

        except Exception as e:
            print(f"  ⚠️  술마켓 오류 (page {page}): {e}")

    return results


# ── 3. 술담화 ──────────────────────────────────────────────────

def fetch_sooldamhwa() -> list[dict]:
    """술담화 신상품 페이지 크롤링"""
    url = "https://www.sooldamhwa.com/damhwaMarket/listing/new"
    results = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # 상품 카드 파싱 (술담화 구조)
        items = soup.select(".product-item, .item_wrap, .goods-item, li.product")
        if not items:
            items = soup.select("ul.product-list li, .product_list li")

        for item in items:
            name_tag  = item.select_one(".product-name, .goods_name, .name, h3, h4")
            price_tag = item.select_one(".product-price, .price, .goods_price")
            link_tag  = item.select_one("a[href]")
            img_tag   = item.select_one("img")

            if not name_tag:
                continue

            name  = name_tag.get_text(strip=True)
            price = price_tag.get_text(strip=True) if price_tag else "-"
            price = re.sub(r"[^\d,]", "", price) or "-"

            href  = link_tag["href"] if link_tag else ""
            link  = href if href.startswith("http") else "https://www.sooldamhwa.com" + href
            image = img_tag.get("src", "") if img_tag else ""

            if not _is_valid_product(name):
                continue

            results.append(_make_product(
                name=name, brand="-", price=price,
                link=link, image=image, source="술담화"
            ))

    except Exception as e:
        print(f"  ⚠️  술담화 오류: {e}")

    return results


# ── 메인 실행 ──────────────────────────────────────────────────

def run() -> list[dict]:
    """세 곳에서 신제품 수집"""
    print("\n🛒 전통주 신제품 수집 중...")

    naver    = fetch_naver_shopping()
    soolmkt  = fetch_soolmarket()
    sooldamhwa = fetch_sooldamhwa()

    print(f"  ✅ 네이버쇼핑: {len(naver)}건")
    print(f"  ✅ 술마켓:     {len(soolmkt)}건")
    print(f"  ✅ 술담화:     {len(sooldamhwa)}건")

    all_items = naver + soolmkt + sooldamhwa
    unique    = _dedup_products(all_items)

    print(f"\n  🍶 신제품 총 수집: {len(unique)}건 (중복 제거 후)")
    return unique


# ── 공통 유틸 ──────────────────────────────────────────────────

def _make_product(name, brand, price, link, image, source) -> dict:
    """상품 딕셔너리 생성"""
    jujeong = _classify_jujeong(name)
    return {
        "title":            name,
        "summary":          f"브랜드: {brand} | 가격: {price}원 | 주종: {jujeong}",
        "brand":            brand,
        "price":            price,
        "product_category": jujeong,
        "image_url":        image,
        "url":              link,
        "source":           source,
        "keyword":          "신제품",
        "category":         "신제품 출시",
        "recommend":        "상",
        "reason":           f"{source} 신상품",
        "one_line":         f"[{jujeong}] {name[:25]}",
        "collected_at":     datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def _classify_jujeong(name: str) -> str:
    """주종 분류: 막걸리 / 약주 / 과실주 / 증류주 / 기타"""
    for jujeong, keywords in JUJEONG_MAP.items():
        if any(kw in name for kw in keywords):
            return jujeong
    return "기타"


def _is_valid_product(name: str) -> bool:
    """유효한 전통주 상품인지 확인"""
    if any(kw in name for kw in EXCLUDE_KEYWORDS):
        return False
    return any(kw in name for kw in REQUIRED_KEYWORDS)


def _format_price(price: str) -> str:
    try:
        return f"{int(price):,}"
    except (ValueError, TypeError):
        return price


def _clean(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _dedup_products(items: list[dict]) -> list[dict]:
    """상품명 기준 중복 제거"""
    seen = set()
    result = []
    for item in items:
        key = item.get("title", "")[:20].lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result
