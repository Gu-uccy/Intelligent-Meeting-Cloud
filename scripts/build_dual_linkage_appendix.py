from pathlib import Path
from textwrap import dedent

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "report_assets"
OUT_DIR = Path(r"D:\QQ")
OUT_DOCX = OUT_DIR / "总结报告_双向联动补充两页.docx"
SOURCE_REPORT = OUT_DIR / "总结报告 .docx"


def font_path(name):
    candidates = {
        "regular": [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simsun.ttc"],
        "bold": [r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\simhei.ttf"],
        "mono": [r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\cour.ttf"],
    }
    for path in candidates[name]:
        if Path(path).exists():
            return path
    return None


FONT_REGULAR = font_path("regular")
FONT_BOLD = font_path("bold")
FONT_MONO = font_path("mono")


def pil_font(kind="regular", size=28):
    path = {"regular": FONT_REGULAR, "bold": FONT_BOLD, "mono": FONT_MONO}.get(kind) or FONT_REGULAR
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def center_text(draw, box, text, font, fill=(0, 0, 0), spacing=6):
    x1, y1, x2, y2 = box
    lines = text.split("\n")
    heights = []
    widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + spacing * (len(lines) - 1)
    y = y1 + (y2 - y1 - total_h) / 2
    for line, w, h in zip(lines, widths, heights):
        draw.text((x1 + (x2 - x1 - w) / 2, y), line, font=font, fill=fill)
        y += h + spacing


def draw_arrow(draw, start, end, fill, width=5):
    draw.line([start, end], fill=fill, width=width)
    sx, sy = start
    ex, ey = end
    if abs(ex - sx) >= abs(ey - sy):
        direction = 1 if ex > sx else -1
        points = [(ex, ey), (ex - direction * 18, ey - 10), (ex - direction * 18, ey + 10)]
    else:
        direction = 1 if ey > sy else -1
        points = [(ex, ey), (ex - 10, ey - direction * 18), (ex + 10, ey - direction * 18)]
    draw.polygon(points, fill=fill)


def build_flow_diagram():
    out = ASSET_DIR / "dual_linkage_flow.png"
    img = Image.new("RGB", (1600, 820), "#F7FAFC")
    draw = ImageDraw.Draw(img)
    title_font = pil_font("bold", 44)
    box_font = pil_font("bold", 28)
    small_font = pil_font("regular", 21)
    note_font = pil_font("regular", 24)

    draw.text((70, 52), "双向联动控制闭环：网页、实体 LED 与 3D 顶灯共享同一设备状态", font=title_font, fill="#123B5D")

    boxes = [
        ((90, 180, 390, 330), "环境控制页", "点击照明按钮\n发送 manual 控制请求"),
        ((500, 180, 800, 330), "Flask 设备接口", "POST /api/control\n更新 devices.lighting"),
        ((910, 180, 1210, 330), "树莓派 GPIO/PWM", "RGB LED 亮白灯\n模拟真实照明设备"),
        ((500, 470, 800, 620), "统一状态读取", "GET /api/current\n返回 devices 状态"),
        ((910, 470, 1210, 620), "3D 会议室", "Three.js 顶灯\n按 lighting 状态亮灭"),
        ((90, 470, 390, 620), "3D 反向控制", "点击3D顶灯/面板\n回写同一接口"),
    ]

    for box, title, body in boxes:
        draw_rounded(draw, box, 22, "#FFFFFF", "#2E74B5", 3)
        x1, y1, x2, y2 = box
        draw.text((x1 + 22, y1 + 20), title, font=box_font, fill="#1F4D78")
        draw.multiline_text((x1 + 22, y1 + 66), body, font=small_font, fill="#334155", spacing=8)

    draw_arrow(draw, (390, 255), (500, 255), "#14B8A6")
    draw_arrow(draw, (800, 255), (910, 255), "#14B8A6")
    draw_arrow(draw, (1060, 330), (1060, 470), "#14B8A6")
    draw_arrow(draw, (910, 545), (800, 545), "#14B8A6")
    draw_arrow(draw, (500, 545), (390, 545), "#14B8A6")
    draw_arrow(draw, (240, 470), (240, 330), "#F59E0B")
    draw_arrow(draw, (390, 545), (500, 255), "#F59E0B")

    draw_rounded(draw, (1250, 188, 1510, 612), 24, "#EAF4FF", "#96BEE5", 2)
    draw.text((1280, 220), "状态字段", font=box_font, fill="#123B5D")
    state_lines = [
        "devices.lighting",
        "lighting_brightness",
        "lighting_source",
        "auto_mode",
    ]
    y = 282
    for item in state_lines:
        draw.ellipse((1280, y + 8, 1292, y + 20), fill="#14B8A6")
        draw.text((1305, y), item, font=note_font, fill="#334155")
        y += 58
    draw.multiline_text(
        (1280, 520),
        "核心原则：\n只维护一份设备状态，\n所有页面和硬件都围绕\n同一状态读写。",
        font=small_font,
        fill="#475569",
        spacing=8,
    )

    img.save(out)
    return out


def build_code_snapshot():
    out = ASSET_DIR / "dual_linkage_code.png"
    blocks = [
        (
            "前端统一控制 API：环境控制页和3D页面共用同一接口",
            [
                "export function setLightingDevice(enabled, brightness = enabled ? 100 : 0, source = 'frontend') {",
                "  return controlClimateDevice({",
                "    action: 'manual', device: 'lighting', state: enabled,",
                "    brightness, source,",
                "  });",
                "}",
            ],
        ),
        (
            "3D页面反向控制：点击虚拟顶灯后回写后端状态",
            [
                "async function toggleRoomLighting() {",
                "  const nextState = !lightingEnabled.value;",
                "  const result = await setLightingDevice(nextState, nextState ? 100 : 0, 'room-3d');",
                "  sensorData.value = { ...sensorData.value, devices: { ...sensorData.value.devices, ...result.devices } };",
                "  updateSensorVisuals();",
                "}",
            ],
        ),
        (
            "树莓派后端输出：统一状态驱动实体 LED 与页面模型",
            [
                "def set_lighting_state(enabled, brightness=None, source=\"manual\"):",
                "    devices[\"lighting\"] = bool(enabled)",
                "    devices[\"lighting_brightness\"] = brightness if enabled else 0",
                "    devices[\"lighting_source\"] = source",
                "    set_rgb_brightness(devices[\"lighting\"], devices[\"lighting_brightness\"])",
                "    apply_device_outputs()",
            ],
        ),
    ]

    width = 1600
    height = 860
    pad = 44
    title_h = 48
    line_h = 28
    block_gap = 22
    block_h = (height - pad * 2 - block_gap * (len(blocks) - 1)) // len(blocks)
    img = Image.new("RGB", (width, height), "#0F172A")
    draw = ImageDraw.Draw(img)
    title_font = pil_font("bold", 25)
    code_font = pil_font("mono", 21)
    number_font = pil_font("mono", 18)

    y = pad
    for block_index, (block_title, lines) in enumerate(blocks):
        y2 = y + block_h
        draw_rounded(draw, (pad, y, width - pad, y2), 14, "#111827", "#334155", 2)
        draw.rectangle((pad, y, width - pad, y + title_h), fill="#0F766E")
        draw.text((pad + 26, y + 10), block_title, font=title_font, fill="#ECFEFF")
        cy = y + title_h + 12
        for offset, line in enumerate(lines):
            draw.text((pad + 24, cy), f"{offset + 1:>2}", font=number_font, fill="#94A3B8")
            safe_line = line[:118]
            draw.text((pad + 78, cy), safe_line, font=code_font, fill="#E5E7EB")
            cy += line_h
        y = y2 + block_gap

    img.save(out)
    return out


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_text(cell, text, bold=False, color="000000", size=9.5):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = bold
    run.font.name = "微软雅黑"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def apply_supplement_geometry(section, source_section=None):
    if source_section is not None:
        section.page_width = source_section.page_width
        section.page_height = source_section.page_height
    section.top_margin = Cm(1.25)
    section.bottom_margin = Cm(1.15)
    section.left_margin = Cm(1.30)
    section.right_margin = Cm(1.30)
    section.header_distance = Cm(0.60)
    section.footer_distance = Cm(0.60)


def add_paragraph(doc, text="", size=10.5, bold=False, color="222222", after=4, before=0, align=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing = 1.15
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    run.font.name = "微软雅黑"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)
    return p


def add_heading(doc, text, level=1):
    size = 15 if level == 1 else 12.5
    color = "1F4D78" if level == 1 else "2E74B5"
    p = add_paragraph(doc, text, size=size, bold=True, color=color, before=4 if level == 1 else 2, after=6)
    return p


def add_bullet(doc, text):
    p = doc.add_paragraph(style=None)
    p.paragraph_format.left_indent = Cm(0.58)
    p.paragraph_format.first_line_indent = Cm(-0.28)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.12
    r = p.add_run("· ")
    r.font.name = "微软雅黑"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor.from_string("14B8A6")
    r.bold = True
    run = p.add_run(text)
    run.font.name = "微软雅黑"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    run.font.size = Pt(9.8)
    run.font.color.rgb = RGBColor.from_string("222222")


def add_caption(doc, text):
    p = add_paragraph(doc, text, size=9, color="666666", after=5, align=WD_ALIGN_PARAGRAPH.CENTER)
    return p


def set_table_borders(table, color="AAB7C4", size="6"):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = borders.find(qn(f"w:{edge}"))
        if el is None:
            el = OxmlElement(f"w:{edge}")
            borders.append(el)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), size)
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)


def create_docx():
    flow = build_flow_diagram()
    code = build_code_snapshot()
    screenshot = ASSET_DIR / "dual_linkage_room3d.png"

    source = Document(SOURCE_REPORT)
    source_sec = source.sections[0]

    doc = Document()
    sec = doc.sections[0]
    apply_supplement_geometry(sec, source_sec)

    styles = doc.styles
    styles["Normal"].font.name = "微软雅黑"
    styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    styles["Normal"].font.size = Pt(10.5)

    add_paragraph(doc, "补充页：双向联动功能实现", size=18, bold=True, color="123B5D", after=2, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_paragraph(doc, "独立补充材料，不改变原报告正文与目录页码", size=9.5, color="666666", after=8, align=WD_ALIGN_PARAGRAPH.CENTER)

    add_heading(doc, "一、功能定位", level=1)
    add_paragraph(
        doc,
        "本次补充实现了“实体 LED 模拟设备”和“3D 会议室模型灯光”的双向联动。系统不再只做传感器到页面的单向展示，而是将前端控制、树莓派 GPIO 输出和 Three.js 虚拟场景绑定到同一个设备状态上，形成可演示、可验证的闭环控制功能。",
        size=10.2,
        after=5,
    )

    add_heading(doc, "二、联动闭环流程", level=2)
    doc.add_picture(str(flow), width=Cm(16.5))
    add_caption(doc, "图 B-1 双向联动控制闭环流程图")

    add_heading(doc, "三、关键状态与接口", level=2)
    table = doc.add_table(rows=1, cols=4)
    table.autofit = False
    headers = ["对象", "核心字段/接口", "作用", "联动方向"]
    widths = [Cm(3.0), Cm(4.2), Cm(5.3), Cm(3.4)]
    for idx, cell in enumerate(table.rows[0].cells):
        cell.width = widths[idx]
        set_cell_shading(cell, "1F4D78")
        set_cell_text(cell, headers[idx], True, "FFFFFF", 9.5)
    rows = [
        ["前端控制页", "POST /sensor-api/control", "点击“照明”按钮，写入灯光开关和亮度", "页面 -> 硬件/3D"],
        ["树莓派后端", "devices.lighting", "维护唯一灯光状态，输出 RGB LED PWM", "状态中枢"],
        ["3D会议室", "GET /sensor-api/current", "轮询设备状态并控制 Three.js 顶灯亮灭", "硬件 -> 3D"],
        ["3D反向控制", "setLightingDevice()", "点击3D面板或顶灯后回写同一接口", "3D -> 硬件"],
    ]
    for row in rows:
        cells = table.add_row().cells
        for idx, text in enumerate(row):
            cells[idx].width = widths[idx]
            set_cell_text(cells[idx], text, False, "222222", 8.8)
            if idx == 1:
                set_cell_shading(cells[idx], "F2F7FA")
    set_table_borders(table)

    add_paragraph(doc, "", after=0)
    add_bullet(doc, "正向联动：环境控制页打开照明后，树莓派 RGB LED 亮起，同时 3D 会议室顶灯自动打开。")
    add_bullet(doc, "反向联动：在 3D 页面点击灯光按钮或顶灯模型后，系统回写后端接口，实体 LED 同步亮灭。")
    add_bullet(doc, "状态隔离：该补充页独立说明新增功能，不修改原报告目录和正文页码。")

    new_sec = doc.add_section(WD_SECTION_START.NEW_PAGE)
    apply_supplement_geometry(new_sec)

    add_paragraph(doc, "补充页：双向联动功能实现", size=18, bold=True, color="123B5D", after=2, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_paragraph(doc, "核心实现与演示验证", size=9.5, color="666666", after=8, align=WD_ALIGN_PARAGRAPH.CENTER)

    add_heading(doc, "四、核心实现", level=1)
    doc.add_picture(str(code), width=Cm(16.2))
    add_caption(doc, "图 B-2 双向联动关键代码片段")

    add_heading(doc, "五、成果展示与演示步骤", level=2)
    two_col = doc.add_table(rows=1, cols=2)
    two_col.autofit = False
    two_col.rows[0].cells[0].width = Cm(8.1)
    two_col.rows[0].cells[1].width = Cm(8.1)
    for cell in two_col.rows[0].cells:
        set_cell_shading(cell, "F8FAFC")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
    left = two_col.rows[0].cells[0]
    right = two_col.rows[0].cells[1]
    left.text = ""
    p = left.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(screenshot), width=Cm(7.6))
    p2 = left.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p2.add_run("图 B-3 3D会议室灯光联动页面")
    r.font.name = "微软雅黑"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    r.font.size = Pt(8.5)
    r.font.color.rgb = RGBColor.from_string("666666")

    right.text = ""
    steps = [
        ("1", "打开环境控制页，点击“照明”设备按钮。"),
        ("2", "观察树莓派端 RGB LED 由熄灭变为白色常亮。"),
        ("3", "切换到 3D 会议室页面，确认虚拟顶灯同步打开。"),
        ("4", "在 3D 页面点击“关闭LED灯”或直接点击顶灯模型。"),
        ("5", "观察实体 LED 熄灭，控制页状态在下一次轮询后同步更新。"),
    ]
    for number, text in steps:
        p = right.add_paragraph()
        p.paragraph_format.space_after = Pt(5)
        badge = p.add_run(f"{number} ")
        badge.font.name = "微软雅黑"
        badge._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
        badge.font.size = Pt(10)
        badge.bold = True
        badge.font.color.rgb = RGBColor.from_string("0F766E")
        run = p.add_run(text)
        run.font.name = "微软雅黑"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
        run.font.size = Pt(9.4)
        run.font.color.rgb = RGBColor.from_string("222222")
    set_table_borders(two_col, color="D7DEE8", size="4")

    add_heading(doc, "六、工程价值", level=2)
    add_bullet(doc, "从“数据展示”提升为“状态可写、硬件可控、模型可反馈”的交互式物联网闭环。")
    add_bullet(doc, "LED 作为低风险模拟执行器，可以清晰展示真实设备控制逻辑，避免直接接入强电照明设备。")
    add_bullet(doc, "3D 场景不再是静态模型，而是实体会议室状态的数字孪生映射，适合答辩现场演示。")

    for section in doc.sections:
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.text = "双向联动功能补充页"
        footer.runs[0].font.name = "微软雅黑"
        footer.runs[0]._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
        footer.runs[0].font.size = Pt(9)
        footer.runs[0].font.color.rgb = RGBColor.from_string("666666")

    doc.save(OUT_DOCX)
    print(OUT_DOCX)


if __name__ == "__main__":
    create_docx()
