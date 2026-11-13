import { createServer } from 'node:http';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..');
const envFilePath = path.join(projectRoot, '.env.agent.local');

const parseEnvFile = (filePath) => {
  if (!existsSync(filePath)) return {};

  return readFileSync(filePath, 'utf8')
    .split(/\r?\n/)
    .reduce((acc, line) => {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) return acc;

      const separatorIndex = trimmed.indexOf('=');
      if (separatorIndex === -1) return acc;

      const key = trimmed.slice(0, separatorIndex).trim();
      const value = trimmed.slice(separatorIndex + 1).trim().replace(/^['"]|['"]$/g, '');

      acc[key] = value;
      return acc;
    }, {});
};

const fileEnv = parseEnvFile(envFilePath);

const getEnvValue = (key, fallback = '') => process.env[key] || fileEnv[key] || fallback;

const AGENT_PROXY_PORT = Number(getEnvValue('AGENT_PROXY_PORT', '8787'));
const DEEPSEEK_BASE_URL = getEnvValue('DEEPSEEK_BASE_URL', 'https://api.deepseek.com');
const DEEPSEEK_MODEL = getEnvValue('DEEPSEEK_MODEL', 'deepseek-chat');
const DEEPSEEK_API_KEY = getEnvValue('DEEPSEEK_API_KEY');

const sendJson = (response, statusCode, payload) => {
  response.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  });
  response.end(JSON.stringify(payload));
};

const readBody = (request) =>
  new Promise((resolve, reject) => {
    let raw = '';

    request.on('data', (chunk) => {
      raw += chunk;
      if (raw.length > 1024 * 1024) {
        reject(new Error('Request body is too large.'));
      }
    });

    request.on('end', () => {
      try {
        resolve(raw ? JSON.parse(raw) : {});
      } catch (error) {
        reject(new Error('Invalid JSON request body.'));
      }
    });

    request.on('error', reject);
  });

const forwardChatCompletion = async (payload) => {
  if (!DEEPSEEK_API_KEY) {
    throw new Error('Missing DEEPSEEK_API_KEY. Please set it in the environment or .env.agent.local.');
  }

  const response = await fetch(`${DEEPSEEK_BASE_URL}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${DEEPSEEK_API_KEY}`,
    },
    body: JSON.stringify({
      model: payload.model || DEEPSEEK_MODEL,
      messages: payload.messages || [],
      tools: payload.tools,
      tool_choice: payload.tool_choice || 'auto',
      temperature: payload.temperature ?? 0.2,
      max_tokens: payload.max_tokens ?? 1200,
      response_format: payload.response_format,
      stream: false,
    }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMessage = data?.error?.message || data?.message || 'DeepSeek request failed.';
    throw new Error(errorMessage);
  }

  return data;
};

const server = createServer(async (request, response) => {
  if (request.method === 'OPTIONS') {
    sendJson(response, 204, {});
    return;
  }

  if (request.method === 'GET' && request.url === '/health') {
    sendJson(response, 200, {
      ok: true,
      model: DEEPSEEK_MODEL,
      hasApiKey: Boolean(DEEPSEEK_API_KEY),
      usingEnvFile: existsSync(envFilePath),
    });
    return;
  }

  if (request.method === 'POST' && request.url === '/chat/completions') {
    try {
      const payload = await readBody(request);
      const data = await forwardChatCompletion(payload);
      sendJson(response, 200, data);
    } catch (error) {
      sendJson(response, 500, {
        error: {
          message: error.message || 'Agent proxy failed.',
        },
      });
    }
    return;
  }

  sendJson(response, 404, {
    error: {
      message: 'Not found.',
    },
  });
});

server.listen(AGENT_PROXY_PORT, '127.0.0.1', () => {
  console.log(`[agent-proxy] listening on http://127.0.0.1:${AGENT_PROXY_PORT}`);
  console.log(`[agent-proxy] model=${DEEPSEEK_MODEL}`);
  console.log(`[agent-proxy] envFile=${existsSync(envFilePath) ? envFilePath : 'not found'}`);
});
