# 3D 闭环说明与 Blender 工具落实（模型清单 / 导出 / 接入）

> 任务书原文：「必须用 Blender 或 Unity 3D 修改模型、材质、灯光、相机、交互」。本文件说明工具选型、建模清单、导出规范与前端接入方式。

## 一、闭环五个环节

| 环节 | 实现方式 | 材料位置 |
| --- | --- | --- |
| 数据 | 传感器每 3 s 采集，写全局快照与 `data/unified_sensor_log.txt` | `Flask/unified_meeting_room_system.py` 613-640 行 |
| 后端接口 | `GET /api/current` 输出 17 顶层字段 + `devices` 12 字段 | `docs/04_接口冻结清单.md` |
| 3D 场景 | 4 类状态映射到对象属性，`updateSensorVisuals()` 统一应用 | `docs/01_状态字段表.md` |
| 用户能看懂 | 状态横幅 + 8 张数值卡片 + 场景内标签与指示灯 | `docs/03_交互与异常提示说明.md` |
| 工具 | Blender 4.x 建模、材质、灯光、相机，导出 glb 接入 GltfLoader | 本文件 |

## 二、选型与分工

- 选型：Blender 4.x（免费开源）→ 导出 glTF 2.0（.glb）→ Three.js `GLTFLoader` 接入。
  理由：前端已是 Three.js，替换程序化几何体成本最低；Unity 需整套工程迁移。
- 分工：建模与材质（Blender）、导出与接入（前端）、状态绑定（前端）、灯光与相机预设（Blender 建模 + 前端参数对齐）。
- 交付文件：`room_301.glb`（董事会议室）、`room_302.glb`（培训室）、`room_501.glb`（创意室），单文件 ≤8 MB，三角面 ≤80k/间。

## 三、模型清单（Blender 对象命名即状态绑定锚点）

| 对象名 | 类型 | 对应状态字段 | 材质/灯光要点 | 导出要求 | 用途 |
| --- | --- | --- | --- | --- | --- |
| `Room_Floor` | Mesh | — | PBR：baseColor #6a4637，roughness 0.6，metallic 0 | 合并为一个 mesh | 场景主体 |
| `Room_Wall` | Mesh | — | baseColor #f6efe4，roughness 0.8 | 单面法线朝内 | 场景主体 |
| `Room_Ceiling` | Mesh | — | 反照率 0.85，粗糙度 0.9 | — | 遮挡与光感 |
| `Table_Main` | Mesh | — | 木纹 baseColor，roughness 0.45 | 保留 UV | 会议桌 |
| `Chair_01..Chair_12` | Mesh（实例） | — | 布料 baseColor #334155，roughness 0.7 | 实例化导出，共享 mesh | 座椅 |
| `Door_Leaf` | Mesh | `door_open` | 门轴在左边缘，木纹 PBR | Origin 设在门轴 | 开关门动画 |
| `Door_Frame` | Mesh | — | 金属 metallic 0.4 | — | 门框 |
| `Person_01..Person_08` | Mesh（简模） | `motion` / `people_count` | 标准材质，颜色 #e8c47d | 命名连续，按人数显隐 | 人数联动 |
| `CeilingLight_01..03` | Mesh + Light | `devices.lighting`、`lighting_brightness` | 灯罩 emission，强度 6，另配 Area Light | 灯罩与光源分开导出 | 照明联动 |
| `DHT_Panel` | Mesh + Text | `temperature` / `humidity` | 屏幕自发光 #34d399，Text 转 Mesh | Text 转 Mesh 后导出 | 温湿度展示 |
| `SmokeBeacon` | Mesh | `smoke` | 红色 emission #ef4444 | 置于吊顶中心，上方无遮挡 | 报警可视化 |
| `HVAC_Unit` | Mesh | `devices.cooling` / `heating` | 蓝/橙两态材质切换 | — | 空调状态 |
| `Humidifier` | Mesh | `devices.humidifier` / `dehumidifier` | 雾化口小面片 | — | 加湿状态 |
| `Camera_Overview` / `_Front` / `_Top` | Camera | — | 焦距 35mm | 随 glb 导出 | 三视角 |

相机预设与前端 `viewOptions` 数值一致（Blender 单位米）：

| 相机 | 位置 (x,y,z) | 目标点 | 用途 |
| --- | --- | --- | --- |
| `Camera_Overview` | (10.8, 5.2, 11.2) | (0, 0.82, -0.35) | 全景 |
| `Camera_Front` | (0, 3.35, 11.8) | (0, 0.92, -0.65) | 正前方 |
| `Camera_Top` | (0.02, 11.2, 0.02) | (0, 0, -0.4) | 俯视 |

## 四、导出规范

1. 场景单位 Metric，Scale 1.0，旋转已 Apply（`Ctrl+A → Rotation`），避免 GLB 出现 −90° X 旋转；
2. `File → Export → glTF 2.0 (.glb)`，勾选 Selected Objects、+Y Up、Apply Modifiers；
3. 材质只用 Principled BSDF，贴图 Pack Images，不使用程序化节点；
4. 灯光导出 `KHR_lights_punctual`，Three.js 侧由 `GLTFLoader` 直接读取；
5. 命名严格使用第三节对象名，状态绑定靠 `scene.getObjectByName()`，改名即断链；
6. 每间导出前写入 Custom Properties，导出到 glTF `extras`：`state_key` = `door_open` / `lighting` / `people_count` / `smoke`；
7. 导出后校验对象名齐全与 `extras` 存在。

## 五、接入步骤

```js
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

const loader = new GLTFLoader();
loader.load('/models/room_301.glb', (gltf) => {
  const root = gltf.scene;
  root.traverse((o) => {
    if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; }
  });
  roomGroup.add(root);

  liveObjects.door = { group: root.getObjectByName('Door_Leaf'), closedRotation: 0, openRotation: -Math.PI * 0.52 };
  liveObjects.people = ['Person_01','Person_02','Person_03','Person_04','Person_05','Person_06','Person_07','Person_08']
    .map(n => root.getObjectByName(n));
  liveObjects.ceilingLightMeshes = ['CeilingLight_01','CeilingLight_02','CeilingLight_03']
    .map(n => root.getObjectByName(n));
  liveObjects.beacon = root.getObjectByName('SmokeBeacon');
  liveObjects.dhtIndicator = root.getObjectByName('DHT_Panel');

  updateSensorVisuals();
});
```

要点：

- 加载完成立即调用一次 `updateSensorVisuals()`，避免先空场景后跳变；
- `Door_Leaf` 的旋转轴依赖 Blender 中的 Origin，若门绕错误点旋转即 Origin 未设在门轴；
- 模型加载失败保留程序化几何体作为回退，并在页面提示「模型加载失败，已回退到简模」。

## 六、Blender 脚本

`scripts/blender_room_binding.py` 在 Blender 4.x 的 Scripting 面板执行，或：

```powershell
blender --background --python scripts/blender_room_binding.py -- --out D:\export\room_301.glb
```

脚本流程：

1. 清空默认场景，按第三节清单生成房间、门（Origin 在门轴）、桌椅、人形、顶灯、DHT 指示牌、烟雾信标；
2. 全部使用 Principled BSDF：地板 roughness 0.6、墙面 0.8、金属门框 metallic 0.4；
3. 布置 3 个 Area Light（主光/补光/窗光）与 3 盏顶灯 Point Light；
4. 建 3 台相机，位置与目标点同前端三视角；
5. 写入 `state_key` 自定义属性；
6. 导出 `.glb`（`export_scene.gltf`，`use_selection=False`，`export_extras=True`）。

## 七、工具使用对照

| 任务书要求 | 本组做法 |
| --- | --- |
| 用 Blender 改模型 | Blender 4.x 按模型清单重建三间会议室，门 Origin 设在门轴，桌椅实例化 |
| 改材质 | 全 PBR：地板/墙面/木纹/金属门框/布料座椅/自发光灯罩与屏幕 |
| 改灯光 | 3 个 Area Light + 3 盏顶灯，冷/暖/暗三套参数 |
| 改相机 | 3 台相机，数值与前端 `viewOptions` 一致 |
| 改交互 | 点击门/灯 → `/api/control` → 回写 → 场景变化，截图见 `results/screenshots/3d_dooropen_light_1920x1080.png` |
| 状态随数据更新 | 4 类（人员/门/温湿度/设备），绑定关系见 `docs/01` |
