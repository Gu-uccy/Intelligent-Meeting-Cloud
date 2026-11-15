"""Synthetic benchmark protocol regressions; never reads photographs or drives GPIO."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'week5/scripts'))
sys.path.insert(0, str(ROOT / 'MachineLearning/human_face'))
import cmu_faces as cmu


def probe(identity='A', kind='known', prediction='A', score=.95, detected=True):
    return {'identity': identity, 'kind': kind, 'prediction': prediction,
            'similarity': score, 'detected': detected}


class Protocol(unittest.TestCase):
    def test_hardware_model_comes_from_device_tree_not_architecture(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp)/'model'
            self.assertIsNone(cmu.device_model(model))
            model.write_bytes(b'Raspberry Pi 4 Model B Rev 1.5\x00')
            self.assertEqual(cmu.device_model(model), 'Raspberry Pi 4 Model B Rev 1.5')
            model.write_text('Other ARM board\n')
            self.assertEqual(cmu.device_model(model), 'Other ARM board')
            model.write_bytes(b'')
            self.assertIsNone(cmu.device_model(model))

    def test_originals_exclude_scaled_and_bad_variants(self):
        self.assertIsNotNone(cmu.IMAGE_NAME.fullmatch('synthetic_straight_happy_open.pgm'))
        for suffix in ['_2.pgm', '_4.pgm', '.pgm.bad', '_2.pgm.bad']:
            self.assertIsNone(cmu.IMAGE_NAME.fullmatch('synthetic_straight_happy_open' + suffix))

    def test_partitions_are_reproducible_disjoint_and_keep_every_image(self):
        people = {f'synthetic{i:02d}': [Path(f'{j:03d}.pgm') for j in range(32)] for i in range(20)}
        rows = cmu.assign_splits(people)
        self.assertEqual(rows, cmu.assign_splits(dict(reversed(list(people.items())))))
        self.assertEqual(len(rows), 640)
        self.assertEqual(len({(r[0], r[1]) for r in rows}), 640)
        counts = Counter((r[2], r[3]) for r in rows)
        self.assertEqual(counts, {('enroll','known'):192, ('calibration','known'):96,
                                  ('test','known'):96, ('calibration','unknown'):128, ('test','unknown'):128})
        unknown_cal = {r[0] for r in rows if r[2:] == ('calibration','unknown')}
        unknown_test = {r[0] for r in rows if r[2:] == ('test','unknown')}
        enrolled = {r[0] for r in rows if r[2] == 'enroll'}
        self.assertFalse(unknown_cal & unknown_test)
        self.assertFalse(enrolled & (unknown_cal | unknown_test))

    def test_archive_rejects_traversal_absolute_links_and_special_members(self):
        for name in ['../faces/a', '/faces/a', 'faces/../escape', 'faces/C:/x', 'faces\\escape', 'other/a']:
            with self.assertRaises(ValueError):
                cmu.validate_archive_listing([name], ['- member'])
        for member_type in ['l', 'h', 'p', 'c', 'b']:
            with self.assertRaises(ValueError):
                cmu.validate_archive_listing(['faces/a'], [member_type + ' member'])
        cmu.validate_archive_listing(['faces/', 'faces/a'], ['d directory', '- file'])

    def test_all_detection_failures_are_rejections_and_stay_in_denominators(self):
        rows = [probe(detected=False, prediction=None, score=None), probe(),
                probe('U','unknown',detected=False,prediction=None,score=None), probe('V','unknown')]
        result = cmu.summarize(rows, .9)
        self.assertEqual(result['accuracy'], .5)
        self.assertEqual(result['far'], .5)
        self.assertEqual(result['frr'], .5)
        self.assertEqual(result['known_detection_failures'], 1)
        self.assertEqual(result['unknown_detection_failures'], 1)
        self.assertEqual(result['conditional_on_detection']['far'], 1)

    def test_wrong_known_identity_is_not_a_correct_accept(self):
        result = cmu.summarize([probe(prediction='B'), probe('U','unknown',score=.3)], .9)
        self.assertEqual(result['wrong_identity'], 1)
        self.assertEqual(result['known_correct'], 0)
        self.assertEqual(result['accuracy'], .5)
        self.assertEqual(result['frr'], 0)

    def test_missing_gallery_prediction_cannot_accept(self):
        result = cmu.summarize([probe(prediction=None, score=-1), probe('U','unknown',prediction=None,score=-1)], 0)
        self.assertEqual(result['known_rejected'], 1)
        self.assertEqual(result['unknown_accepted'], 0)

    def test_calibration_balances_correct_accepts_under_far_constraint(self):
        rows = [probe(score=.96), probe(score=.85), probe('U','unknown',score=.9)]
        threshold, curve = cmu.calibrate(rows)
        self.assertGreater(threshold, .9)
        self.assertLessEqual(threshold, .96)
        chosen = cmu.summarize(rows, threshold)
        self.assertEqual(chosen['known_correct'], 1)
        self.assertEqual(chosen['far'], 0)
        self.assertTrue(all(r['known_count'] == 2 and r['unknown_count'] == 1 for r in curve))

    def test_no_eligible_calibration_does_not_invent_threshold(self):
        threshold, _ = cmu.calibrate([probe(score=1), probe('U','unknown',score=1)])
        self.assertIsNone(threshold)

    def test_all_failed_calibration_cannot_claim_useful_recognition(self):
        rows = [probe(detected=False,prediction=None,score=None),
                probe('U','unknown',detected=False,prediction=None,score=None)]
        threshold, _ = cmu.calibrate(rows)
        self.assertEqual(cmu.summarize(rows,threshold)['known_correct'], 0)
        self.assertEqual(cmu.summarize(rows,threshold)['frr'], 1)

    def test_tampered_manifest_is_rejected_before_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'manifest.csv').write_text('changed', encoding='utf-8')
            (root/'provenance.json').write_text(json.dumps({'archive_sha256':cmu.ARCHIVE_SHA256,
                                                          'manifest_sha256':'wrong'}), encoding='utf-8')
            with patch('run_face_eval.read_manifest',return_value=[]), self.assertRaisesRegex(ValueError,'hash changed'):
                cmu.load_manifest(root)

    def test_test_images_are_processed_after_freeze_and_cannot_change_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); out = root/'results'
            specs = [('A','enroll','known',b'enroll'), ('B','enroll','known',b'fail'),
                     ('A','calibration','known',b'good'), ('U','calibration','unknown',b'unknown'),
                     ('A','test','known',b'testgood'), ('B','test','known',b'fail'),
                     ('V','test','unknown',b'falseaccept'), ('V','test','unknown',b'fail')]
            rows = []
            for i,(identity,split,kind,content) in enumerate(specs):
                file = root/f'{i}.pgm'; file.write_bytes(content)
                rows.append({'identity':identity,'split':split,'kind':kind,'file':file,'path':file.name,
                             'pose':'straight','expression':'neutral','eyes':'open'})
            def extract(content):
                if content in (b'testgood', b'falseaccept'):
                    self.assertTrue((out/'frozen_threshold.json').exists())
                if content == b'fail':
                    raise ValueError('synthetic detection failure')
                return content
            def match(gallery, feature):
                self.assertEqual(set(gallery), {'A'})
                return 'A', {b'good':.95,b'unknown':.9,b'testgood':.96,b'falseaccept':.99}[feature], {}
            args = argparse.Namespace(data_dir=root, output_dir=out, pipeline='service')
            with patch.object(cmu,'load_manifest',return_value=(rows,{'manifest_sha256':'synthetic'})), \
                 patch('face_api.FacePipeline',return_value=extract), patch('lbp_face.match',side_effect=match), \
                 patch('sys.stdout',new_callable=io.StringIO):
                cmu.evaluate(args)
            result = json.loads((out/'face_eval_result.json').read_text(encoding='utf-8'))
            frozen = json.loads((out/'frozen_threshold.json').read_text(encoding='utf-8'))
            self.assertEqual(result['selected_threshold'], frozen['threshold'])
            self.assertEqual(frozen['threshold'], .95)
            self.assertEqual(result['held_out_test']['unknown_accepted'], 1)
            self.assertEqual(result['held_out_test']['known_detection_failures'], 1)
            self.assertEqual(result['gallery_enrollment']['B']['accepted'], 0)
            self.assertEqual(result['extraction']['attempted'], 8)
            self.assertEqual(result['probe_pipeline_latency_ms']['all_probes']['samples'], 6)
            with (out/'per_image_results.csv').open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 8)
            self.assertFalse(result['production_gallery_changed'])
            self.assertFalse(result['production_threshold_exported'])
            self.assertFalse(any('gallery' in p.name or 'feature' in p.name for p in out.iterdir()))
            with self.assertRaisesRegex(ValueError,'new empty'):
                cmu.evaluate(args)


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
    output = Path(os.environ.get('EVIDENCE_OUTPUT_DIR',ROOT/'analysis/cmu-faces-2026-11-15/tests'))
    output.mkdir(parents=True,exist_ok=True)
    (output/'cmu-protocol-tests.json').write_text(json.dumps({'scope':'Synthetic CMU protocol regression; no photographs or GPIO',
        'generated_at':datetime.now(timezone.utc).isoformat(),'records':records},indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
