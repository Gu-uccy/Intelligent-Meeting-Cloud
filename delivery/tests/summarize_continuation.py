"""Summarize only newly executed evidence; never rewrites delivery/results."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'analysis/taskbook-v3-2026-11-14/implementation'
groups={
    'sensor': ('backend/backend_tests.json',None,35),
    'face': ('face-tests.json','records',25),
    'booking': ('booking-constraints.json','records',12),
    'browser_new': ('browser/results.json','records',17),
    'browser_regression': ('legacy-browser/browser_tests.json','tests',20),
}
summary={'generated_at':datetime.now(timezone.utc).isoformat(),'hardware_tested':False,
         'real_faces_tested':False,'video_created':False,'groups':{},
         'scope':'Overlapping regression groups; synthetic face data, API fixtures, mock booking, plus separate real localhost Flask simulation checks'}
for name,(file,key,count) in groups.items():
    data=json.loads((OUT/file).read_text(encoding='utf-8'))
    rows=data[key] if key else data
    assert len(rows)==count,(name,len(rows))
    assert all(r['status']=='PASS' for r in rows),name
    summary['groups'][name]={'passed':len(rows),'total':len(rows),'file':file}
summary['automated_passed']=sum(g['passed'] for g in summary['groups'].values())
runtime=json.loads((OUT/'runtime/runtime-smoke.json').read_text(encoding='utf-8'))
assert runtime['status']=='PASS'
summary['localhost_simulation_http']='PASS'
summary['blender']=json.loads((OUT/'blender/blender-verification.json').read_text(encoding='utf-8'))
for source,target in [('build-new.log','build.log'),('blender-export.log','blender-export.log'),
                      ('blender-verify.log','blender-verify.log'),('face-tests.log','face-tests.log'),
                      ('sensor-tests-new.log','sensor-tests.log'),('demo-start-final.log','demo-start.log'),
                      ('preflight.json','preflight.json')]:
    shutil.copyfile(ROOT/'.codex-run-logs'/source,OUT/target)
assert 'built in' in (OUT/'build.log').read_text(encoding='utf-8')
summary['frontend_build']='PASS; bundle size warning remains'
sources=[
    'Flask/unified_meeting_room_system.py',
    'FrontEnd/Intelligent_meeting_cloud/src/apis/face.js',
    'FrontEnd/Intelligent_meeting_cloud/src/apis/assistant.js',
    'FrontEnd/Intelligent_meeting_cloud/src/utils/bookingAgentParser.js',
    'FrontEnd/Intelligent_meeting_cloud/src/utils/bookingAgentMatcher.js',
    'FrontEnd/Intelligent_meeting_cloud/src/views/User/Room3D/index.vue',
    'FrontEnd/Intelligent_meeting_cloud/src/views/User/Control/components/FaceCapture.vue',
    'FrontEnd/Intelligent_meeting_cloud/src/views/User/FaceAccess/index.vue',
    'MachineLearning/human_face/face_api.py','week5/scripts/preprocess_face.py',
    'week5/scripts/lbp_face.py','week5/scripts/run_face_eval.py',
    'week7-8/scripts/blender_room_binding.py','week7-8/scripts/verify_blender_room.py','scripts/start-all.ps1',
    'delivery/tests/test_face_pipeline.py','delivery/tests/test_sensor_contract.py',
    'delivery/tests/booking_constraints.mjs','delivery/tests/continuation_browser.mjs',
    'delivery/tests/runtime_smoke.mjs','delivery/tests/browser_acceptance.mjs',
]
summary['source_hash_encoding']='SHA256 of UTF-8 text with CRLF normalized to LF; model files use original bytes'
summary['source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in sources}
summary['model_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
    'FrontEnd/Intelligent_meeting_cloud/public/models/room_301.blend',
    'FrontEnd/Intelligent_meeting_cloud/public/models/room_301.glb']}
summary['evidence_sha256']={p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in OUT.rglob('*') if p.is_file() and p.name!='summary.json'}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'automated_passed':summary['automated_passed'],'groups':summary['groups'],'runtime':runtime['status']},ensure_ascii=False,indent=2))
