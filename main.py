"""
전통주 카드뉴스 자동화 에이전트 실행 진입점

사용법:
  python main.py             # 텔레그램 봇 시작
  python main.py --test      # 구글 시트 연결 + 카피 생성 테스트
  python main.py --render    # 시트 승인 없이 샘플 카드 렌더링 테스트
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 윈도우 콘솔 UTF-8 출력 강제 설정
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _test_mode():
    """연결 테스트: 시트 후보 조회 + Claude 카피 1개 생성"""
    print("\n🧪 테스트 모드")
    print("─" * 40)

    import sheet_writer
    print("📊 구글 시트 후보 조회 중...")
    articles = sheet_writer.get_candidate_articles()
    print(f"  → 후보 {len(articles)}건")

    if not articles:
        print("  ⚠️  후보 없음. 크롤러를 먼저 실행하세요: python crawler.py")
        return

    article = articles[0]
    print(f"  → 첫 번째 기사: {article['title'][:50]}")

    import copy_agent
    print("\n🤖 Claude 카피 생성 중 (1~30초)...")
    copies, card_count = copy_agent.generate_copies(article)
    print(f"  → {card_count}장 기준, {len(copies)}개 앵글 생성 완료")
    for c in copies:
        print(f"     [{c['angle']}] {c['headline']}")

    print("\n✅ 테스트 통과!")


def _render_mode():
    """렌더링 테스트: 샘플 카피로 PNG 생성"""
    print("\n🎨 렌더링 테스트 모드")
    print("─" * 40)

    import image_renderer

    sample_copy = {
        "angle":    "Problem",
        "headline": "전통주, 이렇게 마시면 안 됩니다",
        "title":    "테스트 기사",
        "url":      "https://example.com",
        "slides": [
            {
                "slide":    1,
                "type":     "cover",
                "title":    "전통주, 이렇게 마시면 안 됩니다",
                "subtitle": "당신이 몰랐던 전통주의 진짜 이야기",
            },
            {
                "slide": 2,
                "type":  "content",
                "title": "문제는 여기서 시작됩니다",
                "body":  "많은 사람들이 전통주를 막걸리로만 알고 있습니다. 하지만 전통주의 세계는 훨씬 더 넓습니다.",
            },
            {
                "slide": 3,
                "type":  "content",
                "title": "진짜 전통주를 만나다",
                "body":  "청주, 약주, 소주, 과실주… 각 지역의 고유한 맛과 향이 담긴 전통주가 여러분을 기다립니다.",
            },
            {
                "slide": 4,
                "type":  "content",
                "title": "MZ세대가 선택한 이유",
                "body":  "자연 발효, 전통 기법, 스토리가 있는 한 병. 지금 가장 힙한 술이 전통주입니다.",
            },
            {
                "slide":    5,
                "type":     "cta",
                "action":   "지금 바로 전통주를 경험하세요!",
                "hashtags": ["#전통주", "#우리술", "#전통주입문", "#MZ전통주", "#한국술문화"],
            },
        ],
    }

    config = image_renderer.load_config()
    paths  = image_renderer.render_cards(sample_copy, config)
    print(f"\n✅ {len(paths)}장 생성 완료:")
    for p in paths:
        print(f"   {p}")


def main():
    print("=" * 50)
    print("🍶 전통주 카드뉴스 자동화 에이전트")
    print("=" * 50)

    if "--test" in sys.argv:
        _test_mode()
    elif "--render" in sys.argv:
        _render_mode()
    else:
        print("\n텔레그램에서 /목록 명령으로 뉴스를 선택하세요.")
        print("구글 시트에서 카피를 승인하면 PNG가 자동 발송됩니다.\n")
        from telegram_bot import run_bot
        run_bot()


if __name__ == "__main__":
    main()
