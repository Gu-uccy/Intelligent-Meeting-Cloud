import json,os,pathlib,subprocess,signal
root=pathlib.Path('/home/guuccy/meeting-room-check-20261115')
os.chdir(root)
runner=root/'sensor_server.py'
runner.write_text("""import signal
import sys
sys.path.insert(0,'Flask')
import unified_meeting_room_system as m
m.devices['auto_mode']=False
def stop(*args):raise SystemExit(0)
signal.signal(signal.SIGTERM,stop)
try:m.main()
finally:m.cleanup_resources()
""")
base=os.environ.copy()
for name in list(base):
    if name.startswith(('FACE_','MEETING_')):base.pop(name)
sensor_env=base|{'MEETING_DATA_MODE':'hardware','MEETING_ENABLE_SERVOS':'0','MEETING_ENABLE_ULTRASONIC':'0','MEETING_DATA_DIR':str(root/'live-sensor-data'),'MEETING_PORT':'5000','PYTHONUNBUFFERED':'1'}
face_env=base|{'FACE_HOST':'0.0.0.0','FACE_API_PORT':'5001','FACE_DATA_DIR':str(root/'empty-face-gallery'),'PYTHONUNBUFFERED':'1'}
records=[]
for name,command,env in [('sensors',['/home/guuccy/meeting-room-venv/bin/python',str(runner)],sensor_env),('face',['/home/guuccy/human_face/.venv/bin/python','MachineLearning/human_face/face_api.py'],face_env)]:
    with (root/(name+'.out.log')).open('w') as stdout,(root/(name+'.err.log')).open('w') as stderr:
        process=subprocess.Popen(command,cwd=root,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
    records.append({'name':name,'pid':process.pid,'command':command})
(root/'services.json').write_text(json.dumps(records,indent=2))
print(json.dumps(records,indent=2))
