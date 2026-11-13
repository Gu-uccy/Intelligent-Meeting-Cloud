# 现场故障恢复

| 现象 | 检查 | 恢复路径 |
|---|---|---|
| 前端进不去 | URL、session.json、vite.err.log | 用实际端口，5173 占用会递增，不结束其他项目 |
| Maven 不存在 | mvn -v、PATH | 安装配置 Maven 后重开终端；现场先用 Demo |
| 8080 占用 | 监听 PID 和进程名 | 确认所属服务，不能把 Apache 当 Spring |
| Pi 5000 不通 | 同网段/IP、health、Flask 日志 | 恢复连接；演示可切明确标注的模拟 |
| 温湿度 -- | quality、sampled_at | 检查 DHT，不改数值冒充实测 |
| 门指令失败 | control 响应、双 PWM 初始化 | 停止重复点击，查电源/共地/机械卡滞，空载校准 |
| 灯色不一致 | alarm、lighting_source | 报警红灯优先，异常测试后恢复阈值 |
| CSV 503 | 是否已有样本 | 等待采样并查 history，不把错误页改名 CSV |

30 秒切备：打开事先准备的 Demo URL → 确认“模拟” → 展示截图与报告 → 明确实物待复测项。本次排除视频，不声称有预录视频兜底。

恢复后重走 health 来源、current 变化、真实登录预约、数据库核对、门灯物理观察、CSV 对照，填写 hardware-acceptance.md。
