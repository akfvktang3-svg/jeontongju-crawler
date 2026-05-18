"""
글로벌 주류 인텔리전스 크롤러
- RSS 피드에서 위스키/와인/스피릿 뉴스 수집
- Claude API로 필터링 및 점수 평가
- 텔레그램으로 결과 발송
- 2일마다 오후 6시(KST) 자동 실행
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if "--test-telegram" in sys.argv:
    from global_modules.global_telegram import test_connection
    test_connection()
    sys.exit(0)

from global_modules.global_rss import run as rss_run
from global_modules.global_filter import filter_articles
from global_modules.global_evaluator import evaluate_articles, get_top_articles, THRESHOLD_SCORE
from global_modules.global_telegram import send_top_articles
from global_modules.global_sheets import save_to_sheets


def main():
    print("=" * 50)
    print("글로벌 주류 크롤러 시작")
    print("=" * 50)

    # Step 1: RSS 수집
    articles = []
    try:
        articles = rss_run()
    except Exception as e:
        print(f"  WARNING: RSS 수집 오류: {e}")

    if not articles:
        print("수집된 기사가 없어요.")
        return

    print(f"\n수집 완료: {len(articles)}건")

    # Step 2: Claude 필터링
    filtered = filter_articles(articles)
    print(f"필터링 완료: {len(filtered)}건")

    if not filtered:
        print("필터링 후 기사가 없어요.")
        return

    # Step 3: 점수 평가
    evaluated = evaluate_articles(filtered)
    top_articles = get_top_articles(evaluated, threshold=THRESHOLD_SCORE)
    print(f"\n카드뉴스 후보: {len(top_articles)}건 ({THRESHOLD_SCORE}점 이상)")

    # Step 4: 구글 시트 저장
    try:
        save_to_sheets(evaluated)
    except Exception as e:
        print(f"  WARNING: 시트 저장 오류: {e}")

    # Step 5: 텔레그램 발송
    send_top_articles(top_articles)

    # 완료 요약
    print("\n" + "=" * 50)
    print("글로벌 크롤러 완료!")
    print("=" * 50)

    from collections import Counter
    counts = Counter(a.get("category", "기타") for a in evaluated)
    print("\n오늘 수집 요약:")
    for cat, count in counts.most_common():
        print(f"  {cat}: {count}건")

    print(f"\n카드뉴스 후보 TOP {len(top_articles)}:")
    for a in top_articles[:5]:
        print(f"  {a.get('score', 0)}점 | {a.get('title', '')[:40]}")


if __name__ == "__main__":
    main()
