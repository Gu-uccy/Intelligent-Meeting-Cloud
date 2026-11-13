# Intelligent Meeting Cloud Frontend

## Install

```sh
npm install
```

## Start Frontend

```sh
npm run dev
```

## Start DeepSeek Agent Proxy

1. Create `.env.agent.local` in the frontend root. You can copy from [.env.agent.example](/d:/Project/Intelligent-Meeting-Cloud/FrontEnd/Intelligent_meeting_cloud/.env.agent.example).
2. Fill in your `DEEPSEEK_API_KEY`.
3. Start the proxy:

```sh
npm run agent
```

If you want auto-reload while adjusting the proxy:

```sh
npm run agent:watch
```

## Enable Real Agent Mode

Create `.env.local` or update your local Vite env:

```env
VITE_USE_MOCK=true
VITE_AGENT_MODE=deepseek
VITE_AGENT_PROXY_TARGET=http://127.0.0.1:8787
```

Then restart `npm run dev`.

## Agent Architecture

- Frontend UI stays in Vue and keeps the existing booking mock tools.
- DeepSeek is called through a lightweight Node proxy at `scripts/deepseek-agent-proxy.mjs`.
- The model decides whether to ask follow-up questions or call tools.
- Tool execution still happens in the frontend, so it can directly reuse local mock data and current booking APIs.

## Build

```sh
npm run build
```
