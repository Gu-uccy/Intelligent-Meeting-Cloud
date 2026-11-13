# 第3周课堂实践作业2：统一会议室状态对象说明

## 一、背景：为什么要统一状态对象

综II系统中，各模块对“同一会议室状态”的描述字段各不相同：

| 模块 | 原字段 | 说明 |
| --- | --- | --- |
| Flask 综合传感器系统 `/api/current` | temperature / humidity / light / smoke / distance / motion / presence / devices{cooling, heating, humidifier, dehumidifier, lighting, alarm, auto_mode} | 环境与设备状态 |
| 门禁系统（chapter9/10） | door_locked（True/False）、MQTT 主题 `home/meetingroom/door_state`（open/closed） | 门状态 |
| 前端 3D 场景（Room3D） | 轮询 `/sensor-api/current`，读取 presence / motion / devices.lighting / smoke | 可视化消费 |
| Spring Boot 后端 | meeting_room.status（0-空闲，1-占用，2-维修，3-已预约未使用）、roomCode、reservation.status | 业务状态 |
| 前端 mock（mockApi.js） | roomId / status（0/1/2） | 演示数据 |

存在的问题：

1. “是否有人”有 motion、presence、occupancy、status 四种叫法，含义不完全相同（PIR 瞬时移动 vs 会议占用）；
2. “会议室编号”有 roomCode、roomId、room_id 三种叫法，编号格式也不统一；
3. “门状态”在门禁程序里是布尔 door_locked，在 MQTT 里是 open/closed 字符串；
4. “设备状态”在传感器系统里是布尔集合（devices 对象），在前端展示时又被拆成独立字段；
5. 时间字段有的返回 `YYYY-MM-DD HH:MM:SS`，有的返回 ISO 带时区。

统一状态对象就是解决这些“同义不同名”问题的一份数据契约。

## 二、统一字段约定

统一字段采用**小驼峰命名**，全部字段见下表。其中基础字段是各端都必须提供/消费的，扩展字段允许缺省。

### 基础字段（必填）

| 字段 | 类型 | 必填 | 含义 | 示例 | 数据来源 |
| --- | --- | --- | --- | --- | --- |
| timestamp | string (ISO8601) | 是 | 状态产生时间 | `2026-09-09T10:30:00+08:00` | 系统时钟 |
| room_id | string | 是 | 会议室编号 | `301` | 数据库/配置 |
| occupancy | boolean | 是 | 是否有人（0/1 归一化后的布尔值） | `true` | PIR 人体红外 + 占用判定 |
| temperature | number | 是 | 温度（℃） | `24.6` | DHT11 |
| humidity | number | 是 | 相对湿度（%） | `48.0` | DHT11 |
| door_status | string | 是 | 门状态：open / closed | `closed` | 门禁系统 door_state |
| devices | object | 是 | 设备状态（见下表） | `{"lighting":"on",...}` | 自动控制逻辑 |
| source | string | 是 | 数据来源：sensor（真实）/ mock（模拟） | `mock` | 运行环境 |
| quality | string | 是 | 数据质量：normal / abnormal | `normal` | 质量检查 |

### 扩展字段

| 字段 | 类型 | 必填 | 含义 | 示例 | 数据来源 |
| --- | --- | --- | --- | --- | --- |
| light | number | 否 | 光照值（0~255） | `128` | PCF8591+光敏 |
| smoke | number | 否 | 烟雾值（0~200） | `20` | MQ-2 |
| distance | number | 否 | 门前距离（cm，2~450） | `56.7` | HC-SR04 |

### devices 子字段

| 字段 | 类型 | 含义 | 取值 |
| --- | --- | --- | --- |
| lighting | string | 照明状态 | on / off |
| cooling | string | 制冷状态 | on / off |
| heating | string | 制热状态 | on / off |
| humidifier | string | 加湿状态 | on / off |
| dehumidifier | string | 除湿状态 | on / off |
| alarm | string | 烟雾报警状态 | on / off |

> 说明：作业示例中的 projector / air_conditioner 属于会议室“配备设备”（数据库 meeting_room.equipment 中的文本，如“投影+白板+麦克风”），不属于可实时控制的执行器状态，因此本组统一对象以综II系统的真实执行器（照明、制冷、制热、加湿、除湿、报警）为准；投影仪/空调等配置设备信息仍由会议室基础信息接口提供。

## 三、字段统一对照表（同义不同名梳理）

| 统一字段 | 综II原有叫法（不同模块） | 统一后 |
| --- | --- | --- |
| occupancy | motion、presence、meeting_room.status(1)、occupancy_raw | 统一为布尔 occupancy（有人=1/true） |
| room_id | roomCode、roomId、room（CSV列）、room-301 等别名 | 统一为数据库编号 301/302/501 |
| door_status | door_locked（True/False）、door_state（open/closed） | 统一为 open/closed 字符串 |
| devices.lighting | devices.lighting（布尔）、lighting_brightness、lighting_source | 统一为 on/off 字符串 |
| timestamp | 时间戳（YYYY-MM-DD HH:MM:SS）、time（HH:MM:SS）、ISO 时间 | 统一为 ISO8601 带时区 |

## 四、统一状态对象示例

```json
{
  "timestamp": "2026-09-09T10:30:00+08:00",
  "room_id": "301",
  "occupancy": true,
  "temperature": 24.6,
  "humidity": 48.0,
  "light": 128,
  "smoke": 20,
  "distance": 56.7,
  "door_status": "closed",
  "devices": {
    "lighting": "on",
    "cooling": "off",
    "heating": "off",
    "humidifier": "off",
    "dehumidifier": "off",
    "alarm": "off"
  },
  "source": "mock",
  "quality": "normal"
}
```

完整三间会议室的状态对象见 `mock/state.json`。

## 五、异常值处理方式

| 场景 | 处理方式 |
| --- | --- |
| 温度 < 0 或 > 50（℃） | quality 置为 abnormal；数值置空不参与计算 |
| 湿度 < 0 或 > 100（%） | 同上 |
| 光照 < 0 或 > 255 | 同上 |
| 烟雾 < 0 或 > 200 | 同上 |
| 距离 < 2 或 > 450（cm） | 同上 |
| 缺少必填字段（timestamp/room_id/occupancy/temperature/humidity） | 接口返回 400，message 指出缺失字段 |
| 未知会议室编号 | 接口返回 404，message=“room not found” |
| 传感器瞬时不可用 | 保留上一次有效值并标注 quality=abnormal（与综II `read_dht_sensor` 失败回退逻辑一致） |

## 六、Web 端和 3D 端如何使用

- **Web 端（Vue）**：`src/apis/sensor.js` 轮询 `/sensor-api/current`，读取 temperature、humidity、smoke、presence、devices 展示在环境监测页（User/Control）与温湿度控制页（User/ClimateControl）；统一对象将前端字段全部改为 `occupancy / door_status / devices.*` 这套命名。
- **3D 端（Room3D）**：`src/views/User/Room3D/index.vue` 每 2 秒读取一次统一状态对象，按以下映射更新场景：
  - `occupancy`（或 presence/motion）→ 场景中显示/隐藏人员模型；
  - `devices.lighting` → 灯光亮度；
  - `temperature` 越界 → 空调制冷/制热提示；
  - `smoke` 超过 60 → 报警灯与烟雾粒子；
  - `distance` → 门前距离标记；
  - `door_status` → 门模型开/合。
- **后端（Spring Boot）**：统一对象由 `/api/rooms/{room_id}/state` 提供；业务状态（预约/维修）仍由 meeting_room.status 维护，两者通过 room_id 关联。
