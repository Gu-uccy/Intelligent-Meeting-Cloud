"""Select using enrollment/calibration features; test files are only hash-checked."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

import cmu_faces as cmu

sys.path.insert(0, str(cmu.ROOT / 'MachineLearning/human_face'))
from face_api import FacePipeline
from lbp_face import match

CANDIDATES = ['yunet', 'yunet-07', 'yunet-06', 'haar-small']


def compare(args):
    out = Path(args.output_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use a new empty selection directory')
    rows, provenance = cmu.load_manifest(Path(args.data_dir).resolve())
    out.mkdir(parents=True, exist_ok=True)
    candidates = []
    for backend in CANDIDATES:
        pipeline = FacePipeline(detector_backend=backend,feature_mode='bbox-lbp',alignment_scale=1.0,lbp_grid=7)
        gallery, records = {}, []
        # Preserve enrollment-before-probe even if an external manifest is reordered.
        development = [r for r in rows if r['split'] == 'enroll'] + [r for r in rows if r['split'] == 'calibration']
        for row in development:
            started = time.perf_counter()
            prediction = score = feature = None
            error = ''
            try:
                feature = pipeline(row['file'].read_bytes())
                if row['split'] == 'enroll':
                    gallery.setdefault(row['identity'], []).append(feature)
                else:
                    prediction, score, _ = match(gallery, feature)
            except ValueError as exc:
                error = str(exc)
            records.append({k: row[k] for k in ['path','identity','split','kind','pose','expression','eyes']} | {
                'detected': feature is not None, 'prediction': prediction, 'similarity': score,
                'error': error, 'pipeline_ms': (time.perf_counter() - started) * 1000})
        probes = [r for r in records if r['split'] == 'calibration']
        threshold, _ = cmu.calibrate(probes)
        item = {'backend': backend, 'feature_profile': pipeline.profile, 'threshold': threshold,
                'calibration': cmu.summarize(probes, threshold) if threshold is not None else None,
                'development_extraction': dict(Counter(str(r['detected']) for r in records))}
        candidates.append(item)
        target = out / 'candidates' / backend
        target.mkdir(parents=True)
        cmu.write_csv(target / 'development_results.csv', records, list(records[0]))
        cmu.write_json(target / 'calibration.json', item)
    eligible = [r for r in candidates if r['threshold'] is not None]
    if not eligible:
        raise ValueError('No candidate satisfies the calibration FAR constraint')
    best = min(eligible, key=lambda r: (-r['calibration']['known_correct'], r['calibration']['unknown_accepted'],
                                      r['calibration']['wrong_identity'], CANDIDATES.index(r['backend'])))
    result = {'scope': 'Development selection on enrollment/calibration only; no new independent test claim',
              'manifest_sha256': provenance['manifest_sha256'], 'test_features_extracted_in_this_stage': 0,
              'selection_written_before_selected_test': True, 'candidates': candidates, 'selected': best,
              'protocol_sha256': cmu.sha256(Path(args.protocol).read_bytes())}
    # load_manifest verifies file hashes, including test files, but never decodes/extracts their features here.
    cmu.write_json(out / 'selection.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', default=str(cmu.DEFAULT_CACHE / 'dataset'))
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--protocol', required=True, help='Prespecified protocol file hashed in the selection')
    compare(parser.parse_args())
