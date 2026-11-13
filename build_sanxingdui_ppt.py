from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "sanxingdui_assets"
OUT = ROOT / "三星堆祭祀舞蹈鉴赏-舞蹈重点版.pptx"
CANVAS = (1920, 1080)


palette = {
    "ink": RGBColor(36, 28, 24),
    "muted": RGBColor(100, 87, 76),
    "paper": RGBColor(247, 241, 232),
    "red": RGBColor(154, 45, 33),
    "bronze": RGBColor(74, 105, 91),
    "gold": RGBColor(186, 132, 53),
    "dark": RGBColor(25, 29, 27),
}


slides = [
    {
        "kind": "cover",
        "title": "三星堆祭祀舞蹈鉴赏",
        "subtitle": "从动作、节奏、面具和队形感受古蜀祭祀舞蹈",
        "image": "standing_figure.jpg",
    },
    {
        "title": "鉴赏重点：看舞蹈语言",
        "image": "standing_figure.jpg",
        "points": [
            "这类舞蹈不是讲故事为主，而是营造祭祀气氛。",
            "重点看身体姿态、手势、节奏、队形和面具造型。",
            "真实文物提供灵感，舞蹈表演负责把神秘感表现出来。",
        ],
        "tag": "总览",
    },
    {
        "title": "身体姿态：稳、慢、庄重",
        "image": "standing_figure.jpg",
        "points": [
            "舞者的身体要有重量感，像站在祭祀场中央。",
            "动作可以少，但每一次抬手、转身都要清楚有力。",
            "青铜大立人的站姿，适合作为庄重仪式感的参考。",
        ],
        "tag": "动作",
    },
    {
        "title": "手势：像在献祭，也像在请神",
        "image": "bronze_colossal.jpg",
        "points": [
            "手臂可以保持固定造型，形成强烈的仪式符号。",
            "双手前伸、合抱、上举，都能表现“献”“迎”“祈”。",
            "动作不必复杂，关键是节奏整齐、方向明确。",
        ],
        "tag": "手势",
    },
    {
        "title": "节奏：重复带来神圣感",
        "image": "bronze_tree.jpg",
        "points": [
            "祭祀舞蹈常用重复动作，让观众感到庄严和专注。",
            "慢节奏适合表现敬畏，强节拍适合表现呼唤和震撼。",
            "可以想象鼓点、脚步、呼吸一起推动舞蹈向前。",
        ],
        "tag": "节奏",
    },
    {
        "title": "面具：改变舞者的身份",
        "image": "bronze_mask.jpg",
        "points": [
            "面具让舞者不再只是“人”，而像神灵、祖先或祭司。",
            "眼睛突出、耳朵夸张，会放大舞台上的神秘感。",
            "戴面具时动作要更大、更慢，让观众看清造型。",
        ],
        "tag": "造型",
    },
    {
        "title": "服饰与光感：让仪式更醒目",
        "image": "gold_mask.jpg",
        "points": [
            "金色、青铜色、深色服装能形成古朴而神圣的舞台效果。",
            "服饰不一定要完全复原，但色彩和轮廓要接近文物气质。",
            "灯光照到面具和手臂时，能突出“祭祀”这一主题。",
        ],
        "tag": "舞台",
    },
    {
        "title": "空间队形：围绕中心展开",
        "image": "bronze_tree.jpg",
        "points": [
            "神树、祭台或面具可以成为舞台中心。",
            "舞者围绕中心移动，能表现“共同祭祀”的场面。",
            "圆形、半圆形、对称队形，都适合表现古蜀仪式感。",
        ],
        "tag": "队形",
    },
    {
        "title": "情绪表达：敬畏、神秘、召唤",
        "image": "bronze_head.jpg",
        "points": [
            "祭祀舞蹈的情绪不是热闹，而是庄严、神秘、专注。",
            "舞者表情可以被面具隐藏，情绪就由身体和节奏来传达。",
            "观众看到的应是人与神灵沟通的过程。",
        ],
        "tag": "情绪",
    },
    {
        "title": "怎样评价这支舞？",
        "image": "bronze_colossal.jpg",
        "points": [
            "看动作是否庄重有力，而不是只看动作多不多。",
            "看面具、手势、队形是否共同服务祭祀主题。",
            "看它是否让人感到古蜀文化的神秘与震撼。",
        ],
        "tag": "评价",
    },
    {
        "kind": "sources",
        "title": "结语：舞蹈让文物“动起来”",
        "points": [
            "三星堆文物本身是静止的，舞蹈让它们产生动作和节奏。",
            "欣赏时重点看舞蹈如何表现祭祀：站姿、手势、节奏、队形、面具。",
            "真实文物负责提供依据，舞蹈负责表达想象和情感。",
        ],
    },
]


def rgb_tuple(color):
    return (color[0], color[1], color[2])


def make_bg(src_name: str, dest_name: str, overlay=(247, 241, 232, 214)):
    src = Image.open(ASSETS / src_name).convert("RGB")
    sw, sh = src.size
    cw, ch = CANVAS
    scale = max(cw / sw, ch / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    img = src.resize((nw, nh), Image.LANCZOS)
    left = (nw - cw) // 2
    top = (nh - ch) // 2
    img = img.crop((left, top, left + cw, top + ch))
    img = img.filter(ImageFilter.GaussianBlur(5))
    wash = Image.new("RGBA", CANVAS, overlay)
    out = Image.alpha_composite(img.convert("RGBA"), wash).convert("RGB")
    out.save(ASSETS / dest_name, quality=92)


def normalize_image(src_name: str):
    src = ASSETS / src_name
    img = Image.open(src).convert("RGB")
    img.save(src, format="JPEG", quality=94)


def add_textbox(slide, text, x, y, w, h, size=24, bold=False, color=None, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.clear()
    tf.margin_left = Inches(0.03)
    tf.margin_right = Inches(0.03)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = MSO_ANCHOR.TOP
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    font = run.font
    font.name = "Microsoft YaHei"
    font.size = Pt(size)
    font.bold = bold
    font.color.rgb = color or palette["ink"]
    return box


def add_tag(slide, text):
    shape = slide.shapes.add_shape(1, Inches(0.75), Inches(0.55), Inches(1.45), Inches(0.34))
    shape.fill.solid()
    shape.fill.fore_color.rgb = palette["red"]
    shape.line.fill.background()
    tf = shape.text_frame
    tf.clear()
    tf.margin_left = Inches(0.08)
    tf.margin_right = Inches(0.08)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.name = "Microsoft YaHei"
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = RGBColor(255, 250, 240)


def add_image(slide, src_name, x, y, w, h):
    slide.shapes.add_picture(str(ASSETS / src_name), x, y, width=w, height=h)


def add_points(slide, points, x, y, w, start_size=26):
    cy = y
    for idx, point in enumerate(points, start=1):
        num = slide.shapes.add_shape(9, x, cy + Inches(0.05), Inches(0.35), Inches(0.35))
        num.fill.solid()
        num.fill.fore_color.rgb = palette["bronze"] if idx % 2 else palette["gold"]
        num.line.fill.background()
        tf = num.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(idx)
        r.font.name = "Arial"
        r.font.size = Pt(12)
        r.font.bold = True
        r.font.color.rgb = RGBColor(255, 255, 255)
        add_textbox(slide, point, x + Inches(0.52), cy, w - Inches(0.52), Inches(0.78), start_size, False)
        cy += Inches(0.92)


def add_credit(slide, text="图片：Wikimedia Commons；事实参考：三星堆考古公开资料"):
    add_textbox(slide, text, Inches(0.75), Inches(7.08), Inches(11.0), Inches(0.25), 8.5, False, palette["muted"])


def build():
    for src in {s["image"] for s in slides if "image" in s}:
        normalize_image(src)

    for s in slides:
        if "image" in s:
            make_bg(s["image"], f"bg_{s['image']}", overlay=(247, 241, 232, 222))

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    for s in slides:
        slide = prs.slides.add_slide(blank)
        kind = s.get("kind", "content")
        bg_name = f"bg_{s.get('image', 'bronze_mask.jpg')}"
        if kind != "sources":
            slide.shapes.add_picture(str(ASSETS / bg_name), 0, 0, width=prs.slide_width, height=prs.slide_height)
        else:
            rect = slide.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
            rect.fill.solid()
            rect.fill.fore_color.rgb = palette["paper"]
            rect.line.fill.background()

        if kind == "cover":
            add_textbox(slide, s["title"], Inches(0.85), Inches(1.15), Inches(6.7), Inches(0.9), 39, True, palette["ink"])
            add_textbox(slide, s["subtitle"], Inches(0.9), Inches(2.15), Inches(5.9), Inches(0.9), 20, False, palette["muted"])
            add_image(slide, s["image"], Inches(8.05), Inches(0.65), Inches(3.75), Inches(6.15))
            add_textbox(slide, "真实文物 / 简明讲解 / 保留推测边界", Inches(0.9), Inches(6.4), Inches(5.2), Inches(0.35), 14, True, palette["red"])
            add_credit(slide)
            continue

        if kind == "sources":
            add_textbox(slide, s["title"], Inches(0.75), Inches(0.65), Inches(8.5), Inches(0.6), 34, True, palette["ink"])
            add_points(slide, s["points"], Inches(0.85), Inches(1.65), Inches(10.7), 22)
            add_textbox(
                slide,
                "主要事实参考：sanxingduiarchy.com（三星堆考古公开资料）；图片页面已保存在 sanxingdui_assets/sources.json。",
                Inches(0.85),
                Inches(5.85),
                Inches(10.8),
                Inches(0.7),
                15,
                False,
                palette["muted"],
            )
            continue

        add_tag(slide, s["tag"])
        add_textbox(slide, s["title"], Inches(0.75), Inches(1.05), Inches(6.25), Inches(0.75), 31, True, palette["ink"])
        add_image(slide, s["image"], Inches(8.0), Inches(0.72), Inches(4.05), Inches(5.9))
        add_points(slide, s["points"], Inches(0.82), Inches(2.15), Inches(6.2), 22)
        add_credit(slide)

    prs.save(OUT)


if __name__ == "__main__":
    build()
    print(OUT)
