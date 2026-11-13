/**
 * rbac_check.mjs —— RBAC 鉴权矩阵验收（真实接口 + 真实数据库）
 *
 * 验证的是「服务端真的在校验」，不是前端藏了菜单：
 *   ROLE_SYS_ADMIN（admin1）     → 管理端接口应全部 200
 *   ROLE_USER（普通账号）         → 管理端接口应全部 403，且提示缺少的权限点
 *   未登录                        → 401
 *
 * 前置：
 *   1. 后端已启动（默认 8081）
 *   2. 已执行 Database/rbac-align-endpoints.sql
 *   3. 有一个管理员账号：admin1 / 123456（ROLE_SYS_ADMIN）
 *      和一个普通账号：13900000002 / 123456（ROLE_USER）
 *
 * 用法：
 *   node delivery/tests/rbac_check.mjs
 *   $env:ADMIN_ACCOUNT='admin1'; $env:USER_ACCOUNT='13900000002'; node delivery/tests/rbac_check.mjs
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const BASE = process.env.API_BASE || 'http://127.0.0.1:8081';
const ADMIN = { account: process.env.ADMIN_ACCOUNT || 'admin1', password: process.env.ADMIN_PASSWORD || '123456' };
const USER = { account: process.env.USER_ACCOUNT || '13900000002', password: process.env.USER_PASSWORD || '123456' };

const ENDPOINTS = [
  { method: 'GET', path: '/admin/room/page?page=1&pageSize=5', code: 'room:manage' },
  { method: 'GET', path: '/admin/reservation/page?page=1&pageSize=5', code: 'reservation:query:all' },
  { method: 'GET', path: '/admin/statistics/%E8%BF%917%E5%A4%A9', code: 'statistics:view' },
  { method: 'GET', path: '/admin/equipment/page?page=1&pageSize=5', code: 'fault:handle' },
  { method: 'GET', path: '/admin/user/page?page=1&pageSize=5', code: 'user:manage' },
];

const records = [];

function record(id, name, status, detail = '') {
  records.push({ id, name, status, detail });
  console.log(`[${status}] ${id} ${name}${detail ? ' :: ' + detail : ''}`);
}

async function login({ account, password }) {
  const res = await fetch(`${BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ loginAccount: account, password }),
  });
  const body = await res.json().catch(() => ({}));
  return { token: body?.data?.token, isAdmin: body?.data?.isAdmin, status: res.status };
}

async function call(token, ep) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.token = token;
  const res = await fetch(`${BASE}${ep.path}`, { method: ep.method, headers });
  const body = await res.json().catch(() => ({}));
  return { status: res.status, msg: body?.msg || body?.error || '' };
}

async function main() {
  console.log(`后端：${BASE}`);
  const admin = await login(ADMIN);
  const user = await login(USER);
  record('RBAC-00', '管理员登录', admin.token ? 'PASS' : 'FAIL', `${ADMIN.account} isAdmin=${admin.isAdmin}`);
  record('RBAC-00b', '普通用户登录', user.token ? 'PASS' : 'FAIL', `${USER.account} isAdmin=${user.isAdmin}`);

  // 1. 未登录 → 401
  let res = await call(null, ENDPOINTS[0]);
  record('RBAC-01', '未登录访问管理端', res.status === 401 ? 'PASS' : 'FAIL', `http=${res.status}`);

  // 2. 管理员 → 全部 200
  for (const [i, ep] of ENDPOINTS.entries()) {
    res = await call(admin.token, ep);
    record(`RBAC-1${i + 1}`, `管理员访问 ${ep.path.split('?')[0]}`, res.status === 200 ? 'PASS' : 'FAIL', `http=${res.status}`);
  }

  // 3. 普通用户 → 全部 403，且提示里出现所需权限点
  for (const [i, ep] of ENDPOINTS.entries()) {
    res = await call(user.token, ep);
    const ok = res.status === 403 && res.msg.includes(ep.code);
    record(`RBAC-2${i + 1}`, `普通用户访问 ${ep.path.split('?')[0]}`, ok ? 'PASS' : 'FAIL',
      `http=${res.status} ${res.msg}`.slice(0, 90));
  }

  // 4. 普通用户的业务接口不受影响
  res = await fetch(`${BASE}/user/room/page?page=1&pageSize=5`, { headers: { token: user.token } });
  record('RBAC-31', '普通用户访问用户端接口（不应被误伤）', res.status === 200 ? 'PASS' : 'FAIL', `http=${res.status}`);

  const passed = records.filter((r) => r.status === 'PASS').length;
  const outDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../results');
  mkdirSync(outDir, { recursive: true });
  writeFileSync(path.join(outDir, 'rbac_result.json'), JSON.stringify({
    ran_at: new Date().toISOString(),
    base: BASE,
    admin: ADMIN.account,
    user: USER.account,
    passed,
    total: records.length,
    records,
  }, null, 2), 'utf8');

  console.log(`\n=== RBAC：${passed}/${records.length} 通过 ===`);
  console.log(`结果：delivery/results/rbac_result.json`);
  if (passed !== records.length) process.exitCode = 1;
}

main().catch((err) => {
  console.error('执行异常：', err.message);
  process.exitCode = 2;
});
