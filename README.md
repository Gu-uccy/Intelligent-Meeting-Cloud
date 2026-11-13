# Intelligent-Meeting-Cloud

Intelligent Meeting Cloud is a meeting room management project with a Vue 3 frontend and a Spring Boot backend.

> **分支说明**：当前代码在 **`fullchain`** 分支 —— 本学期的最终版本（全链路打通 + RBAC 鉴权 + 操作审计）。
> `main` 分支保留学期中期的旧版本作为对照，未做改动。

> **全链路版本（推荐）**：本项目已把「真实 MySQL + Spring Boot + 自研 LBP 人脸 + 设备层 + 3D」打通，
> 实现「注册登录 → 录脸 → 刷脸预约 → 预约时段内刷脸解锁 → 3D 门打开 → 灯光联动」。
> 一键启动与演示步骤见 **[README_全链路.md](README_全链路.md)**：
>
> ```powershell
> powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-fullchain.ps1
> ```
>
> 该脚本会拉起 MySQL(3307)、后端(8081)、人脸服务(5001)、设备层(5058)、前端(5173)，
> 并自动完成建库、导入 `Database/smart-meeting-room-db`、执行 `Database/align-schema-for-code.sql` 对齐表结构。

## Project Structure

- `FrontEnd/Intelligent_meeting_cloud`: Vue 3 + Vite frontend
- `BackEnd/MeetingRoom-Parent`: Spring Boot backend
- `MachineLearning/human_face`: 自研人脸服务（`face_service_lbp.py`）与识别自测脚本
- `Flask/unified_meeting_room_system.py`: 传感器/门禁/灯光设备层
- `Database/smart-meeting-room-db`: database initialization script
- `Database/align-schema-for-code.sql`: 建表脚本与 Java 实体的列名对齐脚本（必须执行）
- `scripts/start-fullchain.ps1`: 全链路一键启动/停止/状态
- `scripts/seed_demo_data.py`: 造「覆盖当前时刻」的演示预约（刷脸解锁演示必需）

## Prerequisites

- Node.js 20+
- npm
- JDK 17+
- Maven
- MySQL 8.x
- Redis

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
3. Import `Database/smart-meeting-room-db`.
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
