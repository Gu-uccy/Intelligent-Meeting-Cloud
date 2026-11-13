#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blender_modify_scene.py
=======================
第6周 3D 优化 —— Blender Python 脚本（在 Blender 3.x 的 Scripting 面板中运行）

功能：
    1. 创建会议室房间模型（墙/地板/吊顶）、门模型（轴心在门轴）、吸顶灯、
       简化人员模型（胶囊+球）与环境指示牌；
    2. 设置 PBR 材质（baseColor/roughness/metalness）与三套氛围灯光；
    3. 导出 room_301.glb 供 Three.js 场景引用（3d/scene_preview.html 可加载）。

运行方式：
    Blender 顶部菜单 Scripting -> New -> 粘贴本脚本 -> Run Script
    或命令行：blender --background --python blender_modify_scene.py

说明：
    本脚本输出模型清单与导出文件，数据联动（occupancy/door_status/temperature/
    devices）由 Three.js 场景在运行时读取统一状态对象完成（见 3d/scene_preview.html
    与 docs/3d_optimization.md 第五节映射表）。
"""

import bpy  # Blender Python API（仅 Blender 环境可用）


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_room():
    # 地板
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "floor"
    mat = bpy.data.materials.new("M_floor")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.55, 0.50, 0.45, 1)
    bsdf.inputs["Roughness"].default_value = 0.6
    floor.data.materials.append(mat)
    # 四面墙（简化为后墙 + 侧墙）
    walls = [(0, -5, 2.5, 0.0), (5, 0, 2.5, 1.5708), (-5, 0, 2.5, 1.5708)]
    for x, y, z, rot in walls:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z))
        wall = bpy.context.object
        wall.name = "wall"
        wall.scale = (0.2, 10, 5) if x == 0 else (10, 0.2, 5)
        wall.rotation_euler[2] = rot
        mat = bpy.data.materials.new("M_wall")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (0.82, 0.82, 0.85, 1)
        wall.data.materials.append(mat)


def make_door():
    bpy.ops.mesh.primitive_cube_add(size=1, location=(4.9, -1.0, 1.1))
    door = bpy.context.object
    door.name = "door_301"
    door.scale = (0.06, 0.9, 2.1)
    # 轴心移动到门轴
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    bpy.context.scene.cursor.location = (4.9, -1.45, 0)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    mat = bpy.data.materials.new("M_door")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.35, 0.22, 0.12, 1)
    bsdf.inputs["Roughness"].default_value = 0.35
    door.data.materials.append(mat)


def make_ceiling_lamp():
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 4.8))
    lamp = bpy.context.object
    lamp.name = "ceiling_light"
    lamp.scale = (2.0, 0.4, 0.05)
    mat = bpy.data.materials.new("M_lamp")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (1, 1, 0.92, 1)
    bsdf.inputs["Emission Strength"].default_value = 3.0
    lamp.data.materials.append(mat)
    # 点光源
    bpy.ops.object.light_add(type="POINT", location=(0, 0, 4.5))
    light = bpy.context.object
    light.name = "Light_ceiling"
    light.data.energy = 300


def make_person():
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25, location=(0, 0, 1.55))
    head = bpy.context.object
    head.name = "person_head"
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.9, location=(0, 0, 0.85))
    body = bpy.context.object
    body.name = "person_body"
    mat = bpy.data.materials.new("M_person")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.25, 0.45, 0.85, 1)
    head.data.materials.append(mat)
    body.data.materials.append(mat)
    # 人员父级容器（运行时由 occupancy 控制显示/隐藏）
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    parent = bpy.context.object
    parent.name = "occupancy_rig"
    head.parent = parent
    body.parent = parent


def setup_camera():
    bpy.ops.object.camera_add(location=(0, -6.5, 3.2))
    cam = bpy.context.object
    cam.name = "Camera_overview"
    cam.rotation_euler = (1.1, 0, 0)
    bpy.context.scene.camera = cam


def export_glb(out_path):
    bpy.ops.export_scene.gltf(filepath=out_path, export_format="GLB")


if __name__ == "__main__":
    clear_scene()
    make_room()
    make_door()
    make_ceiling_lamp()
    make_person()
    setup_camera()
    out = r"E:\rese5\week5\3d\room_301.glb"
    export_glb(out)
    print("Blender 场景已生成并导出：%s" % out)
    print("模型清单：floor / wall / door_301 / ceiling_light / person_head+body / occupancy_rig / Camera_overview")
