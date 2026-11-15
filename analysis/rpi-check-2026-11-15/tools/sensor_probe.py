import csv,importlib.util,io,json,os,pathlib,subprocess,sys,time
from datetime import datetime,timezone
root=pathlib.Path('/home/guuccy/meeting-room-check-20261115')
os.environ.update(MEETING_DATA_MODE='hardware',MEETING_ENABLE_SERVOS='0',MEETING_ENABLE_ULTRASONIC='0',MEETING_DATA_DIR=str(root/'sensor-data'))
spec=importlib.util.spec_from_file_location('sensor_probe',root/'Flask/unified_meeting_room_system.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
records=[];start=time.perf_counter();result={'generated_at':datetime.now(timezone.utc).isoformat(),'hardware_mode':m.ON_RASPBERRY_PI,'servos_exercised':False,'ultrasonic_exercised':False,'physical_observation_confirmed':False}
try:
    m.setup_gpio();m.devices['auto_mode']=False
    client=m.app.test_client()
    for index in range(10):
        temperature,humidity=m.read_dht_sensor();motion=m.read_pir_sensor();light=m.read_light_sensor();smoke=m.read_smoke_sensor()
        m.append_history(temperature,humidity,None,motion,light,smoke)
        row={'attempt':index+1,'elapsed_seconds':round(time.perf_counter()-start,3),'temperature':temperature,'humidity':humidity,'dht_sample_age_seconds':round(time.time()-m.last_dht_success,3) if m.last_dht_success else None,'motion':motion,'light':light,'smoke_do_alarm':smoke>m.SMOKE_THRESHOLD}
        records.append(row);print('SAMPLE',json.dumps(row),flush=True)
        if index<9:time.sleep(3)
    result['samples']=records
    result['health']=client.get('/api/health').json
    result['current']=client.get('/api/current').json
    # Exercise the actual API function with real GPIO/PWM; no background auto writer.
    transitions=[]
    for enabled,brightness in [(True,30),(False,0),(True,60),(False,0)]:
        response=client.post('/api/control',json={'action':'manual','device':'lighting','state':enabled,'brightness':brightness,'source':'hardware-check'})
        assert response.status_code==200,response.json
        pin_reads={name:int(m.GPIO.input(pin)) for name,pin in m.RGB_LED_PINS.items()}
        transitions.append({'enabled':enabled,'brightness':brightness,'http_status':response.status_code,'response':response.json,'pin_sample':pin_reads,'measurement':'pin_sample is instantaneous software readback, not optical observation'})
        time.sleep(2)
    result['lighting_transitions']=transitions
    blocked=client.post('/api/control',json={'action':'manual','device':'door','state':True})
    assert blocked.status_code==503 and not m.devices['door_open']
    result['disabled_door_check']={'status':blocked.status_code,'response':blocked.json}
    export=client.get('/api/export/csv');assert export.status_code==200
    (root/'results/sensor-export.csv').write_bytes(export.data)
    result['history_rows']=len(m.history_data)
    result['csv_export_status']=export.status_code
    result['pi_throttled']=subprocess.check_output(['vcgencmd','get_throttled'],text=True).strip()
finally:
    m.cleanup_resources()
    result['resources_cleaned_up']=True
    result['duration_seconds']=round(time.perf_counter()-start,3)
    (root/'results/sensor-probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('RESULT',json.dumps(result,indent=2),flush=True)
