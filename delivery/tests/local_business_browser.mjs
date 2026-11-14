// Browser plugin not available: use installed Playwright + Chrome.
// Real Spring/MySQL business requests; real localhost Flask simulation; no API fixtures.
import {createRequire} from 'node:module';
import {mkdirSync, writeFileSync} from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
const {chromium} = require(`${process.env.USERPROFILE}/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright`);
const base = process.env.ACCEPTANCE_URL || 'http://127.0.0.1:5190';
const out = path.resolve(process.env.EVIDENCE_OUTPUT_DIR || '.codex-run-logs/local-business-browser');
const shots = process.env.EVIDENCE_SCREENSHOT_DIR || path.join(os.tmpdir(),'meeting-business-20261114');
mkdirSync(out,{recursive:true}); mkdirSync(shots,{recursive:true});
const browser = await chromium.launch({channel:'chrome',headless:true});
const context = await browser.newContext({viewport:{width:1366,height:900}});
const page = await context.newPage();
const errors=[],consoleErrors=[],records=[],failedResponses=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('console',m=>{if(m.type()==='error') consoleErrors.push(m.text());});
page.on('response',r=>{if(r.status()>=400) failedResponses.push({url:r.url(),status:r.status()});});
const mark = async (name, fn) => { await fn(); records.push({name,status:'PASS'}); };
const result={generated_at:new Date().toISOString(),base,scope:'Real Spring/MySQL UI + real localhost Flask simulation; no Pi or authorized face data',browser_path:'Browser plugin not available; existing Playwright + Chrome',checks:records,screenshot_directory:shots};
const screenshot = async file => {
  await page.evaluate(()=>{
    let el=document.getElementById('source-proof');
    if(!el){el=document.createElement('div');el.id='source-proof';document.body.append(el);}
    el.textContent='本机验收 · 业务 Spring/MySQL · 传感器模拟 · 非树莓派实测';
    Object.assign(el.style,{position:'fixed',bottom:'0',right:'0',background:'#102136',color:'#fbbf24',padding:'6px',fontSize:'12px',zIndex:99999});
  });
  await page.screenshot({path:path.join(shots,file),fullPage:false});
};
try {
  await page.goto(`${base}/login`);
  await page.locator('.sign-in-form').getByPlaceholder('用户名',{exact:true}).fill('test_user');
  await page.locator('.sign-in-form input[type=password]').fill('123456');
  const loginPromise=page.waitForResponse(r=>r.url()===`${base}/api/login`);
  await page.locator('.sign-in-form').evaluate(f=>f.requestSubmit());
  const login=await (await loginPromise).json();
  await page.waitForURL(`${base}/`);
  await mark('real JWT login through Vite proxy',async()=>assert.equal(login.code,1));
  const token=login.data.token;
  await page.goto(`${base}/booking`);
  await page.locator('.room-card').first().waitFor();
  await mark('page identity, nonblank, no framework overlay',async()=>{
    assert.equal(new URL(page.url()).pathname,'/booking');assert.match(await page.title(),/智会云/);
    assert.equal(await page.locator('vite-error-overlay').count(),0);assert.equal(await page.locator('.room-card').count(),3);
  });
  await page.locator('.room-card').first().locator('.btn-book').click();
  await page.getByRole('heading',{name:'预约时间段'}).waitFor();
  const d=new Date();d.setDate(d.getDate()+3);const day=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  await page.locator('.date-picker').fill(day);
  await page.locator('.date-picker').dispatchEvent('change');
  const target=page.locator('.time-slot').filter({hasText:'10:00 - 10:30'});
  await target.filter({hasText:'空闲'}).waitFor();await target.click();
  const title=`UI-LOCAL-${Date.now()}`;
  await page.getByPlaceholder('请输入会议主题').fill(title);
  const createPromise=page.waitForResponse(r=>r.url()===`${base}/api/user/reservation` && r.request().method()==='POST');
  await page.getByRole('button',{name:'提交预约申请',exact:true}).click();
  const added=await (await createPromise).json();
  await page.locator('.modal-overlay').waitFor({state:'hidden'});
  await mark('UI booking commits and pending slot refreshes',async()=>{
    assert.equal(added.code,1);await target.filter({hasText:'已订'}).waitFor();
  });
  const mine=await (await page.request.get(`${base}/api/user/reservation/my`,{headers:{token}})).json();
  assert(mine.data.some(r=>r.meetingTopic===title&&r.status===0));
  await page.locator('.tab-item').filter({hasText:'我的预约'}).click();
  let row=page.locator('tbody tr').filter({hasText:title});
  await row.getByText('审核中',{exact:true}).waitFor();
  await screenshot('01-booking-persisted.png');
  page.once('dialog',d=>d.accept());
  const cancelPromise=page.waitForResponse(r=>r.url().includes('/api/user/reservation/cancel/') && r.request().method()==='PUT');
  await row.getByTitle('取消',{exact:true}).click();assert.equal((await (await cancelPromise).json()).code,1);
  await mark('UI cancellation shows persisted status 2 as cancelled',async()=>{await row.getByText('已取消',{exact:true}).waitFor();assert.equal(await row.getByTitle('取消',{exact:true}).count(),0);});
  await screenshot('02-booking-cancelled.png');
  await page.reload();
  await page.locator('.tab-item').filter({hasText:'我的预约'}).click();
  row=page.locator('tbody tr').filter({hasText:title});
  await mark('cancelled state survives reload',async()=>await row.getByText('已取消',{exact:true}).waitFor());
  await page.setViewportSize({width:390,height:844});
  await screenshot('03-mobile-record.png');
  await mark('mobile table scroll exposes status and actions',async()=>{
    const scroll = page.locator('.records-scroll');
    const dimensions=await scroll.evaluate(el=>({client:el.clientWidth,total:el.scrollWidth}));
    assert(dimensions.total>dimensions.client);
    await scroll.evaluate(el=>{el.scrollLeft=el.scrollWidth;});
    const badge=await row.getByText('已取消',{exact:true}).boundingBox();
    assert(badge.x>=0 && badge.x+badge.width<=390);
  });
  await screenshot('03b-mobile-status.png');
  await page.setViewportSize({width:1366,height:900});
  await page.goto(`${base}/room-3d`);
  await page.getByText('Blender 模型 · 301',{exact:true}).waitFor();await page.locator('.status-pill.simulation').waitFor();
  const before=await (await page.request.get(`${base}/sensor-api/current`)).json();
  await page.locator('.state-button').click();
  await page.waitForFunction(open=>document.querySelector('.stage-state')?.textContent.includes(open?'门开':'门关'),!before.door_open);
  const after=await (await page.request.get(`${base}/sensor-api/current`)).json();
  await mark('3D uses explicit simulation and acknowledged Flask door state',async()=>assert.equal(after.door_open,!before.door_open));
  await screenshot('04-local-3d.png');
  await page.locator('.state-button').click();
  await mark('runtime and console health',async()=>{assert.deepEqual(errors,[]);assert.deepEqual(consoleErrors,[]);});
  result.status='PASS';
} catch(error) {
  result.status='FAIL';result.error=String(error);await page.screenshot({path:path.join(shots,'failure.png'),fullPage:false});process.exitCode=1;
} finally {
  result.page_errors=errors;result.console_errors=consoleErrors;result.passed=records.length;
  result.failed_responses=failedResponses;
  writeFileSync(path.join(out,'business-browser.json'),JSON.stringify(result,null,2));
  await browser.close();console.log(JSON.stringify(result,null,2));
}
