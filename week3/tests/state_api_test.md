# 第3周课堂实践作业2：状态接口测试记录

## 一、测试环境

- 测试时间：2026-10-10
- 测试工具：PowerShell `Invoke-WebRequest` 与 `curl`（等价于 Postman 的 GET 请求）
- 被测服务：`mock/mock_state_api.py`（Flask，端口 5002，数据源 `mock/state.json`）
- 说明：由于真实后端（Spring Boot 8080）与树莓派传感器服务（Flask 5000）需要完整环境，本次使用**模拟接口**验证统一状态对象与错误处理；模拟数据在 `source` 字段明确标注 `mock`，不是真实树莓派实时数据。真实数据映射方案见 `docs/api-contract.md` 第四节。

## 二、测试用例与结果

### 用例1：健康检查

```text
GET /health
```

| 项目 | 结果 |
| --- | --- |
| HTTP 状态码 | 200 |
| 响应体 | `{"code":200,"data":{"rooms":["301","302","501"],"source":"mock","status":"ok"},"message":"success"}` |
| 结论 | 通过 |

### 用例2：会议室列表

```text
GET /api/rooms
```

| 项目 | 结果 |
| --- | --- |
| HTTP 状态码 | 200 |
| 响应体 | 返回 301/302/501 三间会议室完整统一状态对象（见 `tests/state_api_test_log.txt` 第 2 组） |
| 结论 | 通过 |

### 用例3：正常查询——有效会议室 301

```text
GET /api/rooms/301/state
```

| 项目 | 结果 |
| --- | --- |
| HTTP 状态码 | 200 |
| 响应体 | `{"code":200,"data":{"timestamp":"2026-09-09T10:30:00+08:00","room_id":"301","occupancy":true,"temperature":24.6,"humidity":48.0,"light":128,"smoke":20,"distance":56.7,"door_status":"closed","devices":{"lighting":"on","cooling":"off","heating":"off","humidifier":"off","dehumidifier":"off","alarm":"off"},"source":"mock","quality":"normal"},"message":"success"}` |
| 结论 | 通过：统一状态对象字段完整、格式规范 |

### 用例4：正常查询——有效会议室 302

```text
GET /api/rooms/302/state
```

| 项目 | 结果 |
| --- | --- |
| HTTP 状态码 | 200 |
| 响应体 | 返回 302 的统一状态对象（occupancy=false，devices.cooling=on 等，见日志第 4 组） |
| 结论 | 通过 |

### 用例5：异常测试——非法会议室编号 R99

```text
GET /api/rooms/R99/state
```

| 项目 | 结果 |
| --- | --- |
| HTTP 状态码 | 404 |
| 响应体 | `{"code":404,"data":null,"message":"room not found"}` |
| 结论 | 通过：非法编号返回明确错误信息，data 为 null |

### 用例6：异常测试——空会议室编号

```text
GET /api/rooms//state
```

| 项目 | 结果 |
| --- | --- |
| HTTP 状态码 | 404（路由无法匹配，返回错误响应） |
| 结论 | 通过：无编号不会返回任何房间数据 |

## 三、接口验收标准对照

| 验收项 | 合格要求 | 结果 |
| --- | --- | --- |
| 字段统一 | Web、后端和 3D 端使用同一字段名称 | ✅ `docs/state-object.md` 统一字段约定，Web/3D/后端消费方式已写明 |
| 状态对象 | 至少包含会议室、时间、人员、环境和设备状态 | ✅ room_id / timestamp / occupancy / temperature、humidity、light、smoke、distance / door_status、devices |
| 接口返回 | 能够返回规范 JSON | ✅ 统一响应包 {code, message, data} |
| 正常测试 | 有一个有效会议室查询结果 | ✅ 用例 3、4 |
| 异常测试 | 无效会议室能够返回错误提示 | ✅ 用例 5（404 room not found） |
| 数据来源 | 能区分真实数据和模拟数据 | ✅ source 字段：mock（模拟）/ sensor（真实，见 api-contract 第四节映射） |
| 文档记录 | 有状态对象和接口说明 | ✅ state-object.md、api-contract.md |
| 过程证据 | 有测试截图、响应内容或日志 | ✅ 本文件 + `tests/state_api_test_log.txt` 真实运行日志 |

## 四、运行日志

完整真实运行记录见 `tests/state_api_test_log.txt`（包含每次请求的命令、HTTP 状态码与完整响应体）。
