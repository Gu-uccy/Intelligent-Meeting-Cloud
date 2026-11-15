"""Synthetic alignment, histogram embedding and development-selection regressions."""
import argparse
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'week5/scripts'))
sys.path.insert(0,str(ROOT/'MachineLearning/human_face'))
from face_alignment import REFERENCE_POINTS, align_single_face, similarity_transform
from face_detection import YuNetDetector
from face_api import FacePipeline,create_app
from lbp_face import extract_feature,extract_root_feature
import cmu_faces as cmu
import compare_face_features as comparison


def face(points=REFERENCE_POINTS):
    result=np.zeros(15)
    result[:4]=[15,20,85,85];result[4:14]=np.asarray(points).ravel();result[14]=.95
    return result


class Alignment(unittest.TestCase):
    def test_identity_and_known_similarity_transform(self):
        np.testing.assert_allclose(similarity_transform(REFERENCE_POINTS),[[1,0,0],[0,1,0]],atol=1e-12)
        angle=.3;rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        source=REFERENCE_POINTS @ rotation.T*1.3+[20,30]
        transform=similarity_transform(source)
        fitted=source @ transform[:,:2].T+transform[:,2]
        np.testing.assert_allclose(fitted,REFERENCE_POINTS,atol=1e-10)

    def test_no_reflection_even_for_mirrored_landmarks(self):
        mirrored=REFERENCE_POINTS.copy();mirrored[:,0]*=-1
        transform=similarity_transform(mirrored)
        self.assertGreater(np.linalg.det(transform[:,:2]),0)

    def test_bad_or_degenerate_landmarks_rejected(self):
        for points in [np.zeros((5,2)),np.arange(10).reshape(5,2),np.full((5,2),np.nan),
                       np.full((5,2),np.inf),np.zeros((4,2))]:
            with self.assertRaises(ValueError):
                similarity_transform(points)

    def test_identity_alignment_preserves_pixels(self):
        image=np.random.default_rng(3).integers(0,256,(112,112,3),dtype=np.uint8)
        aligned=align_single_face(image,[face()])
        np.testing.assert_array_equal(aligned,image)

    def test_missing_multiple_and_outside_landmarks_rejected(self):
        image=np.zeros((112,112,3),np.uint8)
        for faces in [[],[face(),face()],np.zeros((1,14))]:
            with self.assertRaises(ValueError):
                align_single_face(image,faces)
        for points in [REFERENCE_POINTS+1000,REFERENCE_POINTS-1000,np.full((5,2),20)]:
            with self.assertRaises(ValueError):
                align_single_face(image,[face(points)])

    def test_landmarks_map_back_with_boxes(self):
        original=face();resized=original.copy();resized[:14]*=2.5
        dnn=Mock();dnn.detect.return_value=(None,np.array([resized]))
        with patch('face_detection.cv2.FaceDetectorYN.create',return_value=dnn):
            detector=YuNetDetector(score_threshold=.6)
        output=detector.detect_faces(np.zeros((120,128,3),np.uint8))
        np.testing.assert_allclose(output[0],original)
        self.assertEqual(output[0,14],.95)

    def test_alignment_does_not_fall_back_to_bbox(self):
        detector=Mock();detector.profile='synthetic';detector.detect_faces.return_value=np.zeros((1,15))
        with patch('face_api.create_detector',return_value=detector):
            pipeline=FacePipeline(feature_mode='aligned-root-lbp')
        image=cv2.imencode('.png',np.zeros((112,112,3),np.uint8))[1].tobytes()
        with self.assertRaises(ValueError):
            pipeline(image)
        detector.detect.assert_not_called()

    def test_feature_modes_and_versions_are_explicit(self):
        profiles={FacePipeline(feature_mode=mode).profile for mode in comparison.FEATURE_MODES}
        self.assertEqual(len(profiles),4)
        with self.assertRaisesRegex(ValueError,'FACE_FEATURE_MODE'):
            FacePipeline(feature_mode='invalid')
        with self.assertRaisesRegex(ValueError,'landmark detector'):
            FacePipeline(detector_backend='haar',feature_mode='aligned-root-lbp')


class RootHistogram(unittest.TestCase):
    def test_finite_normalized_features_and_equal_cell_weights(self):
        for gray in [np.full((112,112),75,np.uint8),np.random.default_rng(3).integers(0,256,(112,112),dtype=np.uint8)]:
            feature=extract_root_feature(gray)
            self.assertEqual(feature.shape,(2891,))
            self.assertTrue(np.isfinite(feature).all());self.assertTrue((feature>=0).all())
            self.assertAlmostEqual(np.linalg.norm(feature),1)
            np.testing.assert_allclose(np.sum(feature.reshape(49,59)**2,axis=1),np.full(49,1/49))

    def test_histogram_square_root_matches_hand_calculation(self):
        hist=np.zeros((49,59));hist[:,0]=9;hist[:,1]=16
        with patch('lbp_face.extract_feature',return_value=hist.ravel()):
            result=extract_root_feature(np.zeros((112,112),np.uint8)).reshape(49,59)
        np.testing.assert_allclose(result[:,0],np.full(49,.6/7))
        np.testing.assert_allclose(result[:,1],np.full(49,.8/7))
        self.assertTrue(np.all(result[:,2:]==0))

    def test_empty_bins_do_not_divide_by_zero(self):
        with patch('lbp_face.extract_feature',return_value=np.zeros(2891)),np.errstate(all='raise'):
            result=extract_root_feature(np.zeros((112,112),np.uint8))
        np.testing.assert_array_equal(result,np.zeros(2891))

    def test_historical_feature_unchanged(self):
        gray=np.full((112,112),75,np.uint8)
        baseline=extract_feature(gray)
        self.assertEqual(np.count_nonzero(baseline),49)
        self.assertAlmostEqual(float(np.linalg.norm(baseline)),1)
        extract_root_feature(gray)
        np.testing.assert_array_equal(extract_feature(gray),baseline)


class FeatureContract(unittest.TestCase):
    def test_previous_yunet_features_and_threshold_do_not_mix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);pipeline=FacePipeline(feature_mode='aligned-root-lbp')
            vector=np.zeros(2891);vector[0]=1
            # Keep the real version metadata; substitute image extraction only.
            with patch.object(FacePipeline,'__call__',return_value=vector):
                config={'TESTING':True,'FACE_DATA_DIR':str(root),'FACE_THRESHOLD':.9,
                        'FACE_THRESHOLD_PROFILE':pipeline.profile}
                controller=Mock();client=create_app(config,pipeline=pipeline,controller=controller).test_client()
                (root/'A.json').write_text(json.dumps({'feature_profile':FacePipeline(feature_mode='bbox-lbp').profile,
                                                       'features':[vector.tolist()]}))
                response=client.post('/api/face/verify',data={'image':(io.BytesIO(b'synthetic'),'a.png')})
                self.assertEqual(response.status_code,422)
                self.assertFalse(response.json['matched']);controller.assert_not_called()
                self.assertEqual(client.get('/health').json['feature_mode'],'aligned-root-lbp')


class Selection(unittest.TestCase):
    def test_feature_selection_uses_only_development_features_and_fixed_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);records=[]
            for index,(identity,split,kind) in enumerate([('A','enroll','known'),('A','calibration','known'),
                                                        ('U','calibration','unknown'),('T','test','unknown')]):
                path=root/f'{index}.pgm'
                if split!='test':path.write_bytes(identity.encode())
                records.append(dict(identity=identity,split=split,kind=kind,file=path,path=path.name,
                                    pose='straight',expression='neutral',eyes='open'))
            protocol=root/'protocol.md';protocol.write_text('fixed protocol')
            fake=Mock();fake.profile='synthetic';fake.side_effect=lambda x:x
            args=argparse.Namespace(data_dir=root,output_dir=root/'out',protocol=protocol)
            with patch.object(cmu,'load_manifest',return_value=(records,{'manifest_sha256':'synthetic'})), \
                 patch.object(comparison,'FacePipeline',return_value=fake), \
                 patch.object(comparison,'match',side_effect=lambda g,f:('A',.99 if f==b'A' else .1,{})), \
                 patch('sys.stdout',new_callable=io.StringIO):
                comparison.compare(args)
            result=json.loads((root/'out/selection.json').read_text())
            self.assertEqual(result['selected']['feature_mode'],'bbox-lbp')
            self.assertEqual(result['test_features_extracted_in_selection_stage'],0)
            self.assertEqual(fake.call_count,12)

    def test_selection_feature_version_mismatch_stops_before_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);records=[]
            for index,(identity,split,kind) in enumerate([('A','enroll','known'),('A','calibration','known'),
                                                        ('U','calibration','unknown'),('T','test','unknown')]):
                path=root/f'{index}.pgm';path.write_bytes(identity.encode())
                records.append(dict(identity=identity,split=split,kind=kind,file=path,path=path.name,
                                    pose='straight',expression='neutral',eyes='open'))
            selected=root/'selection.json';selected.write_text(json.dumps({'manifest_sha256':'synthetic',
                'selected':{'backend':'yunet-06','threshold':.99,'feature_profile':'wrong'}}))
            fake=Mock();fake.profile='current';fake.side_effect=lambda x:x
            args=argparse.Namespace(data_dir=root,output_dir=root/'out',pipeline='service',detector='yunet-06',
                                    feature_mode='aligned-root-lbp',selection=selected)
            with patch.object(cmu,'load_manifest',return_value=(records,{'manifest_sha256':'synthetic'})), \
                 patch('face_api.FacePipeline',return_value=fake), \
                 patch('lbp_face.match',side_effect=lambda g,f:('A',.99 if f==b'A' else .1,{})), \
                 self.assertRaisesRegex(ValueError,'do not read test images'):
                cmu.evaluate(args)
            self.assertNotIn(b'T',[call.args[0] for call in fake.call_args_list])


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
    out=Path(os.environ.get('EVIDENCE_OUTPUT_DIR',ROOT/'analysis/face-recognition-2026-11-15/tests'));out.mkdir(parents=True,exist_ok=True)
    (out/'face-recognition-tests.json').write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),
        'scope':'Synthetic similarity geometry, Root-LBP, feature versions and development-selection isolation; no private data or GPIO',
        'records':records},indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
