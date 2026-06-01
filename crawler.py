"""
전통주 크롤러 메인 실행 파일
사용법: python crawler.py
        python crawler.py --test-telegram (텔레그램 연결 테스트)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# -- 텔레그램 테스트 모드: 크롤링 없이 바로 실행 --
if "--test-telegram" in sys.argv:
    from crawler.telegram_sender import test_connection
    test_connection()
    sys.exit(0)

# -- 일반 실행 시에만 나머지 모듈 import --
from crawler import naver_crawler
from crawler import google_crawler
from crawler import classifier
from crawler import sheets_writer
from crawler import rss_collector
from crawler.deduplicator import remove_duplicates, print_dedup_report
from crawler.filter import filter_news
from crawler.evaluator import evaluate_articles, get_top_articles, THRESHOLD_SCORE
from crawler.telegram_sender import send_top_articles
import notion_writer  # 노션 저장 모듈 추가


def main():
    print("=" * 50)
    print("전통주 크롤러 시작")
    print("=" * 50)

    # Step 1: 수집
    naver_results = []
    google_results = []
    rss_results = []

    try:
        naver_results = naver_crawler.run()
    except Exception as e:
        print(f" WARNING: 네이버 수집 오류: {e}")

    try:
        google_results = google_crawler.run()
    except Exception as e:
        print(f" WARNING: 구글 수집 오류: {e}")

    try:
        rss_results = rss_collector.run()
    except Exception as e:
        print(f" WARNING: RSS 수집 오류: {e}")

    news_articles = naver_results + google_results + rss_results
    print(f"\n수집 완료: {len(news_articles)}건")
    print(f"  국내(네이버): {len(naver_results)}건")
    print(f"  국내(구글): {len(google_results)}건")
    print(f"  글로벌(RSS): {len(rss_results)}건")

    # Step 2: 필터링
    print("\n필터링 중...")
    filtered_news = filter_news(news_articles)
    print(f"  뉴스: {len(news_articles)}건 -> {len(filtered_news)}건")

    # Step 3: 중복 제거
    unique_articles, stats = remove_duplicates(filtered_news)
    print_dedup_report(stats)

    if not unique_articles:
        print("수집된 기사가 없어요.")
        return

    # Step 4: 분류
    classified = classifier.classify_articles(unique_articles)

    # Step 5: 평가
    evaluated = evaluate_articles(classified)
    top_articles = get_top_articles(evaluated, threshold=THRESHOLD_SCORE)
    print(f"\n카드뉴스 후보: {len(top_articles)}건 ({THRESHOLD_SCORE}점 이상)")

    # Step 6: 구글 시트 저장
    try:
        sheets_writer.save_to_sheets(evaluated)
        sheets_writer.save_selected_to_sheets(top_articles)
    except Exception as e:
        print(f" WARNING: 시트 저장 오류: {e}")

    # Step 7: 노션 DB 저장 (신규 추가)
    print("\n노션 DB 저장 중...")
    try:
        notion_writer.cleanup_old_articles()
        notion_writer.save_articles(top_articles)
    except Exception as e:
        print(f" WARNING: 노션 저장 오류: {e}")

    # Step 8: 텔레그램 발송
    send_top_articles(top_articles)

    # 완료 요약
    print("\n" + "=" * 50)
    print("크롤러 완료!")
    print("=" * 50)

    from collections import Counter
    counts = Counter(a.get("category", "기타") for a in evaluated)
    print("\n오늘 수집 요약:")
    for cat, count in counts.most_common():
        print(f"  {cat}: {count}건")

    print(f"\n카드뉴스 후보 TOP {len(top_articles)}:")
    for a in top_articles[:5]:
        print(f"  {a.get('score', 0)}점 | {a.get('title', '')[:35]}")


if __name__ == "__main__":
    main()
