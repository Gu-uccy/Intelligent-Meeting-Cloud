from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "video_assets"
OUT = ROOT / "三星堆祭祀舞蹈鉴赏-根据视频改写版.pptx"


palette = {
    "ink": RGBColor(248, 242, 230),
    "muted": RGBColor(219, 207, 188),
    "dark": RGBColor(20, 22, 21),
    "bronze": RGBColor(78, 114, 101),
    "gold": RGBColor(214, 155, 71),
    "fire": RGBColor(195, 77, 43),
    "paper": RGBColor(246, 239, 226),
    "paper_ink": RGBColor(43, 34, 29),
}


slides = [
    {
        "kind": "cover",
        "title": "三星堆祭祀舞蹈鉴赏",
        "subtitle": "根据视频《舞蹈鉴赏第二版》改写",
        "image": "cover.jpg",
        "note": "面具、神树、火光与群舞构成一场古蜀祭祀想象。",
    },
    {
        "title": "作品整体：一场祭祀仪式的展开",
        "image": "stage_wide.jpg",
        "tag": "整体感受",
        "points": [
            "视频把舞蹈放在祭祀场景中：神树居中，火光环绕。",
            "舞者不是单纯表演技巧，而是在完成“请神、迎神、通神”的仪式。",
            "观看重点：动作是否庄重，队形是否有秩序，画面是否有神圣感。",
        ],
    },
    {
        "title": "开场独舞：用身体建立仪式感",
        "image": "opening_pose.jpg",
        "tag": "动作",
        "points": [
            "开场舞者手臂展开，身体重心下沉，姿态稳定。",
            "动作幅度大但速度不快，给人庄严、肃穆的感觉。",
            "这种开场像是在召唤观众进入祭祀空间。",
        ],
    },
    {
        "title": "面具造型：让舞者变成神秘角色",
        "image": "mask_close.jpg",
        "tag": "造型",
        "points": [
            "视频多次强调面具近景，突出眼部和青铜纹样。",
            "面具遮住表情后，情绪主要靠头部角度、手势和身体线条表达。",
            "它让舞者从“人”转化为祭司、神灵或古蜀祖先的形象。",
        ],
    },
    {
        "title": "手势语言：献、迎、祈",
        "image": "gesture_statue.jpg",
        "tag": "手势",
        "points": [
            "双手在胸前、头侧或向上展开，形成清楚的仪式符号。",
            "手势重复出现，像是在献祭、迎接神灵、表达祈愿。",
            "这些动作不追求复杂，而追求清晰、稳定、有力量。",
        ],
    },
    {
        "title": "神树中心：舞蹈围绕“通天”展开",
        "image": "tree_detail.jpg",
        "tag": "空间",
        "points": [
            "神树在视频中是视觉中心，也像整个仪式的精神中心。",
            "舞者围绕神树移动，形成从地面到天空的空间想象。",
            "神鸟升起时，舞蹈的主题从祭祀推进到神灵降临。",
        ],
    },
    {
        "title": "火光与鼓点感：推动情绪升高",
        "image": "torch_circle.jpg",
        "tag": "节奏",
        "points": [
            "火把、烟雾和夜色让舞台更像真实祭场。",
            "圆形行进和整齐步伐制造出强烈节奏感。",
            "观众能感到仪式从安静开始，逐步变得热烈。",
        ],
    },
    {
        "title": "群舞队形：圆阵表现共同祭祀",
        "image": "circle_formation.jpg",
        "tag": "队形",
        "points": [
            "视频中多次出现围绕中心的圆形或半圆形队列。",
            "圆阵让舞蹈看起来有秩序，也强调所有人面对同一个祭祀中心。",
            "持杖、举手、行进动作统一，增强了集体仪式感。",
        ],
    },
    {
        "title": "神鸟意象：把舞蹈推向高潮",
        "image": "bird_tree.jpg",
        "tag": "意象",
        "points": [
            "发光神鸟出现在神树上方，是视频最强的视觉高潮。",
            "它象征升腾、沟通天地，也让舞蹈从现实动作进入神话想象。",
            "这一段适合讲“舞蹈如何用画面表达神圣力量”。",
        ],
    },
    {
        "title": "白衣旋转：柔美与火光形成对比",
        "image": "white_dance.jpg",
        "tag": "对比",
        "points": [
            "白衣舞者的旋转让画面从厚重青铜感转向流动感。",
            "柔软衣袖与火光、神树形成对比，丰富了舞蹈层次。",
            "这一段表现的不只是力量，也有祝祷、净化和升华的意味。",
        ],
    },
    {
        "kind": "summary",
        "title": "鉴赏总结：这支舞好在哪里？",
        "image": "stage_wide.jpg",
        "points": [
            "它把三星堆元素变成了舞蹈语言：面具、手势、神树、火光、圆阵。",
            "动作并不靠炫技取胜，而是靠庄重节奏和仪式氛围打动人。",
            "欣赏时要抓住一句话：舞蹈让静止的文物变成一场可观看的祭祀。",
        ],
    },
]


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
    r = p.add_run()
    r.text = text
    r.font.name = "Microsoft YaHei"
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color or palette["ink"]
    return box


def add_overlay(slide, x, y, w, h, color=RGBColor(18, 20, 19), transparency=14):
    shape = slide.shapes.add_shape(1, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.fill.transparency = transparency
    shape.line.fill.background()
    return shape


def add_tag(slide, text):
    shape = slide.shapes.add_shape(1, Inches(0.72), Inches(0.52), Inches(1.28), Inches(0.34))
    shape.fill.solid()
    shape.fill.fore_color.rgb = palette["fire"]
    shape.line.fill.background()
    tf = shape.text_frame
    tf.clear()
    tf.margin_left = Inches(0.05)
    tf.margin_right = Inches(0.05)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.name = "Microsoft YaHei"
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = RGBColor(255, 248, 235)


def add_points(slide, points, x, y, w, size=21):
    cy = y
    for idx, point in enumerate(points, start=1):
        marker = slide.shapes.add_shape(9, x, cy + Inches(0.06), Inches(0.32), Inches(0.32))
        marker.fill.solid()
        marker.fill.fore_color.rgb = palette["gold"] if idx == 1 else palette["bronze"]
        marker.line.fill.background()
        tf = marker.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(idx)
        r.font.name = "Arial"
        r.font.size = Pt(11)
        r.font.bold = True
        r.font.color.rgb = RGBColor(22, 20, 18)
        add_textbox(slide, point, x + Inches(0.48), cy, w - Inches(0.48), Inches(0.72), size, False)
        cy += Inches(0.88)


def add_credit(slide):
    add_textbox(
        slide,
        "画面来源：D:/QQ/舞蹈鉴赏第二版.mp4 截图；文字根据视频舞蹈内容改写",
        Inches(0.72),
        Inches(7.08),
        Inches(11.5),
        Inches(0.24),
        8,
        False,
        palette["muted"],
    )


def build():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    for item in slides:
        slide = prs.slides.add_slide(blank)
        kind = item.get("kind", "content")
        bg = item["image"].replace(".jpg", "_bg.jpg")
        slide.shapes.add_picture(str(ASSETS / bg), 0, 0, width=prs.slide_width, height=prs.slide_height)

        if kind == "cover":
            add_overlay(slide, Inches(0.65), Inches(0.78), Inches(5.95), Inches(5.65), transparency=18)
            add_textbox(slide, item["title"], Inches(0.95), Inches(1.15), Inches(5.4), Inches(0.8), 38, True)
            add_textbox(slide, item["subtitle"], Inches(0.98), Inches(2.05), Inches(5.2), Inches(0.5), 18, False, palette["muted"])
            add_textbox(slide, item["note"], Inches(0.98), Inches(5.65), Inches(5.0), Inches(0.5), 16, True, palette["gold"])
            slide.shapes.add_picture(str(ASSETS / item["image"]), Inches(7.0), Inches(0.62), Inches(4.65), Inches(6.2))
            add_credit(slide)
            continue

        if kind == "summary":
            add_overlay(slide, Inches(0.75), Inches(0.74), Inches(11.55), Inches(5.85), transparency=9)
            add_textbox(slide, item["title"], Inches(1.05), Inches(1.08), Inches(8.8), Inches(0.7), 34, True)
            add_points(slide, item["points"], Inches(1.08), Inches(2.22), Inches(9.8), 23)
            add_credit(slide)
            continue

        add_tag(slide, item["tag"])
        add_overlay(slide, Inches(0.68), Inches(0.95), Inches(6.05), Inches(5.72), transparency=10)
        add_textbox(slide, item["title"], Inches(0.95), Inches(1.23), Inches(5.35), Inches(0.72), 29, True)
        add_points(slide, item["points"], Inches(0.98), Inches(2.25), Inches(5.35), 20)
        slide.shapes.add_picture(str(ASSETS / item["image"]), Inches(7.15), Inches(0.8), Inches(4.45), Inches(5.95))
        add_credit(slide)

    prs.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
