# 第 7-8 周提交材料（3D 动态 + 节点闭环）

> 对应任务书：《智能会议室管理系统III——第7-8周项目实践任务》
> 依托仓库：https://github.com/Gu-uccy/Intelligent-Meeting-Cloud
> 本目录是**提交材料**（文档、脚本、截图证据），代码本身在仓库主目录，未在本目录重复存放。

## 一、目录结构

```
week7-8/
├─ README.md                          ← 本文件（提交说明 + 接口冻结摘要 + 运行方式）
├─ docs/
│  ├─ 01_状态字段表.md                 4 类状态逐字段映射（含代码行号）
│  ├─ 02_实时联动与刷新机制.md          轮询机制定性 + 实测 + 录屏脚本
│  ├─ 03_交互与异常提示说明.md          操作清单 + 异常提示逐项判定与整改
│  ├─ 04_接口冻结清单.md               api-v1.0：路径/参数/返回字段/错误处理
│  ├─ 05_端适配与分辨率记录.md          5 档分辨率实测 + 窄屏问题与修复
│  ├─ 06_联调记录.md                   15 步联调 + 故障排查手册 + 缺陷表
│  ├─ 07_3D闭环与Blender工具说明.md     模型清单/导出规范/接入代码/工具证据
│  ├─ 08_周推进计划_第7周.md
│  └─ 09_周推进计划_第8周.md
├─ scripts/
│  ├─ verify_state_binding.py         状态字段校验（29 字段 + 派生 + 阈值口径）
│  ├─ check_interfaces.py             接口冒烟 + 错误码 + 顺序/并发性能
│  ├─ screenshot_matrix.ps1           5 档分辨率截图（Chrome headless）
│  └─ blender_room_binding.py         Blender 4.x 建�� + glb 导出（状态锚点命名）
└─ results/
   ├─ 接口字段快照.json                 /api/current 全字段样本
   ├─ 接口冒烟结果.json                 11 条用例 + 性能统计
   ├─ 状态字段校验结果.json              字段/类型/阈值校验结论
   ├─ 轮询刷新实测.json                 10 次采样、间隔 3.01 s、9/9 有变化
   ├─ 端适配测试记录.csv                 截图 ↔ 分辨率 ↔ 判定
   └─ screenshots/                     9 张真实截图（含 390×844 窄屏）
```

## 二、逐条对照任务书要求

### 第 7 周

| # | 要求 | 本组交付 | 判定 |
| --- | --- | --- | --- |
| 1 | 至少 3 类状态随数据变化更新（人员/门/温湿度/设备） | 4 类：人员 8 人形、门 93.6° 旋转、温湿度面板、照明/报警 | 通过（`docs/01`） |
| 2 | 基于第 3 周统一状态对象与接口 | 字段差异 4 处已逐条登记并对齐口径 | 通过（`docs/01` 第四节） |
| 3 | 至少一类实时联动 + 录屏 + 说清轮询还是推送 | 门/灯/人员/读数四类联动；机制=**轮询 3 s**，实测 3.01 s | 机制已说明；**录屏待录制**（脚本见 `docs/02` 第五节） |
| 4 | 至少一种点击/旋转/缩放/视角切换 | Raycaster 点门/点灯 + OrbitControls + 三视角 + 三氛围 | 通过（`docs/03`） |
| 5 | 异常状态有明显提示，不能只靠颜色 | **当前不达标**（颜色为主，烟雾信标被墙遮挡） | **不通过 → D-03/D-04**，方案已给 |
| 6 | 停掉后端仍显示正常内容 = 写死 | 已主动做“停服务检验”，暴露静默降级 | **不通过 → D-02**，方案已给 |

### 第 8 周（节点周）

| # | 要求 | 本组交付 | 判定 |
| --- | --- | --- | --- |
| 1 | 3D 闭环：数据→接口→场景→用户看懂 | 15 步联调，13 步通过 | 链路通，提示项待修（`docs/06`） |
| 2 | 一种端适配 + 记录分辨率 + 跨分辨率截图 | 桌面端 4 档通过；390×844 窄屏测出不通过 | 桌面端通过；窄屏问题已登记（`docs/05`） |
| 3 | 冻结核心接口写进接口文档与 README | `docs/04` + 本文第三节 | 通过（api-v1.0） |
| 4 | 交付：跨分辨率截图 | 9 张（`results/screenshots`） | 通过 |
| 5 | 交付：联调记录 | `docs/06` | 通过 |
| 6 | 交付：阶段演示 2 | 8 分钟脚本（`docs/09` 第五节） | 脚本就绪，**待排练** |
| 7 | 交付：可运行 3D 模块 | `Room3D` 页面实测可运行 | 通过 |
| 8 | 交付：接口清单文档 | `docs/04` | 通过 |
| 9 | 工具：必须用 Blender/Unity 改模型/材质/灯光/相机 | Blender 4.x 方案 + 建模脚本 + 模型清单 | **代码就绪，待工作站导出回填** |

### 3D 最低要求表（必须）

| 项 | 要求周 | 状态 |
| --- | --- | --- |
| 模型和场景 | 第 6 周 | 已有（程序化几何体 → 待换 glb） |
| 状态显示 | 第 7 周 | 通过 |
| 操作与提示 | 第 7 周 | 操作通过；**提示不通过（待修）** |
| 一种端适配 | 第 8 周 | 桌面端通过 |
| 数据/3D 联调 | 第 8 周 | 通过 |
| 工具（Blender/Unity） | 全程 | **未完成，待实际导出** |

> 务必注意任务书原话：“沿用 Three.js 现状不改工具，即使状态绑定做完整，这项仍然不合格”。**Blender 必须真的跑起来并导出 glb**，回填位置见 `docs/07` 第七节。

## 三、接口冻结摘要（详见 `docs/04`）

| 接口 | 方法 | 关键字段 | 错误处理 |
| --- | --- | --- | --- |
| `/api/current` | GET | 17 顶层字段 + `devices` 11 字段 + `timestamp` | 数据未就绪 503 `{"error":"Sensor data not available"}` |
| `/api/control` | POST | `action`(manual/set_auto/set_params)、`device`、`state`、`brightness`、`source` | 非法 action 400 `Unknown action`；空 body 400（带 JSON 头）/ 415（无头，待修 D-07）；GET 405；未知路径 404 |
| `/api/history` | GET | 最多 120 点，每点 time/temperature/humidity/distance/motion/light/smoke | — |
| `/api/export/csv` | GET | `text/csv` | 无数据 503 |
| `/chart/temp_humidity`、`/chart/distance_motion`、`/chart/sensor` | GET | `image/png` | 未生成 503 |
| `/api/health` | GET | **建议第 9 周新增**：`{status, uptime_s, sensor_age_s, timestamp}` | 当前 404 |

冻结规则：只允许新增可选字段；删除/改名/改类型须升 v2.0 并保留 v1 一个版本周期；改字段必须同步本 README 与 `docs/04`。

## 四、如何跑起来（现场 3 分钟复现）

```powershell
# 1. 传感器服务（模拟模式，本机无树莓派）
cd <仓库>\Flask
pip install flask flask-cors matplotlib numpy   # 首次
python unified_meeting_room_system.py            # 监听 0.0.0.0:5000

# 2. 前端
cd <仓库>\FrontEnd\Intelligent_meeting_cloud
npm install
$env:VITE_SENSOR_PROXY_TARGET="http://127.0.0.1:5000"
npm run dev                                       # http://127.0.0.1:5173

# 3. 打开 3D 页面
#    http://127.0.0.1:5173/room-3d

# 4. 一键校验（本目录内执行）
python scripts/verify_state_binding.py --base http://127.0.0.1:5000
python scripts/check_interfaces.py    --base http://127.0.0.1:5000
powershell -ExecutionPolicy Bypass -File scripts/screenshot_matrix.ps1 -Base http://127.0.0.1:5173
```

预期输出：

- `verify_state_binding.py`：字段总数 29、异常 0、阈值不一致 5 处；
- `check_interfaces.py`：10/11 通过（唯一失败项 D-07：空 body 415）；
- `screenshot_matrix.ps1`：5 档分辨率全部产出 png + CSV 记录。

## 五、数据真实性说明（重要，验收会问）

1. 所有截图、接口返回、性能数字均为**本机真实运行**产物（Windows 11 / Ryzen 9 7945HX / Python 3.13 / Node 22 / Chrome 156）；
2. 传感器为**模拟模式**（仓库代码内置降级：未检测到树莓派时打印「警告: 未检测到树莓派环境，使用模拟传感器数据运行」），但数据链路真实：`sensor_loop` 每 3 s 生成 → `/api/current` → 前端轮询 → 3D 属性；
3. 业务后端（Spring Boot）**本轮未启动**（本机无 Maven），业务接口按源码与 `Database/smart-meeting-room-db` 脚本核对，**未声称已联调通过**；
4. 凡未完成项一律标「待回填 / 待录制 / 未完成」，不编造截图与数字。

## 六、已知缺陷（第 9-11 周要闭环，编号连续）

| 编号 | 等级 | 问题 | 归属 |
| --- | --- | --- | --- |
| D-01 | 中 | 390×844 窄屏重叠、横向溢出 | 第 9 周 |
| D-02 | 高 | 接口断开后静默降级、仍渲染完整场景 | 第 9 周 |
| D-03 | 高 | 烟雾报警在 3D 中不可见 | 第 8 周 |
| D-04 | 高 | 烟雾阈值三处不一致（100/60/未定义） | 第 8 周 |
| D-05 | 中 | `door_status` 与 `door_open` 两套口径 | 第 8 周 |
| D-06 | 中 | 温湿度阈值前端硬编码，未读接口字段 | 第 9 周 |
| D-07 | 中 | 空 body 返回 415 而非 400 | 第 9 周 |
| D-09 | 中 | 接口未下发 `people_count`，人数恒为 1（8 个人形只显示 1 个） | 第 9 周 |

跟踪表见 `week9-11/docs/07_缺陷跟踪表.md`。

## 七、待办提醒（提交前当天完成）

- [ ] 录制 3 分钟联动录屏，放入 `results/录屏_3D联动.mp4`（脚本已给）；
- [ ] 在工作站安装 Blender 4.x，运行 `scripts/blender_room_binding.py` 导出 `room_301/302/501.glb`，回填 `docs/07` 第七节证据表；
- [ ] 合入 D-02/D-03/D-04 修复后重跑 `check_interfaces.py` 与截图，替换 `results/` 中旧证据；
- [ ] 在 GitHub 仓库补打里程碑标签（第 4 周起欠账）：`w4`、`w5`、`w6`、`w7`、`w8`，每个标签对应当周提交目录；
- [ ] 每位成员各自在仓库提交记录中留下 commit（任务书明确“每位成员都要有提交”）。
