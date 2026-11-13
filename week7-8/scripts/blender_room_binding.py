# -*- coding: utf-8 -*-
"""Blender 4.x 建模脚本：智能会议室 301（状态绑定锚点命名）

在 Blender 中执行：
    Scripting 面板 → Run Script
或命令行：
    blender --background --python blender_room_binding.py -- --room 301 --out D:\\export\\room_301.glb

脚本产出：
    1. 房间（地板/墙/吊顶）、会议桌、12 把椅子、左右门（Origin 在门轴）
    2. 8 个人形简模（Person_01..08，按 people_count 显隐）
    3. 3 盏顶灯（灯罩 emission + Point Light，按 lighting/brightness 驱动）
    4. DHT 指示牌（temperature/humidity 文本）
    5. 烟雾信标（SmokeBeacon，置于吊顶中心上方无遮挡）
    6. 3 台相机（与前端三视角数值一致）
    7. 每个对象写入 state_key 自定义属性，导出 .glb

约定：对象名是 Three.js 侧 scene.getObjectByName() 的唯一锚点，改名即断链。
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOM_CONFIG = {
    "301": {"floor": (0x6A, 0x46, 0x37), "wall": (0xF6, 0xEF, 0xE4), "accent": (0xB9, 0x85, 0x52),
            "size": (12.0, 7.0), "chairs": 12, "people": 8},
    "302": {"floor": (0x53, 0x63, 0x6D), "wall": (0xE7, 0xEE, 0xF2), "accent": (0x2F, 0x7C, 0x9F),
            "size": (14.0, 8.0), "chairs": 24, "people": 8},
    "501": {"floor": (0x6B, 0x5B, 0x45), "wall": (0xF4, 0xF0, 0xDF), "accent": (0x3B, 0x9F, 0x7F),
            "size": (11.0, 7.0), "chairs": 16, "people": 8},
}

CAMERAS = [
    ("Camera_Overview", (10.8, 5.2, 11.2), (0.0, 0.82, -0.35)),
    ("Camera_Front", (0.0, 3.35, 11.8), (0.0, 0.92, -0.65)),
    ("Camera_Top", (0.02, 11.2, 0.02), (0.0, 0.0, -0.4)),
]


def srgb(rgb_tuple):
    """0-255 → 0-1 线性近似（Blender base_color 期望线性值）。"""
    return tuple((c / 255.0) for c in rgb_tuple)


def make_material(name, rgb, roughness=0.6, metallic=0.0, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*srgb(rgb), 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*srgb(emission), 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def add_box(name, size, location, material, state_key=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (size[0] / 2.0, size[1] / 2.0, size[2] / 2.0)
    obj.data.materials.append(material)
    if state_key:
        obj["state_key"] = state_key
    return obj


def add_cylinder(name, radius, depth, location, material, state_key=None, vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=location, vertices=vertices)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material)
    if state_key:
        obj["state_key"] = state_key
    return obj


def add_door(name, hinge_location, width=0.95, height=2.1, thickness=0.05, material=None):
    """门扇：把网格整体右移半宽，使**局部原点落在门轴**，旋转即绕门轴开合。"""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (width / 2.0, thickness / 2.0, height / 2.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # 平移网格数据，使对象原点位于门的左边缘（门轴）
    for v in obj.data.vertices:
        v.co.x += width / 2.0
    obj.location = hinge_location
    obj.data.materials.append(material)
    obj["state_key"] = "door_open"
    obj["open_rotation_deg"] = -93.6
    return obj


def add_person(name, location, material):
    """人形简模：胶囊（圆柱 + 上下球）+ 头部球，合并为一个对象。"""
    bpy.ops.mesh.primitive_cylinder_add(radius=0.16, depth=0.9, location=(location[0], location[1], location[2] + 0.45))
    body = bpy.context.active_object
    body.name = name + "_body"
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.14, location=(location[0], location[1], location[2] + 1.05))
    head = bpy.context.active_object
    head.name = name + "_head"

    body.select_set(True)
    head.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material)
    obj["state_key"] = "people_count"
    return obj


def add_text_panel(name, text, location, material, size=0.18):
    """文字牌：Text → MESH，导出后可被 Three.js 直接渲染。"""
    bpy.ops.object.text_add(location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.body = text
    obj.data.size = size
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.active_object
    obj.data.materials.append(material)
    obj["state_key"] = "temperature"
    return obj


def add_camera(name, location, target):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = 35
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = Vector(location)
    direction = Vector(target) - Vector(location)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return cam


def build(room_id="301", out_path=None):
    cfg = ROOM_CONFIG.get(room_id, ROOM_CONFIG["301"])
    w, d = cfg["size"]

    bpy.ops.wm.read_factory_settings(use_empty=True)

    mat_floor = make_material("MAT_Floor", cfg["floor"], roughness=0.6)
    mat_wall = make_material("MAT_Wall", cfg["wall"], roughness=0.85)
    mat_wood = make_material("MAT_Wood", cfg["accent"], roughness=0.45)
    mat_metal = make_material("MAT_Metal", (0x8A, 0x8F, 0x96), roughness=0.35, metallic=0.4)
    mat_fabric = make_material("MAT_Fabric", (0x33, 0x41, 0x55), roughness=0.75)
    mat_person = make_material("MAT_Person", (0xE8, 0xC4, 0x7D), roughness=0.6)
    mat_lamp = make_material("MAT_Lamp", (0xFF, 0xF0, 0xC2), roughness=0.3,
                             emission=(0xFF, 0xF2, 0xD0), emission_strength=6.0)
    mat_screen = make_material("MAT_Screen", (0x34, 0xD3, 0x99), roughness=0.2,
                               emission=(0x34, 0xD3, 0x99), emission_strength=2.0)
    mat_alarm = make_material("MAT_Alarm", (0xEF, 0x44, 0x44), roughness=0.4,
                              emission=(0xEF, 0x44, 0x44), emission_strength=4.0)

    # 房间
    floor = add_box("Room_Floor", (w, d, 0.1), (0, 0, -0.05), mat_floor)
    ceiling = add_box("Room_Ceiling", (w, d, 0.1), (0, 0, 3.1), mat_wall)
    add_box("Room_Wall_Back", (w, 0.1, 3.1), (0, -d / 2, 1.55), mat_wall)
    add_box("Room_Wall_Left", (0.1, d, 3.1), (-w / 2, 0, 1.55), mat_wall)
    add_box("Room_Wall_Right", (0.1, d, 3.1), (w / 2, 0, 1.55), mat_wall)

    # 会议桌
    add_box("Table_Main", (w * 0.62, 1.2, 0.08), (0, 0, 0.76), mat_wood)
    add_box("Table_Leg_L", (0.1, 0.9, 0.72), (-w * 0.25, 0, 0.36), mat_metal)
    add_box("Table_Leg_R", (0.1, 0.9, 0.72), (w * 0.25, 0, 0.36), mat_metal)

    # 椅子（沿两侧排布）
    half = cfg["chairs"] // 2
    spacing = min(0.9, (w * 0.55) / max(1, half))
    for i in range(half):
        x = -w * 0.52 + 0.5 + i * spacing
        for side, y in (("A", 0.95), ("B", -0.95)):
            add_box("Chair_%s%02d" % (side, i + 1), (0.45, 0.45, 0.9), (x, y, 0.45), mat_fabric)

    # 门（门轴在 x=+w/2 的右侧，向内开 93.6°）
    hinge = (w / 2 - 0.05, d / 2 - 0.1, 1.05)
    add_door("Door_Leaf", hinge, material=mat_wood)
    add_box("Door_Frame", (0.1, 0.12, 2.2), (w / 2 - 0.05, d / 2 - 0.16, 1.1), mat_metal)

    # 人员
    for i in range(cfg["people"]):
        x = -w * 0.35 + i * (w * 0.7 / max(1, cfg["people"] - 1))
        add_person("Person_%02d" % (i + 1), (x, 1.55, 0.0), mat_person)

    # 顶灯（灯罩 + 光源）
    for i in range(3):
        x = -w / 4 + i * (w / 4)
        lamp = add_box("CeilingLight_%02d" % (i + 1), (1.2, 0.22, 0.06), (x, 0, 2.98),
                       mat_lamp, state_key="lighting")
        light_data = bpy.data.lights.new("Light_%02d" % (i + 1), type="AREA")
        light_data.energy = 60
        light_data.size = 1.2
        light = bpy.data.objects.new("Light_%02d" % (i + 1), light_data)
        bpy.context.scene.collection.objects.link(light)
        light.location = (x, 0, 2.9)
        light["state_key"] = "lighting"

    # 环境指示牌
    add_text_panel("DHT_Panel", "24.5C / 50%", (w / 2 - 0.3, -d / 2 + 0.06, 2.2), mat_screen, size=0.28)

    # 烟雾信标（吊顶中心，上方无遮挡）
    add_cylinder("SmokeBeacon", 0.22, 0.14, (0, 0, 2.94), mat_alarm, state_key="smoke")

    # 空调 / 加湿
    add_box("HVAC_Unit", (1.4, 0.35, 0.5), (w / 2 - 0.5, d / 2 - 0.4, 2.6), mat_metal, state_key="cooling")
    add_box("Humidifier", (0.5, 0.5, 0.9), (-w / 2 + 0.6, d / 2 - 0.6, 0.45), mat_metal, state_key="humidifier")

    # 三台相机
    for name, loc, target in CAMERAS:
        add_camera(name, loc, target)

    # 导出
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        bpy.ops.export_scene.gltf(
            filepath=out_path,
            export_format="GLB",
            export_apply=True,
            export_extras=True,
            export_cameras=True,
            export_lights=True,
            use_selection=False,
        )
        print("已导出：%s" % out_path)

    print("对象总数：%d（含相机与灯光）" % len(bpy.data.objects))
    return bpy.data.objects


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    room = "301"
    out = None
    for i, a in enumerate(argv):
        if a == "--room" and i + 1 < len(argv):
            room = argv[i + 1]
        if a == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
    build(room_id=room, out_path=out)


if __name__ == "__main__":
    main()
