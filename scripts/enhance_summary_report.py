from pathlib import Path
import shutil

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph


ROOT = Path(r"D:\Project\Intelligent-Meeting-Cloud")
SRC_DIR = Path(r"D:\QQ")
SRC = SRC_DIR / "\u603b\u7ed3\u62a5\u544a.docx"
OUT = SRC_DIR / "\u603b\u7ed3\u62a5\u544a_\u8865\u56fe\u589e\u5f3a\u7248.docx"

ASSETS = {
    "arch": ROOT / "report_assets/diagram_system_architecture.png",
    "env_flow": ROOT / "report_assets/diagram_environment_flow.png",
    "face_flow": ROOT / "report_assets/diagram_face_access_flow.png",
    "three_flow": ROOT / "report_assets/diagram_threejs_flow.png",
    "hardware": ROOT / "video_assets/raspberry_pi_annotated_cn.jpg",
    "ui_sensor": ROOT / "report_control.png",
    "ui_climate": ROOT / "report_climate.png",
    "ui_room3d": ROOT / "report_room3d.png",
    "code_env": ROOT / "report_assets/code_environment_fetch.png",
    "code_face_front": ROOT / "report_assets/code_face_access_decision.png",
    "code_face_api": ROOT / "report_assets/code_face_api_deepface.png",
    "code_three": ROOT / "report_assets/code_threejs_sensor_visuals.png",
}


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_run_font(run, name="宋体"):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)


def style_caption(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(8)
    for run in paragraph.runs:
        set_run_font(run, "宋体")
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(80, 80, 80)


def add_caption(doc, text):
    p = doc.add_paragraph(text)
    style_caption(p)
    return p


def add_figure(doc, path, caption, width=5.9):
    if not path.exists():
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    run = p.add_run()
    run.add_picture(str(path), width=Inches(width))
    add_caption(doc, caption)


def insert_paragraph_after(paragraph, text=None):
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    if text:
        new_para.add_run(text)
    return new_para


def insert_caption_after(paragraph, text):
    p = insert_paragraph_after(paragraph, text)
    style_caption(p)
    return p


def insert_note_after(paragraph, text):
    p = insert_paragraph_after(paragraph)
    p.paragraph_format.left_indent = Inches(0.18)
    p.paragraph_format.right_indent = Inches(0.18)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(text)
    set_run_font(run, "宋体")
    run.font.size = Pt(10.5)
    run.font.color.rgb = RGBColor(71, 85, 105)
    return p


def insert_figure_after(paragraph, path, caption, width=5.9):
    if not path.exists():
        return paragraph
    p = insert_paragraph_after(paragraph)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    run = p.add_run()
    run.add_picture(str(path), width=Inches(width))
    return insert_caption_after(p, caption)


def add_note(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.18)
    p.paragraph_format.right_indent = Inches(0.18)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(text)
    set_run_font(run, "宋体")
    run.font.size = Pt(10.5)
    run.font.color.rgb = RGBColor(71, 85, 105)
    return p


def add_table_summary(doc):
    doc.add_heading("图表化补充说明", level=2)
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    headers = ["图示类型", "对应内容", "放入报告的作用"]
    for i, text in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = text
        set_cell_shading(cell, "D9EAF7")
        for run in cell.paragraphs[0].runs:
            set_run_font(run, "宋体")
            run.bold = True
    rows = [
        ("系统架构图", "感知层、传输层、服务层、可视化层、控制层", "说明系统不是单点功能，而是完整物联网链路。"),
        ("硬件标注图", "树莓派、面包板、摄像头、DHT11、人体/距离检测模块", "证明系统具有真实硬件接入与调试过程。"),
        ("功能流程图", "环境控制、人脸门禁、3D会议室联动流程", "把文字描述转化为可读的工程流程。"),
        ("界面成果图", "环境监测、温湿度控制、3D会议室页面", "展示项目最终运行效果。"),
        ("核心代码图", "前端数据获取、门禁权限判断、DeepFace后端、Three.js联动", "突出实现细节与技术含量。"),
    ]
    for row in rows:
        cells = table.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = text
            for para in cells[i].paragraphs:
                for run in para.runs:
                    set_run_font(run, "宋体")
                    run.font.size = Pt(9.5)
    add_note(doc, "以上图示均来自本项目运行界面、硬件实物照片或关键源码，作为正文说明的补充证据。")


def find_para(doc, needle):
    for idx, para in enumerate(doc.paragraphs):
        if needle in para.text:
            return idx
    return None


def append_visual_appendix(doc):
    doc.add_page_break()
    doc.add_heading("附录A 系统图示与关键代码补充", level=1)
    add_note(
        doc,
        "本附录补充项目运行界面、硬件实物、流程图和核心代码截图，用于增强报告的工程实现证明与成果展示完整性。",
    )
    add_table_summary(doc)

    doc.add_heading("A.1 系统架构与硬件连接", level=2)
    add_figure(doc, ASSETS["arch"], "图A-1 智能会议室系统分层架构图", 6.1)
    add_figure(doc, ASSETS["hardware"], "图A-2 树莓派硬件连接与传感器模块标注图", 6.1)

    doc.add_heading("A.2 环境控制与设备联动", level=2)
    add_figure(doc, ASSETS["env_flow"], "图A-3 环境控制数据流与设备联动流程图", 6.1)
    add_figure(doc, ASSETS["ui_sensor"], "图A-4 会议室环境监测页面运行效果", 6.1)
    add_figure(doc, ASSETS["ui_climate"], "图A-5 智能温湿度控制页面运行效果", 6.1)
    add_figure(doc, ASSETS["code_env"], "图A-6 环境控制前端实时数据获取核心代码", 6.1)

    doc.add_heading("A.3 人脸门禁识别", level=2)
    add_figure(doc, ASSETS["face_flow"], "图A-7 人脸门禁识别与预约权限判断流程图", 6.1)
    add_figure(doc, ASSETS["code_face_front"], "图A-8 人脸门禁前端权限判断核心代码", 6.1)
    add_figure(doc, ASSETS["code_face_api"], "图A-9 树莓派 DeepFace 人脸识别后端核心代码", 6.1)

    doc.add_heading("A.4 3D会议室可视化", level=2)
    add_figure(doc, ASSETS["three_flow"], "图A-10 3D会议室场景构建与传感器联动流程图", 6.1)
    add_figure(doc, ASSETS["ui_room3d"], "图A-11 3D智能会议室模型展示页面", 6.1)
    add_figure(doc, ASSETS["code_three"], "图A-12 Three.js 传感器数据驱动虚拟场景核心代码", 6.1)


def insert_body_figures(doc):
    insertions = [
        (
            "1.1.2 系统总体架构设计",
            lambda p: (
                insert_note_after(
                    insert_figure_after(p, ASSETS["arch"], "图1-1 智能会议室系统分层架构图", 5.9),
                    "系统采用分层结构组织硬件采集、服务接口、前端展示和设备控制，便于模块化开发与后续扩展。",
                )
            ),
        ),
        (
            "感知层是系统的数据源头",
            lambda p: insert_figure_after(p, ASSETS["hardware"], "图1-2 树莓派硬件连接与主要传感器标注", 5.9),
        ),
        (
            "1.1.3.1. 多传感器环境感知模块",
            lambda p: insert_figure_after(p, ASSETS["env_flow"], "图1-3 环境数据采集、处理与设备联动流程", 5.9),
        ),
        (
            "1.1.3.2. 智能设备控制模块",
            lambda p: insert_figure_after(p, ASSETS["ui_climate"], "图1-4 智能温湿度控制与设备状态页面", 5.9),
        ),
        (
            "⑤智能门禁控制",
            lambda p: insert_figure_after(p, ASSETS["face_flow"], "图1-5 人脸识别门禁与预约权限判断流程", 5.9),
        ),
        (
            "1.1.3.3. 3D 会议室可视化模块",
            lambda p: insert_figure_after(p, ASSETS["three_flow"], "图1-6 3D会议室场景构建与传感器联动流程", 5.9),
        ),
        (
            "2.2.1.1 DHT11 温湿度测试",
            lambda p: insert_figure_after(p, ASSETS["ui_sensor"], "图2-1 环境监测页面运行效果与实时数据展示", 5.9),
        ),
        (
            "2.2.3.1. 场景加载测试",
            lambda p: insert_figure_after(p, ASSETS["ui_room3d"], "图2-2 3D会议室模型展示与交互界面", 5.9),
        ),
        (
            "3.2 后端服务与接口开发技能",
            lambda p: insert_figure_after(p, ASSETS["code_face_api"], "图3-1 树莓派端人脸识别 Flask 接口核心代码", 5.9),
        ),
        (
            "3.3 前端开发与 3D 可视化技能",
            lambda p: insert_figure_after(
                insert_figure_after(p, ASSETS["code_env"], "图3-2 前端环境数据获取与异常处理代码", 5.9),
                ASSETS["code_three"],
                "图3-3 Three.js 传感器联动可视化核心代码",
                5.9,
            ),
        ),
    ]

    for needle, callback in insertions:
        idx = find_para(doc, needle)
        if idx is not None:
            callback(doc.paragraphs[idx])


def normalize_figures(doc):
    for section in doc.sections:
        section.top_margin = Inches(0.9)
        section.bottom_margin = Inches(0.9)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

    for para in doc.paragraphs:
        for run in para.runs:
            if run.text:
                set_run_font(run, "宋体")


def main():
    shutil.copy2(SRC, OUT)
    doc = Document(OUT)
    normalize_figures(doc)
    insert_body_figures(doc)
    append_visual_appendix(doc)
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
