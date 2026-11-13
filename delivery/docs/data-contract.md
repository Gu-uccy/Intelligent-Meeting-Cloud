# 统一状态与数据来源契约

数据链：采集/GPIO → Flask /api/current → Vite /sensor-api/current → Vue 统一场景状态 → Three.js 人员、门、环境、灯光。预约独立走 Spring /api 代理；Demo 业务 mock 不证明数据库写入。

| 字段 | 含义/限制 |
|---|---|
| source | sensor / simulation；不能仅凭数值判断来源 |
| quality | normal / partial；当前只反映温湿度就绪/过期，不覆盖全部硬件 |
| sensor_status.climate | ok / unavailable / stale；DHT 距成功读取超过 15 秒为 stale |
| sampled_at | 最近 DHT 成功采样时间，可能 null；timestamp 是响应时间 |
| temperature / humidity | ℃ / 相对湿度 %；缺失 null，前端显示 -- |
| motion / presence | PIR 占用状态，不能给准确人数；人物是占用示意 |
| light / smoke | 原始/映射等级，不是校准 lux、ppm 或浓度百分比；UI % 是等级显示 |
| devices.lighting / lighting_brightness | 照明指令 / 0..100；报警红灯优先 |
| door_open / door_state_kind | 门指令 / commanded；无门磁，不能代表机械到位 |

GET /api/health 识别服务。GET /api/history 最多保留 120 样本。GET /api/export/csv 空历史返回 503，有样本时下载含 source 和门指令列的 CSV，缺失值留空。

POST /api/control 的开门示例：

```json
{"action":"manual","device":"door","state":true}
```

关门用 false，照明 device=lighting，可传 brightness=0..100。state 必须布尔值；非法类型、越界亮度、未知设备/阈值返回 400。硬件舵机未初始化或 PWM 报错返回 503 和 success=false，不回写成功状态。一台成功而另一台失败时实物可能部分动作，接口没有机械回滚，需现场核对。

MEETING_DATA_MODE=hardware 强制要求硬件库，simulation 强制模拟，auto 默认自动检测。硬件模式不再用模拟空调逻辑修改真实温湿度。缺失时仍提供门灯；断线页面保留最近状态并显示断连提示。
