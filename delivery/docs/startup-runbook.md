# 启动与端口说明

## Demo

双击根目录 start-all.cmd，或 `npm run demo`。需要 Node 20+、npm、Python、Flask、matplotlib，前端先执行 npm ci。脚本不会安装依赖。

Demo 预约/登录使用业务 mock。脚本探测 Pi 的 5000/api/health，仅 service=meeting-room-sensors 且 source=sensor 才选用它，否则启动/复用本机 5058 的会议室 Flask。健康接口成功不等于全部传感器正常，仍须核对 current 的质量字段。

## Full

```powershell
./start-all.cmd -Mode Full -CheckOnly
$env:MYSQL_PASSWORD='本机数据库密码'
./start-all.cmd -Mode Full -RpiHost 192.168.43.206
```

先准备 JDK 17+、Maven、MySQL 8、Redis；按根 README 导入 Database/smart-meeting-room-db 并配置环境变量，在 Pi 运行更新的 Flask 硬件服务。Full 不负责安装/启动系统数据库。预检后安装 Maven reactor 依赖、运行 Management 模块，再启动 Vite。首次 Maven 下载较慢，若超时，查看日志后重试。TCP 可达仅表示监听，仍须验收登录、真实预约和数据库记录。

| 端口 | 服务 | 注意 |
|---|---|---|
| 3306 / 6379 | MySQL / Redis | Full 前置依赖 |
| 8080 | Spring Boot | 占用时退出，不把 Apache 当作后端 |
| 5000 | Pi Flask | 与前端不同；固定端口，冲突报错 |
| 5001 | 人脸服务 | 独立服务，本轮不做真实识别验收 |
| 5058 | 本机传感器模拟 | source=simulation |
| 5173 起 | Vite | 占用自动递增，以输出为准 |

日志在 .codex-run-logs：preflight.json、session.json、flask.*.log、spring.*.log、vite.*.log。仅停止自己启动的进程：先用 Get-NetTCPConnection 和 Get-Process 确认身份，再 Stop-Process。重复启动可能产生多个 Vite 实例。
