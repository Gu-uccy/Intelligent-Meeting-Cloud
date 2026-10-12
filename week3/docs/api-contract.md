# 第3周课堂实践作业2：状态查询接口契约

## 一、接口总览

| 接口 | 方法 | 说明 | 现状 |
| --- | --- | --- | --- |
| `/api/rooms/{room_id}/state` | GET | 查询指定会议室统一状态对象 | 已实现（模拟接口 mock_state_api.py） |
| `/api/rooms` | GET | 会议室状态列表 | 已实现 |
| `/health` | GET | 服务健康检查 | 已实现 |
| `/api/current` | GET | 综II综合传感器系统实时数据（真实源） | 综II已有（Flask 5000） |
| `/api/export/csv` | GET | 综II传感器数据导出 | 综II已有 |
| `/admin/room/page` 等 | GET | Spring Boot 会议室业务接口 | 综II已有（8080） |

## 二、统一响应包

所有接口统一返回：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

错误时 `data` 为 `null`：

```json
{ "code": 404, "message": "room not found", "data": null }
```

| code | 含义 |
| --- | --- |
| 200 | 成功 |
| 400 | 参数错误 |
| 404 | 会议室不存在 |

## 三、接口详情

### 3.1 GET /api/rooms/{room_id}/state

查询指定会议室的统一状态对象。

请求示例：

```text
GET /api/rooms/301/state
```

响应示例（HTTP 200）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
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
}
```

异常场景：

```text
GET /api/rooms/R99/state
```

响应（HTTP 404）：

```json
{ "code": 404, "message": "room not found", "data": null }
```

```text
GET /api/rooms//state  
```

响应（HTTP 404，路由无法匹配，返回错误页面）：

```json
{ "code": 404, "message": "room not found", "data": null }
```

### 3.2 GET /api/rooms

返回全部会议室统一状态对象列表，供前端/3D 端批量加载。

### 3.3 GET /health

返回服务与数据源信息。

## 四、真实数据落地映射

模拟接口的 `source` 固定为 `mock`。接入真实环境时按以下映射替换数据源：

| 统一对象字段 | 真实来源（综II） |
| --- | --- |
| timestamp | Flask `/api/current` 的 timestamp（统一为 ISO8601） |
| room_id | 数据库 meeting_room.room_code（301/302/501） |
| occupancy | `/api/current` 的 presence / motion（PIR） |
| temperature / humidity | `/api/current` 的 temperature / humidity（DHT11） |
| light / smoke / distance | `/api/current` 的 light / smoke / distance |
| door_status | 门禁系统 MQTT 主题 `home/meetingroom/door_state`（open/closed） |
| devices.* | `/api/current` 的 devices（cooling/heating/humidifier/dehumidifier/lighting/alarm） |
| source | "sensor"（真实传感器）或 "mock"（模拟） |
| quality | 按本文档第五节异常规则计算 |

## 五、测试方式

```powershell
# 1. 启动模拟接口
python mock/mock_state_api.py

# 2. 正常查询
curl http://127.0.0.1:5002/api/rooms/301/state

# 3. 非法会议室
curl http://127.0.0.1:5002/api/rooms/R99/state
```

