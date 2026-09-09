# Intelligent-Meeting-Cloud

Intelligent Meeting Cloud is a meeting room management project with a Vue 3 frontend and a Spring Boot backend.

## Project Structure

- `FrontEnd/Intelligent_meeting_cloud`: Vue 3 + Vite frontend
- `BackEnd/MeetingRoom-Parent`: Spring Boot backend
- `Database/smart-meeting-room-db`: database initialization script

## Prerequisites

- Node.js 20+
- npm
- JDK 11
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

This command opens two PowerShell windows:

- one for the Spring Boot backend
- one for the Vite frontend

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
