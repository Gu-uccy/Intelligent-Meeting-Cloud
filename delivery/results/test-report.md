# 本轮测试与交付报告

汇总时间：2026-11-11T12:41:26.054745+00:00。52 条中通过 52，失败 0；截图 9 张。

环境：Windows，Chrome 158.0.8127.18，Vue/Vite/Three.js；Browser plugin 不可用，使用 Playwright。构建退出码 0。

## 结果及范围

| 项目 | 实际验证 | 结论 |
|---|---|---|
| TC_01–32 | Flask 隔离、GPIO 替身、非法输入、缺失/过期、导出、双 PWM | 见 backend_tests.json |
| TC_33–52 | 浏览器业务 mock/API 夹具；CSV 下载本地模拟 HTTP | 见 browser_tests.json |
| Demo 运行 | 前端 HTTP 200，Flask source=simulation | 本机演示可用 |
| Full 预检 | Maven=False，Redis=False，8080空闲=False，Pi=None | 受阻，未跑完整业务链路 |
| 实物执行 | Pi 不可达，无物理 GPIO/机械观察 | 待现场 |

浏览器 pageerror 0 条，console warning 0 条。生产构建日志另见 build.log（含大包提示）。

## 本轮修复

- 硬件温湿度不再被模拟环境覆盖；缺失保留 null、过期标识，不阻断门灯返回。
- 舵机失败返回失败并保留指令状态；控制参数校验，门无门磁的限制明确展示。
- 模拟/实时/缺失/断线来源提示、烟雾报警、CSV 下载，预约失败不再显示成功。
- 手机数据面板移到模型下方，导航可横滚；桌面侧栏可滚动，卡片不拆单位。
- 启动预检、识别传感器服务、端口避让和 Maven 多模块启动修正。

## 待现场与限制

树莓派 192.168.43.206 当前不可达。MySQL TCP 可达不代表数据库权限/业务通过；Maven/Redis 缺失且 8080 占用。52 条不是 52 条硬件或完整后端端到端测试。Blender 脚本保留但本轮未运行原生工具验证。视频按用户要求排除。

复测步骤见 ../docs/test-protocol.md；现场填 ../docs/hardware-acceptance.md。旧 week7-8/week9-11 报告为合入远端的历史材料，不计为本轮实测。
