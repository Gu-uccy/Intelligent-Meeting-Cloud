from pathlib import Path
from datetime import datetime,timezone
import os,json,sys,time
root=Path('/home/guuccy/meeting-room-check-20261115')
os.environ.update(MEETING_DATA_MODE='hardware',MEETING_ENABLE_SERVOS='0',MEETING_ENABLE_ULTRASONIC='1',MEETING_DATA_DIR=str(root/'distance-data'))
sys.path.insert(0,str(root/'Flask'))
import unified_meeting_room_system as m
records=[]
m.GPIO.setmode(m.GPIO.BCM);m.GPIO.setwarnings(False)
try:
    m.GPIO.setup(m.ULTRASONIC_ECHO,m.GPIO.IN)
    m.GPIO.setup(m.ULTRASONIC_TRIG,m.GPIO.OUT,initial=m.GPIO.LOW)
    time.sleep(.2)
    for index in range(10):
        m.current_distance=None
        begin=time.perf_counter();value=m.read_distance_sensor()
        record={'at':datetime.now(timezone.utc).isoformat(),'sample':index+1,'distance_cm':value,'elapsed_ms':(time.perf_counter()-begin)*1000,'fresh_for_this_attempt':value is not None}
        records.append(record);print(json.dumps(record),flush=True);time.sleep(.4)
finally:
    m.GPIO.output(m.ULTRASONIC_TRIG,m.GPIO.LOW)
    m.GPIO.cleanup([m.ULTRASONIC_TRIG,m.ULTRASONIC_ECHO])
    result={'scope':'Physical HC-SR04 GPIO20/21; last distance cleared on each attempt so timeouts stay null; no target movement or ruler comparison','echo_level_shift':'Human user confirmed divider or level shifter before test','records':records,'only_pins_20_21_released':True,'servos_exercised':False}
    (root/'results/distance-probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
