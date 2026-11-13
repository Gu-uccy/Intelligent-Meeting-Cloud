from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def u(text):
    return text.encode("ascii").decode("unicode_escape")


SRC = Path(
    r"C:\Users\Guche\Documents\Tencent Files\1917016796\nt_qq\nt_data\Pic\2026-06\Thumb\54ec25a728553845e27f408d1b3cae4c_720.jpg"
)
OUT_DIR = Path(r"D:\Project\Intelligent-Meeting-Cloud\video_assets")
OUT = OUT_DIR / "raspberry_pi_annotated_cn.jpg"
FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"


def draw_label(draw, text, anchor, target, font, color, side="right"):
    x, y = anchor
    tx, ty = target
    padding_x, padding_y = 14, 9
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=4)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    box = [x, y, x + text_w + padding_x * 2, y + text_h + padding_y * 2]
    shadow = [box[0] + 3, box[1] + 3, box[2] + 3, box[3] + 3]

    draw.rounded_rectangle(shadow, radius=12, fill=(0, 0, 0, 120))
    draw.rounded_rectangle(box, radius=12, fill=(12, 18, 28, 232), outline=color, width=3)
    draw.multiline_text(
        (x + padding_x, y + padding_y - 1),
        text,
        font=font,
        fill=(255, 255, 255, 255),
        spacing=4,
    )

    if side == "left":
        start = (box[0], (box[1] + box[3]) // 2)
    elif side == "top":
        start = ((box[0] + box[2]) // 2, box[1])
    elif side == "bottom":
        start = ((box[0] + box[2]) // 2, box[3])
    else:
        start = (box[2], (box[1] + box[3]) // 2)

    draw.line([start, target], fill=color, width=5)
    r = 9
    draw.ellipse([tx - r, ty - r, tx + r, ty + r], fill=color, outline=(255, 255, 255, 255), width=3)


def draw_highlight(draw, rect, color):
    draw.rounded_rectangle(rect, radius=16, outline=color + (215,), width=4)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.open(SRC).convert("RGB")
    width, height = img.size
    canvas = img.convert("RGBA")

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([0, 0, width, 94], fill=(0, 0, 0, 98))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    font = ImageFont.truetype(FONT_PATH, 30)
    small_font = ImageFont.truetype(FONT_PATH, 22)

    draw.text((28, 24), u(r"\u6811\u8393\u6d3e\u73af\u5883\u76d1\u6d4b\u4e0e\u4eba\u8138\u8bc6\u522b\u786c\u4ef6\u8fde\u63a5\u793a\u610f"), font=font, fill=(255, 255, 255, 255))
    draw.text((30, 61), u(r"\u7528\u4e8e\u6f14\u793a\uff1a\u73af\u5883\u6570\u636e\u91c7\u96c6\u3001\u6444\u50cf\u5934\u8bc6\u522b\u3001\u524d\u7aef\u8054\u52a8\u63a7\u5236"), font=small_font, fill=(203, 213, 225, 255))

    labels = [
        (u(r"\u6811\u8393\u6d3e\u4e3b\u677f\n\u8fd0\u884c Flask \u670d\u52a1"), (275, 640), (558, 532), (168, 85, 247), "right"),
        (u(r"\u9762\u5305\u677f\n\u4f20\u611f\u5668\u63a5\u7ebf\u6c47\u603b"), (870, 392), (988, 508), (236, 72, 153), "right"),
        (u(r"\u6444\u50cf\u5934\u6a21\u5757\n\u4eba\u8138\u91c7\u96c6"), (935, 690), (1138, 842), (59, 130, 246), "bottom"),
        (u(r"DHT11 \u6e29\u6e7f\u5ea6\u4f20\u611f\u5668"), (555, 820), (763, 728), (14, 165, 233), "right"),
        (u(r"\u4eba\u4f53/\u8ddd\u79bb\u68c0\u6d4b\u6a21\u5757"), (55, 705), (96, 762), (34, 197, 94), "top"),
        (u(r"\u7ea2\u5916/\u907f\u969c\u4f20\u611f\u5668"), (110, 430), (219, 496), (245, 158, 11), "right"),
        (u(r"\u675c\u90a6\u7ebf/GPIO \u8fde\u63a5\n\u4f9b\u7535\u4e0e\u6570\u636e\u4f20\u8f93"), (725, 120), (682, 330), (239, 68, 68), "bottom"),
        (u(r"\u72b6\u6001\u6307\u793a\u706f/\u6267\u884c\u6a21\u5757"), (920, 185), (946, 179), (250, 204, 21), "left"),
    ]

    for text, anchor, target, color, side in labels:
        draw_label(draw, text, anchor, target, font, color, side)

    highlight = Image.new("RGBA", img.size, (0, 0, 0, 0))
    highlight_draw = ImageDraw.Draw(highlight)
    draw_highlight(highlight_draw, [465, 430, 690, 595], (168, 85, 247))
    draw_highlight(highlight_draw, [790, 370, 1110, 610], (236, 72, 153))
    draw_highlight(highlight_draw, [1070, 780, 1260, 935], (59, 130, 246))
    draw_highlight(highlight_draw, [710, 685, 805, 790], (14, 165, 233))
    draw_highlight(highlight_draw, [35, 720, 135, 805], (34, 197, 94))
    draw_highlight(highlight_draw, [160, 400, 280, 550], (245, 158, 11))
    canvas = Image.alpha_composite(canvas, highlight)

    draw = ImageDraw.Draw(canvas)
    footer = u(r"\u6ce8\uff1a\u5c0f\u6a21\u5757\u53d7\u8df3\u7ebf\u906e\u6321\uff0c\u6309\u53ef\u89c1\u4f4d\u7f6e\u4e0e\u6f14\u793a\u529f\u80fd\u8fdb\u884c\u6807\u6ce8")
    footer_box = [22, height - 62, 650, height - 18]
    draw.rounded_rectangle(footer_box, radius=10, fill=(0, 0, 0, 135))
    draw.text((40, height - 52), footer, font=small_font, fill=(226, 232, 240, 255))

    canvas.convert("RGB").save(OUT, quality=94)
    print(OUT)


if __name__ == "__main__":
    main()
