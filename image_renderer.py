"""
Pillow 기반 카드뉴스 PNG 생성
커버(1장) + 본문(N장) + CTA(1장) 구조
"""

import os
from pathlib import Path
from datetime import datetime

import yaml
from PIL import Image, ImageDraw, ImageFont

CONFIG_PATH = Path(__file__).parent / "config.yaml"

# 윈도우 한글 폰트 우선순위
_WIN_BOLD_FONTS = [
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/NanumGothicBold.ttf",
    "C:/Windows/Fonts/gulim.ttc",
]
_WIN_BODY_FONTS = [
    "C:/Windows/Fonts/malgun.ttf",
    "C:/Windows/Fonts/NanumGothic.ttf",
    "C:/Windows/Fonts/gulim.ttc",
]


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_cards(approved_copy: dict, config: dict | None = None) -> list[Path]:
    """
    승인된 카피 dict를 받아 PNG 카드 리스트 생성
    반환: 저장된 Path 리스트
    """
    if config is None:
        config = load_config()

    brand    = config.get("brand", {})
    fonts_c  = config.get("fonts", {})
    card_c   = config.get("card", {})
    out_dir  = Path(config.get("output", {}).get("directory", "./output/cards"))
    out_dir.mkdir(parents=True, exist_ok=True)

    W   = card_c.get("width",   1080)
    H   = card_c.get("height",  1080)
    PAD = card_c.get("padding",   80)

    colors = {
        "primary":   tuple(brand.get("primary_color",   [101, 67,  33])),
        "secondary": tuple(brand.get("secondary_color", [255, 248, 220])),
        "accent":    tuple(brand.get("accent_color",    [184, 134,  11])),
        "text":      tuple(brand.get("text_color",      [ 30,  30,  30])),
        "white":     (255, 255, 255),
    }
    brand_name = brand.get("name", "전통주 인사이트")
    logo_path  = brand.get("logo_path", "")

    fnt_title = fonts_c.get("title", "")
    fnt_body  = fonts_c.get("body",  "")

    slides    = approved_copy.get("slides", [])
    angle     = approved_copy.get("angle", "unknown")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved     = []

    for slide in slides:
        snum  = slide.get("slide", len(saved) + 1)
        stype = slide.get("type", "content")

        img  = Image.new("RGB", (W, H), color=colors["secondary"])
        draw = ImageDraw.Draw(img)

        ctx = _DrawCtx(draw, img, W, H, PAD, colors, brand_name, logo_path, fnt_title, fnt_body, len(slides))

        if stype == "cover":
            _draw_cover(ctx, slide)
        elif stype == "cta":
            _draw_cta(ctx, slide)
        else:
            _draw_content(ctx, slide, snum)

        fname = out_dir / f"card_{timestamp}_{angle}_{snum:02d}.png"
        img.save(fname, "PNG")
        saved.append(fname)
        print(f"  🖼️  {fname.name} 저장")

    return saved


# ── 내부 구조체 ───────────────────────────────────────────────

class _DrawCtx:
    """렌더링 컨텍스트 - 설정값 묶음"""
    def __init__(self, draw, img, W, H, PAD, colors, brand_name, logo_path, fnt_title, fnt_body, total_slides):
        self.draw         = draw
        self.img          = img
        self.W            = W
        self.H            = H
        self.PAD          = PAD
        self.colors       = colors
        self.brand_name   = brand_name
        self.logo_path    = logo_path
        self.fnt_title    = fnt_title
        self.fnt_body     = fnt_body
        self.total_slides = total_slides


# ── 슬라이드 렌더러 ───────────────────────────────────────────

def _draw_cover(ctx: _DrawCtx, slide: dict):
    d, img, W, H, PAD = ctx.draw, ctx.img, ctx.W, ctx.H, ctx.PAD
    c = ctx.colors

    # 배경: 브랜드 원색
    d.rectangle([0, 0, W, H], fill=c["primary"])

    # 테두리 장식
    d.rectangle([PAD // 2, PAD // 2, W - PAD // 2, H - PAD // 2], outline=c["accent"], width=5)
    d.rectangle([PAD, PAD, W - PAD, PAD + 8], fill=c["accent"])

    # 브랜드명
    f_brand = _font(ctx.fnt_body, 32, bold=False)
    d.text((PAD + 10, PAD + 24), f"🍶 {ctx.brand_name}", font=f_brand, fill=c["accent"])

    # 메인 헤드라인
    title = slide.get("title", "")
    f_title = _font(ctx.fnt_title, 76, bold=True)
    _wrapped_text(d, title, f_title, c["white"], PAD, H // 3, W - PAD * 2, line_spacing=16)

    # 서브타이틀
    subtitle = slide.get("subtitle", "")
    f_sub = _font(ctx.fnt_body, 42, bold=False)
    _wrapped_text(d, subtitle, f_sub, c["secondary"], PAD, H // 3 + 230, W - PAD * 2, line_spacing=12)

    # 하단 바
    d.rectangle([0, H - 80, W, H], fill=c["accent"])
    f_page = _font(ctx.fnt_body, 28, bold=False)
    d.text((PAD, H - 56), "1", font=f_page, fill=c["primary"])


def _draw_content(ctx: _DrawCtx, slide: dict, page_num: int):
    d, W, H, PAD = ctx.draw, ctx.W, ctx.H, ctx.PAD
    c = ctx.colors

    # 상단 강조 바 (이중)
    d.rectangle([0, 0, W, 14], fill=c["primary"])
    d.rectangle([0, 14, W, 26], fill=c["accent"])

    # 소제목
    stitle = slide.get("title", "")
    f_sub  = _font(ctx.fnt_title, 54, bold=True)
    _wrapped_text(d, stitle, f_sub, c["primary"], PAD, 70, W - PAD * 2, line_spacing=10)

    # 구분선
    d.rectangle([PAD, 260, W - PAD, 266], fill=c["accent"])

    # 본문
    body   = slide.get("body", "")
    f_body = _font(ctx.fnt_body, 46, bold=False)
    _wrapped_text(d, body, f_body, c["text"], PAD, 296, W - PAD * 2, line_spacing=14)

    # 하단 바
    d.rectangle([0, H - 80, W, H], fill=c["primary"])
    f_page = _font(ctx.fnt_body, 30, bold=False)
    d.text((PAD, H - 55), f"🍶 {ctx.brand_name}", font=f_page, fill=c["accent"])
    page_text = f"{page_num} / {ctx.total_slides}"
    bbox = d.textbbox((0, 0), page_text, font=f_page)
    d.text((W - PAD - (bbox[2] - bbox[0]), H - 55), page_text, font=f_page, fill=c["secondary"])


def _draw_cta(ctx: _DrawCtx, slide: dict):
    d, img, W, H, PAD = ctx.draw, ctx.img, ctx.W, ctx.H, ctx.PAD
    c = ctx.colors

    # 배경: 브랜드 원색
    d.rectangle([0, 0, W, H], fill=c["primary"])

    # 장식
    d.rectangle([PAD // 2, PAD // 2, W - PAD // 2, H - PAD // 2], outline=c["accent"], width=4)
    d.rectangle([PAD, H // 2 - 4, W - PAD, H // 2 + 4], fill=c["accent"])

    # 행동 촉구 문구
    action  = slide.get("action", "")
    f_cta   = _font(ctx.fnt_title, 66, bold=True)
    _wrapped_text(d, action, f_cta, c["white"], PAD, H // 4, W - PAD * 2, line_spacing=14)

    # 해시태그
    hashtags = slide.get("hashtags", [])
    tags_text = "  ".join(hashtags)
    f_tags = _font(ctx.fnt_body, 36, bold=False)
    _wrapped_text(d, tags_text, f_tags, c["accent"], PAD, H // 2 + 30, W - PAD * 2, line_spacing=10)

    # 브랜드명
    f_brand = _font(ctx.fnt_body, 36, bold=False)
    d.text((PAD, H - 120), f"🍶 {ctx.brand_name}", font=f_brand, fill=c["secondary"])


# ── 유틸리티 ──────────────────────────────────────────────────

def _font(path: str, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """폰트 로드 (없으면 시스템 폰트 → 기본 폰트 순 폴백)"""
    candidates = [path] if path else []
    candidates += (_WIN_BOLD_FONTS if bold else _WIN_BODY_FONTS)

    for fp in candidates:
        if fp and os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrapped_text(
    draw:         ImageDraw.ImageDraw,
    text:         str,
    font:         ImageFont.FreeTypeFont,
    color:        tuple,
    x:            int,
    y:            int,
    max_width:    int,
    line_spacing: int = 10,
) -> int:
    """자동 줄바꿈 텍스트 그리기. 마지막 y 위치 반환"""
    if not text:
        return y

    # 공백 기준 분리 (한글도 공백 있으면 단어 단위, 없으면 글자 단위 폴백)
    segments = text.split(" ") if " " in text else list(text)
    lines: list[str] = []
    current = ""

    for seg in segments:
        sep   = " " if " " in text else ""
        trial = (current + sep + seg).strip()
        bbox  = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] > max_width and current:
            lines.append(current)
            current = seg
        else:
            current = trial
    if current:
        lines.append(current)

    # 줄 높이 계산
    sample_bbox = draw.textbbox((0, 0), "가나다", font=font)
    line_h = (sample_bbox[3] - sample_bbox[1]) + line_spacing

    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        y += line_h

    return y
