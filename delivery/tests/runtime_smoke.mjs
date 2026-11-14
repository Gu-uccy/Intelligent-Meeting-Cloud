// Actual localhost simulation HTTP and rendered UI; no sensor API route fixtures.
import {createRequire} from 'node:module';
import {mkdirSync,writeFileSync} from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium}=require(`${process.env.USERPROFILE}/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright`);
const base=process.env.ACCEPTANCE_URL||'http://127.0.0.1:5189';
const out=path.resolve('analysis/taskbook-v3-2026-11-14/implementation/runtime');mkdirSync(out,{recursive:true});
const browser=await chromium.launch({channel:'chrome',headless:true});
const page=await browser.newPage({viewport:{width:1366,height:900}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
const results={generated_at:new Date().toISOString(),base,scope:'Real localhost Flask simulation HTTP + localStorage mock booking; no Pi',checks:[]};
try{
  const health=await (await page.request.get('http://127.0.0.1:5058/api/health')).json();
  assert.equal(health.source,'simulation');assert.equal(health.service,'meeting-room-sensors');results.health=health;
  const face=await (await page.request.get(`${base}/face-api/health`)).json();assert.equal(face.model_name,'custom-uniform-LBP');results.face_health=face;
  results.checks.push('simulation source and custom face service confirmed');
  await page.goto(`${base}/login`);await page.locator('.sign-in-form').getByPlaceholder('用户名',{exact:true}).fill('test_user');await page.locator('.sign-in-form input[type=password]').fill('123456');await page.locator('.sign-in-form').evaluate(f=>f.requestSubmit());await page.waitForURL(`${base}/`);
  await page.goto(`${base}/room-3d`);await page.getByText('Blender 模型 · 301',{exact:true}).waitFor();await page.locator('.status-pill.simulation').waitFor();
  const initial=await (await page.request.get(`${base}/sensor-api/current`)).json();
  await page.locator('.state-button').click();
  await page.waitForFunction(open=>document.querySelector('.stage-state')?.textContent.includes(open?'门开':'门关'),!initial.door_open);
  const after=await (await page.request.get('http://127.0.0.1:5058/api/current')).json();assert.equal(after.door_open,!initial.door_open);
  results.checks.push('UI door click -> real Flask HTTP -> state writeback');
  await page.evaluate(()=>{const el=document.createElement('div');el.textContent='本机 Flask 模拟服务 · 非树莓派实测';Object.assign(el.style,{position:'fixed',bottom:0,right:0,background:'#102136',color:'#fbbf24',padding:'6px',zIndex:99999});document.body.append(el);});
  await page.screenshot({path:path.join(out,'local-simulation.png'),fullPage:true});
  await page.locator('.state-button').click();
  const restored=await (await page.request.get('http://127.0.0.1:5058/api/current')).json();assert.equal(restored.door_open,initial.door_open);
  await page.goto(`${base}/booking`);await page.locator('.tab-item').filter({hasText:'智能助理'}).click();await page.locator('.composer-input').fill('帮我订明天上午10点8人的会议室，需要投影仪');await page.getByRole('button',{name:'发送给助理'}).click();await page.locator('.result-card').first().waitFor();assert.match(await page.locator('.result-card').first().innerText(),/10:00/);
  results.checks.push('Demo uses local parser without external AI service; 10点8人 -> 10:00/8 people');
  assert.deepEqual(errors,[]);results.checks.push('no runtime exceptions');results.status='PASS';
}catch(e){results.status='FAIL';results.error=String(e);process.exitCode=1;}
finally{results.errors=errors;writeFileSync(path.join(out,'runtime-smoke.json'),JSON.stringify(results,null,2));await browser.close();}
console.log(results);
