# 第6周 3D 场景优化：模型/材质/灯光/交互 + 数据联动

## 一、现状与目标

- 综II现有 3D 场景：`FrontEnd/Intelligent_meeting_cloud/src/views/User/Room3D/index.vue`，基于 Three.js 程序化几何体构建 3 间会议室（董事会议室、培训研讨室、创意协作室），支持 3 种氛围模式与 3 个视角预设，每 2 秒轮询统一状态对象更新场景。
- 第6周要求：在已有 Three.js 方案基础上，**使用 Blender 或 Unity 3D 修改会议室模型、材质、灯光、相机与交互方式，并把设备或环境状态接到统一数据对象上**；至少 3 类状态（人员、门、温湿度、设备）随数据变化更新。

## 二、选型

本组选 **Blender 3.x（免费开源）+ 导出 glTF/GLB 接入 Three.js**：

- 原因：现有前端已是 Three.js，Blender 建模后导出 .glb 可直接替换程序化几何体，改动最小；Unity 工程较大，适合后续扩展时再迁移。
- 分工：模型与材质在 Blender 中完成，场景组织、相机与交互保留在 Three.js（`scene_preview.html` 为独立可运行的场景初版）。

## 三、模型清单与修改方案（Blender）

| 模型 | 现状 | 修改内容（Blender） | 材质/灯光 | 用途 |
| --- | --- | --- | --- | --- |
| 会议室房间 | 程序化长方体 | 替换为 Blender 建模房间（墙/地板/吊顶），导出 `room_301.glb` | PBR：地板粗糙度 0.6，墙体 base color 灰白 | 场景主体 |
| 门 | 无（仅状态文字） | 新增门模型（门扇 + 门框），轴心设置在门轴 | 金属/木纹 PBR | door_status 联动 |
| 会议桌/座椅 | 简单几何体 | 细化桌面与会客椅模型 | 桌面木纹、椅面布料 | 场景真实感 |
| 显示器/投影 | 简单平面 | 新增屏幕模型 | 自发光材质（emission） | 展示联动 |
| 人员模型 | 点光源占位 | 新增简化人形模型（胶囊+球） | 标准材质 | occupancy 联动 |
| 灯具 | 无 | 新增吸顶灯模型（发光体） | emission + 实际灯光源 | devices.lighting 联动 |
| 温湿度指示 | 无 | 新增环境指示牌（Text 模型） | 自发光文字 | temperature/humidity 联动 |

## 四、材质/灯光/相机/交互修改

| 项 | 修改方案 |
| --- | --- |
| 材质 | 全部改为 PBR（baseColor/roughness/metalness），灯光亮度用 emission 表现，避免纯色漫反射的“塑料感” |
| 灯光 | 主光：区域光（Area Light）模拟窗光；辅光：环境光 + 吸顶灯点光源；氛围模式：冷色（白天）/暖色（傍晚）/暗色（夜间）三套灯光参数，与综II Room3D 的 3 种氛围一致 |
| 相机 | 3 个预设视角（全景/桌面/门口）+ 轨道控制器（OrbitControls），与现有视角预设一致 |
| 交互 | 点击门 → 显示 door_status 与开门按钮（联动 mock 状态）；点击人员 → 显示占用与温湿度面板 |

## 五、状态数据联动

统一数据对象（第3周约定，`mock/state.json` / `results/state_with_baseline.json`）与 3D 场景的映射：

| 状态类 | 字段 | 3D 场景更新 |
| --- | --- | --- |
| 人员 | occupancy（或 presence/motion） | 显示/隐藏人员模型；多人按 occupancy=true 显示 |
| 门 | door_status（open/closed） | 门模型绕门轴旋转 90°（open）/归位（closed） |
| 温湿度 | temperature、humidity | 环境指示牌文字更新；温度越界时空调区域提示 |
| 设备 | devices.lighting、devices.alarm、smoke | lighting→灯光亮度；alarm/smoke→报警灯与烟雾粒子 |

独立可运行初版：`3d/scene_preview.html`（浏览器直接打开，内嵌统一状态对象，演示上述 4 类状态联动；联机时替换为轮询 `/api/rooms/{id}/state` 即可）。

## 六、Blender 修改脚本

`scripts/blender_modify_scene.py` 为 Blender Python 脚本（在 Blender 3.x 中通过 Scripting 面板运行）：创建房间/门/灯/人员模型，设置 PBR 材质与灯光，导出 `room_301.glb` 供 Three.js 场景引用。

## 七、验收对照

| 课堂要求 | 完成情况 |
| --- | --- |
| 在 Blender/Unity 中修改模型 | ✅ Blender 脚本 + 模型修改方案 |
| 材质/灯光/相机/交互修改 | ✅ 第四节方案 |
| 至少 3 类状态随数据变化更新 | ✅ 人员、门、温湿度、设备（4 类） |
| 场景初版/截图或联动录屏 | ✅ `3d/scene_preview.html`（可运行初版）+ `3d/场景截图_空闲.png`、`3d/场景截图_有人开门.png`（浏览器实测截图，已真实运行验证状态联动） |
