# 测试与交付包（视频除外）

后续本机真实业务链路已单独验收：见 [Spring/MySQL 联调补充](../analysis/taskbook-v3-2026-11-14/backend-integration/README.md)。Local 使用真实登录/预约与模拟传感器；36 项 HTTP/数据库、16 项新增 Java 回归和 8 项浏览器检查通过。Redis 和树莓派仍待接通；下方旧结果保持历史语义。

2026-11-14 最新交付见 [正式材料目录](final-2026-11-14/README.md)：8 页 Word、19 页校正版 PPT，均按最新实现与 109 次回归执行结果校正。Blender 原生模型与 GLB 已实际生成并接入，见 [续作验收记录](../analysis/taskbook-v3-2026-11-14/续作验收记录.md)。本轮真实人脸、实物动作和 Full 链路仍待验。

本目录结果为 **2026-11-11 历史归档**。11月14日代码续作后的新结果单独保存在 [最新验收记录](../analysis/taskbook-v3-2026-11-14/续作验收记录.md)，原52条/9图不能直接作为当前源码全部验证的结论。

本包对应“启动 → 预约 → 3D → 控制 → 异常 → 导出”的演示路径。结果以实际测试来源为准，未连接的硬件不计为通过。

| 交付项 | 入口 | 当前范围 |
|---|---|---|
| 一键启动 | 根目录 start-all.cmd | Demo 自动选择在线树莓派或明确标注的本地模拟；Full 先预检 |
| 52 条自动化用例 | [用例清单](tests/test-cases.md)、[报告](results/test-report.md) | 32 条 Flask 隔离测试 + 20 条 Chrome 浏览器测试 |
| CSV / JSON 原始结果 | [结果目录](results) | 接口、页面耗时、帧间隔、CSV 下载及预检快照 |
| 9 张截图 | [截图矩阵](docs/screenshot-matrix.md) | 4 档视口 + 门、灯、烟雾、缺失、中断；注明夹具来源 |
| 文档清单 | [文档目录](docs/document-inventory.md) | 按实际 Git 跟踪文件和交付文件统计 |
| 版本追溯 | [版本说明](docs/version-traceability.md) | w4 为补建历史标记；w8、v1.0-rc1 为本次候选交付 |
| 现场恢复与核验 | [故障恢复](docs/failure-recovery.md)、[实物验收表](docs/hardware-acceptance.md) | 实物链路需恢复网络后填写 |

## 立即演示

仓库根目录运行 `./start-all.cmd`，以输出 URL 为准。业务演示账号 `test_user / 123456` 仅用于 Demo。日志和来源见 `.codex-run-logs/session.json`。完整业务启动见 [启动说明](docs/startup-runbook.md)。

## 复现本次结果

1. 安装前端依赖：`npm --prefix FrontEnd/Intelligent_meeting_cloud ci`；Python 需 Flask、matplotlib。
2. 运行 `python delivery/tests/test_sensor_contract.py`。
3. 按 [测试协议](docs/test-protocol.md) 启动独立本地模拟服务和 Vite。
4. 设置 ACCEPTANCE_URL 为实际前端地址，运行 `node delivery/tests/browser_acceptance.mjs`。需 Chrome 和 Playwright；非 Codex 环境先 `npm install --no-save playwright` 或设置 PLAYWRIGHT_MODULE_PATH。
5. 运行 `npm run build:frontend`，保存构建日志后执行 `python delivery/build_evidence.py` 汇总。单独复测时也要更新预检，不把旧快照当成新验收。

## 验收边界

浏览器预约使用内置 localStorage mock；传感器变化和异常通过 API 夹具注入；CSV 下载走真实本地 Flask 模拟服务；GPIO 使用替身。目前树莓派不可达，Maven/Redis 缺失且 8080 占用，完整 Spring/MySQL/Redis 和实物执行未验收。截图中“实时数据”只检验来源字段的显示映射，水印标注了测试夹具。

上述 11-11 历史测试包本身不构成 Blender 编辑证明。11-14 续作另交付了原生 .blend、GLB 与 Blender 4.5.9 LTS 导出及几何检查记录；以最新验收目录为准。
