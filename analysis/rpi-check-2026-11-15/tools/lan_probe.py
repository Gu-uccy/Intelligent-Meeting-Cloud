import csv,io,json,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
host='http://192.168.43.206:5000';out=Path('analysis/rpi-check-2026-11-15')
def request(url,data=None,content_type='application/json'):
    if isinstance(data,dict):data=json.dumps(data).encode()
    started=time.perf_counter()
    try:
        with urlopen(Request(url,data=data,headers={'Content-Type':content_type}),timeout=8) as response:
            raw=response.read();return response.status,raw,(time.perf_counter()-started)*1000
    except HTTPError as exc:return exc.code,exc.read(),(time.perf_counter()-started)*1000
result={'generated_at':datetime.now(timezone.utc).isoformat(),'scope':'Windows LAN HTTP to physical Pi; GPIO outputs exercised; visual response requires user confirmation'}
for name,url in [('sensor_health',host+'/api/health'),('face_health','http://192.168.43.206:5001/health')]:
    code,body,ms=request(url);result[name]={'status':code,'body':json.loads(body),'lan_ms':ms};assert code==200
assert result['sensor_health']['body']['source']=='sensor'
assert result['face_health']['body']['threshold'] is None
samples=[];led=[]
try:
    for state in [True,False,True,False]:
        code,body,ms=request(host+'/api/control',{'action':'manual','device':'lighting','state':state,'brightness':100 if state else 0,'source':'lan-check'})
        body=json.loads(body);assert code==200 and body['success'];assert body['devices']['lighting']==state
        led.append({'state':state,'response':body,'status':code,'lan_ms':ms});print('LED',state,flush=True)
        for _ in range(2):
            time.sleep(2)
            code,body,ms=request(host+'/api/current');body=json.loads(body);assert code==200 and body['source']=='sensor'
            samples.append({'body':body,'lan_ms':ms})
    for _ in range(4):
        time.sleep(3);code,body,ms=request(host+'/api/current');samples.append({'body':json.loads(body),'lan_ms':ms})
finally:
    request(host+'/api/control',{'action':'manual','device':'lighting','state':False,'brightness':0,'source':'lan-check'})
result['led_transitions']=led;result['samples']=samples
code,body,ms=request(host+'/api/export/csv');assert code==200
(out/'sensor-export-lan.csv').write_bytes(body);rows=list(csv.DictReader(io.StringIO(body.decode('utf-8-sig'))))
result['export']={'status':code,'rows':len(rows),'lan_ms':ms,'all_sensor_source':all(r.get('数据来源')=='sensor' for r in rows)}
assert result['export']['all_sensor_source']
code,body,ms=request(host+'/api/control',{'action':'manual','device':'door','state':True});assert code==503 and not json.loads(body)['success']
result['door_disabled']={'status':code,'body':json.loads(body)}
code,body,ms=request('http://192.168.43.206:5001/api/face/verify',b'');assert code==422 and not json.loads(body)['access']['allowed']
result['face_missing_image']={'status':code,'body':json.loads(body)}
code,body,ms=request('http://192.168.43.206:5001/api/face/enroll',b'');assert code==403
result['face_admin_rejection']={'status':code,'body':json.loads(body)}
(out/'lan-probe.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'samples':len(samples),'temperature':[s['body']['temperature'] for s in samples],'humidity':[s['body']['humidity'] for s in samples],'motion':[s['body']['motion'] for s in samples],'light':[s['body']['light'] for s in samples],'csv_rows':len(rows),'health':result['sensor_health']},indent=2,ensure_ascii=False),flush=True)
