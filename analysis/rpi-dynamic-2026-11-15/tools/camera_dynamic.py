import json,os,sys,time,subprocess
from pathlib import Path
from datetime import datetime,timezone
root=Path('/home/guuccy/meeting-room-check-20261115')
for key in list(os.environ):
    if key.startswith('FACE_'):os.environ.pop(key)
sys.path.insert(0,str(root/'MachineLearning/human_face'))
from face_api import FacePipeline
import cv2,numpy as np
pipeline=FacePipeline();records=[];start=time.monotonic()
try:
    for index in range(14):
        began=time.monotonic();at=datetime.now(timezone.utc).isoformat()
        capture=subprocess.run(['rpicam-still','--nopreview','--timeout','1000','--width','640','--height','480','--output','-'],capture_output=True,timeout=15)
        record={'at':at,'elapsed_seconds':round(began-start,3),'capture_returncode':capture.returncode,'frame_bytes':len(capture.stdout)}
        if capture.returncode==0:
            image=cv2.imdecode(np.frombuffer(capture.stdout,np.uint8),cv2.IMREAD_COLOR)
            record['dimensions']=list(image.shape) if image is not None else None
            if image is not None:
                gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY);record['gray_mean']=round(float(gray.mean()),2);record['gray_std']=round(float(gray.std()),2)
                detected=pipeline.detector.detect_faces(image);record['faces']=len(detected)
                if len(detected)==1:
                    try:record['feature_dimensions']=len(pipeline(capture.stdout));record['extraction']='success'
                    except ValueError as exc:record['extraction']='rejected';record['error']=str(exc)
        else:record['error']=capture.stderr.decode(errors='replace')[-600:]
        records.append(record);print(json.dumps(record),flush=True)
        # Original frame discarded each iteration; only aggregate metadata persisted.
        if index<13:time.sleep(max(0,8-(time.monotonic()-began)))
finally:
    output={'scope':'Physical CSI frames in RAM; face detection/feature extraction only; no identity matching, images or feature vectors stored; no GPIO','feature_profile':pipeline.profile,'records':records}
    (root/'results/camera-dynamic.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
