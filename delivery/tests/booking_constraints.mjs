import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { findAvailableRoomsForDraft as find, findCancelableReservations as cancel } from '../../FrontEnd/Intelligent_meeting_cloud/src/utils/bookingAgentMatcher.js';
import { parseBookingAssistantMessage as parse } from '../../FrontEnd/Intelligent_meeting_cloud/src/utils/bookingAgentParser.js';
const draft={date:'2026-12-01',startTime:'10:00',endTime:'11:00',attendeeCount:8,equipment:['投影仪']};
const rooms=[
  {id:1,roomCode:'A101',isActive:1,capacity:10,equipment:'投影仪,白板'},
  {id:2,roomCode:'A102',isActive:1,capacity:20,equipment:'投影仪'},
  {id:3,roomCode:'A103',isActive:0,capacity:10,equipment:'投影仪'},
  {id:4,roomCode:'A104',isActive:1,capacity:5,equipment:'投影仪'},
  {id:5,roomCode:'A105',isActive:1,capacity:10,equipment:'白板'},
];
const tools={getUserRoomPage:async()=>({code:1,data:{records:rooms}}),
  getTimeSlots:async()=>({code:1,data:[{startTime:'09:00:00',endTime:'10:00:00',status:1},{startTime:'10:00:00',endTime:'11:00:00',status:0}]})};
const records=[];
async function check(name,fn){try{await fn();records.push({name,status:'PASS'});}catch(e){records.push({name,status:'FAIL',detail:String(e)});}}
await check('启用/容量/设备/容量差排序',async()=>assert.deepEqual((await find(draft,tools)).map(x=>x.id),[1,2]));
await check('指定会议室编号',async()=>assert.deepEqual((await find({...draft,roomCode:'A102'},tools)).map(x=>x.id),[2]));
await check('已占用含字符串状态排除',async()=>assert.deepEqual(await find(draft,{...tools,getTimeSlots:async()=>({code:1,data:[{startTime:'10:00:00',endTime:'11:00:00',status:'1'}]})}),[]));
await check('过期时间排除',async()=>assert.deepEqual(await find(draft,{...tools,getTimeSlots:async()=>({code:1,data:[{startTime:'10:00:00',endTime:'11:00:00',status:2}]})}),[]));
await check('相邻预约边界不算冲突',async()=>assert.equal((await find(draft,tools)).length,2));
await check('时间片缺口不得推荐',async()=>assert.deepEqual(await find(draft,{...tools,getTimeSlots:async()=>({code:1,data:[{startTime:'10:30:00',endTime:'11:00:00',status:0}]})}),[]));
await check('服务业务失败不得假装空闲',async()=>assert.rejects(find(draft,{...tools,getTimeSlots:async()=>({code:0,msg:'error'})})));
await check('网络异常向上传递',async()=>assert.rejects(find(draft,{...tools,getUserRoomPage:async()=>{throw Error('offline')}})));
await check('非法人数和倒序时间拒绝',async()=>{await assert.rejects(find({...draft,attendeeCount:0},tools));await assert.rejects(find({...draft,endTime:'09:00'},tools));});
await check('取消无匹配时不得退回其他预约',async()=>assert.deepEqual(cancel({roomCode:'A999'},[{id:1,status:'pending',room:'A101'}]),[]));
await check('10点8人应解析为10:00及8人',async()=>{const d=parse('帮我订明天上午10点8人的会议室，需要投影仪').extracted;assert.equal(d.startTime,'10:00');assert.equal(d.attendeeCount,8);});
await check('整点范围及半点解析',async()=>{let d=parse('明天下午3点到4点8人').extracted;assert.equal(d.startTime,'15:00');assert.equal(d.endTime,'16:00');d=parse('明天上午10点半8人').extracted;assert.equal(d.startTime,'10:30');});
const out=path.resolve(process.env.EVIDENCE_OUTPUT_DIR||'analysis/taskbook-v3-2026-11-14/implementation');mkdirSync(out,{recursive:true});
writeFileSync(path.join(out,'booking-constraints.json'),JSON.stringify({scope:'pure matcher with synthetic API fixtures',generated_at:new Date().toISOString(),records},null,2));
console.log(records);if(records.some(x=>x.status==='FAIL'))process.exitCode=1;
