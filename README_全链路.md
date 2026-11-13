# 全链路打通说明（真实 MySQL + Spring Boot + 自研人脸 + 设备层 + 3D）

> 本文档对应本次「把全链路真正跑起来」的改造：**注册/登录 → 录脸 → 刷脸预约 → 预约时段内刷脸解锁 → 3D 门打开 → 灯光控制 3D 与设备层同步**。
> 全部环节都已在本机实测通过（`delivery/results/e2e_fullchain_result.json`，17/17）。

---

## 一、现在这套系统能做什么

| 能力 | 是否真实 | 落到哪里 |
|---|---|---|
| 用户注册 / 登录 | 真实 | Vue → `/api/register` `/api/login`（proxy 到 8081）→ MySQL `user` 表（BCrypt + JWT） |
| 会议室列表 / 时段 | 真实 | `/user/room/page`、`/user/reservation/slots` → MySQL `meeting_room` / `reservation` |
| 人脸录入 | 真实 | 浏览器摄像头或上传照片 → 5001 `/api/face/enroll` → 底库目录 + 特征 |
| **刷脸才能预约** | 真实（**服务端强制**） | 提交预约前刷脸换一次性凭据 → 后端 `FaceTicketInterceptor` 校验 `X-Face-Ticket` → 通过才落库 |
| **预约时段内刷脸解锁** | 真实（**服务端判定**） | 5001 `/api/face/unlock`：1:1 核身 + 查 MySQL 当前时段有效预约 + 调设备层开门 |
| 3D 门联动 | 真实 | 设备层 `door_open=True` → Room3D 每 3s 轮询 → 门绕轴旋转打开 |
| 3D 灯 ↔ 设备层 | 真实 | 3D 页「打开LED灯」→ `/api/control` → `devices.lighting` → 3D 顶灯亮度/颜色变化 |
| 人脸审计日志 | 真实 | 每次注册/识别/开门/拒绝都写 `face_audit_log` 表，`/api/face/audit` 可查 |
| 权限控制（RBAC） | 真实（服务端） | `/admin/**` 由 `RbacInterceptor` 按 `user_role → role_permission → permission(url+method)` 判定；越权 403 并落 `operation_log` |
| 操作审计 | 真实 | `@AuditLog` + AOP 切面写 `operation_log`（操作人/角色/IP/UA/耗时/成功失败/脱敏入参） |

**失败一律不放行**（fail-closed）：
未检测到人脸 → 422；人脸与登录账号不一致 → 403；当前时段该会议室没有本人有效预约 → 403；门禁驱动失败 → 502。所有拒绝都会落审计日志。

---

## 二、服务与端口

```
浏览器 http://127.0.0.1:5173
   ├── /api/*        ──proxy──▶ Spring Boot 8081 ──JDBC──▶ MySQL 3307
   ├── /face-api/*   ──proxy──▶ 自研人脸服务 5001 ──JDBC──▶ MySQL 3307
   │                                    └──HTTP──▶ 设备层 5058（开门/开灯）
   └── /sensor-api/* ──proxy──▶ 设备层 5058（传感器 + 门禁 + 灯光）
```

| 服务 | 端口 | 代码位置 | 说明 |
|---|---|---|---|
| MySQL | 3307 | `D:\zongshe\.localmysql\data` | **独立实例**，不动你机器上原有的 3306 服务 |
| Spring Boot | 8081 | `BackEnd/MeetingRoom-Parent` | 用户/会议室/预约；原项目默认 8080，被本机 httpd 占用故改 8081 |
| 自研人脸服务 | 5001 | `MachineLearning/human_face/face_service_lbp.py` | 复用 `week5/scripts` 的自研预处理 + LBP |
| 设备层 | 5058 | `Flask/unified_meeting_room_system.py` | 模拟模式；树莓派在线时自动切硬件 GPIO |
| 前端 | 5173 | `FrontEnd/Intelligent_meeting_cloud` | `.env.local` 已切到真实模式（`VITE_USE_MOCK=false`） |

---

## 三、一键启动

```powershell
cd D:\zongshe\Intelligent-Meeting-Cloud-main

# 启动全部服务（首次会自动初始化数据库、安装前端依赖、打包后端）
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-fullchain.ps1

# 查看状态
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-fullchain.ps1 -Status

# 停止全部
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-fullchain.ps1 -Stop
```

启动日志在 `.run/logs/`，进程号在 `.run/pids.json`。
首次启动约 2~4 分钟（导库 + npm ci + mvn package）；之后约 30 秒。

### 手动启动（不想用脚本时）

```powershell
# 1) MySQL（已有独立数据目录时）
D:\mysql-8.0.31-winx64\bin\mysqld.exe --datadir=D:\zongshe\.localmysql\data --basedir=D:\mysql-8.0.31-winx64 --port=3307 --console

# 2) 后端
$env:SPRING_DATASOURCE_URL='jdbc:mysql://127.0.0.1:3307/meeting_room_db?serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf-8&zeroDateTimeBehavior=convertToNull&useSSL=false&allowPublicKeyRetrieval=true'
$env:SPRING_DATASOURCE_USERNAME='root'; $env:SPRING_DATASOURCE_PASSWORD=''
$env:SERVER_PORT='8081'; $env:SPRING_PROFILES_ACTIVE='dev'
java -jar BackEnd\MeetingRoom-Parent\MeetingRoom-Management\target\MeetingRoom-Management-0.0.1-SNAPSHOT.jar

# 3) 自研人脸服务
$env:MYSQL_PORT='3307'; $env:MYSQL_USER='root'; $env:MYSQL_PASSWORD=''; $env:MYSQL_DB='meeting_room_db'
$env:FACE_SENSOR_BASE='http://127.0.0.1:5058'
python MachineLearning\human_face\face_service_lbp.py

# 4) 设备层
$env:MEETING_DATA_MODE='simulation'; $env:MEETING_PORT='5058'
python Flask\unified_meeting_room_system.py

# 5) 前端
npm --prefix FrontEnd\Intelligent_meeting_cloud run dev
```

---

## 四、首次使用（三步）

1. **注册并登录**：打开 http://127.0.0.1:5173/login → 「注册」页填手机号（作为登录账号）、姓名、密码 → 回到登录页登录。
   - 已内置演示账号：`13900000002 / 123456`（姓名：李四）
2. **录入本人人脸**：进入「人脸门禁」页 →
   - 有摄像头：点「打开摄像头」→「录入当前用户」（建议换角度/光照多录 2~3 张）；
   - 没摄像头：用「上传照片录入」（同一个自研链路）。
3. **刷脸预约**：进入「会议预定」→ 点会议室 → 选一个空闲时段 → 填会议主题 → 「刷脸确认并提交预约」→ 摄像头刷脸（或上传照片）→ 通过后自动提交。

> 人脸身份 = 登录账号，所以「识别到的人」能直接对上数据库里的用户，这是后面校验预约权限的基础。

## 五、演示「刷脸解锁 + 3D 门开 + 灯光联动」

前提：当前时刻该会议室有一条**本人的有效预约**。没有就先用脚本造一条：

```powershell
$env:MYSQL_PORT='3307'
python scripts/seed_demo_data.py --account 13900000002 --room 301
```

然后：

1. 打开 **3D 会议室** 页面（左栏「会议室切换」选 301 对应的「董事会议室」）；
2. 点 **「刷脸解锁会议室」** → 刷脸（或上传照片）；
3. 通过后：左栏出现「已解锁 · 301 / 相似度 / 阈值 / 预约号 / 时段」，门状态变「已开启」，**3D 场景里的门绕门轴转开**；
4. 点 **「打开LED灯」**：设备层 `devices.lighting=true`，3D 顶灯变亮；再点一次熄灭；
5. 点「重新上锁」关门，3D 门复位。

反向演示（都会被拒绝并写审计日志）：
- 用别人的脸 → 「人脸与当前账号不匹配」；
- 换到没有当前时段预约的会议室 → 「当前时段没有该会议室的有效预约」；
- 上传一张没有人脸的图片 → 「未检测到人脸」；
- 直接调预约接口不带凭据 → 403「预约必须先通过人脸核验」。

---

## 六、人脸算法：自研到什么程度

复用 `week5/scripts` 的两个自研环节，**业务用的就是这两份代码**（不是另写一份调用库的接口）：

| 环节 | 代码 | 说明 |
|---|---|---|
| ① 预处理 | `week5/scripts/preprocess_face.py` | 纯 numpy 灰度化（0.299/0.587/0.114）→ 双线性 resize 112×112 → 直方图均衡化（自建 LUT） |
| ② 特征 | `week5/scripts/lbp_face.py` | 均匀模式 LBP（256→59 维映射表）+ 7×7 分块 → 2891 维 + L2 归一化 |
| ③ 比对 | 同上 | 余弦相似度，一人多图取最大 |
| ④ 阈值 | `face_service_lbp.py: calibrate_threshold()` | **类间上界 + 0.06 安全边际**（FAR 优先），只有 1 个身份时退化为类内均值 − 0.8×标准差 |

调用的成熟库（报告中需列明）：`opencv-python-headless 4.10.0`（仅图像解码 + Haar 人脸检测 `CascadeClassifier`）、`numpy`、`flask`、`pymysql`。**特征提取与比对全部自研**。

### 真实人脸照片上的实测指标

用公开示例照片（scikit-image `astronaut`、matplotlib `grace_hopper`）做受控增强，结论在 `week5/results/face_realdata_result.json`：

| 指标 | 结果 |
|---|---|
| 1:N 识别 Top-1 准确率 | **6/6 = 1.0000** |
| 1:1 本人相似度（6 个探针） | 0.7885 / 0.8320 / 0.9074 / 0.9586 / 0.9602 / 0.9662 |
| 1:1 冒名相似度（4 个探针） | 0.5263 / 0.6376 / 0.6582 / 0.6590 |
| 可分间隙 | 0.7885 − 0.6590 = **0.1295** |
| 自动标定阈值 | **0.7209**（类间 max 0.6609 + 0.06） |
| 该阈值下 | Accuracy 1.0000，**FAR 0.0000，FRR 0.0000**（TP6 FP0 FN0 TN4） |
| 无人脸图片 | coffee / chelsea → **422 未检测到人脸**（2/2 拒绝） |
| 复现命令 | `python MachineLearning/human_face/tools/face_dataset_selftest.py` |

**重要说明**：这些是「公开示例照片」上的指标，不是本组同学的照片。要把这条写进报告，必须用你自己/同学的真实人脸重跑（见第八节）。

---

## 七、本次改动清单（按文件）

### 新增

| 文件 | 作用 |
|---|---|
| `MachineLearning/human_face/face_service_lbp.py` | 自研人脸业务服务：注册/1:N 识别/刷脸取凭据/刷脸解锁/审计/自动标定 |
| `MachineLearning/human_face/tools/face_dataset_selftest.py` | 真实人脸照片的可复现识别测试（1:N + 1:1 FAR/FRR + 负样本） |
| `BackEnd/.../interceptor/FaceTicketInterceptor.java` | **服务端**强制校验「刷脸后才能预约」，一次性凭据防重放 |
| `Database/align-schema-for-code.sql` | 把建表脚本与 Java 实体对齐（`name→username`、补 `is_admin`/`image`/`version`），并新建 `face_verification`、`face_audit_log` |
| `FrontEnd/.../components/FaceGate.vue` | 通用「刷脸闸门」弹窗（摄像头 + 上传兜底 + 明确拒绝原因） |
| `FrontEnd/.../.env.local` | 切到真实模式（`VITE_USE_MOCK=false` + 三个 proxy 目标） |
| `delivery/tests/e2e_fullchain.mjs` | 17 条全链路端到端用例（真实浏览器 + 真实接口 + 真实数据库） |
| `delivery/tests/fixtures/face_*.jpg` | E2E 用的探针图（公开示例照片的增强版） |
| `scripts/start-fullchain.ps1` | 一键启动/停止/状态 |
| `scripts/seed_demo_data.py` | 造「覆盖当前时刻」的演示预约 |
| `requirements.txt` | Python 依赖清单（原项目缺） |

### 修改

| 文件 | 改了什么 |
|---|---|
| `WebMvcConfiguration.java` | ① 放行 `/register`（否则**永远无法注册**）；② 注册刷脸预约拦截器 |
| `ReservationServiceImpl.java` | ① 时段口径与下单校验对齐（待审核也算占用）；② 去掉「10 分钟间隔」死规则并排除已取消预约 |
| `apis/face.js` | 增加 ticket / unlock / audit / gallery 接口 |
| `apis/reservation.js` | `addReservation(data, faceTicket)` 带 `X-Face-Ticket` |
| `RoomDetail.vue` | 提交预约前弹出刷脸闸门，通过后带凭据提交 |
| `Room3D/index.vue` | 三间房映射真实 room_id，新增「刷脸解锁 / 重新上锁 / 解锁结果」卡片 |
| `FaceCapture.vue` | ① 去掉「演示预约直接放行」的假逻辑，改为 1:1 口径；② 增加「上传照片录入/核验」兜底 |

---

## 八、还需要你本人做的事

### A. 必须由你完成（我无法代替）

1. **录你自己的脸并重跑真实指标**
   - 登录 → 人脸门禁 → 录入本人 3~5 张正脸照；
   - 再找 2 位同学各录 3~5 张（凑够 3 个身份，类间标定才有意义）；
   - 跑 `python MachineLearning/human_face/tools/face_dataset_selftest.py` 前，先确认人脸服务读的是真实底库（`/health` 里的 `db_path`），或直接看 `/api/face/gallery` + `/api/face/recalibrate` 的阈值；
   - 把真实 FAR/FRR 和平均响应时间填进 `week5/tests/face_test_record.md` 第三、四节（现在是「待实测」）。
2. **答辩前把「真实照片」的指标替换掉现在的「公开示例照片」指标**，否则报告里的数字站不住。
3. **录 3~5 分钟演示视频**：按第五节流程录屏（启动 → 注册登录 → 录脸 → 刷脸预约 → 3D 刷脸解锁 → 门开 → 灯控 → 反向拒绝），放进 `delivery/`。
4. **补团队五角色分工表 + 个人贡献**：任务书要求，目前全库只有「组长 田宏斌」一个真名。
5. **补中期/总结报告**：现在只有周实验报告，不是任务书要求的「中期和总结报告」。
6. **老师确认**：若把「自研人脸 + 刷脸预约/开门」作为扩展申报，需不需要事前确认，按你们老师的口径补一份说明。

### B. 需要外部条件（我已经留好接口/文档，但环境不具备）

7. **树莓派实物联调**：Pi（192.168.43.206）当前不可达。
   - 设备层已支持 `MEETING_DATA_MODE=hardware`，接线见 `delivery/docs/hardware-pinout.md`；
   - 上电后把 `FACE_SENSOR_BASE` 指向 Pi 的地址（默认 `http://127.0.0.1:5058`）；
   - 到 `delivery/docs/hardware-acceptance.md` 填实测记录。
8. **Blender 资产改造**（任务书「必须用 Blender/Unity」那条仍未完成）：
   - 装 Blender 4.x → `blender --background --python week7-8/scripts/blender_room_binding.py -- --out room_301.glb`
   - 前端 `Room3D` 里用 `GLTFLoader` 接入（现在还是程序化几何体，`public/models/meeting_room.glb` 是第三方 Sketchfab 资产且未被引用）。
9. **Safari/移动端真机验证**：我只在 Chrome（headless）里做了自动化，摄像头权限在 iOS Safari 上需要 HTTPS 或 localhost。

### C. 可选增强（不影响验收）

10. 把 `13900000002 / 123456` 这个演示账号的底库清掉，换成你自己的账号（删 `MachineLearning/human_face/id/13900000002` 目录即可）。
11. `MeetingRoom-Parent` 的 `SecurityConfig` 仍是 `/** permitAll`，生产化应改成分角色授权（答辩时如实说「认证已做、授权未做」）。

---

## 九、排障

| 现象 | 原因 / 处理 |
|---|---|
| 页面一直显示「模拟数据」 | 设备层 5058 没起；看 `.run/logs/sensor.err.log` |
| 刷脸报「未检测到人脸」 | 光线太暗 / 脸太小 / 侧脸；换正面照，或临时 `set FACE_REQUIRE_FACE=0` 再重启人脸服务（演示兜底） |
| 刷脸报「当前账号未注册人脸」 | 去「人脸门禁」页录入；注意**人脸身份 = 登录账号**，换账号要重录 |
| 刷脸报「人脸与当前账号不匹配」 | 底库阈值偏高或拍的确实不是你；可 `/api/face/recalibrate` 重算阈值，或补录样本 |
| 解锁报「没有该会议室的有效预约」 | 这是**正确行为**；用 `scripts/seed_demo_data.py` 造一条覆盖当前时刻的预约 |
| 预约提交报「预约必须先通过人脸核验」 | 说明服务端拦截生效；点「刷脸确认并提交预约」走闸门 |
| 预约报「会议室已被占用」 | 该时段已有待审核/已确认预约；换时段 |
| 后端启动报 DataSource 错误 | 缺 `SPRING_DATASOURCE_URL` 环境变量（本项目的 druid 配置在 Spring Boot 3 下不生效，必须用标准 key） |
| 8080 冲突 | 本机 8080 被 httpd 占用，已统一用 8081 |
| 表结构报 `Unknown column 'username'` | 没执行 `Database/align-schema-for-code.sql` |

---

## 十、验证入口

```powershell
# 服务健康
powershell -NoProfile -File scripts/start-fullchain.ps1 -Status

# 人脸服务（含底库人数、当前阈值、标定依据）
curl http://127.0.0.1:5001/health

# 人脸审计日志
curl "http://127.0.0.1:5001/api/face/audit?limit=20"

# 全链路 17 条端到端用例（需要 playwright，见文件头注释）
$env:PLAYWRIGHT_MODULE_PATH='D:\zongshe\Intelligent-Meeting-Cloud-main\FrontEnd\Intelligent_meeting_cloud\node_modules\playwright'
node delivery/tests/e2e_fullchain.mjs
# 结果：delivery/results/e2e_fullchain_result.json
# 截图：delivery/screenshots_e2e/
```

> E2E 用到的两张探针图在 `delivery/tests/fixtures/`（`face_genuine.jpg` / `face_impostor.jpg`，
> 来自公开示例照片的受控增强，仅用于链路验证）。默认账号 `13900000002` 已在底库中预置了
> 「astronaut」这张示例脸；换成你自己的脸时，删掉 `MachineLearning/human_face/id/13900000002`
> 目录并在网页上重新录入即可。
---

## 十一、RBAC 与操作审计（服务端）

### 11.1 判定链路

```
登录 → JWT 拦截器写 BaseContext(userId)
     → RbacInterceptor（只拦 /admin/**）
         user_role → role_permission → permission(url + method)
         取「本次请求需要的权限点」与「该用户拥有的权限点」比对
         不匹配 → 403 + 写 operation_log（越权留痕）
     → 业务方法
         @AuditLog 标注的方法由 AuditLogAspect 环绕
         执行后写 operation_log（成功/失败、耗时、脱敏入参）
```

关键点：

- **权限点存在数据库里**，`permission` 表带 `url + method`，改一行权限就能改变一个接口的访问要求，不用改代码；
- **精确路径优先于通配**：`/admin/reservation/page`（`reservation:query:all`）先于 `/admin/reservation/**`（`reservation:manage`）；
- **fail-closed**：`/admin/**` 上找不到对应权限点的接口一律拒绝；
- **未登录 → 401**，**越权 → 403**，两种情况都写日志。

### 11.2 三个角色的权限规模

| 角色 | 权限点数 | 能做什么 |
|---|---|---|
| ROLE_USER | 4 | 建预约 / 取消自己的预约 / 查会议室 / 上报故障 |
| ROLE_ROOM_ADMIN | 12 | 上述 + 会议室管理、预约审核、故障处理、统计、上传 |
| ROLE_SYS_ADMIN | 23 | 全部（含用户管理、日志查询） |

新用户注册即自动分配 `role.is_default=1` 的 ROLE_USER（`UserMapper.assignDefaultRole`）。

### 11.3 现场演示（30 秒）

```powershell
# 权限矩阵 14 条：管理员全 200 / 普通用户全 403 / 未登录 401
node delivery/tests/rbac_check.mjs

# 看审计日志（谁在什么时候试图做了什么）
mysql --host=127.0.0.1 --port=3307 --user=root --database=meeting_room_db ^
  -e "SELECT user_name,operation_type,operation_result,error_msg,ip_address FROM operation_log ORDER BY id DESC LIMIT 10;"
```

演示账号（密码统一 `123456`，已实测三种角色行为不同）：

| 账号 | 角色 | 权限点 | 实测结果（/admin/room → /admin/user） |
|---|---|---|---|
| `sys_admin` | ROLE_SYS_ADMIN | 23 | 200 → 200 |
| `admin1` | ROLE_SYS_ADMIN | 23 | 200 → 200 |
| `room_admin` | ROLE_ROOM_ADMIN | 12 | 200 → **403**（没有 user:manage） |
| `test_user` | ROLE_USER | 4 | **403** → **403** |
| `13900000002` | ROLE_USER | 4 | **403** → **403**（同时是刷脸链路的主演示账号） |

> 说明：建表脚本里 `sys_admin / room_admin / test_user` 的 BCrypt 哈希是示意值，实际登录会失败；
> 本轮已把可用哈希写入这三个账号（`Database/rbac-align-endpoints.sql` 之外的一次性数据修正），
> 因此现在可以用它们分别演示"系统管理员 / 会议室管理员 / 普通用户"。

### 11.4 与建表脚本的关系

原 `Database/smart-meeting-room-db` 里的 `permission.url` 用的是设计稿的 `/api/reservations/*`，与真实接口 `/admin/reservation/page` 对不上，所以 21 个权限点在代码里从没被用过。
`Database/rbac-align-endpoints.sql` 把 url 对齐到真实接口，并补上 `statistics:view`、`file:upload` 两个漏掉的权限点——**执行它之后 RBAC 才真正生效**。

### 11.5 还没做的部分（如实标注）

- 前端没有 `v-perm` 指令和路由守卫：页面仍然按 `isAdmin` 分流，服务端拦住了但界面上还能点进去（点进去会 403）；
- 没有"角色/权限管理"页面，角色与权限点目前靠 SQL 维护；
- `SecurityConfig` 的 `/** permitAll` 没有动：鉴权由 `RbacInterceptor` 承担（复用 JWT 登录态），不是 Spring Security 的 `@PreAuthorize` 语义。
