# Intelligent-Meeting-Cloud

2026-11-14 本机业务联调已补齐：Maven Wrapper、Spring Boot 3 数据源/MyBatis/Redis 配置、独立 MySQL 实际预约链路与 Local 启动模式。36 项真实 HTTP/数据库检查、16 项新增预约回归及 8 项网页检查通过，见 [联调验收补充](analysis/taskbook-v3-2026-11-14/backend-integration/README.md)。Redis 和树莓派仍未接通；Local 的传感器明确为模拟。

正式材料已更新：[综III交付目录](delivery/final-2026-11-14/README.md) 包含 8 页可编辑 Word 总结报告、19 页验收校正版 PPT，以及材料文件哈希。两份材料已逐页检查，原文件保留。

2026-11-14 续作：已实际生成 Blender 原生模型并接入 3D、自研人脸算法接入服务与模拟门禁、预约助理约束和异常恢复补齐。最新完成情况和实测边界见 [续作验收记录](analysis/taskbook-v3-2026-11-14/续作验收记录.md)。历史 `delivery/results` 属于 11月11日，不能代替当前源码测试。人脸授权样本暂缺，真实指标保留待办；人脸服务默认拒绝放行。

Intelligent Meeting Cloud is a meeting room management project with a Vue 3 frontend and a Spring Boot backend.

## Project Structure

- `FrontEnd/Intelligent_meeting_cloud`: Vue 3 + Vite frontend
- `BackEnd/MeetingRoom-Parent`: Spring Boot backend
- `Database/schema-current.sql`: current schema for a NEW empty database; the old `smart-meeting-room-db` is historical and contains DROP statements

## Prerequisites

- Node.js 20+
- npm
- JDK 17+
- Maven Wrapper included; first run downloads pinned Maven 3.9.9 with checksum verification
- MySQL 8.x
- Redis (required by Full; Local reports degraded health when unavailable)

## Local Default Ports

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8080`

## Quick Start

Run from the repository root:

```powershell
npm run dev
```

This command runs the Full-mode preflight, starts Spring Boot and Vite in the background, and opens the browser. It requires MySQL, Redis and the updated Raspberry Pi Flask hardware service to already be running. Logs are in `.codex-run-logs`. Missing dependencies are reported before launch.

For an offline walkthrough, double-click `start-all.cmd` or run `npm run demo`. This uses mock booking/login and an explicitly labelled local sensor simulation when the Raspberry Pi is unavailable. The output and `.codex-run-logs/session.json` show the actual URL and source; occupied frontend ports are skipped automatically.

For real local business with simulated sensors, configure `MYSQL_*`, set `JAVA_HOME` to JDK 17+, then run `./start-all.cmd -Mode Local -BackendPort 18080`. The backend checks `/health` and current schema readiness; it never treats an occupied Apache port as Spring. To reproduce acceptance with a separate MySQL instance and fresh synthetic data, run `./scripts/test-local-business.ps1`; add `-LaunchLocal` to retain that test instance and open the UI. See [startup instructions](delivery/docs/startup-runbook.md).

Read-only preflight: `npm run preflight`. Full preflight: `./start-all.cmd -Mode Full -CheckOnly`.

You can also start them separately:

```powershell
npm run dev:backend
npm run dev:frontend
```

## Frontend Proxy

The frontend now proxies `/api` requests to the local backend by default:

- proxy target default: `http://127.0.0.1:8080`
- frontend port default: `5173`

If you want to customize it, create `FrontEnd/Intelligent_meeting_cloud/.env.local`:

```env
VITE_API_URL=/api
VITE_API_PROXY_TARGET=http://127.0.0.1:8080
VITE_PORT=5173
```

An example file is already included at:

- `FrontEnd/Intelligent_meeting_cloud/.env.example`

## Backend Preparation

Before starting the backend, make sure:

1. MySQL is running locally.
2. Create a database named `meeting_room_db`.
3. Import `Database/schema-current.sql` into a NEW empty database. Existing databases need a reviewed migration; `IF NOT EXISTS` does not add missing columns or fix existing seed accounts. Do not run the historical DROP-based initializer against an existing installation.
4. Redis is running locally on `127.0.0.1:6379`.

The backend default profile is `dev`, and it currently uses local MySQL and Redis.

## Backend Config Override

The backend config has been changed to use environment variables with local defaults.

Common variables:

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_DB`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_DB`
- `REDIS_PASSWORD`
- `JWT_USER_SECRET_KEY`
- `JWT_ADMIN_SECRET_KEY`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `OSS_ENDPOINT`
- `OSS_ACCESS_KEY_ID`
- `OSS_ACCESS_KEY_SECRET`
- `OSS_BUCKET_NAME`

Reference file:

- `BackEnd/MeetingRoom-Parent/MeetingRoom-Management/src/main/resources/application-dev.example.yml`

Example PowerShell session:

```powershell
$env:MYSQL_PASSWORD="your_mysql_password"
$env:REDIS_PASSWORD=""
npm run dev:backend
```

## One-Click Windows Start

You can also double-click:

```text
start-dev.cmd
```

## Raspberry Pi Demo Entry

When the Raspberry Pi sensor service is running on `192.168.43.206:5000`, double-click:

```text
start-demo.cmd
```

The script detects the Raspberry Pi automatically, starts the Vue frontend, and opens the demo page. If the Raspberry Pi sensor service is temporarily offline, it starts the included local simulation so the frontend can still be demonstrated. Set `RPI_HOST` before running the script when the Raspberry Pi uses another address.

## Delivery and acceptance

See [delivery/README.md](delivery/README.md) for 52 executable cases, nine screenshots, CSV/JSON raw results, startup and recovery procedures, documentation inventory and version traceability. Video is excluded from this delivery. Fixture tests do not certify physical hardware or the Spring/MySQL/Redis integration.
