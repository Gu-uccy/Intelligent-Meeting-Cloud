# Spring/MySQL 本机联调补充

2026-11-14，承接 `0b4cd3b` 后续工作。本轮将登录、会议室分页、预约提交与取消从此前的业务 mock 扩展到真实 Spring/MySQL HTTP 验收。用户确认树莓派当前未连接；传感器继续使用本机 Flask 模拟，Redis 未就绪，未做真实人脸测试。Word/PPT 保持原交付快照，本补充记录新增结果，不把新执行次数合入旧 109 次。

## 修复和实际行为

- 仓库加入官方 Maven Wrapper 3.3.2，固定 Maven 3.9.9 和分发包 SHA256；首次运行联网下载，无需全局安装 mvn。本机用 Windows PowerShell 5.1 和 JDK 21.0.4 构建成功。[Maven 官方说明](https://maven.apache.org/install.html)
- 数据源改为 Spring Boot 管理的 Hikari，使用兼容 Boot 3 的 MyBatis；移除混用的 Boot 2 MyBatis-Plus/连接池启动器，时间片改为显式 SQL，PageHelper 插件保留真实分页。Redis 配置迁至 `spring.data.redis` 并设置超时。[Boot 3 Redis 配置依据](https://docs.spring.io/spring-boot/docs/3.0.x/reference/html/data.html)
- 新增无 DROP 的 `Database/schema-current.sql`，与当前 `username/is_admin/image/version` 字段一致，种子 BCrypt 可验证。只在新空库初始化，不自动迁移现有库、不修改现有账号。验收脚本使用独立 mysqld 数据目录、随机端口和随机本机凭据，原3306数据库未读取、重置或导入；原8080 Apache保留。
- `start-all.ps1 -Mode Local` 使用真实业务、5058模拟传感器和独立人脸模拟服务；`-BackendPort` 同步配置前端代理。`/health`检查数据库、当前字段与Redis PING，schema不可用返回503。Local允许Redis缺失并报告degraded，Full仍要求Redis和真实Pi传感器服务；不以TCP监听冒充就绪。
- 预约服务端补齐缺失时间、人数/容量、禁用/不存在房间、过去时间、整半点、零时长及8小时边界校验；有效预约含待审核，前后10分钟缓冲一致；已取消预约不再阻塞时段，限制只能取消本人预约。请求结束清除当前身份，登录/JWT/对象存储初始化不再输出密码、令牌或密钥配置对象。
- 修复网页将服务端状态2误认成“即将开始”的问题，保留旧mock的-1兼容；取消须code=1才提示成功，已确认预约隐藏不可用的取消按钮。错误处理可显示后端msg，网络错误不会再因缺少response抛出二次异常。手机端预约标签可横向滚动，记录表可以横向查看状态/操作；favicon复用现有SVG。
- 补齐首页请求的当前用户通知读取接口，读取已持久化的审批通知，校验用户归属和字段映射，空表返回空列表。此次未新增自动生成审批通知、已读更新或完整RBAC权限体系。

## 验证结果

| 检查 | 结果 | 原始证据与边界 |
|---|---|---|
| Maven reactor构建 | PASS | `summary.json`、JUnit原始结果摘要；官方Wrapper，JDK21 |
| 新增预约Java回归 | 16/16 | 13类无效请求、8小时边界、他人取消、并发版本变化；Mockito隔离，不计实物 |
| 原Java占位检查 | 2/2 | 旧common/management各1，不当成新增功能证明 |
| 真实业务HTTP/数据库 | 36/36 | [business-http.json](business-http.json)：BCrypt/JWT、分页、时段、写库、冲突、取消/再预约、通知数据隔离；独立MySQL8.0.19，无业务mock |
| 桌面/手机浏览器 | 8/8 | [business-browser.json](business-browser.json)：真实登录→预约→状态回写→我的预约→取消→刷新仍取消；1366×900、390×844；传感器仅localhost模拟 |
| schema不可用 | PASS | [unavailable-health.json](unavailable-health.json)：独立失败配置，真实HTTP503，不返回伪就绪 |
| 启动/清理脚本 | PASS | [script-checks.json](script-checks.json)：PS5.1、缺依赖退出1、默认验收停止本次Spring/MySQL、已占用8080保持原进程 |
| 前端生产构建 | PASS | 主JS仍约2.05MB，保留包体积警告；不声称性能指标达标 |

浏览器检查路径：`/login`真实登录 → `/booking`选择301与未来时间片 → 提交并读取待审核占用 → “我的预约”取消 → 刷新保持已取消 → `/room-3d`真实GLB与明确标注模拟的门控确认。Browser插件未提供，使用已有Playwright和Chrome，无业务或传感器API拦截夹具。

| 网页检查 | 结果 |
|---|---|
| 页面URL/标题和非空内容 | PASS |
| Vite覆盖层 | 无 |
| 浏览器运行异常/console error | 0 / 0 |
| 交互与真实HTTP确认 | PASS |
| 截图复核 | 桌面预约前后、390宽表格左右两端、3D状态均已检查 |

截图在本机临时目录 `C:/Users/Guche/AppData/Local/Temp/meeting-business-20261114`，包含来源水印；摘要记录哈希，临时截图不作为仓库永久附件。未检查其他浏览器、全部管理接口、跨午夜预约弹窗或低性能设备。

## 复现

```powershell
$env:JAVA_HOME='C:\Program Files\Java\jdk-21' # 改为实际JDK17+目录
./scripts/test-local-business.ps1
# 保留新建的测试实例并打开Local模式：
./scripts/test-local-business.ps1 -LaunchLocal
```

默认脚本构建并执行Java测试，创建全新 `meeting_acceptance_*` 数据库，执行HTTP检查，结束后停止本次服务；可通过 `-MysqlBinDirectory` 指定已安装MySQL的bin目录。日志与凭据仅存 `.codex-run-logs/business-*`，不要提交。浏览器复测需Local启动完成后：

```powershell
$env:ACCEPTANCE_URL='http://127.0.0.1:5190' # 改为控制台实际地址
$env:EVIDENCE_OUTPUT_DIR='.codex-run-logs/recheck-business-ui'
node delivery/tests/local_business_browser.mjs
```

浏览器脚本当前使用本机已有的Playwright运行时路径；其他机器需要调整模块路径，前端、Python依赖亦需预先安装。测试账号 `test_user / 123456` 仅用于本地合成数据验收。

## 保留待办

Redis真实连接/认证、Full模式与树莓派LED/舵机实物联调；授权人脸≥3人×10张及真实指标/目标设备完整耗时；真实团队姓名、学号、分工、签名和学校格式确认。视频继续按用户要求不制作。当前结果不能证明完整RBAC、全部管理接口、实时人数、门磁到位、真实人脸识别或物理设备性能。
