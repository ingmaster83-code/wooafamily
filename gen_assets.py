"""공유 미리보기(og:image)·파비콘 생성. 한 번 만들어 static/ 에 두고 커밋한다(빌드 때 매번 만들지 않음)."""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
FONT_B = "C:/Windows/Fonts/malgunbd.ttf"
FONT_R = "C:/Windows/Fonts/malgun.ttf"
GREEN = (16, 185, 129)
DARK = (17, 24, 39)
GRAY = (107, 114, 128)


def rounded(draw, box, r, fill):
    draw.rounded_rectangle(box, radius=r, fill=fill)


# 1) OG 이미지 1200x630
W, H = 1200, 630
img = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)
d.rectangle([0, 0, W, 14], fill=GREEN)
rounded(d, (90, 110, 210, 230), 30, GREEN)
d.text((150, 170), "우", font=ImageFont.truetype(FONT_B, 84), fill="white", anchor="mm")
d.text((235, 138), "우아패밀리", font=ImageFont.truetype(FONT_B, 62), fill=DARK)
d.text((237, 214), "우아하게 절약하자", font=ImageFont.truetype(FONT_R, 30), fill=GRAY)
d.text((90, 310), "알뜰폰 요금제 비교", font=ImageFont.truetype(FONT_B, 76), fill=DARK)
d.text((90, 408), "편의점·마트 1+1 행사, 개당 가격으로", font=ImageFont.truetype(FONT_B, 50), fill=GREEN)
d.text((90, 500), "통신비 절약 계산기 · 자급제폰 인기 순위 · 제휴카드 혜택", font=ImageFont.truetype(FONT_R, 34), fill=GRAY)
d.text((90, 566), "wooafamily.com", font=ImageFont.truetype(FONT_B, 30), fill=GREEN)
img.save(os.path.join(OUT, "og-default.png"), optimize=True)

# 2) 파비콘/앱 아이콘 (둥근 초록 사각형 + '우')
def icon(size):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    dd.rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * 0.24), fill=GREEN)
    dd.text((size / 2, size / 2 + size * 0.02), "우", font=ImageFont.truetype(FONT_B, int(size * 0.62)), fill="white", anchor="mm")
    return im

icon(180).convert("RGB").save(os.path.join(OUT, "apple-touch-icon.png"), optimize=True)
icon(512).save(os.path.join(OUT, "icon-512.png"), optimize=True)
icon(256).save(os.path.join(OUT, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
open(os.path.join(OUT, "favicon.svg"), "w", encoding="utf-8").write(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="15" fill="#10b981"/>'
    '<text x="32" y="45" text-anchor="middle" font-size="40" font-weight="800" fill="#fff" '
    'font-family="Pretendard,Malgun Gothic,Apple SD Gothic Neo,sans-serif">우</text></svg>')
print("생성:", sorted(os.listdir(OUT)))
