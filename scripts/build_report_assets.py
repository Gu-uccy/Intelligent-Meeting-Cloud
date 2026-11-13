from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"D:\Project\Intelligent-Meeting-Cloud")
OUT = ROOT / "report_assets"
OUT.mkdir(parents=True, exist_ok=True)

FONT_CN = r"C:\Windows\Fonts\simhei.ttf"
FONT_CODE = r"C:\Windows\Fonts\CascadiaMono.ttf"


def font(size, code=False):
    return ImageFont.truetype(FONT_CODE if code else FONT_CN, size)


def rounded(draw, rect, fill, outline=None, width=2, radius=14):
    draw.rounded_rectangle(rect, radius=radius, fill=fill, outline=outline, width=width)


def center_text(draw, rect, text, fnt, fill=(15, 23, 42), spacing=6):
    x1, y1, x2, y2 = rect
    lines = text.split("\n")
    heights = [draw.textbbox((0, 0), line, font=fnt)[3] for line in lines]
    total = sum(heights) + spacing * (len(lines) - 1)
    y = y1 + (y2 - y1 - total) / 2
    for line, h in zip(lines, heights):
        bbox = draw.textbbox((0, 0), line, font=fnt)
        w = bbox[2] - bbox[0]
        draw.text((x1 + (x2 - x1 - w) / 2, y), line, font=fnt, fill=fill)
        y += h + spacing


def arrow(draw, start, end, color=(20, 184, 166), width=4):
    draw.line([start, end], fill=color, width=width)
    ex, ey = end
    sx, sy = start
    if abs(ex - sx) >= abs(ey - sy):
        sign = 1 if ex > sx else -1
        pts = [(ex, ey), (ex - sign * 14, ey - 8), (ex - sign * 14, ey + 8)]
    else:
        sign = 1 if ey > sy else -1
        pts = [(ex, ey), (ex - 8, ey - sign * 14), (ex + 8, ey - sign * 14)]
    draw.polygon(pts, fill=color)


def title(draw, text):
    draw.text((40, 28), text, font=font(34), fill=(15, 23, 42))
    draw.line([(40, 78), (1160, 78)], fill=(20, 184, 166), width=4)


def save(img, name):
    path = OUT / name
    img.convert("RGB").save(path, quality=95)
    return path


def architecture():
    img = Image.new("RGB", (1200, 760), (248, 250, 252))
    d = ImageDraw.Draw(img)
    title(d, "智能会议室系统分层架构")
    layers = [
        ("可视化层", "Vue3 前端界面\nThree.js 3D会议室\n环境控制与门禁页面", (239, 246, 255), (59, 130, 246)),
        ("服务层", "Flask REST API\n规则引擎 / 数据缓存\n人脸识别接口", (240, 253, 250), (20, 184, 166)),
        ("传输层", "HTTP 轮询\nWebSocket 预留\nVite 反向代理", (255, 251, 235), (245, 158, 11)),
        ("感知层", "DHT11 / 光敏 / MQ-2\nPIR人体红外 / HC-SR04\n摄像头采集", (253, 242, 248), (236, 72, 153)),
        ("控制层", "照明 / 制冷 / 加湿\n报警 / 舵机门禁预留\n自动与手动模式", (245, 243, 255), (139, 92, 246)),
    ]
    y = 112
    for i, (name, desc, fill, accent) in enumerate(layers):
        rect = [90, y, 1110, y + 102]
        rounded(d, rect, fill, accent, 3)
        rounded(d, [110, y + 23, 250, y + 79], (255, 255, 255), accent, 2)
        center_text(d, [110, y + 23, 250, y + 79], name, font(25), accent)
        d.multiline_text((295, y + 18), desc, font=font(20), fill=(30, 41, 59), spacing=5)
        if i < len(layers) - 1:
            arrow(d, (600, y + 108), (600, y + 126), color=(100, 116, 139), width=4)
        y += 118
    return save(img, "diagram_system_architecture.png")


def environment_flow():
    img = Image.new("RGB", (1200, 680), (248, 250, 252))
    d = ImageDraw.Draw(img)
    title(d, "环境控制数据流与设备联动流程")
    boxes = [
        ("传感器采集", "温度 / 湿度 / 光照\n烟雾 / 人体 / 距离", 70, 180),
        ("数据预处理", "中值滤波\n异常值兜底\n时间戳记录", 350, 180),
        ("规则引擎判断", "阈值比较\n自动/手动模式\n设备状态计算", 630, 180),
        ("前端展示", "数据卡片\n趋势图表\n控制面板", 910, 180),
    ]
    for name, desc, x, y in boxes:
        rounded(d, [x, y, x + 220, y + 160], (236, 253, 245), (16, 185, 129), 3)
        center_text(d, [x, y + 18, x + 220, y + 70], name, font(26), (6, 95, 70))
        center_text(d, [x + 12, y + 78, x + 208, y + 145], desc, font(20), (51, 65, 85))
    for x in [290, 570, 850]:
        arrow(d, (x, 260), (x + 50, 260))
    actions = [
        ("温度异常", "制冷/加热"),
        ("湿度异常", "加湿/除湿"),
        ("光照偏低", "自动照明"),
        ("烟雾报警", "蜂鸣器/告警"),
        ("无人状态", "节能模式"),
    ]
    start_x = 95
    for i, (cond, act) in enumerate(actions):
        x = start_x + i * 215
        rounded(d, [x, 455, x + 170, 555], (255, 255, 255), (14, 165, 233), 2)
        center_text(d, [x, 462, x + 170, 505], cond, font(22), (2, 132, 199))
        center_text(d, [x, 507, x + 170, 548], act, font(20), (51, 65, 85))
    arrow(d, (740, 340), (740, 440), color=(245, 158, 11))
    center_text(d, [630, 375, 850, 430], "联动控制结果", font(24), (180, 83, 9))
    return save(img, "diagram_environment_flow.png")


def face_flow():
    img = Image.new("RGB", (1200, 690), (248, 250, 252))
    d = ImageDraw.Draw(img)
    title(d, "人脸门禁识别与预约权限判断流程")
    steps = [
        ("1 摄像头采集", "浏览器获取画面\n截取 JPEG 图像"),
        ("2 上传识别", "POST /api/face/verify\n发送到树莓派服务"),
        ("3 DeepFace 比对", "ArcFace 模型\nRetinaFace 检测"),
        ("4 权限判断", "匹配当前预约\n判断是否放行"),
        ("5 门禁联动", "自动签到\n开门 / 拒绝记录"),
    ]
    y = 155
    for i, (name, desc) in enumerate(steps):
        x = 70 + i * 220
        rounded(d, [x, y, x + 170, y + 155], (239, 246, 255), (37, 99, 235), 3)
        center_text(d, [x, y + 16, x + 170, y + 66], name, font(22), (30, 64, 175))
        center_text(d, [x + 10, y + 72, x + 160, y + 138], desc, font(18), (51, 65, 85))
        if i < len(steps) - 1:
            arrow(d, (x + 172, y + 78), (x + 216, y + 78), color=(37, 99, 235))
    rounded(d, [165, 440, 515, 555], (254, 242, 242), (239, 68, 68), 3)
    center_text(d, [165, 455, 515, 540], "失败分支：未匹配底库或无预约权限\n门禁保持关闭，生成异常访问记录", font(21), (153, 27, 27))
    rounded(d, [675, 440, 1035, 555], (240, 253, 244), (34, 197, 94), 3)
    center_text(d, [675, 455, 1035, 540], "成功分支：识别成功且匹配预约\n自动签到，门禁切换为已开门", font(21), (21, 128, 61))
    arrow(d, (810, 310), (820, 438), color=(34, 197, 94))
    arrow(d, (810, 310), (360, 438), color=(239, 68, 68))
    return save(img, "diagram_face_access_flow.png")


def three_flow():
    img = Image.new("RGB", (1200, 680), (248, 250, 252))
    d = ImageDraw.Draw(img)
    title(d, "3D会议室场景构建与传感器联动流程")
    boxes = [
        ("场景初始化", "Scene / Camera / Renderer\nOrbitControls 轨道控制"),
        ("程序化建模", "地面 / 墙体 / 桌椅\n屏幕 / 灯光 / 传感器点位"),
        ("实时数据接入", "定时请求传感器 API\n更新 sensorData 状态"),
        ("视觉联动", "灯光亮度 / 人员显隐\n空调状态 / 烟雾特效"),
    ]
    for i, (name, desc) in enumerate(boxes):
        x = 95 + i * 270
        rounded(d, [x, 170, x + 220, 330], (245, 243, 255), (124, 58, 237), 3)
        center_text(d, [x, 188, x + 220, 238], name, font(24), (91, 33, 182))
        center_text(d, [x + 12, 245, x + 208, 315], desc, font(18), (51, 65, 85))
        if i < 3:
            arrow(d, (x + 222, 250), (x + 265, 250), color=(124, 58, 237))
    rounded(d, [170, 455, 1030, 555], (255, 255, 255), (20, 184, 166), 3)
    center_text(d, [185, 465, 1015, 545], "物理会议室状态通过数据映射到虚拟场景，实现基础数字孪生展示", font(25), (15, 118, 110))
    arrow(d, (690, 332), (690, 450), color=(20, 184, 166))
    return save(img, "diagram_threejs_flow.png")


def read_lines(path, start, end):
    lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(f"{i + 1:>4}  {lines[i]}" for i in range(start - 1, min(end, len(lines))))


def code_image(title_text, code, name):
    wrapped_lines = []
    for raw in code.splitlines():
        if len(raw) <= 112:
            wrapped_lines.append(raw)
        else:
            parts = textwrap.wrap(raw, width=112, subsequent_indent="      ", replace_whitespace=False, drop_whitespace=False)
            wrapped_lines.extend(parts)
    width = 1800
    line_h = 28
    height = 120 + line_h * (len(wrapped_lines) + 1)
    img = Image.new("RGB", (width, height), (15, 23, 42))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, 70], fill=(17, 94, 89))
    d.text((32, 20), title_text, font=font(28), fill=(255, 255, 255))
    mono = font(20)
    y = 92
    for line in wrapped_lines:
        d.text((28, y), line, font=mono, fill=(226, 232, 240))
        y += line_h
    return save(img, name)


def code_assets():
    snippets = [
        (
            "环境控制前端：实时数据获取与接口容错",
            read_lines(ROOT / "FrontEnd/Intelligent_meeting_cloud/src/views/User/Control/index.vue", 129, 151),
            "code_environment_fetch.png",
        ),
        (
            "人脸门禁前端：刷脸核验与预约权限判断",
            read_lines(ROOT / "FrontEnd/Intelligent_meeting_cloud/src/views/User/Control/components/FaceCapture.vue", 145, 184),
            "code_face_access_decision.png",
        ),
        (
            "人脸识别后端：DeepFace 比对与最佳匹配返回",
            read_lines(ROOT / "MachineLearning/human_face/face_api.py", 77, 104),
            "code_face_api_deepface.png",
        ),
        (
            "3D会议室：传感器数据驱动虚拟场景联动",
            read_lines(ROOT / "FrontEnd/Intelligent_meeting_cloud/src/views/User/Room3D/index.vue", 646, 688),
            "code_threejs_sensor_visuals.png",
        ),
    ]
    return [code_image(*item) for item in snippets]


if __name__ == "__main__":
    paths = [architecture(), environment_flow(), face_flow(), three_flow()]
    paths.extend(code_assets())
    for p in paths:
        print(p)
