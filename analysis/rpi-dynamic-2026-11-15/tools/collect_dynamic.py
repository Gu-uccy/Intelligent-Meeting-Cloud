import json,time,concurrent.futures
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen
out=Path('analysis/rpi-dynamic-2026-11-15');out.mkdir(parents=True,exist_ok=True)
records=[];start=time.monotonic()
try:
    for index in range(125):
        began=time.perf_counter()
        try:
            with urlopen('http://192.168.43.206:5000/api/current',timeout=3) as response:body=json.load(response)
            records.append({'at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-start,3),'http_status':200,'lan_ms':round((time.perf_counter()-began)*1000,3),'body':body})
        except Exception as exc:records.append({'at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-start,3),'error':str(exc)})
        if index%15==0:
            print(json.dumps({'sample':index+1,'elapsed_seconds':round(time.monotonic()-start,1),'motion':records[-1].get('body',{}).get('motion'),'light':records[-1].get('body',{}).get('light')},ensure_ascii=False),flush=True)
        time.sleep(max(0,1-(time.perf_counter()-began)))
finally:
    (out/'dynamic-samples.json').write_text(json.dumps({'scope':'LAN polling physical sensor service during user-requested PIR/light stimuli; not simulated','records':records},indent=2,ensure_ascii=False),encoding='utf-8')
    good=[r['body'] for r in records if 'body' in r]
    print(json.dumps({'samples':len(records),'good':len(good),'motion_values':sorted(set(r['motion'] for r in good)),'light_range':[min(r['light'] for r in good),max(r['light'] for r in good)]},ensure_ascii=False),flush=True)
