"""Multiscale geometry, runtime compatibility and development selection isolation."""
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'week5/scripts'))
sys.path.insert(0, str(ROOT / 'MachineLearning/human_face'))
from face_alignment import REFERENCE_POINTS
from face_api import FacePipeline, create_app
from lbp_face import (MULTISCALE_BRANCHES, _uniform_mapping_table, extract_multiscale_feature,
                      extract_root_grid_feature, lbp_histogram, lbp_histogram_radius,
                      match, multiscale_dimensions, root_lbp_branch)
import cmu_faces as cmu
import compare_multiscale_lbp as comparison


class Geometry(unittest.TestCase):
    def setUp(self):
        self.gray = np.random.default_rng(31).integers(0, 256, (112, 112), dtype=np.uint8)

    def test_radius1_is_historical_histogram_exactly(self):
        np.testing.assert_array_equal(lbp_histogram_radius(self.gray, 1), lbp_histogram(self.gray))

    def test_radius2_matches_scalar_square_lattice_reference(self):
        gray = self.gray[:11, :13]
        expected = np.zeros(59)
        offsets = [(-2,-2),(-2,0),(-2,2),(0,2),(2,2),(2,0),(2,-2),(0,-2)]
        table = _uniform_mapping_table()
        for y in range(2, gray.shape[0]-2):
            for x in range(2, gray.shape[1]-2):
                code = sum(int(gray[y+dy,x+dx] >= gray[y,x]) << bit
                           for bit, (dy,dx) in enumerate(offsets))
                expected[table[code]] += 1
        np.testing.assert_array_equal(lbp_histogram_radius(gray, 2), expected)
        self.assertEqual(expected.sum(), 7*9)

    def test_constant_block_places_every_interior_pixel_in_all_ones_bin(self):
        for radius in (1, 2):
            hist = lbp_histogram_radius(np.full((9, 11), 30, np.uint8), radius)
            self.assertEqual(np.count_nonzero(hist), 1)
            self.assertEqual(hist[_uniform_mapping_table()[255]], (9-2*radius)*(11-2*radius))

    def test_single_preserves_baseline_feature_exactly(self):
        np.testing.assert_array_equal(extract_multiscale_feature(self.gray, 'single'),
                                      extract_root_grid_feature(self.gray, 4))

    def test_all_variants_have_expected_dimensions_and_unit_norm(self):
        dims = [944, 1180, 1180, 3835, 3835, 1888, 1888, 2124]
        for variant, dimension in zip(MULTISCALE_BRANCHES, dims):
            with self.subTest(variant=variant):
                feature = extract_multiscale_feature(self.gray, variant)
                self.assertEqual(multiscale_dimensions(variant), dimension)
                self.assertEqual(feature.shape, (dimension,))
                self.assertTrue(np.isfinite(feature).all())
                self.assertAlmostEqual(np.linalg.norm(feature), 1)

    def test_branch_squared_norms_equal_weights(self):
        for variant, branches in MULTISCALE_BRANCHES.items():
            vector = extract_multiscale_feature(self.gray, variant)
            cursor = 0
            for grid, _, weight in branches:
                part = vector[cursor:cursor+59*grid**2]
                self.assertAlmostEqual(float(part @ part), weight)
                cursor += 59*grid**2

    def test_cosine_is_weighted_sum_for_same_enrollment_photo(self):
        other = np.roll(self.gray, 3, axis=0)
        for variant, branches in MULTISCALE_BRANCHES.items():
            expected = sum(weight * (root_lbp_branch(self.gray, grid, radius) @
                                     root_lbp_branch(other, grid, radius))
                           for grid, radius, weight in branches)
            actual = extract_multiscale_feature(self.gray, variant) @ extract_multiscale_feature(other, variant)
            self.assertAlmostEqual(actual, expected)

    def test_matching_cannot_pick_a_different_photo_for_each_branch(self):
        # Each photo matches only one branch: joint scores must stay at .5, not 1.
        probe = np.sqrt(.5) * np.array([1,0,1,0])
        photo_a = np.sqrt(.5) * np.array([1,0,0,1])
        photo_b = np.sqrt(.5) * np.array([0,1,1,0])
        best, score, _ = match({'A': [photo_a, photo_b]}, probe)
        self.assertEqual(best, 'A')
        self.assertAlmostEqual(score, .5)

    def test_invalid_branch_variant_image_or_radius_fails(self):
        for radius in (0, 3):
            with self.assertRaises(ValueError):
                lbp_histogram_radius(self.gray, radius)
        for image in (np.zeros((4,4)), np.zeros((5,5,3))):
            with self.assertRaises(ValueError):
                lbp_histogram_radius(image, 2)
        for grid, radius in ((3,1), (4,3)):
            with self.assertRaises(ValueError):
                root_lbp_branch(self.gray, grid, radius)
        with self.assertRaises(ValueError):
            extract_multiscale_feature(self.gray[:32], 'coarse-50')
        for function in (multiscale_dimensions, lambda v: extract_multiscale_feature(self.gray, v)):
            with self.assertRaises(ValueError):
                function('unknown')


class Runtime(unittest.TestCase):
    def test_default_remains_single_after_non_improving_experiment(self):
        with patch.dict(os.environ, {}, clear=True):
            pipeline = FacePipeline()
        self.assertEqual(pipeline.lbp_variant, 'single')
        self.assertEqual(pipeline.feature_dimensions, 944)
        self.assertTrue(pipeline.profile.endswith('-align0.85-grid4-v1'))

    def test_equal_dimensions_have_different_profiles_and_invalid_combinations_fail(self):
        a = FacePipeline(lbp_variant='coarse-80')
        b = FacePipeline(lbp_variant='coarse-50')
        self.assertEqual(a.feature_dimensions, b.feature_dimensions)
        self.assertNotEqual(a.profile, b.profile)
        for settings in ({'lbp_variant':'unknown'}, {'lbp_variant':'coarse-50','lbp_grid':7},
                         {'lbp_variant':'coarse-50','feature_mode':'bbox-root-lbp'}):
            with self.assertRaisesRegex(ValueError, 'FACE_LBP_VARIANT'):
                FacePipeline(**settings)

    def test_app_config_and_environment_report_experimental_variant(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'FACE_LBP_VARIANT':'radius-50'}):
            self.assertEqual(FacePipeline().feature_dimensions, 1888)
            app = create_app({'TESTING':True, 'FACE_DATA_DIR':tmp, 'FACE_LBP_VARIANT':'coarse-50'})
            health = app.test_client().get('/health').json
            self.assertEqual(health['lbp_variant'], 'coarse-50')
            self.assertEqual(health['feature_dimensions'], 1180)
            self.assertTrue(health['feature_profile'].endswith('-coarse-50-v1'))
            self.assertIsNone(health['threshold'])
            self.assertEqual(health['mode'], 'simulation-only')

    def test_experimental_enrollment_verify_and_version_dimension_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipe = FacePipeline(lbp_variant='coarse-50')
            face = np.zeros(15)
            face[:4] = [5,5,100,100]
            face[4:14] = REFERENCE_POINTS.ravel()
            face[14] = .95
            pipe.detector.detect_faces = Mock(return_value=np.array([face]))
            control = Mock()
            app = create_app({'TESTING':True,'FACE_DATA_DIR':tmp,'FACE_ADMIN_TOKEN':'test',
                              'FACE_THRESHOLD':.99,'FACE_THRESHOLD_PROFILE':pipe.profile}, pipeline=pipe, controller=control)
            client = app.test_client()
            image = cv2.imencode('.png', np.random.default_rng(6).integers(0,256,(112,112,3),dtype=np.uint8))[1].tobytes()
            upload = lambda: {'image':(io.BytesIO(image),'synthetic.png')}
            response = client.post('/api/face/enroll', headers={'X-Face-Admin-Token':'test'},
                                   data=dict(upload(),identity='A',consent='true'))
            self.assertEqual(response.status_code, 200)
            item = json.loads((root/'A.json').read_text())
            self.assertEqual(len(item['features'][0]), 1180)
            self.assertTrue(client.post('/api/face/verify', data=upload()).json['matched'])
            self.assertFalse(client.post('/api/face/verify', data=upload()).json['access']['allowed'])
            other_profile = FacePipeline(lbp_variant='coarse-80').profile
            app.config['FACE_THRESHOLD_PROFILE'] = other_profile
            self.assertEqual(client.post('/api/face/verify', data=upload()).status_code, 422)
            app.config['FACE_THRESHOLD_PROFILE'] = pipe.profile
            item['feature_profile'] = other_profile
            (root/'A.json').write_text(json.dumps(item))
            self.assertEqual(client.post('/api/face/verify', data=upload()).status_code, 422)
            item['feature_profile'] = pipe.profile
            item['features'] = [np.zeros(944).tolist()]
            (root/'A.json').write_text(json.dumps(item))
            response = client.post('/api/face/verify', data=upload())
            self.assertEqual(response.status_code, 422)
            self.assertFalse(response.json['access']['allowed'])
            control.assert_not_called()


class Selection(unittest.TestCase):
    @staticmethod
    def rows(root):
        rows = []
        for index, (identity, split, kind) in enumerate([('A','enroll','known'),('A','calibration','known'),
                                                       ('U','calibration','unknown'),('T','test','unknown')]):
            path = root / f'{index}.pgm'
            if split != 'test':
                path.write_bytes(identity.encode())
            rows.append(dict(identity=identity,split=split,kind=kind,file=path,path=path.name,
                             pose='straight',expression='neutral',eyes='open'))
        return rows

    def test_fixed_eight_candidates_never_extract_test_and_tie_keeps_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = self.rows(root)
            fake = Mock(profile='synthetic', feature_dimensions=944, side_effect=lambda x:x)
            protocol = root/'protocol.md'
            protocol.write_text('fixed protocol')
            args = argparse.Namespace(data_dir=root,output_dir=root/'out',protocol=protocol)
            with patch.object(cmu,'load_manifest',return_value=(rows,{'manifest_sha256':'synthetic'})), \
                 patch.object(comparison,'FacePipeline',return_value=fake) as constructor, \
                 patch.object(comparison,'match',side_effect=lambda g,f:('A',.99 if f==b'A' else .1,{})), \
                 patch('sys.stdout',new_callable=io.StringIO):
                comparison.compare(args)
            result = json.loads((root/'out/selection.json').read_text())
            self.assertEqual(result['selected']['lbp_variant'], 'single')
            self.assertEqual(len(result['candidates']), 8)
            self.assertEqual([c.kwargs['lbp_variant'] for c in constructor.call_args_list], list(MULTISCALE_BRANCHES))
            self.assertEqual(fake.call_count, 24)
            self.assertEqual(result['test_features_extracted_in_selection_stage'], 0)
            with self.assertRaisesRegex(ValueError, 'new empty'):
                comparison.compare(args)

    def test_variant_profile_mismatch_stops_before_test_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = self.rows(root)
            selected = root/'selection.json'
            selected.write_text(json.dumps({'manifest_sha256':'synthetic','selected':{
                'backend':'yunet-06','threshold':.99,'feature_profile':'coarse-80-profile'}}))
            fake = Mock(profile='coarse-50-profile',feature_dimensions=1180,side_effect=lambda x:x)
            args = argparse.Namespace(data_dir=root,output_dir=root/'out',pipeline='service',detector='yunet-06',
                                      feature_mode='aligned-root-lbp',alignment_scale=.85,lbp_grid=4,
                                      lbp_variant='coarse-50',selection=selected)
            with patch.object(cmu,'load_manifest',return_value=(rows,{'manifest_sha256':'synthetic'})), \
                 patch('face_api.FacePipeline',return_value=fake), \
                 patch('lbp_face.match',side_effect=lambda g,f:('A',.99 if f==b'A' else .1,{})), \
                 self.assertRaisesRegex(ValueError,'do not read test images'):
                cmu.evaluate(args)
            self.assertNotIn(b'T', [call.args[0] for call in fake.call_args_list])

    def test_all_failed_candidates_cannot_produce_a_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = self.rows(root)
            fake = Mock(profile='synthetic', feature_dimensions=944, side_effect=ValueError('No face'))
            protocol = root/'protocol.md'
            protocol.write_text('fixed protocol')
            args = argparse.Namespace(data_dir=root,output_dir=root/'out',protocol=protocol)
            with patch.object(cmu,'load_manifest',return_value=(rows,{'manifest_sha256':'synthetic'})), \
                 patch.object(comparison,'FacePipeline',return_value=fake), \
                 patch('sys.stdout',new_callable=io.StringIO), \
                 self.assertRaisesRegex(ValueError,'No calibrated'):
                comparison.compare(args)
            self.assertFalse((root/'out/selection.json').exists())
            for variant in MULTISCALE_BRANCHES:
                record = json.loads((root/'out/candidates'/variant/'calibration.json').read_text())
                self.assertEqual(record['calibration']['known_correct'], 0)
                self.assertEqual(record['development_extraction'], {'False':3})


if __name__ == '__main__':
    records = []
    class JsonResult(unittest.TextTestResult):
        def addSuccess(self, test):
            super().addSuccess(test); records.append({'name':str(test),'status':'PASS'})
        def addFailure(self, test, err):
            super().addFailure(test,err); records.append({'name':str(test),'status':'FAIL'})
        def addError(self, test, err):
            super().addError(test,err); records.append({'name':str(test),'status':'ERROR'})
    result = unittest.TextTestRunner(verbosity=2,resultclass=JsonResult).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    out = Path(os.environ.get('EVIDENCE_OUTPUT_DIR', ROOT/'analysis/cmu-multiscale-2026-11-15/tests'))
    out.mkdir(parents=True,exist_ok=True)
    (out/'multiscale-tests.json').write_text(json.dumps({
        'generated_at':datetime.now(timezone.utc).isoformat(),
        'scope':'Synthetic geometry, radius sampling, multiscale runtime/version contracts and selection isolation; no private data or GPIO',
        'records':records},indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
