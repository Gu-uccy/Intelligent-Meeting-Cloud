import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const rootDir = fileURLToPath(new URL('../', import.meta.url));
const distDir = join(rootDir, 'dist');
const port = Number(process.env.FRONTEND_PORT || process.env.VITE_PORT || 5173);
const sensorTarget = process.env.VITE_SENSOR_PROXY_TARGET || 'http://192.168.43.206:5000';

const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.woff2': 'font/woff2',
  '.glb': 'model/gltf-binary',
};

function sendStatic(requestPath, res) {
  const cleanPath = normalize(decodeURIComponent(requestPath.split('?')[0])).replace(/^(\.\.[/\\])+/, '');
  let filePath = join(distDir, cleanPath === '/' ? 'index.html' : cleanPath);

  if (!existsSync(filePath) || statSync(filePath).isDirectory()) {
    filePath = join(distDir, 'index.html');
  }

  const contentType = mimeTypes[extname(filePath).toLowerCase()] || 'application/octet-stream';
  res.writeHead(200, { 'Content-Type': contentType });
  createReadStream(filePath).pipe(res);
}

async function proxyToSensor(req, res, prefix, rewritePrefix) {
  const targetPath = req.url.replace(prefix, rewritePrefix);
  const targetUrl = new URL(targetPath, sensorTarget);
  const headers = { ...req.headers };
  delete headers.host;

  try {
    const upstream = await fetch(targetUrl, {
      method: req.method,
      headers,
      body: ['GET', 'HEAD'].includes(req.method) ? undefined : req,
      duplex: ['GET', 'HEAD'].includes(req.method) ? undefined : 'half',
    });

    const responseHeaders = {};
    upstream.headers.forEach((value, key) => {
      responseHeaders[key] = value;
    });
    res.writeHead(upstream.status, responseHeaders);

    if (req.method === 'HEAD') {
      res.end();
      return;
    }

    const buffer = Buffer.from(await upstream.arrayBuffer());
    res.end(buffer);
  } catch (error) {
    res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ error: `Sensor proxy failed: ${error.message}` }));
  }
}

const server = createServer((req, res) => {
  if (req.url.startsWith('/sensor-api')) {
    proxyToSensor(req, res, '/sensor-api', '/api');
    return;
  }

  if (req.url.startsWith('/sensor-chart')) {
    proxyToSensor(req, res, '/sensor-chart', '/chart');
    return;
  }

  sendStatic(req.url, res);
});

server.listen(port, '0.0.0.0', () => {
  console.log(`Frontend server: http://127.0.0.1:${port}`);
  console.log(`Sensor target: ${sensorTarget}`);
});

