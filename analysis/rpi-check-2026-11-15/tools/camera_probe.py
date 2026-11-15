from pathlib import Path
from datetime import datetime,timezone
import json,os,subprocess,sys,time
root=Path('/home/guuccy/meeting-room-check-20261115')
for key in list(os.environ):
    if key.startswith('FACE_'):os.environ.pop(key)
sys.path.insert(0,str(root/'MachineLearning/human_face'))
from face_api import FacePipeline
import cv2,numpy as np
started=time.perf_counter()
command=['rpicam-still','--nopreview','--timeout','1500','--width','640','--height','480','--output','-']
capture=subprocess.run(command,capture_output=True,timeout=20)
result={'generated_at':datetime.now(timezone.utc).isoformat(),'scope':'One CSI camera frame in RAM; decode/detection/feature extraction only; no identity matching, image persistence or actuator action','capture_returncode':capture.returncode,'capture_ms':(time.perf_counter()-started)*1000,'frame_bytes':len(capture.stdout)}
if capture.returncode==0:
    image=cv2.imdecode(np.frombuffer(capture.stdout,np.uint8),cv2.IMREAD_COLOR)
    result['decoded_dimensions']=list(image.shape) if image is not None else None
    pipeline=FacePipeline();begin=time.perf_counter()
    try:
        feature=pipeline(capture.stdout)
        result.update(extraction='success',feature_dimensions=len(feature))
    except ValueError as exc:result.update(extraction='rejected',reason=str(exc))
    result.update(pipeline_ms=(time.perf_counter()-begin)*1000,feature_profile=pipeline.profile)
else:result['error']=capture.stderr.decode(errors='replace')[-1200:]
(root/'results/camera-probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
