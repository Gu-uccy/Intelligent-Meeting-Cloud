# 3D 闭环说明与 Blender 工具落实（模型清单 / 导出 / 接入）

> 任务书原文：「**必须用 Blender 或 Unity 3D 修改模型、材质、灯光、相机、交互**」「沿用 Three.js 现状不改工具，即使状态绑定做完整，这项仍然不合格」。
> 因此本节点把“工具”单列一节，写清用什么工具、怎么导出、怎么接入，避免整项被判不合格。

## 一、闭环定义与当前达成情况

| 环节 | 要求 | 当前状态 | 证据 |
| --- | --- | --- | --- |
| 数据 | 传感器/模拟数据持续产生 | 已达成（3 s 采集，日志 114 行） | `Flask/data/unified_sensor_log.txt` |
| 后端接口 | 统一接口对外提供状态 | 已达成（`GET /api/current` 17 字段冻结） | `docs/04_接口冻结清单.md` |
| 3D 场景 | 状态映射到对象属性 | 已达成（4 类状态，见状态字段表） | `docs/01_状态字段表.md` |
| 用户能看懂 | 面板 + 场景 + 提示文案 | **部分达成**：面板/场景 OK，异常提示不合格（D-02/D-03） | `docs/03_交互与异常提示说明.md` |
| 工具 | 用 Blender/Unity 改模型 | **进行中**：Blender 建模脚本已交付，导出与接入待在工作站执行 | 本节 + `scripts/blender_room_binding.py` |

## 二、选型与分工

- 选型：**Blender 4.x（免费开源）→ 导出 glTF 2.0 (.glb) → Three.js `GLTFLoader` 接入**。
  理由：现有前端已是 Three.js，替换程序化几何体成本最低；Unity 需整套工程迁移，本学期不做。
- 分工（按组员填）：建模与材质（Blender）／导出与接入（前端）／状态绑定（前端）／灯光与相机预设（Blender + 前端各一半）。
- 版本与交付：`room_301.glb`（董事会议室）、`room_302.glb`、`room_501.glb`，单文件 ≤8 MB，三角面 ≤80k/间。

## 三、模型清单（Blender 端对象命名 = 状态绑定锚点）

| 对象名（Blender） | 类型 | 对应状态字段 | 材质/灯光要点 | 导出要求 | 用途 |
| --- | --- | --- | --- | --- | --- |
| `Room_Floor` | Mesh | — | PBR：baseColor #6a4637，roughness 0.6，metallic 0 | 合并为一个 mesh | 场景主体 |
| `Room_Wall` | Mesh | — | baseColor #f6efe4，roughness 0.8 | 单面法线朝内 | 场景主体 |
| `Room_Ceiling` | Mesh | — | 反照率 0.85，粗糙 0.9 | — | 遮挡与光感 |
| `Table_Main` | Mesh | — | 木纹 baseColor，roughness 0.45 | 保留 UV | 会议桌 |
| `Chair_01..Chair_12` | Mesh（实例） | — | 布料 baseColor #334155，roughness 0.7 | 实例化导出（共享 mesh） | 座椅 |
| **`Door_Leaf`** | Mesh | `door_open` | 门轴在左边缘（原点 x=0），木纹 PBR | **Origin 设在门轴**，否则旋转错位 | 开关门动画 |
| `Door_Frame` | Mesh | — | 金属 metallic 0.4 | — | 门框 |
| **`Person_01..Person_08`** | Mesh（简模） | `motion`/`presence`/`people_count` | 标准材质，颜色 #e8c47d | 命名连续，便于按 count 显隐 | 人数联动 |
| **`CeilingLight_01..03`** | Mesh + Light | `devices.lighting`、`lighting_brightness` | 灯罩 emission，强度 6；另建 Area Light | 灯罩与光源分开导出 | 照明联动 |
| **`DHT_Panel`** | Mesh + Text | `temperature`/`humidity` | 屏幕自发光 #34d399，文字用 Text 转 Mesh | Text 需转 Mesh 后导出 | 温湿度展示 |
| **`SmokeBeacon`** | Mesh | `smoke`（≥阈值） | 红色 emission #ef4444 | 置于吊顶中心，**上方无遮挡** | 报警可视化（修 D-03） |
| `HVAC_Unit` | Mesh | `devices.cooling`/`heating` | 蓝/橙两态用材质切换 | — | 空调状态 |
| `Humidifier` | Mesh | `devices.humidifier`/`dehumidifier` | 雾化口小面片 | — | 加湿状态 |
| `Camera_Overview` / `_Front` / `_Top` | Camera | — | 焦距 35mm，位置见下表 | 导出相机（含在 glb） | 三视角 |

相机预设（与前端 `viewOptions` 一致，Blender 单位米）：

| 相机 | 位置 (x,y,z) | 目标点 | 用途 |
| --- | --- | --- | --- |
| `Camera_Overview` | (10.8, 5.2, 11.2) | (0, 0.82, -0.35) | 全景 |
| `Camera_Front` | (0, 3.35, 11.8) | (0, 0.92, -0.65) | 正前方 |
| `Camera_Top` | (0.02, 11.2, 0.02) | (0, 0, -0.4) | 俯视 |

## 四、导出规范（Blender）

1. 场景单位：Metric，Scale 1.0，旋转已 Apply（`Ctrl+A → Rotation`），避免 GLB 里出现 −90° X 旋转；
2. 导出选项卡：`File → Export → glTF 2.0 (.glb)`，勾选 **Selected Objects**、`+Y Up`、`Apply Modifiers`；
3. 材质：只用 Principled BSDF，贴图打包（`Pack Images`），不使用程序化节点（除 Principled 外）；
4. 灯光：导出 `KHR_lights_punctual`，Three.js 侧 `GLTFLoader` 直接读；
5. 命名：**严格使用第三节对象名**，脚本靠 `scene.getObjectByName()` 绑定状态，改名即断链；
6. 每间导出前设置自定义属性（Custom Properties，导出到 glTF `extras`）：
   - `state_key`: `door_open` / `lighting` / `people_count` / `smoke` 等，供接入侧自动识别；
7. 校验：导出后用 `scripts/verify_glb.py`（可选）检查对象名齐全、`extras` 是否存在。

## 五、接入步骤（Three.js）

```js
// Room3D 中新增：模型加载替换程序化几何体
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

const loader = new GLTFLoader();
loader.load('/models/room_301.glb', (gltf) => {
  const root = gltf.scene;
  root.traverse((o) => {
    if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; }
  });
  roomGroup.add(root);

  // 状态绑定锚点：按命名取对象，替换原程序化对象引用
  liveObjects.door = { group: root.getObjectByName('Door_Leaf'), closedRotation: 0, openRotation: -Math.PI * 0.52 };
  liveObjects.people = ['Person_01','Person_02','Person_03','Person_04','Person_05','Person_06','Person_07','Person_08']
    .map(n => root.getObjectByName(n));
  liveObjects.ceilingLightMeshes = ['CeilingLight_01','CeilingLight_02','CeilingLight_03']
    .map(n => root.getObjectByName(n));
  liveObjects.beacon = root.getObjectByName('SmokeBeacon');
  liveObjects.dhtIndicator = root.getObjectByName('DHT_Panel');

  updateSensorVisuals(); // 加载完成后立即应用当前状态，避免“先空场景后跳变”
});
```

要点：

- 加载完成必须**立刻调一次 `updateSensorVisuals()`**，否则会先显示空场景再跳变；
- `Door_Leaf` 的旋转轴依赖 Blender 里的 Origin，接入后若门绕着错误点转，说明 Origin 没设在门轴；
- 模型加载失败要有回退（保留现有程序化几何体），并在页面提示「模型加载失败，已回退到简模」，不能白屏。

## 六、Blender 脚本（已交付）

`scripts/blender_room_binding.py`：在 Blender 4.x 的 Scripting 面板执行，或

```powershell
blender --background --python scripts/blender_room_binding.py -- --out D:\export\room_301.glb
```

脚本做的事：

1. 清空默认场景，按第三节清单生成房间/门（Origin 在门轴）/桌椅/人形/顶灯/DHT 指示牌/烟雾信标；
2. 全部使用 Principled BSDF（PBR）材质：地板 roughness 0.6、墙面 0.8、金属门框 metallic 0.4；
3. 布置 3 个 Area Light（主光/补光/窗光）+ 3 盏顶灯 Point Light；
4. 建 3 台相机（位置/目标与前端预设一致）；
5. 写入 `state_key` 自定义属性；
6. 导出 `.glb`（`export_scene.gltf`，`use_selection=False`，`export_extras=True`）。

> 说明：脚本可在无 Blender 的机器上编写与评审，但**必须在装有 Blender 的工作站实际运行并回填导出截图**才算“工具已使用”。回填位置：本节第七节。

## 七、工具使用证据（待工作站回填，不编造）

| 证据 | 文件 | 状态 |
| --- | --- | --- |
| Blender 版本与运行截图 | `results/blender_运行截图.png` | **待回填** |
| 导出文件 `room_301.glb` 体积/面数 | 填入下表 | **待回填** |
| 材质预览渲染图 | `results/blender_材质预览.png` | **待回填** |

| 模型 | 文件大小 | 三角面数 | 对象数 | 导出时间 |
| --- | --- | --- | --- | --- |
| room_301.glb |  |  |  |  |
| room_302.glb |  |  |  |  |
| room_501.glb |  |  |  |  |

## 八、验收对照

| 任务书要求 | 本组做法 | 状态 |
| --- | --- | --- |
| 必须用 Blender/Unity 改模型 | Blender 4.x 建模 + glb 导出接入，脚本与清单已交付 | 代码就绪，待工作站出图 |
| 改材质 | 全 PBR（地板/墙/木纹/金属/布料/自发光） | 同上 |
| 改灯光 | 3 个 Area Light + 3 个顶灯，冷/暖/暗三套参数 | 同上 |
| 改相机 | 3 台相机，与前端三视角数值一致 | 同上 |
| 改交互 | 点击门/灯 → 接口 → 回写 → 场景变化 | **已实测通过**（截图） |
| ≥3 类状态随数据更新 | 4 类（人员/门/温湿度/设备） | **已实测通过** |
