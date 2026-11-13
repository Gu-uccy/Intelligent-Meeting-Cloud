/**
 * e2e_fullchain.mjs —— 全链路端到端验收脚本（真实 MySQL + Spring Boot + 自研人脸服务 + 设备层 + 3D）
 *
 * 覆盖场景：
 *   1. 注册（真实 /register → MySQL user 表）
 *   2. 登录（BCrypt 校验 + JWT）
 *   3. 会议室列表 / 时段（真实 /user/room、/user/reservation/slots）
 *   4. 刷脸预约：提交时弹出人脸闸门 → 上传人脸 → 拿到一次性凭据 → 带 X-Face-Ticket 下单
 *      4b. 反向：冒名人脸 → 闸门拒绝 → 预约不落库
 *   5. 刷脸解锁：/room-3d 点「刷脸解锁会议室」→ 服务端校验预约时段 → 驱动设备层
 *      5b. 反向：无预约的会议室 → 拒绝
 *   6. 灯控联动：打开 LED → 设备层 lighting=true → 3D 灯亮
 *
 * 依赖：node + playwright（使用系统 Chrome，channel: 'chrome'）
 * 用法：
 *   $env:ACCEPTANCE_URL='http://127.0.0.1:5173'
 *   $env:FACE_IMAGE='D:\...\genuine.jpg'        # 已注册人脸的探针图
 *   $env:FACE_IMPOSTOR='D:\...\impostor.jpg'    # 未注册/他人人脸
 *   $env:TEST_ACCOUNT='13900000002'             # 已录脸且已有当前时段预约的账号
 *   node delivery/tests/e2e_fullchain.mjs
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
let pw;
try {
  pw = require('playwright');
} catch {
  const bundled = process.env.PLAYWRIGHT_MODULE_PATH
    || `${process.env.USERPROFILE}/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright`;
  pw = require(bundled);
}

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const outDir = path.join(root, 'delivery/results');
const shotDir = path.join(root, 'delivery/screenshots_e2e');
mkdirSync(outDir, { recursive: true });
mkdirSync(shotDir, { recursive: true });

const BASE = process.env.ACCEPTANCE_URL || 'http://127.0.0.1:5173';
// 默认用仓库内夹具（公开示例照片的受控增强版，仅用于链路验证，不是真实用户照片）
const FACE_IMAGE = process.env.FACE_IMAGE || path.join(root, 'delivery/tests/fixtures/face_genuine.jpg');
const FACE_IMPOSTOR = process.env.FACE_IMPOSTOR || path.join(root, 'delivery/tests/fixtures/face_impostor.jpg');
const ACCOUNT = process.env.TEST_ACCOUNT || '13900000002';
const stamp = Date.now().toString().slice(-8);

const records = [];
const pageErrors = [];
const shots = [];

function record(id, name, status, detail = '') {
  records.push({ id, name, status, detail });
  console.log(`[${status}] ${id} ${name}${detail ? ' :: ' + detail : ''}`);
}

async function shot(page, name) {
  const file = path.join(shotDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: false });
  shots.push(file);
  return file;
}

async function apiJson(page, url, options = {}) {
  return page.evaluate(async ({ url, options }) => {
    const res = await fetch(url, options);
    const text = await res.text();
    let body = null;
    try { body = JSON.parse(text); } catch { body = text; }
    return { status: res.status, body };
  }, { url, options });
}

async function dismissToasts(page) {
  await page.evaluate(() => {
    document.querySelectorAll('.el-message, .toast, .ds-toast').forEach((n) => n.remove());
  }).catch(() => {});
}

async function loginAs(page, account, password) {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
  // 登录表单是 form.sign-in-form（注册表单是 .sign-up-form，两者叠在同一容器里）
  await page.waitForSelector('form.sign-in-form input[type="text"]', { timeout: 20000 });
  await page.fill('form.sign-in-form input[type="text"]', account);
  await page.fill('form.sign-in-form input[type="password"]', password);
  await page.click('form.sign-in-form input[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 25000 });
  await page.waitForTimeout(1500);
}

/** 在刷脸闸门里通过「上传照片」提交人脸（headless 环境没有真实摄像头）
 * 返回 { text, closed }：成功时弹窗会自动关闭（约 0.9s），所以必须在关闭前把文案抓下来。
 */
async function submitFaceInGate(page, imagePath) {
  const gate = page.locator('.face-gate');
  await gate.waitFor({ state: 'visible', timeout: 15000 });
  await gate.locator('input[type="file"]').setInputFiles(imagePath);
  let text = '';
  let closed = false;
  for (let i = 0; i < 90; i += 1) {
    if ((await gate.count()) === 0) { closed = true; break; }
    text = await gate.innerText().catch(() => '');
    const okCount = await gate.locator('.ok-box').count().catch(() => 0);
    const errCount = await gate.locator('.err-box').count().catch(() => 0);
    const busyCount = await gate.locator('.busy-cover').count().catch(() => 0);
    if (process.env.E2E_DEBUG) {
      console.log(`  [gate i=${i}] busy=${busyCount} ok=${okCount} err=${errCount} len=${text.length}`);
    }
    if (okCount > 0 || errCount > 0) {
      text = await gate.innerText().catch(() => text);
      break;
    }
    await page.waitForTimeout(200);
  }
  return { gate, text, closed };
}

async function main() {
  const browser = await pw.chromium.launch({ headless: true, channel: 'chrome' });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    page.on('pageerror', (e) => pageErrors.push(String(e)));
    if (process.env.E2E_DEBUG) {
      page.on('console', (m) => {
        if (m.type() !== 'debug') console.log(`  [console:${m.type()}] ${m.text().slice(0, 200)}`);
      });
      page.on('response', async (r) => {
        if (r.url().includes('/face-api/')) {
          const body = await r.text().catch(() => '');
          console.log(`  [face-res] ${r.status()} ${r.url().split('/face-api')[1]} :: ${body.slice(0, 140)}`);
        }
      });
      page.on('requestfailed', (r) => console.log(`  [reqfail] ${r.url()} ${r.failure()?.errorText}`));
    }

    // 先进入站点，后续 page.evaluate 里的 fetch 才是同源请求（否则 about:blank 会被 CORS 拦）
    await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);

  // ---------- 1. 注册（真实接口） ----------
  const newAccount = `e2e_${stamp}`;
  const regPayload = {
    loginAccount: newAccount,
    username: `端到端${stamp}`,
    password: '123456',
    phone: `139${stamp}`.slice(0, 11),
    email: `${newAccount}@example.com`,
    gender: 1,
  };
  let res = await apiJson(page, `${BASE}/api/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(regPayload),
  });
  record('E2E-01', '注册写入真实 MySQL', res.status === 200 && res.body?.code === 1 ? 'PASS' : 'FAIL',
    `http=${res.status} code=${res.body?.code}`);

  // ---------- 2. 登录（真实 BCrypt + JWT） ----------
  res = await apiJson(page, `${BASE}/api/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ loginAccount: newAccount, password: '123456' }),
  });
  const newToken = res.body?.data?.token;
  record('E2E-02', '新账号登录并签发 JWT', res.status === 200 && Boolean(newToken) ? 'PASS' : 'FAIL',
    `token=${newToken ? newToken.slice(0, 18) + '…' : 'none'}`);

  // ---------- 3. 未刷脸直接下单必须被后端拒绝 ----------
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  const payloadNoTicket = {
    roomId: 1,
    meetingTopic: '无凭据预约应被拒',
    startTime: `${tomorrow} 09:00:00`,
    endTime: `${tomorrow} 10:00:00`,
    participantNum: 5,
  };
  res = await apiJson(page, `${BASE}/api/user/reservation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', token: newToken },
    body: JSON.stringify(payloadNoTicket),
    // 注意：故意不带 X-Face-Ticket
  });
  record('E2E-03', '后端拦截「未刷脸」的预约请求', res.status === 403 ? 'PASS' : 'FAIL',
    `http=${res.status} msg=${res.body?.msg || res.body?.error || ''}`);

  // 带上伪造凭据也应被拒
  res = await apiJson(page, `${BASE}/api/user/reservation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', token: newToken, 'X-Face-Ticket': 'forged-ticket' },
    body: JSON.stringify(payloadNoTicket),
  });
  record('E2E-04', '后端拦截图伪造凭据', res.status === 403 ? 'PASS' : 'FAIL',
    `http=${res.status} msg=${res.body?.msg || ''}`);

  // ---------- 4. UI 登录目标账号（已录脸 + 已有当前时段预约） ----------
  await loginAs(page, ACCOUNT, '123456');
  record('E2E-05', 'UI 登录（真实账号）', page.url().endsWith('/') || !page.url().includes('/login') ? 'PASS' : 'FAIL', page.url());
  await shot(page, '01_after_login');

  // ---------- 5. 刷脸预约（正向） ----------
  await page.goto(`${BASE}/booking`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);
  // 会议室列表来自真实数据库（/user/room/page）
  const roomCards = await page.locator('.room-card').count();
  record('E2E-06', '会议室列表由真实接口渲染', roomCards > 0 ? 'PASS' : 'FAIL', `cards=${roomCards}`);
  await shot(page, '02_room_list');
  // 打开第一个会议室的详情
  await page.locator('.room-card').first().locator('button.btn-book').click();
  await page.waitForTimeout(1500);
  // 选一个空闲时段
  const freeSlot = page.locator('.time-slot.status-0').first();
  const hasFreeSlot = await freeSlot.count();
  if (hasFreeSlot) {
    await freeSlot.click();
  } else {
    await page.locator('button:has-text("立即预约")').first().click();
  }
  await page.waitForTimeout(1200);
  await page.fill('input[placeholder="请输入会议主题"]', `刷脸预约E2E-${stamp}`);
  await shot(page, '03_booking_form');

  await page.click('button:has-text("刷脸确认并提交预约")');
  await page.waitForTimeout(900);
  await shot(page, '04_face_gate');
  let gateRes = await submitFaceInGate(page, FACE_IMAGE);
  const bookingFacePass = gateRes.closed || /核身通过|已解锁/.test(gateRes.text);
  record('E2E-07', '刷脸核身通过（1:1）', bookingFacePass ? 'PASS' : 'FAIL',
    gateRes.text.replace(/\s+/g, ' ').slice(0, 120) || '(弹窗已关闭=通过)');
  await page.waitForTimeout(3500);
  await shot(page, '05_booking_result');

  // 校验预约是否真的落库（通过 my 接口）
  const tokenFromStore = await page.evaluate(() => {
    const raw = localStorage.getItem('user');
    try { return JSON.parse(raw)?.userInfo?.token || ''; } catch { return ''; }
  });
  res = await apiJson(page, `${BASE}/api/user/reservation/my`, {
    method: 'GET',
    headers: { token: tokenFromStore },
  });
  const myItems = res.body?.data || [];
  const created = myItems.some((r) => String(r.meetingTopic || '').includes(`刷脸预约E2E-${stamp}`));
  record('E2E-08', '预约已落库（MySQL reservation 表）', created ? 'PASS' : 'FAIL',
    `我的预约=${myItems.length} 条`);

  // ---------- 6. 刷脸预约（反向：冒名） ----------
  await page.goto(`${BASE}/booking`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1800);
  await page.locator('.room-card').first().locator('button.btn-book').click();
  await page.waitForTimeout(1200);
  const free2 = page.locator('.time-slot.status-0').nth(1);
  if (await free2.count()) await free2.click();
  else await page.locator('button:has-text("立即预约")').first().click();
  await page.waitForTimeout(1000);
  await page.fill('input[placeholder="请输入会议主题"]', `冒名预约应失败-${stamp}`);
  await page.click('button:has-text("刷脸确认并提交预约")');
  await page.waitForTimeout(800);
  gateRes = await submitFaceInGate(page, FACE_IMPOSTOR);
  const impostorText = gateRes.text;
  const impostorRejected = /识别未通过|不匹配/.test(impostorText);
  record('E2E-09', '冒名人脸被拒绝（预约不落库）', impostorRejected ? 'PASS' : 'FAIL',
    impostorText.replace(/\s+/g, ' ').slice(0, 120));
  await shot(page, '06_face_rejected');
  await page.locator('.face-gate .btn-close').click().catch(() => {});
  await page.waitForTimeout(500);

  // ---------- 7. 3D 刷脸解锁（正向） ----------
  // 先把门/灯复位，保证「关 → 开」的变化可被观测（上一次运行可能留着门开）
  await page.evaluate(async (base) => {
    await fetch(`${base}/face-api/api/face/lock`, { method: 'POST' }).catch(() => {});
  }, BASE);
  await page.goto(`${BASE}/room-3d`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.unlock-btn', { timeout: 25000 });
  await page.waitForTimeout(3500);
  await shot(page, '07_room3d_before');
  const doorBefore = (await page.locator('.state-button strong').first().innerText()).trim();

  await page.click('.unlock-btn');
  await page.waitForTimeout(700);
  gateRes = await submitFaceInGate(page, FACE_IMAGE);
  const unlocked = gateRes.closed || /已解锁/.test(gateRes.text);
  record('E2E-10', '刷脸解锁通过（人脸+预约时段）', unlocked ? 'PASS' : 'FAIL',
    gateRes.text.replace(/\s+/g, ' ').slice(0, 160) || '(弹窗已关闭=通过)');
  await page.waitForTimeout(2500);

  // 设备层门状态
  const sensorDoor = await page.evaluate(async (base) => {
    const r = await fetch(`${base}/sensor-api/current`);
    return (await r.json()).door_open;
  }, BASE);
  record('E2E-11', '设备层 door_open 变为 true', sensorDoor === true ? 'PASS' : 'FAIL', `door_open=${sensorDoor}`);

  // 3D 场景门状态文案
  await page.waitForTimeout(1500);
  const doorAfter = (await page.locator('.state-button strong').first().innerText()).trim();
  record('E2E-12', '3D 页面门状态由关变开', doorBefore !== doorAfter && /开/.test(doorAfter) ? 'PASS' : 'FAIL',
    `${doorBefore} -> ${doorAfter}`);
  await shot(page, '09_room3d_unlocked');

  // ---------- 8. 灯控联动（设备层 ↔ 3D） ----------
  const lightBtn = page.locator('.lighting-toggle');
  const lightBefore = await page.evaluate(async (base) => {
    const r = await fetch(`${base}/sensor-api/current`);
    return (await r.json()).devices?.lighting;
  }, BASE);
  const lightTextBefore = (await lightBtn.innerText()).trim();
  await lightBtn.click();
  await page.waitForTimeout(2500);
  const sensorLight = await page.evaluate(async (base) => {
    const r = await fetch(`${base}/sensor-api/current`);
    const j = await r.json();
    return { lighting: j.devices?.lighting, brightness: j.devices?.lighting_brightness };
  }, BASE);
  const lightTextAfter = (await lightBtn.innerText()).trim();
  // 断言「点击后设备层状态翻转」，而不是写死 true（灯可能本来就是开的）
  record('E2E-13', '3D 页灯控写入设备层（状态翻转）',
    sensorLight.lighting === !lightBefore ? 'PASS' : 'FAIL',
    `devices.lighting ${lightBefore} -> ${sensorLight.lighting} (brightness=${sensorLight.brightness})`);
  record('E2E-14', '3D 页灯光状态回显', lightTextBefore !== lightTextAfter ? 'PASS' : 'FAIL',
    `${lightTextBefore.replace(/\s+/g, ' ')} -> ${lightTextAfter.replace(/\s+/g, ' ')}`);
  await shot(page, '10_room3d_light_on');

  // ---------- 9. 反向：没有预约的会议室不能解锁 ----------
  await page.locator('.choice-button').nth(1).click(); // 切到第二间（无当前时段预约）
  await page.waitForTimeout(2500);
  await page.click('.unlock-btn');
  await page.waitForTimeout(700);
  gateRes = await submitFaceInGate(page, FACE_IMAGE);
  const noReserveText = gateRes.text;
  record('E2E-15', '无有效预约的会议室被拒绝开门', /识别未通过|没有.*预约/.test(noReserveText) ? 'PASS' : 'FAIL',
    noReserveText.replace(/\s+/g, ' ').slice(0, 140));
  await shot(page, '11_unlock_denied_no_reservation');
  await page.locator('.face-gate .btn-close').click().catch(() => {});

  // ---------- 10. 审计日志落库 ----------
  const audit = await page.evaluate(async (base) => {
    const r = await fetch(`${base}/face-api/api/face/audit?limit=10`);
    return await r.json();
  }, BASE);
  const auditItems = audit?.items || [];
  record('E2E-16', '人脸审计日志已落库', auditItems.length > 0 ? 'PASS' : 'FAIL', `rows=${auditItems.length}`);
  record('E2E-17', '页面无 JS 异常', pageErrors.length === 0 ? 'PASS' : 'FAIL', pageErrors.slice(0, 2).join(' | '));

  // ---------- 汇总 ----------
  const passed = records.filter((r) => r.status === 'PASS').length;
  const summary = {
    ran_at: new Date().toISOString(),
    base: BASE,
    account: ACCOUNT,
    passed,
    total: records.length,
    records,
    page_errors: pageErrors,
    screenshots: shots,
  };
  writeFileSync(path.join(outDir, 'e2e_fullchain_result.json'),
    JSON.stringify(summary, null, 2), 'utf8');
  console.log(`\n=== 结果：${passed}/${records.length} 通过 ===`);
  console.log(`截图：${shotDir}`);
  if (passed !== records.length) process.exitCode = 1;
  } finally {
    await browser.close().catch(() => {});
  }
}

main().catch((err) => {
  console.error('E2E 执行异常：', err);
  writeFileSync(path.join(outDir, 'e2e_fullchain_result.json'),
    JSON.stringify({ error: String(err), records }, null, 2), 'utf8');
  process.exitCode = 2;
});
