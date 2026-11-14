# 启动与端口说明

## Demo

双击根目录 start-all.cmd，或 `npm run demo`。需要 Node 20+、npm、Python、Flask、matplotlib，前端先执行 npm ci。脚本不会安装依赖。

Demo 预约/登录使用业务 mock。脚本探测 Pi 的 5000/api/health，仅 service=meeting-room-sensors 且 source=sensor 才选用它，否则启动/复用本机 5058 的会议室 Flask。健康接口成功不等于全部传感器正常，仍须核对 current 的质量字段。

## Local：真实业务与本机模拟传感器

JDK 17+、MySQL 与当前数据库结构就绪后：

```powershell
$env:JAVA_HOME='C:\Program Files\Java\jdk-21' # 改为实际安装目录
$env:MYSQL_PASSWORD='本机数据库密码'
./start-all.cmd -Mode Local -BackendPort 18080
```

登录、预约、分页、取消走真实 Spring/MySQL，传感器固定走本机5058模拟，人脸仍为拒绝优先的独立模拟门禁。Redis不可用时 `/health` 为 `degraded` 并明确输出警告；当前业务方法未使用缓存，Local可继续。会验证数据库和当前字段，不能仅凭TCP开放当作就绪。已有端口必须返回正确服务身份与schema检查才复用，否则要求更换 `-BackendPort`，不会停止其他进程。日志和session记录业务、传感器的不同来源。

本机已安装 MySQL Server 时，可以在独立数据目录和随机端口复现全部业务HTTP测试，不需要现有root密码：

```powershell
./scripts/test-local-business.ps1
# 验收成功后保留独立实例并打开Local页面：
./scripts/test-local-business.ps1 -LaunchLocal
```

可用 `-MysqlBinDirectory` 指定MySQL的bin目录。脚本每次新建 `.codex-run-logs/business-*`，只导入该次新建的 `meeting_acceptance_*` 库，随机设置本地凭据，不读取、清空或迁移现有3306数据库。默认完成后停止本次Spring与MySQL；`-KeepRunning`/`-LaunchLocal`保留，并输出仅在本机的 `local-env.ps1`。该文件含本次随机凭据，不提交。保留运行后关闭服务，可用该目录的mysql-client.ini执行 `mysqladmin --defaults-file=... shutdown`，Spring按本次端口确认进程后停止。

## Full

```powershell
./start-all.cmd -Mode Full -CheckOnly
$env:MYSQL_PASSWORD='本机数据库密码'
./start-all.cmd -Mode Full -RpiHost 192.168.43.206
# 若8080被Apache等程序占用，改用：
./start-all.cmd -Mode Full -BackendPort 18080 -RpiHost 192.168.43.206
```

先准备 JDK 17+、MySQL 8、Redis；新空库导入 `Database/schema-current.sql`，配置MYSQL_*与REDIS_*，在Pi运行更新的Flask硬件服务。现有数据库需单独审查迁移，不能导入旧DROP脚本。仓库自带Maven Wrapper并校验固定版本，不要求全局mvn；首次联网下载后构建可执行JAR。Full校验Spring服务身份、数据库字段和Redis PING，再启动Vite。它不负责安装/启动系统数据库，也不把TCP可达等同于业务可用。实际通过范围见 [联调记录](../../analysis/taskbook-v3-2026-11-14/backend-integration/README.md)。

| 端口 | 服务 | 注意 |
|---|---|---|
| 3306 / 6379 | MySQL / Redis | Full 前置依赖 |
| 8080 或 -BackendPort | Spring Boot | 占用时核对服务身份；可改18080，代理同步更新 |
| 5000 | Pi Flask | 与前端不同；固定端口，冲突报错 |
| 5001 | 人脸服务 | 独立服务，本轮不做真实识别验收 |
| 5058 | 本机传感器模拟 | source=simulation |
| 5173 起 | Vite | 占用自动递增，以输出为准 |

日志在 .codex-run-logs：preflight.json、session.json、flask.*.log、spring.*.log、vite.*.log。仅停止自己启动的进程：先用 Get-NetTCPConnection 和 Get-Process 确认身份，再 Stop-Process。重复启动可能产生多个 Vite 实例。
