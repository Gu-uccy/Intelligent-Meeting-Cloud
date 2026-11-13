# 第6周人脸识别业务联动与“失败不放行”说明

## 一、业务联动目标

| 业务 | 识别通过 | 识别失败（失败不放行） | 对应综II代码 |
| --- | --- | --- | --- |
| 门禁开门 | 驱动舵机开门（SERVO_PIN=18），记录开门日志 | 保持门锁，提示重试，记录失败日志与报警 | `chapter9/smart_door_system.py`、`chapter10/smart_door_system_mqtt.py` |
| 登录验证 | 发放登录凭证（模拟 JWT），进入会议室内页 | 拒绝登录，提示“人脸不匹配” | 前端 `User/FaceAccess` 页 + 后端登录接口 |
| 预约联动 | 识别通过且预约有效 → 自动开门并点亮“已预约”状态 | 保持锁闭，提示“无预约/识别失败” | `meeting_room.reservation`（Spring Boot） |
| 权限控制 | 管理员（role=admin）开门后允许设备控制 | 普通用户仅查看环境数据 | RBAC（user/role/permission 表） |

## 二、失败不放行（fail-closed）实现

1. 判定规则：`Sim_max >= θ` 才“通过”，否则一律“拒绝”——**不确定时默认拒绝**；
2. 联动动作：
   - 门禁：`door_control` 仅当通过才发送 `open`；拒绝时门锁保持 `closed` 并触发提示音/提示文案；
   - 登录：拒绝时前端显示“人脸识别失败，请重试”，不进入会议室内页；
3. 日志记录（统一事件日志，写入 `logs/face_access.log`）：

```text
[2026-10-10 10:30:12] VERIFY result=DENY person_id=UNKNOWN sim=0.42 threshold=0.50 reason=below_threshold action=door_locked
[2026-10-10 10:31:05] VERIFY result=PASS person_id=A01 sim=0.91 threshold=0.50 action=door_open
[2026-10-10 10:31:05] LOGIN result=PASS person_id=A01 token=eyJ... action=allow
[2026-10-10 10:32:40] VERIFY result=DENY person_id=A02 sim=0.46 threshold=0.50 reason=below_threshold action=login_rejected
```

4. 异常处理：
   - 摄像头不可用/检测不到人脸：不判“通过”，返回 `no_face`，提示重试（与 `face_api.py /api/face/verify` 无脸时返回错误一致）；
   - 数据库/人脸库不可读：fail-closed，拒绝放行并告警；
   - 连续 3 次失败：触发管理员通知（复用综II `notification` 表机制）。

## 三、联动时序（门禁闭环）

```text
摄像头帧 → 预处理 → 检测 → LBP 特征 → 与库比对 → 阈值判定
    ├─ 通过: 开门指令(MQTT home/meetingroom/door_control=open) → 门状态回读 → 3D/Web 状态更新
    └─ 拒绝: 保持锁定 → 提示重试 → 写失败日志 → 连续失败告警
```

## 四、验收对照

| 课堂要求 | 完成情况 |
| --- | --- |
| 至少 1 个业务闭环（登录/预约/权限/开门） | ✅ 门禁开门 + 登录双闭环（含预约/权限映射表） |
| 失败不放行 | ✅ 统一 fail-closed 判定与动作 |
| 有联动录屏或日志 | ✅ 日志格式示例 + 真实评估日志 `results/face_eval_run.log`（硬件联动录屏待现场，见 tests/face_test_record.md） |
| 有异常处理说明 | ✅ 本文件第二节 |
