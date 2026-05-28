from PIL import Image, ImageDraw, ImageFont
import os
import textwrap

FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "generated")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _font(size, bold=False):
    try:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        return ImageFont.truetype(os.path.join(FONTS_DIR, name), size)
    except Exception:
        return ImageFont.load_default()


def _draw_rounded_rect(draw, xy, radius, fill, outline=None, width=2):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def generate_discount_image(product_name, old_price, new_price,
                             weight="", reason="Muddat yaqinlashdi",
                             shop_name="Do'kon",
                             output_name="discount.png"):
    W, H = 800, 600
    img = Image.new("RGB", (W, H), color="#FFF3E0")
    draw = ImageDraw.Draw(img)

    discount_pct = round((old_price - new_price) / old_price * 100)

    # Fon doiralar
    draw.ellipse([-60, -60, 180, 180], fill="#FFCC80")
    draw.ellipse([680, -40, 920, 200], fill="#FFCC80")

    # Do'kon nomi badge
    _draw_rounded_rect(draw, [30, 30, 260, 62], radius=16,
                        fill="#FFFFFF", outline="#FFB74D", width=2)
    shop_text = f"🏪 {shop_name}"
    draw.text((145, 46), shop_text, font=_font(14, bold=True),
              fill="#E65100", anchor="mm")

    # Chegirma % doira
    draw.ellipse([630, 20, 770, 160], fill="#F44336")
    draw.text((700, 80), f"-{discount_pct}%", font=_font(32, bold=True),
              fill="#FFFFFF", anchor="mm")
    draw.text((700, 118), "chegirma", font=_font(14),
              fill="#FFCDD2", anchor="mm")

    # Mahsulot nomi
    wrapped = textwrap.fill(product_name, width=28)
    draw.text((400, 210), wrapped, font=_font(28, bold=True),
              fill="#BF360C", anchor="mm", align="center")

    # Sabab badge
    _draw_rounded_rect(draw, [260, 250, 540, 286], radius=18, fill="#FF8A65")
    draw.text((400, 268), reason, font=_font(15),
              fill="#FFFFFF", anchor="mm")

    if weight:
        draw.text((400, 310), weight, font=_font(14),
                  fill="#8D6E63", anchor="mm")

    # Narx bloki
    _draw_rounded_rect(draw, [80, 330, 720, 460], radius=20,
                        fill=(255, 255, 255, 180))

    # Eski narx
    old_text = f"{old_price:,} so'm".replace(",", " ")
    draw.text((400, 375), old_text, font=_font(28),
              fill="#9E9E9E", anchor="mm")
    bbox = draw.textbbox((400, 375), old_text, font=_font(28), anchor="mm")
    mid_y = (bbox[1] + bbox[3]) // 2
    draw.line([bbox[0]-4, mid_y, bbox[2]+4, mid_y], fill="#F44336", width=3)

    # Chaqmoq
    draw.text((220, 430), "⚡", font=_font(32), fill="#FDD835", anchor="mm")
    draw.text((580, 430), "⚡", font=_font(32), fill="#FDD835", anchor="mm")

    # Yangi narx
    new_text = f"{new_price:,} so'm".replace(",", " ")
    draw.text((400, 430), new_text, font=_font(40, bold=True),
              fill="#D32F2F", anchor="mm")

    # Zo'r narx doira
    draw.ellipse([640, 460, 770, 590], fill="#D32F2F")
    draw.text((705, 518), "Zo'r", font=_font(18, bold=True),
              fill="#FFFFFF", anchor="mm")
    draw.text((705, 542), "narx!", font=_font(18, bold=True),
              fill="#FFFFFF", anchor="mm")

    draw.text((400, 500), "Day+ orqali yaratildi",
              font=_font(12), fill="#BCAAA4", anchor="mm")

    out_path = os.path.join(OUTPUT_DIR, output_name)
    img.save(out_path, "PNG")
    return out_path
