"""Synthetic detector, coordinate, concurrency, and feature-version regressions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'MachineLearning/human_face'))
sys.path.insert(0, str(ROOT / 'week5/scripts'))
from face_detection import DEFAULT_DETECTOR, YuNetDetector, create_detector, crop_single_face
from face_api import FacePipeline, create_app
import cmu_faces as cmu
import compare_face_detectors as comparison


def encoded_blank():
    return cv2.imencode('.png', np.zeros((120,128,3),np.uint8))[1].tobytes()


class Detection(unittest.TestCase):
    def test_default_and_real_blank_image(self):
        pipeline = FacePipeline(detector_backend=DEFAULT_DETECTOR)
        self.assertIn('s0.6', pipeline.profile)
        with self.assertRaisesRegex(ValueError,'found 0'):
            pipeline(encoded_blank())

    def test_empty_and_invalid_uploads(self):
        pipeline = FacePipeline()
        for content in [b'', b'not an image']:
            with self.assertRaisesRegex(ValueError,'Invalid'):
                pipeline(content)

    def test_size_limits_keep_aspect_ratio(self):
        self.assertEqual(YuNetDetector.input_size(128,120),(320,300))
        self.assertEqual(YuNetDetector.input_size(3840,2160),(960,540))
        self.assertEqual(YuNetDetector.input_size(640,480),(640,480))

    def test_coordinates_map_to_original_image(self):
        faces = np.zeros((1,15)); faces[0,:4]=[80,60,100,120]; faces[0,14]=.95
        dnn=Mock(); dnn.detect.return_value=(None,faces)
        with patch('face_detection.cv2.FaceDetectorYN.create',return_value=dnn):
            detector=YuNetDetector(score_threshold=.6)
        boxes=detector.detect(np.zeros((120,128,3),np.uint8))
        np.testing.assert_allclose(boxes,[[32,24,40,48]])
        dnn.setInputSize.assert_called_once_with((320,300))

    def test_detector_filters_only_by_detection_score(self):
        faces=np.zeros((2,15)); faces[:,:4]=[20,20,50,50]; faces[:,14]=[.59,.61]
        dnn=Mock(); dnn.detect.return_value=(None,faces)
        with patch('face_detection.cv2.FaceDetectorYN.create',return_value=dnn):
            detector=YuNetDetector(score_threshold=.6)
        self.assertEqual(len(detector.detect(np.zeros((320,320,3),np.uint8))),1)

    def test_two_faces_never_choose_only_largest(self):
        dnn=Mock(); faces=np.zeros((2,15)); faces[:,:4]=[[5,5,100,100],[150,150,50,50]];faces[:,14]=.95
        dnn.detect.return_value=(None,faces)
        with patch('face_detection.cv2.FaceDetectorYN.create',return_value=dnn):
            detector=YuNetDetector(score_threshold=.6)
        with patch('face_api.create_detector',return_value=detector):
            pipeline=FacePipeline()
        with self.assertRaisesRegex(ValueError,'found 2'):
            pipeline(encoded_blank())

    def test_bounds_are_clamped_without_negative_index_wrapping(self):
        image=np.arange(10*20*3).reshape(10,20,3)
        np.testing.assert_array_equal(crop_single_face(image,[[-2,-3,7,8]]),image[:5,:5])
        np.testing.assert_array_equal(crop_single_face(image,[[18,8,9,9]]),image[8:,18:])

    def test_invalid_and_outside_boxes_rejected(self):
        for box in [[1,1,0,2],[1,1,-2,2],[float('nan'),1,2,2],[500,500,10,10],[-50,0,1,2]]:
            with self.assertRaises(ValueError):
                crop_single_face(np.zeros((10,20,3)),[box])

    def test_corrupt_detector_output_rejected(self):
        dnn=Mock()
        with patch('face_detection.cv2.FaceDetectorYN.create',return_value=dnn):
            detector=YuNetDetector()
        for output in [np.zeros((1,14)), np.full((1,15),np.nan)]:
            dnn.detect.return_value=(None,output)
            with self.assertRaisesRegex(ValueError,'Invalid face detector output'):
                detector.detect(np.zeros((120,128,3),np.uint8))

    def test_missing_or_tampered_model_never_silently_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'model.onnx'
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                YuNetDetector(path)
            path.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                YuNetDetector(path)
        with self.assertRaisesRegex(ValueError,'FACE_DETECTOR'):
            create_detector('invalid')

    def test_concurrent_requests_keep_input_dimensions_isolated(self):
        class MutableDnn:
            def setInputSize(self,size):
                self.size=size
            def detect(self,image):
                size=(image.shape[1],image.shape[0])
                time.sleep(.002)
                if self.size != size:
                    raise AssertionError('concurrent size mutation')
                return None,None
        with patch('face_detection.cv2.FaceDetectorYN.create',return_value=MutableDnn()):
            detector=YuNetDetector()
        images=[np.zeros((h,w,3),np.uint8) for h,w in [(120,128),(480,640)]*10]
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertTrue(all(len(boxes)==0 for boxes in pool.map(detector.detect,images)))


class FeatureVersions(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.control=Mock()
        class Extractor:
            profile='synthetic-new-v1'
            detector=SimpleNamespace(backend='synthetic')
            def __call__(self,content):
                vec=np.zeros(2891);vec[0]=1
                return vec
        self.config={'TESTING':True,'FACE_DATA_DIR':str(self.root),'FACE_ADMIN_TOKEN':'test-token',
                     'FACE_THRESHOLD':.99,'FACE_THRESHOLD_PROFILE':'synthetic-new-v1'}
        self.app=create_app(self.config,pipeline=Extractor(),controller=self.control)
        self.client=self.app.test_client()

    def enroll(self):
        return self.client.post('/api/face/enroll',headers={'X-Face-Admin-Token':'test-token'},
            data={'identity':'A','consent':'true','image':(io.BytesIO(b'synthetic'),'sample.png')})

    def verify(self):
        return self.client.post('/api/face/verify',data={'image':(io.BytesIO(b'synthetic'),'sample.png')})

    def test_new_features_store_profile_and_match(self):
        self.assertEqual(self.enroll().status_code,200)
        item=json.loads((self.root/'A.json').read_text())
        self.assertEqual(item['feature_profile'],'synthetic-new-v1')
        self.assertTrue(self.verify().json['matched'])
        self.control.assert_not_called()  # no reservation

    def test_old_feature_schema_cannot_match(self):
        self.enroll();path=self.root/'A.json';item=json.loads(path.read_text());item.pop('feature_profile')
        path.write_text(json.dumps(item))
        response=self.verify()
        self.assertEqual(response.status_code,422)
        self.assertFalse(response.json['access']['allowed']);self.control.assert_not_called()

    def test_wrong_profile_cannot_append_or_overwrite(self):
        self.enroll();path=self.root/'A.json';item=json.loads(path.read_text());item['feature_profile']='old'
        path.write_text(json.dumps(item));before=path.read_bytes()
        self.assertEqual(self.enroll().status_code,422)
        self.assertEqual(path.read_bytes(),before)

    def test_unbound_threshold_cannot_grant_access(self):
        self.enroll();self.app.config['FACE_THRESHOLD_PROFILE']='old'
        response=self.verify()
        self.assertEqual(response.status_code,422)
        self.assertIn('FACE_THRESHOLD_PROFILE',response.json['error']);self.control.assert_not_called()

    def test_health_exposes_actual_backend_and_profile(self):
        health=self.client.get('/health').json
        self.assertEqual(health['detector_backend'],'synthetic')
        self.assertEqual(health['feature_profile'],'synthetic-new-v1')
        self.assertFalse(health['calibrated'])


class Selection(unittest.TestCase):
    def test_candidate_selection_never_extracts_test_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rows=[]
            for i,(identity,split,kind) in enumerate([('A','enroll','known'),('A','calibration','known'),
                                                     ('U','calibration','unknown'),('T','test','unknown')]):
                path=root/f'{i}.pgm'
                if split!='test':path.write_bytes(b'known' if identity=='A' else b'unknown')
                rows.append(dict(identity=identity,split=split,kind=kind,file=path,path=path.name,
                                 pose='straight',expression='neutral',eyes='open'))
            protocol=root/'protocol.md';protocol.write_text('synthetic predefined protocol')
            fake=Mock();fake.profile='synthetic';fake.side_effect=lambda x:x
            def match(gallery,feature):
                return 'A',.99 if feature==b'known' else .1,{}
            args=argparse.Namespace(data_dir=root,output_dir=root/'out',protocol=protocol)
            with patch.object(cmu,'load_manifest',return_value=(rows,{'manifest_sha256':'synthetic'})), \
                 patch.object(comparison,'FacePipeline',return_value=fake),patch.object(comparison,'match',side_effect=match), \
                 patch('sys.stdout',new_callable=io.StringIO):
                comparison.compare(args)
            result=json.loads((root/'out/selection.json').read_text())
            self.assertEqual(result['selected']['backend'],'yunet')
            self.assertEqual(result['test_features_extracted_in_this_stage'],0)
            self.assertEqual(fake.call_count,12)
            with self.assertRaisesRegex(ValueError,'new empty'):
                comparison.compare(args)

    def test_selection_mismatch_blocks_test_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rows=[]
            for i,(identity,split,kind,content) in enumerate([('A','enroll','known',b'known'),
                ('A','calibration','known',b'known'),('U','calibration','unknown',b'unknown'),('T','test','unknown',b'test')]):
                path=root/f'{i}.pgm';path.write_bytes(content)
                rows.append(dict(identity=identity,split=split,kind=kind,file=path,path=path.name,
                                 pose='straight',expression='neutral',eyes='open'))
            selection=root/'selection.json';selection.write_text(json.dumps({'manifest_sha256':'synthetic',
                'selected':{'backend':'yunet-06','threshold':.5}}))
            fake=Mock();fake.profile='synthetic';fake.side_effect=lambda x:x
            args=argparse.Namespace(data_dir=root,output_dir=root/'out',pipeline='service',detector='yunet-06',selection=selection)
            with patch.object(cmu,'load_manifest',return_value=(rows,{'manifest_sha256':'synthetic'})), \
                 patch('face_api.FacePipeline',return_value=fake), \
                 patch('lbp_face.match',side_effect=lambda g,f:('A',.99 if f==b'known' else .1,{})), \
                 self.assertRaisesRegex(ValueError,'do not read test images'):
                cmu.evaluate(args)
            self.assertNotIn(b'test',[call.args[0] for call in fake.call_args_list])


if __name__=='__main__':
    records=[]
    class JsonResult(unittest.TextTestResult):
        def addSuccess(self,test):
            super().addSuccess(test);records.append({'name':str(test),'status':'PASS'})
        def addFailure(self,test,err):
            super().addFailure(test,err);records.append({'name':str(test),'status':'FAIL'})
        def addError(self,test,err):
            super().addError(test,err);records.append({'name':str(test),'status':'ERROR'})
    result=unittest.TextTestRunner(verbosity=2,resultclass=JsonResult).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    output=Path(os.environ.get('EVIDENCE_OUTPUT_DIR',ROOT/'analysis/face-detection-2026-11-15/tests'))
    output.mkdir(parents=True,exist_ok=True)
    (output/'face-detection-tests.json').write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),
        'scope':'Synthetic coordinates, detection failures, real model blank image, concurrency and feature contracts; no private images or GPIO',
        'records':records},indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
