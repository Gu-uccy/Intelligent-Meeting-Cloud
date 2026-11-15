from pathlib import Path
from urllib.request import urlopen
from datetime import datetime,timezone
import json,subprocess,time
out=Path('analysis/rpi-dynamic-2026-11-15')
remote_root='/home/guuccy/meeting-room-check-20261115'
def ssh(script):
    result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5','guuccy@192.168.43.206','python3 -'],input=script,text=True,encoding='utf-8',capture_output=True,timeout=15)
    if result.returncode:raise RuntimeError(result.stderr)
    return json.loads(result.stdout)
def get(path):
    start=time.perf_counter()
    with urlopen('http://192.168.43.206:5000'+path,timeout=3) as response:return {'status':response.status,'body':json.load(response),'lan_ms':(time.perf_counter()-start)*1000}
record={'generated_at':datetime.now(timezone.utc).isoformat(),'scope':'Stop only verified test sensor process; observe real LAN failure; restart with unchanged hardware flags; no browser validation','before':get('/api/health')}
stop_script="""from pathlib import Path
import os,signal,json,time
root=Path('/home/guuccy/meeting-room-check-20261115')
services=json.loads((root/'services.json').read_text())
service=next(s for s in services if s['name']=='sensors');pid=service['pid']
args=Path(f'/proc/{pid}/cmdline').read_bytes().split(bytes([0]))
assert b'/home/guuccy/meeting-room-check-20261115/sensor_server.py' in args
assert str(Path(f'/proc/{pid}/cwd').resolve())==str(root)
os.kill(pid,signal.SIGTERM)
print(json.dumps({'pid':pid,'verified_cmdline':[x.decode() for x in args if x],'signal':'SIGTERM'}))
"""
start_script="""from pathlib import Path
import os,subprocess,json
root=Path('/home/guuccy/meeting-room-check-20261115')
services=json.loads((root/'services.json').read_text());env=os.environ.copy()
for key in list(env):
    if key.startswith('MEETING_'):env.pop(key)
env.update(MEETING_DATA_MODE='hardware',MEETING_ENABLE_SERVOS='0',MEETING_ENABLE_ULTRASONIC='0',MEETING_DATA_DIR=str(root/'live-sensor-data'),MEETING_PORT='5000',PYTHONUNBUFFERED='1')
cmd=['/home/guuccy/meeting-room-venv/bin/python',str(root/'sensor_server.py')]
with (root/'sensors.out.log').open('a') as stdout,(root/'sensors.err.log').open('a') as stderr:
    process=subprocess.Popen(cmd,cwd=root,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
service={'name':'sensors','pid':process.pid,'command':cmd}
services=[service if s['name']=='sensors' else s for s in services]
(root/'services.json').write_text(json.dumps(services,indent=2))
print(json.dumps(service))
"""
stopped=False
try:
    record['stop']=ssh(stop_script);stopped=True
    for attempt in range(25):
        time.sleep(.2)
        try:get('/api/health')
        except Exception as exc:record['observed_offline']={'attempt':attempt+1,'error':str(exc)};break
    assert 'observed_offline' in record,'sensor port did not close'
finally:
    if stopped:record['restart']=ssh(start_script)
    (out/'recovery-probe.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
started=time.monotonic()
for attempt in range(40):
    try:
        health=get('/api/health')
        if health['body']['source']=='sensor' and health['body']['status']=='ok':
            record['after']=health;record['recovery_wait_seconds']=time.monotonic()-started;record['current']=get('/api/current');break
    except Exception:pass
    time.sleep(.5)
else:raise RuntimeError('Sensor failed to recover healthy climate within 20 seconds')
assert not record['after']['body']['hardware_config']['servos_enabled']
assert not record['after']['body']['hardware_config']['ultrasonic_enabled']
with urlopen('http://192.168.43.206:5001/health',timeout=3) as r:record['face_service_unchanged']=json.load(r)
assert record['face_service_unchanged']['threshold'] is None
record['status']='PASS'
(out/'recovery-probe.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2),flush=True)
