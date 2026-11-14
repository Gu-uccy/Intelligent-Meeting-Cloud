"""Synthetic regression data only. Never reads the private id/ or test/ folders."""
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "week5/scripts"))
sys.path.insert(0, str(ROOT / "MachineLearning/human_face"))
from lbp_face import _uniform_mapping_table, extract_feature
from preprocess_face import equalize_hist, preprocess_face, resize_face
from run_face_eval import metrics, read_manifest
from face_api import FacePipeline, create_app, simulation_door_control


class Algorithm(unittest.TestCase):
    def test_uniform_bins_are_fixed(self):
        table = _uniform_mapping_table()
        self.assertEqual(len(set(table)), 59)
        self.assertEqual(np.count_nonzero(table == 58), 198)
        rng = np.random.default_rng(3)
        for image in (np.zeros((112,112), np.uint8), rng.integers(0,256,(112,112),dtype=np.uint8)):
            vec = extract_feature(image)
            self.assertEqual(vec.shape, (2891,))
            self.assertAlmostEqual(np.linalg.norm(vec), 1)

    def test_constant_image_no_divide_by_zero(self):
        with np.errstate(all="raise"):
            for value in (0, 75, 255):
                image = np.full((112,112),value,np.uint8)
                np.testing.assert_array_equal(equalize_hist(image),image)

    def test_resize_single_pixel_and_boundary(self):
        np.testing.assert_array_equal(resize_face(np.array([[255]],np.uint8)), np.full((112,112),255,np.uint8))
        image = np.array([[0,255],[128,64]], np.uint8)
        scaled = resize_face(image)
        self.assertEqual(int(scaled[0,0]),0)
        self.assertEqual(int(scaled[-1,-1]),64)

    def test_full_preprocess_finite(self):
        image = np.random.default_rng(4).integers(0,256,(75,90,3),dtype=np.uint8)
        feature = extract_feature(preprocess_face(image))
        self.assertTrue(np.isfinite(feature).all())

    def test_metrics_unknown_denominator_and_wrong_identity(self):
        a,b=np.array([1.,0.]),np.array([0.,1.])
        result=metrics({"A":[a],"B":[b]},[("A",b)],[("unknown",a)],.9)
        self.assertEqual(result["far"],1)
        self.assertEqual(result["wrong_identity"],1)
        self.assertEqual(result["frr"],0)
        self.assertIsNone(metrics({"A":[a]},[("A",a)],[],.9)["far"])

    def test_no_face_rejected(self):
        _, image=cv2.imencode('.png',np.zeros((120,120,3),np.uint8))
        with self.assertRaisesRegex(ValueError,"one detectable face"):
            FacePipeline()(image.tobytes())

    def test_manifest_duplicate_content_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'a.png').write_bytes(b'synthetic'); (root/'b.png').write_bytes(b'synthetic')
            (root/'samples.csv').write_text('path,identity,split,kind\na.png,A,enroll,known\nb.png,A,test,known\n')
            with self.assertRaisesRegex(ValueError,'Duplicate'):
                read_manifest(root,root/'samples.csv')

    def test_manifest_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'samples.csv').write_text('path,identity,split,kind\n../outside.png,A,enroll,known\n')
            with self.assertRaisesRegex(ValueError,'inside'):
                read_manifest(root,root/'samples.csv')


class Access(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.vector=extract_feature(np.random.default_rng(3).integers(0,256,(112,112),dtype=np.uint8))
        self.extract=Mock(return_value=self.vector)
        self.control=Mock(return_value={"acknowledged":True,"source":"simulation","state_kind":"commanded"})
        self.policy=self.root/'policy.local'
        self.write_policy()
        self.config={"TESTING":True,"FACE_DATA_DIR":str(self.root/'gallery'),"FACE_ADMIN_TOKEN":"test-token",
                     "FACE_THRESHOLD":.99,"FACE_POLICY_PATH":str(self.policy)}
        self.app=create_app(self.config,pipeline=self.extract,controller=self.control)
        self.client=self.app.test_client()

    def write_policy(self, **overrides):
        now=datetime.now(timezone.utc)
        booking={"id":"SIM-1","room":"A101","identities":["A01"],"approved":True,
                 "start":(now-timedelta(minutes=5)).isoformat(),"end":(now+timedelta(minutes=5)).isoformat()}
        booking.update(overrides)
        self.policy.write_text(json.dumps({"mode":"simulation","reservations":[booking]}))

    def enroll(self, token='test-token',consent='true'):
        return self.client.post('/api/face/enroll',headers={'X-Face-Admin-Token':token},
                                data={'identity':'A01','consent':consent,'image':(io.BytesIO(b'synthetic'),'test.png')})

    def verify(self,room='A101'):
        return self.client.post('/api/face/verify',data={'room':room,'image':(io.BytesIO(b'synthetic'),'test.png')})

    def test_enrollment_requires_admin(self):
        self.assertEqual(self.enroll(token='').status_code,403); self.extract.assert_not_called()

    def test_enrollment_requires_consent(self):
        self.assertEqual(self.enroll(consent='false').status_code,400); self.extract.assert_not_called()

    def test_enrollment_appends_features_no_photo(self):
        self.assertEqual(self.enroll().json['samples'],1)
        self.assertEqual(self.enroll().json['samples'],2)
        self.assertEqual([p.suffix for p in (self.root/'gallery').iterdir()],['.json'])

    def test_empty_gallery_denied(self):
        self.assertFalse(self.verify().json['access']['allowed']); self.control.assert_not_called()

    def test_recognized_authorized_and_acknowledged(self):
        self.enroll(); result=self.verify().json
        self.assertTrue(result['access']['allowed']); self.control.assert_called_once()
        self.assertEqual(result['access']['reservation_id'],'SIM-1')
        self.assertTrue((self.root/'gallery/access.jsonl').exists())

    def test_recognized_but_not_on_list_denied(self):
        self.enroll(); self.write_policy(identities=['A02'])
        self.assertFalse(self.verify().json['access']['allowed']); self.control.assert_not_called()

    def test_expired_reservation_denied(self):
        self.enroll(); self.write_policy(end=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
        self.assertFalse(self.verify().json['access']['allowed']); self.control.assert_not_called()

    def test_pending_reservation_denied(self):
        self.enroll(); self.write_policy(approved=False)
        self.assertFalse(self.verify().json['access']['allowed']); self.control.assert_not_called()

    def test_wrong_room_denied(self):
        self.enroll(); self.assertFalse(self.verify('A102').json['access']['allowed']); self.control.assert_not_called()

    def test_no_threshold_denied(self):
        self.enroll(); self.app.config['FACE_THRESHOLD']=None
        self.assertFalse(self.verify().json['access']['allowed']); self.control.assert_not_called()

    def test_no_face_denied(self):
        self.enroll(); self.extract.side_effect=ValueError('No face')
        self.assertFalse(self.verify().json['access']['allowed']); self.control.assert_not_called()

    def test_unknown_feature_denied(self):
        self.enroll(); self.extract.return_value=-self.vector
        self.assertFalse(self.verify().json['access']['allowed']); self.control.assert_not_called()

    def test_device_down_denied(self):
        self.enroll(); self.control.side_effect=OSError('offline')
        result=self.verify(); self.assertEqual(result.status_code,503); self.assertFalse(result.json['access']['allowed'])

    def test_unacknowledged_device_denied(self):
        self.enroll(); self.control.return_value={'acknowledged':False,'source':'simulation'}
        self.assertFalse(self.verify().json['access']['allowed'])

    def test_corrupt_policy_denied(self):
        self.enroll(); self.policy.write_text('invalid')
        self.assertFalse(self.verify().json['access']['allowed']); self.control.assert_not_called()

    def test_delete_removes_features(self):
        self.enroll()
        self.assertEqual(self.client.delete('/api/face/enroll/A01').status_code,403)
        self.client.delete('/api/face/enroll/A01',headers={'X-Face-Admin-Token':'test-token'})
        self.assertFalse(self.verify().json['matched'])

    def test_real_unified_simulation_control(self):
        os.environ['MEETING_DATA_MODE']='simulation'; os.environ['MEETING_DATA_DIR']=str(self.root/'sensors')
        spec=importlib.util.spec_from_file_location('face_test_sensors',ROOT/'Flask/unified_meeting_room_system.py')
        sensors=importlib.util.module_from_spec(spec); spec.loader.exec_module(sensors)
        sensor_client=sensors.app.test_client()
        def control():
            ack=sensor_client.post('/api/control',json={'action':'manual','device':'door','state':True,'source':'face-demo'}).json
            return {'acknowledged':ack['success'] and ack['devices']['door_open'],'source':ack['source']}
        self.client=create_app(self.config,pipeline=self.extract,controller=control).test_client()
        self.enroll(); self.assertTrue(self.verify().json['access']['allowed'])
        self.assertTrue(sensor_client.get('/api/current').json['door_open'])


if __name__=='__main__':
    records=[]
    class JsonResult(unittest.TextTestResult):
        def startTest(self,test):
            self.started=time.perf_counter(); super().startTest(test)
        def addSuccess(self,test):
            super().addSuccess(test)
            records.append({'name':str(test),'status':'PASS','duration_ms':round((time.perf_counter()-self.started)*1000,3)})
        def addFailure(self,test,err):
            super().addFailure(test,err); records.append({'name':str(test),'status':'FAIL'})
        def addError(self,test,err):
            super().addError(test,err); records.append({'name':str(test),'status':'FAIL'})
    result=unittest.TextTestRunner(verbosity=2,resultclass=JsonResult).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    output=Path(os.environ.get('EVIDENCE_OUTPUT_DIR',ROOT/'analysis/taskbook-v3-2026-11-14/implementation'))
    output.mkdir(parents=True,exist_ok=True)
    (output/'face-tests.json').write_text(json.dumps({'scope':'Synthetic vectors and injected detection; no private photos or physical GPIO',
        'generated_at':datetime.now(timezone.utc).isoformat(),'records':records},ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
