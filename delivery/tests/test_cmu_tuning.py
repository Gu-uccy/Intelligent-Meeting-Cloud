"""Grid coverage, parameter/version contracts and tuning isolation; synthetic data."""
import argparse
from datetime import datetime,timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'week5/scripts'))
sys.path.insert(0,str(ROOT/'MachineLearning/human_face'))
from face_alignment import REFERENCE_POINTS,align_single_face
from face_api import FacePipeline,create_app
from lbp_face import extract_root_feature,extract_root_grid_feature
import cmu_faces as cmu
import tune_cmu_parameters as tuning


class Parameters(unittest.TestCase):
    def test_fixed_grid_dimension_finite_norm_and_cell_weights(self):
        gray=np.random.default_rng(4).integers(0,256,(112,112),dtype=np.uint8)
        for grid in (4,7,8):
            feature=extract_root_grid_feature(gray,grid)
            self.assertEqual(feature.shape,(59*grid**2,))
            self.assertTrue(np.isfinite(feature).all())
            self.assertAlmostEqual(np.linalg.norm(feature),1)
            np.testing.assert_allclose(np.sum(feature.reshape(grid**2,59)**2,axis=1),np.full(grid**2,1/grid**2))

    def test_grid7_preserves_prior_root_features_exactly(self):
        gray=np.random.default_rng(2).integers(0,256,(112,112),dtype=np.uint8)
        np.testing.assert_array_equal(extract_root_grid_feature(gray,7),extract_root_feature(gray))

    def test_all_nonbaseline_grid_pixels_are_covered_once(self):
        gray=np.arange(112*112).reshape(112,112)
        for grid in (4,8):
            blocks=[]
            def histogram(block):
                blocks.append(block.copy())
                return np.ones(59)
            with patch('lbp_face.lbp_histogram',side_effect=histogram):
                extract_root_grid_feature(gray,grid)
            values=np.concatenate([b.ravel() for b in blocks])
            np.testing.assert_array_equal(np.sort(values),np.arange(112*112))

    def test_alignment_template_scale_has_known_mapping(self):
        image=np.zeros((112,112,3),np.uint8)
        face=np.zeros(15);face[:4]=[10,10,100,100];face[4:14]=REFERENCE_POINTS.ravel();face[14]=.95
        for scale in (.85,1.0,1.15):
            with patch('face_alignment.cv2.warpAffine',return_value=image) as warp:
                align_single_face(image,[face],scale)
            transform=warp.call_args.args[1]
            mapped=REFERENCE_POINTS@transform[:,:2].T+transform[:,2]
            np.testing.assert_allclose(mapped,56+(REFERENCE_POINTS-56)*scale,atol=1e-10)

    def test_invalid_scales_and_grids_are_rejected_not_rounded(self):
        for grid in (0,3,7.5,'bad',float('inf'),float('nan')):
            with self.assertRaisesRegex(ValueError,'FACE_LBP_GRID'):
                FacePipeline(lbp_grid=grid)
        for scale in (0,.9,'bad',float('inf'),float('nan')):
            with self.assertRaisesRegex(ValueError,'FACE_ALIGNMENT_SCALE'):
                FacePipeline(alignment_scale=scale)
        for grid in (3,0,9):
            with self.assertRaises(ValueError):
                extract_root_grid_feature(np.zeros((112,112),np.uint8),grid)

    def test_nine_parameter_sets_have_distinct_versions_and_baseline_reproduces(self):
        profiles=set()
        for scale,grid in tuning.CANDIDATES:
            pipe=FacePipeline(detector_backend='yunet-06',feature_mode='aligned-root-lbp',alignment_scale=scale,lbp_grid=grid)
            self.assertEqual(pipe.feature_dimensions,59*grid**2);profiles.add(pipe.profile)
        self.assertEqual(len(profiles),9)
        baseline=FacePipeline(detector_backend='yunet-06',feature_mode='aligned-root-lbp',alignment_scale=1.0,lbp_grid=7)
        self.assertTrue(baseline.profile.endswith('-aligned-root-lbp-v1'))
        self.assertNotIn('-grid',baseline.profile)
        self.assertTrue(FacePipeline().profile.endswith('-align0.85-grid4-v1'))


class ApiContract(unittest.TestCase):
    def test_current_grid_enroll_verify_and_dimensions_validate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            pipe=FacePipeline(detector_backend='yunet-06',feature_mode='aligned-root-lbp',alignment_scale=.85,lbp_grid=4)
            face=np.zeros(15);face[:4]=[5,5,100,100];face[4:14]=REFERENCE_POINTS.ravel();face[14]=.95
            pipe.detector.detect_faces=Mock(return_value=np.array([face]))
            controller=Mock()
            client=create_app({'TESTING':True,'FACE_DATA_DIR':str(root),'FACE_ADMIN_TOKEN':'test',
                'FACE_THRESHOLD':.99,'FACE_THRESHOLD_PROFILE':pipe.profile},pipeline=pipe,controller=controller).test_client()
            image=cv2.imencode('.png',np.random.default_rng(2).integers(0,256,(112,112,3),dtype=np.uint8))[1].tobytes()
            def verify():
                return client.post('/api/face/verify',data={'image':(io.BytesIO(image),'synthetic.png')})
            response=client.post('/api/face/enroll',headers={'X-Face-Admin-Token':'test'},
                data={'identity':'A','consent':'true','image':(io.BytesIO(image),'synthetic.png')})
            self.assertEqual(response.status_code,200)
            item=json.loads((root/'A.json').read_text());self.assertEqual(len(item['features'][0]),944)
            self.assertTrue(verify().json['matched']);controller.assert_not_called()  # no authorized booking
            health=client.get('/health').json
            self.assertEqual(health['feature_dimensions'],944);self.assertEqual(health['lbp_grid'],4)
            self.assertEqual(health['alignment_scale'],.85)
            item['features']=[np.zeros(2891).tolist()];(root/'A.json').write_text(json.dumps(item))
            bad=verify();self.assertEqual(bad.status_code,422);self.assertFalse(bad.json['matched'])
            self.assertFalse(bad.json['access']['allowed']);controller.assert_not_called()

    def test_old_profile_threshold_and_matching_dimension_do_not_bypass_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);pipe=FacePipeline(lbp_grid=4,alignment_scale=.85)
            baseline=FacePipeline(lbp_grid=7,alignment_scale=1.0)
            vector=np.zeros(944);vector[0]=1
            controller=Mock()
            with patch.object(FacePipeline,'__call__',return_value=vector):
                app=create_app({'TESTING':True,'FACE_DATA_DIR':str(root),'FACE_THRESHOLD':.99,
                    'FACE_THRESHOLD_PROFILE':baseline.profile},pipeline=pipe,controller=controller)
                client=app.test_client()
                def verify():return client.post('/api/face/verify',data={'image':(io.BytesIO(b'synthetic'),'a.png')})
                response=verify();self.assertEqual(response.status_code,422)
                self.assertIn('FACE_THRESHOLD_PROFILE',response.json['error'])
                app.config['FACE_THRESHOLD_PROFILE']=pipe.profile
                (root/'A.json').write_text(json.dumps({'feature_profile':baseline.profile,'features':[vector.tolist()]}))
                response=verify();self.assertEqual(response.status_code,422)
                self.assertFalse(response.json['matched']);controller.assert_not_called()


class Tuning(unittest.TestCase):
    def test_descriptor_diagnostic_cannot_mislabel_tuned_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=argparse.Namespace(data_dir=Path(tmp),output_dir=Path(tmp)/'out',pipeline='portrait-descriptor',
                detector='yunet-06',feature_mode='aligned-root-lbp',alignment_scale=.85,lbp_grid=4)
            with patch.object(cmu,'load_manifest',return_value=([],{})), self.assertRaisesRegex(ValueError,'historical'):
                cmu.evaluate(args)

    def test_all_nine_candidates_use_development_only_and_tie_keeps_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rows=[]
            for index,(identity,split,kind) in enumerate([('A','enroll','known'),('A','calibration','known'),
                                                       ('U','calibration','unknown'),('T','test','unknown')]):
                path=root/f'{index}.pgm'
                if split!='test':path.write_bytes(identity.encode())
                rows.append(dict(identity=identity,split=split,kind=kind,file=path,path=path.name,
                                 pose='straight',expression='neutral',eyes='open'))
            fake=Mock();fake.profile='synthetic';fake.feature_dimensions=944;fake.side_effect=lambda x:x
            protocol=root/'protocol.md';protocol.write_text('fixed protocol')
            args=argparse.Namespace(data_dir=root,output_dir=root/'out',protocol=protocol)
            with patch.object(cmu,'load_manifest',return_value=(rows,{'manifest_sha256':'synthetic'})), \
                 patch.object(tuning,'FacePipeline',return_value=fake), \
                 patch.object(tuning,'match',side_effect=lambda g,f:('A',.99 if f==b'A' else .1,{})), \
                 patch('sys.stdout',new_callable=io.StringIO):
                tuning.tune(args)
            result=json.loads((root/'out/selection.json').read_text())
            self.assertEqual(result['selected']['alignment_scale'],1.0)
            self.assertEqual(result['selected']['lbp_grid'],7)
            self.assertEqual(len(result['candidates']),9)
            self.assertEqual(result['test_features_extracted_in_selection_stage'],0)
            self.assertEqual(fake.call_count,27)
            with self.assertRaisesRegex(ValueError,'new empty'):
                tuning.tune(args)

    def test_parameter_profile_mismatch_stops_before_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rows=[]
            for index,(identity,split,kind) in enumerate([('A','enroll','known'),('A','calibration','known'),
                                                       ('U','calibration','unknown'),('T','test','unknown')]):
                path=root/f'{index}.pgm';path.write_bytes(identity.encode())
                rows.append(dict(identity=identity,split=split,kind=kind,file=path,path=path.name,
                                 pose='straight',expression='neutral',eyes='open'))
            selected=root/'selection.json';selected.write_text(json.dumps({'manifest_sha256':'synthetic',
                'selected':{'backend':'yunet-06','feature_profile':'wrong-parameters','threshold':.99}}))
            fake=Mock();fake.profile='current';fake.side_effect=lambda x:x
            args=argparse.Namespace(data_dir=root,output_dir=root/'out',pipeline='service',detector='yunet-06',
                feature_mode='aligned-root-lbp',alignment_scale=.85,lbp_grid=4,selection=selected)
            with patch.object(cmu,'load_manifest',return_value=(rows,{'manifest_sha256':'synthetic'})), \
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
    out=Path(os.environ.get('EVIDENCE_OUTPUT_DIR',ROOT/'analysis/cmu-tuning-2026-11-15/tests'));out.mkdir(parents=True,exist_ok=True)
    (out/'cmu-tuning-tests.json').write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),
        'scope':'Synthetic grid coverage, parameters, feature dimensions/versions and tuning isolation; no private data or GPIO',
        'records':records},indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
