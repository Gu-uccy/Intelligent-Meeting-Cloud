// Browser plugin not available: Playwright + installed Chrome. All sensor/face APIs are fixtures.
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
const { chromium } = require(`${process.env.USERPROFILE}/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright`);
const out=path.resolve(process.env.EVIDENCE_OUTPUT_DIR || 'analysis/taskbook-v3-2026-11-14/implementation/browser');
mkdirSync(out,{recursive:true});
const base=process.env.ACCEPTANCE_URL || 'http://127.0.0.1:5188';
const browser=await chromium.launch({channel:'chrome',headless:true,args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
const context=await browser.newContext({viewport:{width:1366,height:900},permissions:['camera']});
const page=await context.newPage();
const records=[],errors=[],warnings=[],polls=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('console',m=>{if(m.type()==='warning')warnings.push(m.text());});
let offline=false,denyFace=false,failModel=false,deviceFailure=false;
const state={source:'simulation',quality:'normal',temperature:24,humidity:50,light:70,smoke:20,motion:true,presence:true,people_count:3,
  temp_min:20,temp_max:26,humidity_min:40,humidity_max:60,smoke_threshold:100,door_open:false,
  devices:{door_open:false,lighting:true,lighting_brightness:70,door_source:'simulation'}};
const commands=[];
await page.route('**/models/room_301.glb',route=>failModel?route.fulfill({status:404,body:'fixture missing model'}):route.continue());
await page.route('**/sensor-api/**',async route=>{
  if(route.request().url().endsWith('/current'))polls.push(Date.now());
  if(offline)return route.fulfill({status:503,json:{error:'fixture offline'}});
  if(route.request().url().endsWith('/control')){
    const command=route.request().postDataJSON();commands.push(command);
    if(deviceFailure)return route.fulfill({status:503,json:{error:'fixture actuator failure'}});
    if(command.device==='door')state.devices.door_open=state.door_open=command.state;
    if(command.device==='lighting'){state.devices.lighting=command.state;state.devices.lighting_brightness=command.brightness;}
    return route.fulfill({json:{success:true,source:'simulation',devices:state.devices}});
  }
  return route.fulfill({json:state});
});
await page.route('**/face-api/**',route=>{
  if(route.request().url().endsWith('/health'))return route.fulfill({json:{model_name:'custom-uniform-LBP',mode:'simulation-only',threshold:.99}});
  return route.fulfill({json:{matched:true,identity:'A01',similarity:.999,threshold:.99,
    access:{allowed:!denyFace,reason:denyFace?'不在当前预约名单中':'模拟开门指令已确认',device:denyFace?null:{acknowledged:true,source:'simulation'}}}});
});
const check=async(name,fn)=>{try{await fn();records.push({name,status:'PASS'});}catch(e){records.push({name,status:'FAIL',detail:String(e)});console.log(e);}console.log(records.at(-1).status,name);};
const shot=async(file)=>{
  await page.evaluate(()=>{let el=document.getElementById('test-badge');if(!el){el=document.createElement('div');el.id='test-badge';document.body.append(el);}
    el.textContent='自动验收 · 合成 API 夹具 · 非现场硬件/人脸实测';Object.assign(el.style,{position:'fixed',bottom:'0',right:'0',background:'#102136',color:'#fbbf24',padding:'6px',zIndex:99999});});
  await page.screenshot({path:path.join(out,file),fullPage:true});
};
try{
  await page.goto(`${base}/login`);
  await page.locator('.sign-in-form').getByPlaceholder('用户名',{exact:true}).fill('test_user');
  await page.locator('.sign-in-form input[type=password]').fill('123456');
  await page.locator('.sign-in-form').evaluate(f=>f.requestSubmit());await page.waitForURL(`${base}/`);
  await page.goto(`${base}/room-3d`);
  await check('页面身份/主体/无框架覆盖层',async()=>{assert.equal(new URL(page.url()).pathname,'/room-3d');assert.match(await page.title(),/智会云/);await page.getByRole('heading',{name:'3D智能会议室模型展厅'}).waitFor();assert.equal(await page.locator('vite-error-overlay').count(),0);});
  await check('真实导出 Blender GLB 已加载',async()=>{await page.getByText('Blender 模型 · 301',{exact:true}).waitFor();await page.locator('.viewport canvas').waitFor();await page.waitForTimeout(500);await shot('01_blender_closed.png');});
  await check('直接点击3D门扇发送指令并回写',async()=>{
    const point=await page.evaluate(async()=>{
      const THREE=await import('/node_modules/.vite/deps/three.js');
      const canvas=document.querySelector('.viewport canvas'),rect=canvas.getBoundingClientRect();
      const camera=new THREE.PerspectiveCamera(42,rect.width/rect.height,.1,120);
      const target=new THREE.Vector3(0,.82,-.35),offset=new THREE.Vector3(13.8,9.2,14.5).sub(target);
      camera.position.copy(target).add(offset);camera.lookAt(target);camera.updateMatrixWorld();
      const p=new THREE.Vector3(6,1.05,2.175).project(camera);
      return {x:rect.left+(p.x+1)*rect.width/2,y:rect.top+(1-p.y)*rect.height/2};
    });
    const before=commands.length;await page.mouse.click(point.x,point.y);
    await page.locator('.stage-state').getByText('门开',{exact:true}).waitFor();
    assert.equal(commands.length,before+1);assert.equal(commands.at(-1).device,'door');
    await page.locator('.state-button').click();await page.locator('.stage-state').getByText('门关',{exact:true}).waitFor();
  });
  await check('统一状态对象人员/门/环境更新',async()=>{assert.match(await page.locator('.stage-state').innerText(),/3人/);state.people_count=5;state.temperature=29.7;await page.getByText('29.7℃',{exact:true}).first().waitFor({timeout:10000});assert.match(await page.locator('.stage-state').innerText(),/5人/);});
  await check('PIR只有存在信号时不伪造精确人数',async()=>{state.people_count=null;await page.getByText('有人（PIR）',{exact:true}).waitFor({timeout:10000});assert.match(await page.locator('.stage-state').innerText(),/有人/);state.people_count=5;});
  await check('门控制回写并显示开门',async()=>{await page.locator('.state-button').click();await page.locator('.stage-state').getByText('门开',{exact:true}).waitFor();assert.equal(commands.at(-1).device,'door');assert.equal(commands.at(-1).state,true);await shot('02_blender_open.png');});
  await check('灯控制回写',async()=>{await page.locator('.lighting-toggle').click();await page.locator('.stage-state').getByText('灯关',{exact:true}).waitFor();assert.equal(commands.at(-1).device,'lighting');});
  await check('设备控制失败保留原状态',async()=>{deviceFailure=true;await page.locator('.state-button').click();await page.locator('.control-error').waitFor();assert.match(await page.locator('.stage-state').innerText(),/门开/);deviceFailure=false;});
  await check('沿用服务端烟雾阈值及报警状态',async()=>{state.smoke=90;await page.waitForTimeout(3300);assert.equal(await page.getByRole('alert').filter({hasText:'烟雾越界'}).count(),0);state.smoke=101;await page.getByRole('alert').filter({hasText:'烟雾越界'}).waitFor({timeout:10000});state.smoke=20;});
  await check('断线禁用控制/退避/手动恢复',async()=>{offline=true;await page.locator('.status-pill.disconnected').waitFor({timeout:10000});assert.equal(await page.locator('.state-button').isDisabled(),true);await page.waitForTimeout(6500);assert.ok(polls.at(-1)-polls.at(-2)>=5700);assert.match(await page.locator('.sensor-warning').innerText(),/12 秒后重试/);offline=false;await page.getByRole('button',{name:'立即重连'}).click();await page.locator('.status-pill.simulation').waitFor();assert.equal(await page.locator('.state-button').isDisabled(),false);});
  await check('移动端无横向溢出且画布不被卡片覆盖',async()=>{await page.setViewportSize({width:390,height:844});await page.waitForTimeout(400);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));const canvas=await page.locator('.viewport').boundingBox(),dock=await page.locator('.sensor-dock').boundingBox();assert.ok(dock.y>=canvas.y+canvas.height);await shot('03_blender_mobile.png');await page.setViewportSize({width:1366,height:900});});
  await check('GLB 丢失时明确降级且备用模型可控制',async()=>{failModel=true;await page.reload();await page.getByText('模型加载失败，已使用程序备用模型',{exact:true}).waitFor();await page.locator('.status-pill.simulation').waitFor();await page.locator('.state-button').click();assert.equal(commands.at(-1).device,'door');failModel=false;});
  await page.goto(`${base}/face-access`);
  await check('刷脸页面需授权及管理员令牌才能录入',async()=>{await page.getByRole('button',{name:'录入当前用户'}).waitFor();assert.equal(await page.getByRole('button',{name:'录入当前用户'}).isDisabled(),true);await page.getByRole('button',{name:'打开摄像头'}).click();await page.waitForFunction(()=>document.querySelector('video')?.videoWidth>0);});
  await check('服务端拒绝预约时不得因 matched 绕过',async()=>{denyFace=true;await page.getByRole('button',{name:'刷脸核验'}).click();await page.getByText('拒绝进入',{exact:true}).waitFor();assert.equal(await page.getByText('模拟指令已确认',{exact:true}).count(),0);});
  await check('只有服务端设备确认后显示模拟放行',async()=>{denyFace=false;await page.getByRole('button',{name:'刷脸核验'}).click();await page.getByText('允许进入',{exact:true}).waitFor();await page.getByText('模拟指令已确认',{exact:true}).waitFor();await shot('04_face_simulation.png');});
  await page.goto(`${base}/booking`);
  await check('预约助理输入约束到推荐到确认提交',async()=>{
    await page.locator('.tab-item').filter({hasText:'智能助理'}).click();
    await page.locator('.composer-input').fill('帮我订明天上午10点8人的会议室，需要投影仪');
    await page.getByRole('button',{name:'发送给助理'}).click();
    await page.locator('.result-card').first().waitFor();
    assert.match(await page.locator('.result-card').first().innerText(),/投影仪/);
    await page.locator('.result-card').first().getByRole('button',{name:'提交预约申请'}).click();
    await page.getByText(/需要等待管理员审核通过后才算预约成功/).waitFor();
    await shot('05_booking_assistant.png');
  });
  await check('无运行时异常',async()=>{assert.deepEqual(errors,[]);});
}finally{
  writeFileSync(path.join(out,'results.json'),JSON.stringify({generated_at:new Date().toISOString(),base,browser:await browser.version(),browser_plugin:'absent',fallback_reason:'Browser plugin not available',scope:'API fixtures + localStorage business mock; actual Blender GLB; no physical devices or real faces',records,errors,warnings,polls},null,2));
  await browser.close();
}
console.log(JSON.stringify(records,null,2));
if(records.some(x=>x.status==='FAIL'))process.exitCode=1;
