// Browser plugin not available. Use local Playwright; API fixtures never reach physical GPIO.
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
let pw;
try { pw = require('playwright'); } catch {
  const bundled = process.env.PLAYWRIGHT_MODULE_PATH || `${process.env.USERPROFILE}/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright`;
  pw = require(bundled);
}
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const out = process.env.EVIDENCE_OUTPUT_DIR || path.join(root, 'delivery/results');
const shots = process.env.EVIDENCE_SCREENSHOT_DIR || path.join(root, 'delivery/screenshots');
mkdirSync(out, { recursive: true }); mkdirSync(shots, { recursive: true });
const base = process.env.ACCEPTANCE_URL || 'http://127.0.0.1:5188';
const records = [], errors = [], warnings = [], screenshots = [], timings = [];
const browser = await pw.chromium.launch({ headless: true, channel: process.env.ACCEPTANCE_BROWSER || 'chrome' });
const context = await browser.newContext({ viewport: { width: 1366, height: 768 }, acceptDownloads: true });
const page = await context.newPage();
page.on('pageerror', error => errors.push(String(error)));
page.on('console', msg => { if (msg.type() === 'warning') warnings.push(msg.text()); });
let fixture = {
  source: 'simulation', quality: 'normal', temperature: 24.5, humidity: 48, distance: 85,
  light: 70, smoke: 20, motion: false, presence: false, people_count: 0,
  door_open: false, door_source: 'simulation', sensor_status: { climate: 'ok' },
  devices: { lighting: true, lighting_brightness: 100, door_open: false, door_source: 'simulation', alarm: false },
};
let unavailable = false, controlFailure = false;
await context.route('**/sensor-api/**', async route => {
  const url = route.request().url();
  if (unavailable) return route.fulfill({ status: 503, json: { error: 'acceptance injected outage' } });
  // Exercise a real HTTP download from the local simulation Flask server.
  if (url.includes('/export/csv')) return route.continue();
  if (url.endsWith('/control')) {
    if (controlFailure) return route.fulfill({ status: 503, json: { success: false, error: 'injected driver failure' } });
    const req = route.request().postDataJSON();
    if (req.device === 'door') {
      fixture.door_open = fixture.devices.door_open = req.state;
      fixture.door_source = fixture.devices.door_source = 'test-fixture';
    } else if (req.device === 'lighting') {
      fixture.devices.lighting = req.state; fixture.devices.lighting_brightness = req.brightness;
    }
    return route.fulfill({ json: { success: true, devices: fixture.devices, source: fixture.source } });
  }
  return route.fulfill({ json: { ...fixture, timestamp: new Date().toISOString() } });
});
const check = async (id, name, fn) => {
  const started = performance.now();
  try { await fn(); records.push({ id: `TC_${id}`, name, status: 'PASS', scope: 'Chromium / browser API fixtures / business mock', duration_ms: +(performance.now()-started).toFixed(2) }); }
  catch (error) { console.log(String(error)); records.push({ id: `TC_${id}`, name, status: 'FAIL', scope: 'Chromium / browser API fixtures / business mock', detail: String(error), duration_ms: +(performance.now()-started).toFixed(2) }); }
  console.log(`${records.at(-1).id} ${records.at(-1).status} ${name}`);
};
// playwright package ships no expect; small assertion using auto-wait instead.
const waitVisible = async locator => { await locator.waitFor({ state: 'visible', timeout: 15000 }); };
const refresh = async () => { await page.reload(); await waitVisible(page.locator('.status-pill')); await page.waitForFunction(() => !document.querySelector('.status-pill')?.classList.contains('connecting')); };
const screenshot = async (file, scenario) => {
  await page.evaluate(() => {
    let badge = document.getElementById('acceptance-evidence');
    if (!badge) { badge = document.createElement('div'); badge.id = 'acceptance-evidence'; document.body.appendChild(badge); }
    badge.textContent = '验收自动化 · API测试夹具 · 非现场硬件读数';
    Object.assign(badge.style, { position: 'fixed', bottom: '0', right: '0', background: '#0f172a', color: '#fbbf24', font: '12px sans-serif', padding: '6px', zIndex: '99999' });
  });
  await page.screenshot({ path: path.join(shots, file), fullPage: true });
  screenshots.push({ file, scenario, viewport: page.viewportSize(), data_source: 'browser-test-fixture' });
};
try {
  await check(33, '登录页内容与输入框', async () => { await page.goto(`${base}/login`); await waitVisible(page.locator('.sign-in-form').getByPlaceholder('用户名', { exact: true })); assert.match(await page.title(), /智会云/); });
  await check(34, '演示账号登录跳转', async () => {
    await page.locator('.sign-in-form').getByPlaceholder('用户名', { exact: true }).fill('test_user');
    await page.locator('.sign-in-form input[type=password]').fill('123456');
    await page.locator('.sign-in-form').evaluate(form => form.requestSubmit());
    await page.waitForURL(`${base}/`); assert.ok(await page.evaluate(() => !!localStorage.getItem('user')));
  });
  await check(35, '会议室列表加载', async () => { await page.goto(`${base}/booking`); await waitVisible(page.locator('.room-card').first()); });
  await check(36, '选择会议室与空闲时间片', async () => {
    await page.getByRole('button', { name: '立即预约', exact: true }).first().click();
    const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate()+1);
    const date = `${tomorrow.getFullYear()}-${String(tomorrow.getMonth()+1).padStart(2,'0')}-${String(tomorrow.getDate()).padStart(2,'0')}`;
    await page.locator('.date-picker').fill(date);
    await page.locator('.date-picker').dispatchEvent('change');
    await waitVisible(page.locator('.time-slot.status-0').first());
    await page.locator('.time-slot.status-0').first().click();
    await waitVisible(page.getByPlaceholder('请输入会议主题'));
  });
  await check(37, '提交预约并持久化到演示存储', async () => {
    await page.getByPlaceholder('请输入会议主题').fill('交付验收自动测试');
    await page.getByRole('button', { name: '提交预约申请', exact: true }).click();
    await page.waitForFunction(() => Object.values(localStorage).some(v => v.includes('交付验收自动测试')));
    await page.locator('.modal-overlay').waitFor({ state: 'hidden' });
  });
  await check(38, '3D页面身份、主体与无错误覆盖层', async () => {
    await page.goto(`${base}/room-3d`); await waitVisible(page.getByRole('heading', { name: '3D智能会议室模型展厅' }));
    assert.equal(await page.locator('vite-error-overlay').count(), 0); assert.equal(new URL(page.url()).pathname, '/room-3d');
  });
  await check(39, 'WebGL画布创建且尺寸有效', async () => {
    await waitVisible(page.locator('.viewport canvas')); const box = await page.locator('.viewport canvas').boundingBox(); assert.ok(box.width > 200 && box.height > 200);
    await page.waitForTimeout(500);
  });
  await check(40, '模拟接口明确标注', async () => { await waitVisible(page.locator('.status-pill.simulation')); });
  await check(41, '传感器来源映射为实时状态（夹具）', async () => { fixture.source = 'sensor'; await refresh(); await waitVisible(page.locator('.status-pill.live')); });
  await check(42, '温湿度轮询动态更新', async () => {
    fixture.temperature = 28.7; fixture.humidity = 55;
    await page.locator('.sensor-card').filter({ hasText: '温度' }).getByText('28.7℃').waitFor({ timeout: 10000 });
    await waitVisible(page.locator('.sensor-card').filter({ hasText: '湿度' }).getByText('55%'));
  });
  await check(43, '人员状态刷新', async () => { fixture.motion = fixture.presence = true; fixture.people_count = 3; await refresh(); await waitVisible(page.locator('.stage-state').getByText('3人', { exact: true })); });
  await check(44, '点击门回写并更新场景状态', async () => {
    await page.locator('.state-button').click(); await waitVisible(page.locator('.stage-state').getByText('门开', { exact: true })); assert.equal(fixture.door_open, true);
    await screenshot('05_door_open.png', 'door command written back, door open');
  });
  await check(45, '点击灯回写并更新场景状态', async () => {
    await page.getByRole('button', { name: /关闭LED灯/ }).click();
    await waitVisible(page.locator('.stage-state').getByText('灯关', { exact: true })); assert.equal(fixture.devices.lighting, false);
    await screenshot('06_light_off.png', 'lighting command written back, light off');
  });
  await check(46, '会议室、氛围与视角切换', async () => {
    await page.locator('button[title="培训研讨室"]').click();
    await page.getByRole('button', { name: '演示汇报', exact: true }).click();
    await page.getByRole('button', { name: '俯视', exact: true }).click();
    await waitVisible(page.locator('.stage-bar').getByText('培训研讨室', { exact: true }));
    assert.match(await page.locator('.stage-bar').innerText(), /演示汇报/);
  });
  await check(47, '烟雾越界显示报警', async () => { fixture.smoke = 180; await refresh(); await waitVisible(page.getByRole('alert').filter({ hasText: '烟雾越界' })); await screenshot('07_smoke_alarm.png', 'smoke threshold alarm fixture'); fixture.smoke = 20; });
  await check(48, '传感器缺失仍保留门灯且不伪造零值', async () => {
    fixture.temperature = fixture.humidity = null; fixture.quality = 'partial'; fixture.sensor_status.climate = 'unavailable';
    await refresh(); await waitVisible(page.locator('.status-pill.partial'));
    assert.equal(await page.locator('.sensor-card').filter({ hasText: '温度' }).locator('strong').innerText(), '--');
    await waitVisible(page.locator('.state-button')); await screenshot('08_sensor_partial.png', 'DHT missing, door and light retained');
    fixture.temperature = 24.5; fixture.humidity = 48; fixture.quality = 'normal'; fixture.sensor_status.climate = 'ok';
  });
  await check(49, '控制失败保留状态、服务中断与恢复', async () => {
    controlFailure = true;
    await page.locator('.state-button').click();
    await waitVisible(page.getByRole('alert').filter({ hasText: '门控制失败' }));
    await waitVisible(page.locator('.stage-state').getByText('门开', { exact: true }));
    await page.getByRole('button', { name: /打开LED灯/ }).click();
    await waitVisible(page.getByRole('alert').filter({ hasText: '灯光控制失败' }));
    await waitVisible(page.locator('.stage-state').getByText('灯关', { exact: true }));
    assert.equal(fixture.door_open, true); assert.equal(fixture.devices.lighting, false);
    controlFailure = false;
    unavailable = true; await refresh(); await waitVisible(page.locator('.status-pill.disconnected'));
    await screenshot('09_service_disconnected.png', 'injected service 503, retained last state');
    unavailable = false; await refresh(); await waitVisible(page.locator('.status-pill.live'));
  });
  await check(50, '四档分辨率无水平溢出与截图矩阵', async () => {
    let i = 0;
    for (const [width, height] of [[1920,1080], [1366,768], [1024,768], [390,844]]) {
      await page.setViewportSize({ width, height }); const started = performance.now(); await refresh();
      await page.locator('.viewport canvas').scrollIntoViewIfNeeded(); await page.waitForTimeout(300);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `overflow at ${width}`);
      assert.ok(await page.locator('.sensor-card strong').evaluateAll(nodes => nodes.every(n => n.scrollWidth <= n.clientWidth + 1)), `sensor text clipped at ${width}`);
      assert.ok(await page.locator('.brand-text').evaluate(n => n.getBoundingClientRect().height < 50), `brand wraps at ${width}`);
      if (width < 641) {
        const canvas = await page.locator('.viewport').boundingBox();
        const dock = await page.locator('.sensor-dock').boundingBox();
        assert.ok(dock.y >= canvas.y + canvas.height, 'mobile cards must not cover the room');
      }
      timings.push({ viewport: `${width}x${height}`, ready_ms: +(performance.now()-started).toFixed(2), scope: 'dev_server_reload_and_state_ready' });
      await screenshot(`0${++i}_room3d_${width}x${height}.png`, 'responsive normal state');
    }
  });
  await check(51, '浏览器运行异常与帧间隔采样', async () => {
    assert.deepEqual(errors, []);
    const frames = await page.evaluate(() => new Promise(resolve => { const intervals = []; let prev; const begin = performance.now(); function frame(t) { if (prev) intervals.push(t-prev); prev=t; if(t-begin<2000) requestAnimationFrame(frame); else resolve(intervals); } requestAnimationFrame(frame); }));
    writeFileSync(path.join(out, 'frame_intervals.csv'), 'sample,interval_ms,scope\n' + frames.map((v,i)=>`${i+1},${v.toFixed(3)},headless_browser_raf`).join('\n'));
    assert.ok(frames.length > 5);
  });
  await check(52, 'CSV导出下载闭环', async () => {
    const download = page.waitForEvent('download'); await page.getByRole('link', { name: '导出采样 CSV' }).click();
    const file = await download; assert.match(file.suggestedFilename(), /\.csv$/);
    await file.saveAs(path.join(out, 'browser_download.csv'));
    assert.match(readFileSync(path.join(out, 'browser_download.csv'), 'utf8'), /simulation/);
  });
} finally {
  const meta = { generated_at: new Date().toISOString(), browser: await browser.version(), base, browser_plugin: 'absent', fallback_reason: 'Browser plugin not available',
    data_source: 'isolated browser route fixtures; booking uses project localStorage mock', hardware_tested: false,
    errors, warnings, screenshots, performance: timings, tests: records };
  writeFileSync(path.join(out, 'browser_tests.json'), JSON.stringify(meta, null, 2));
  writeFileSync(path.join(out, 'browser_performance.csv'), 'viewport,ready_ms,scope\n' + timings.map(x=>`${x.viewport},${x.ready_ms},${x.scope}`).join('\n'));
  await browser.close();
}
if (records.length !== 20 || records.some(x=>x.status!=='PASS')) process.exitCode = 1;
