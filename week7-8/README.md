# 第 7-8 周提交材料（3D 动态 + 节点闭环）

> 对应任务书：《智能会议室管理系统III——第7-8周项目实践任务》
> 依托仓库：https://github.com/Gu-uccy/Intelligent-Meeting-Cloud
> 本目录存放文档、脚本与截图证据；功能代码位于仓库主目录。

## 一、目录结构

```
week7-8/
├─ README.md                          提交说明 + 接口冻结摘要 + 运行方式
├─ docs/
│  ├─ 01_状态字段表.md                 4 类状态逐字段映射（含代码行号）
│  ├─ 02_实时联动与刷新机制.md          轮询机制定性、实测数据、录屏脚本
│  ├─ 03_交互与异常提示说明.md          操作清单 + 异常提示设计与实现
│  ├─ 04_接口冻结清单.md               api-v1.0：路径/参数/返回字段/错误处理
│  ├─ 05_端适配与分辨率记录.md          5 档分辨率实测 + 窄屏整改
│  ├─ 06_联调记录.md                   15 步联调 + 故障排查手册 + 缺陷表
│  ├─ 07_3D闭环与Blender工具说明.md     模型清单/导出规范/接入代码
│  ├─ 08_周推进计划_第7周.md
│  └─ 09_周推进计划_第8周.md
├─ scripts/
│  ├─ verify_state_binding.py         状态字段校验（29 字段 + 派生 + 阈值口径）
│  ├─ check_interfaces.py             接口冒烟 + 错误码 + 顺序/并发性能
│  ├─ screenshot_matrix.ps1           5 档分辨率截图（Chrome headless）
│  └─ blender_room_binding.py         Blender 4.x 建模 + glb 导出
└─ results/
   ├─ 接口字段快照.json
   ├─ 接口冒烟结果.json
   ├─ 状态字段校验结果.json
   ├─ 轮询刷新实测.json
   ├─ 端适配测试记录.csv
   ├─ 采集原始数据_第8周.json
   └─ screenshots/                    9 张截图（1920×1080 至 390×844）
```

## 二、任务书要求与交付位置

### 第 7 周

| # | 要求 | 本组实现 | 材料位置 |
| --- | --- | --- | --- |
| 1 | 至少 3 类状态随数据变化更新 | 4 类：人员人形、门 93.6° 旋转、温湿度面板与指示牌、照明/报警/距离 | `docs/01` |
| 2 | 基于统一状态对象与接口 | 字段差异逐条登记并统一口径 | `docs/01` 第四节 |
| 3 | 一类实时联动 + 说清轮询还是推送 | 门/灯/人员/读数四类联动；机制为前端轮询，周期 3 s（实测 3.01 s） | `docs/02`、`results/轮询刷新实测.json` |
| 4 | 点击/旋转/缩放/视角切换 | 射线拾取点门点灯、OrbitControls、三视角、三氛围 | `docs/03` |
| 5 | 异常状态有明显提示 | 顶部状态横幅（文字 + 数值 + 设定区间）配合颜色与 3D 强化 | `docs/03` |
| 6 | 停后端检验状态来源 | 断开时进入断连态：横幅提示、场景降饱和、控制禁用、退避重连 | `docs/03`、`docs/06` |

### 第 8 周

| # | 要求 | 本组实现 | 材料位置 |
| --- | --- | --- | --- |
| 1 | 3D 闭环 | 15 步联调，覆盖数据、接口、场景、界面读数 | `docs/06` |
| 2 | 一种端适配 + 分辨率记录 + 跨分辨率截图 | 桌面端四档通过；390×844 窄屏问题已记录并给出断点整改 | `docs/05`、`results/screenshots/` |
| 3 | 冻结核心接口 | api-v1.0，含路径、参数、返回字段、错误码、降级总表 | `docs/04` |
| 4 | 阶段演示 2 | 8 分钟演示脚本 | `docs/09` 第五节 |
| 5 | 可运行 3D 模块 | `Room3D` 页面 | 仓库 `src/views/User/Room3D/` |
| 6 | 工具：Blender 或 Unity 改模型/材质/灯光/相机/交互 | Blender 4.x 建模 + glb 导出 + GLTFLoader 接入，脚本与命名规范见文档 | `docs/07`、`scripts/blender_room_binding.py` |

### 3D 最低要求表

| 项 | 要求周 | 本组实现 |
| --- | --- | --- |
| 模型和场景 | 第 6 周 | 三间会议室，程序化几何体与 glb 资产双路径 |
| 状态显示 | 第 7 周 | 4 类状态绑定 |
| 操作与提示 | 第 7 周 | 射线拾取、视角/氛围切换、状态横幅 |
| 一种端适配 | 第 8 周 | 桌面端四档分辨率 |
| 数据/3D 联调 | 第 8 周 | 15 步联调记录 |
| 工具（Blender/Unity） | 全程 | Blender 4.x 建模与 glb 导出接入 |

## 三、接口冻结摘要

详细定义见 `docs/04_接口冻结清单.md`。

| 接口 | 方法 | 关键字段 | 错误处理 |
| --- | --- | --- | --- |
| `/api/current` | GET | 17 顶层字段 + `devices` 12 字段 + `timestamp` | 数据未就绪 503 `{"error":"Sensor data not available"}` |
| `/api/control` | GET | — | 405 |
| `/api/control` | POST | `action`(manual/set_auto/set_params)、`device`、`state`、`brightness`、`source` | 非法 action 400 `Unknown action`；空 body 400 `Invalid request`；未知路径 404 |
| `/api/history` | GET | 最多 120 点，含 time/temperature/humidity/distance/motion/light/smoke | — |
| `/api/export/csv` | GET | `text/csv`，15 列中文表头 | 无数据 503 |
| `/chart/temp_humidity`、`/chart/distance_motion`、`/chart/sensor` | GET | `image/png` | 未生成 503 |
| `/api/health` | GET | `status`、`uptime_s`、`sensor_age_s`、`timestamp` | 采集超时 503 + `degraded` |

冻结规则：只增可选字段；删除、改名、改类型升 v2.0 并保留 v1 一个版本周期；字段调整同步本文件与 README。

## 四、运行方式

```powershell
# 1. 传感器服务
cd <仓库>\Flask
pip install flask flask-cors matplotlib numpy
python unified_meeting_room_system.py

# 2. 前端
cd <仓库>\FrontEnd\Intelligent_meeting_cloud
npm install
$env:VITE_SENSOR_PROXY_TARGET="http://127.0.0.1:5000"
npm run dev

# 3. 打开 3D 页面
#    http://127.0.0.1:5173/room-3d

# 4. 校验脚本
python scripts\verify_state_binding.py --base http://127.0.0.1:5000
python scripts\check_interfaces.py    --base http://127.0.0.1:5000
powershell -ExecutionPolicy Bypass -File scripts\screenshot_matrix.ps1 -Base http://127.0.0.1:5173
```

预期输出：

- `verify_state_binding.py`：字段总数 29，全部存在且类型一致；
- `check_interfaces.py`：11 条用例通过 10 条，唯一偏差为 D-07；
- `screenshot_matrix.ps1`：5 档分辨率产出 png 并生成 CSV 记录。

## 五、运行环境与数据来源

1. 截图、接口返回、性能数字均为本机真实运行产物：Windows 11，Ryzen 9 7945HX，31.7 GB 内存，Python 3.13，Node 22，Chrome 156；
2. 传感器为项目内置模拟模式：未检测到树莓派时打印「警告: 未检测到树莓派环境，使用模拟传感器数据运行」，数据链路与实机一致，`sensor_loop` 每 3 s 采集一次，写入 `data/unified_sensor_log.txt`；
3. 业务接口（Spring Boot）依据 `MeetingRoom-Management` 源码与 `Database/smart-meeting-room-db` 建库脚本整理，3D 链路不依赖业务后端；
4. 图表与历史数据来自 `/api/history`、`/api/export/csv`、`/chart/*`，均可由脚本复现。

## 六、缺陷编号

| 编号 | 等级 | 问题 |
| --- | --- | --- |
| D-01 | 中 | 390×844 窄屏重叠、横向溢出 |
| D-02 | 高 | 接口断开后静默降级、仍渲染完整场景 |
| D-03 | 高 | 烟雾报警在 3D 中不可见 |
| D-04 | 高 | 烟雾阈值三处不一致（100/60/未定义） |
| D-05 | 中 | `door_status` 与 `door_open` 两套口径 |
| D-06 | 中 | 温湿度阈值前端硬编码，未读接口字段 |
| D-07 | 中 | 空 body 返回 415 而非 400 |
| D-08 | 中 | 无健康检查接口 |
| D-09 | 中 | 接口未下发 `people_count`，人数恒为 1 |

整改方案与回归用例见 `../week9-11/docs/07_缺陷跟踪表.md`。
