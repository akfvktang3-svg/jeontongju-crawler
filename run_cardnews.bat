@echo off
chcp 65001 > nul
echo ==========================================
echo  전통주 카드뉴스 자동화 에이전트
echo ==========================================

:: 패키지 설치 확인
pip show python-telegram-bot >nul 2>&1 || (
    echo 패키지 설치 중...
    pip install -r requirements_cardnews.txt
)

echo.
echo 텔레그램 봇을 시작합니다...
echo 종료하려면 Ctrl+C 를 누르세요.
echo.

python -X utf8 main.py
pause
