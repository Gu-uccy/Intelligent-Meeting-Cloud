"""Reproducible CMU educational face benchmark. Never enables the access service.

prepare: official download, license provenance, full-resolution-only anonymous CSV.
evaluate: existing FacePipeline, failed detections count as rejections, calibration
and test separated; unknown calibration/test identities also disjoint.
"""
import argparse
import csv
import hashlib
import json
import math
import platform
import random
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
PAGE_URL = 'https://www.cs.cmu.edu/~tom/faces.html'
ARCHIVE_URL = 'https://www.cs.cmu.edu/afs/cs.cmu.edu/project/theo-8/faceimages/faces.tar.Z'
DOC_URL = 'https://www.cs.cmu.edu/afs/cs.cmu.edu/project/theo-8/faceimages/docs/hw97.tex'
ARCHIVE_SHA256 = '74a1c594babd985515be58c0c679df283e6b1b9ec0a84d3fc32f9f88c27713f4'
IMAGE_NAME = re.compile(r'[^_]+_(straight|left|right|up)_(neutral|happy|sad|angry)_(open|sunglasses)\.pgm$')
ATTRIBUTION = 'CMU / Tom M. Mitchell, Machine Learning Chapter 4 educational face-image materials; initial implementation credited by the source to Jeff Shufelt.'
DEFAULT_CACHE = ROOT / '.codex-run-logs/cmu-faces-20261115'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def write_csv(path, rows, fields):
    with Path(path).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def official_download(url, path):
    with urlopen(url, timeout=60) as response:
        final = response.geturl()
        if not final.startswith('https://www.cs.cmu.edu/'):
            raise ValueError('Refuse a redirect outside the official HTTPS source')
        content = response.read(32 * 1024 * 1024 + 1)
    if len(content) > 32 * 1024 * 1024:
        raise ValueError('Download exceeds the expected size limit')
    path.write_bytes(content)


def validate_archive_listing(names, verbose):
    if not names or len(names) > 5000:
        raise ValueError('Unexpected archive inventory')
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != 'faces' or '\\' in name or ':' in name:
            raise ValueError('Unsafe archive path')
    if len(verbose) != len(names) or any(not line or line[0] not in '-d' for line in verbose):
        raise ValueError('Archive links or special members are not permitted')


def assign_splits(people):
    """Fixed before detection/matching; no selecting people based on accuracy."""
    result = []
    for index, (person, images) in enumerate(sorted(people.items()), 1):
        if len(images) < 10:
            raise ValueError('Each source identity needs at least ten unique originals')
        identity = f'CMU{index:02d}'
        order = list(sorted(images))
        random.Random(20261115 + index).shuffle(order)
        for n, image in enumerate(order):
            if index <= 12:
                split = 'enroll' if n < 16 else ('calibration' if n < 24 else 'test')
                kind = 'known'
            else:
                split = 'calibration' if index <= 16 else 'test'
                kind = 'unknown'
            result.append((identity, image, split, kind))
    return result


def prepare(args):
    if not args.accept_educational_use:
        raise ValueError('Record educational-use basis with --accept-educational-use')
    cache, data = Path(args.cache).resolve(), Path(args.data_dir).resolve()
    if data.exists() and any(data.iterdir()):
        raise ValueError('Use a new empty data directory; existing datasets are never overwritten')
    cache.mkdir(parents=True, exist_ok=True)
    for url, name in [(PAGE_URL, 'source-page.html'), (ARCHIVE_URL, 'faces.tar.Z'), (DOC_URL, 'hw97.tex')]:
        path = cache / name
        if not path.exists():
            official_download(url, path)
    page = (cache / 'source-page.html').read_text(encoding='utf-8')
    if not all(phrase in page for phrase in ['educational purpose', 'attribution', 'outside CMU']):
        raise ValueError('Official educational-use statement could not be verified')
    if sha256((cache / 'faces.tar.Z').read_bytes()) != ARCHIVE_SHA256:
        raise ValueError('Official archive changed: review provenance before updating the pinned hash')
    raw = cache / 'raw'
    if not (raw / 'faces').exists():
        if raw.exists() and any(raw.iterdir()):
            raise ValueError('Use a fresh extraction directory')
        archive = str(cache / 'faces.tar.Z')
        names = subprocess.check_output(['tar', '-tf', archive], text=True).splitlines()
        details = subprocess.check_output(['tar', '-tvf', archive], text=True).splitlines()
        validate_archive_listing(names, details)
        raw.mkdir(exist_ok=True)
        subprocess.run(['tar', '-xf', archive, '-C', str(raw)], check=True)
    import cv2
    import numpy as np
    people, exclusions = {}, Counter()
    for folder in sorted((raw / 'faces').iterdir()):
        if folder.name == '.anonr' and folder.is_file() and not folder.is_symlink():
            exclusions['archive_metadata'] += 1
            continue
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError('Unexpected source identity entry')
        images = []
        for path in sorted(folder.iterdir()):
            if path.is_symlink() or not path.is_file():
                raise ValueError('Unexpected source member')
            if not IMAGE_NAME.fullmatch(path.name):
                exclusions['marked_bad' if '.bad' in path.name else 'scaled_versions'] += 1
                continue
            image = cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if image is None or image.shape != (120, 128):
                raise ValueError('Unexpected original image dimensions')
            images.append(path)
        people[folder.name] = images
    if len(people) != 20 or sum(map(len, people.values())) != 624:
        raise ValueError('Source differs from the pinned 20-person, 624-good-original inventory')
    data.mkdir(parents=True, exist_ok=True)
    rows, seen_content, seen_pixels, mapping = [], set(), set(), []
    counters = Counter()
    for identity, source, split, kind in assign_splits(people):
        content = source.read_bytes()
        digest = sha256(content)
        pixels = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_GRAYSCALE)
        pixel_digest = sha256(pixels.tobytes())
        if digest in seen_content or pixel_digest in seen_pixels:
            raise ValueError('Duplicate original photograph; do not split variants across partitions')
        seen_content.add(digest); seen_pixels.add(pixel_digest)
        counters[identity] += 1
        relative = f'samples/{identity}/{counters[identity]:03d}.pgm'
        target = data / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        pose, expression, eyes = IMAGE_NAME.fullmatch(source.name).groups()
        rows.append({'path': relative, 'identity': identity, 'split': split, 'kind': kind,
                     'pose': pose, 'expression': expression, 'eyes': eyes, 'sha256': digest})
        mapping.append({'anonymous_path': relative, 'source_relative_path': source.relative_to(raw).as_posix()})
    write_csv(data / 'manifest.csv', rows, ['path', 'identity', 'split', 'kind', 'pose', 'expression', 'eyes', 'sha256'])
    # Source aliases stay in ignored storage; they are pseudonyms, not a claim of irreversible anonymization.
    write_json(cache / 'identity-map.local.json', mapping)
    metadata = {'dataset': 'CMU Machine Learning Chapter 4 faces', 'prepared_at': datetime.now(timezone.utc).isoformat(),
                'official_page': PAGE_URL, 'archive_url': ARCHIVE_URL, 'documentation_url': DOC_URL,
                'archive_sha256': ARCHIVE_SHA256, 'source_page_sha256': sha256((cache / 'source-page.html').read_bytes()),
                'documentation_sha256': sha256((cache / 'hw97.tex').read_bytes()),
                'attribution': ATTRIBUTION, 'permission_basis': 'Official free educational use with attribution; not new participant consent or teacher acceptance',
                'original_resolution': [128, 120], 'people': 20, 'unique_originals': len(rows), 'per_identity': dict(counters),
                'excluded': dict(exclusions), 'known_identities': 12, 'unknown_calibration_identities': 4, 'unknown_test_identities': 4,
                'split_counts': dict(Counter(f"{r['split']}/{r['kind']}" for r in rows)), 'seed': 20261115,
                'manifest_sha256': sha256((data / 'manifest.csv').read_bytes()),
                'split_limitations': 'Same historical controlled collection; no capture-session metadata or independent camera/device validation. No detection-based selection.',
                'production_gallery_changed': False}
    write_json(data / 'provenance.json', metadata)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


def load_manifest(data):
    # Reuse the general duplicate/path/known-vs-unknown checks.
    from run_face_eval import read_manifest
    rows = read_manifest(data, data / 'manifest.csv')
    provenance = json.loads((data / 'provenance.json').read_text(encoding='utf-8'))
    if provenance['archive_sha256'] != ARCHIVE_SHA256 or provenance['manifest_sha256'] != sha256((data / 'manifest.csv').read_bytes()):
        raise ValueError('CMU provenance or manifest hash changed')
    if len(rows) != 624 or len({r['identity'] for r in rows}) != 20:
        raise ValueError('Evaluate the complete fixed CMU partition, without removing hard images')
    unknown_cal = {r['identity'] for r in rows if r['kind'] == 'unknown' and r['split'] == 'calibration'}
    unknown_test = {r['identity'] for r in rows if r['kind'] == 'unknown' and r['split'] == 'test'}
    if unknown_cal & unknown_test:
        raise ValueError('Unknown calibration/test identities must be disjoint')
    for row in rows:
        if row['sha256'] != sha256(row['file'].read_bytes()):
            raise ValueError('Manifest image hash mismatch')
    return rows, provenance


def summarize(probes, threshold):
    known = [r for r in probes if r['kind'] == 'known']
    unknown = [r for r in probes if r['kind'] == 'unknown']
    accepted = lambda r: r['detected'] and r['prediction'] is not None and r['similarity'] >= threshold
    correct = sum(accepted(r) and r['prediction'] == r['identity'] for r in known)
    wrong = sum(accepted(r) and r['prediction'] != r['identity'] for r in known)
    rejected = len(known) - correct - wrong
    false = sum(accepted(r) for r in unknown)
    total = len(known) + len(unknown)
    dknown = [r for r in known if r['detected']]
    dunknown = [r for r in unknown if r['detected']]
    return {'accuracy': (correct + len(unknown) - false) / total if total else None,
            'far': false / len(unknown) if unknown else None, 'frr': rejected / len(known) if known else None,
            'known_identification_accuracy': correct / len(known) if known else None,
            'known_count': len(known), 'unknown_count': len(unknown), 'known_correct': correct,
            'known_rejected': rejected, 'wrong_identity': wrong, 'unknown_accepted': false,
            'unknown_rejected': len(unknown) - false, 'known_detection_failures': sum(not r['detected'] for r in known),
            'unknown_detection_failures': sum(not r['detected'] for r in unknown),
            'conditional_on_detection': {'known_count': len(dknown), 'unknown_count': len(dunknown),
                'known_identification_accuracy': correct / len(dknown) if dknown else None,
                'far': false / len(dunknown) if dunknown else None}}


def calibrate(probes):
    scores = {float(r['similarity']) for r in probes if r['detected'] and r['prediction'] is not None}
    thresholds = {0.0, 1.0} | scores | {math.nextafter(s, math.inf) for s in scores if s < 1.0}
    curve = [{'threshold': t, **summarize(probes, t)} for t in sorted(thresholds) if 0 <= t <= 1]
    eligible = [r for r in curve if r['far'] is not None and r['far'] <= .05]
    if not eligible:
        return None, curve
    # Count wrong accepted identities as failures; never optimize with final test results.
    best = min(eligible, key=lambda r: ((r['known_rejected'] + r['wrong_identity']) / max(1, r['known_count']), r['far'], -r['threshold']))
    return best['threshold'], curve


def latency(records):
    import numpy as np
    def values(items):
        xs = [r['pipeline_ms'] for r in items]
        return {'samples': len(xs), 'mean': float(np.mean(xs)), 'p50': float(np.percentile(xs, 50)),
                'p95': float(np.percentile(xs, 95)), 'max': max(xs)} if xs else None
    return {'all_probes': values(records), 'successful_detection': values([r for r in records if r['detected']]),
            'failed_detection': values([r for r in records if not r['detected']])}


def evaluate(args):
    import cv2
    import numpy as np
    from lbp_face import match, extract_feature
    from preprocess_face import preprocess_face
    sys.path.insert(0, str(ROOT / 'MachineLearning/human_face'))
    from face_api import FacePipeline
    data, out = Path(args.data_dir).resolve(), Path(args.output_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use a new empty result directory')
    rows, provenance = load_manifest(data)
    out.mkdir(parents=True, exist_ok=True)
    detector = getattr(args, 'detector', 'haar')
    feature_mode = getattr(args,'feature_mode','bbox-lbp')
    pipeline = FacePipeline(detector_backend=detector,feature_mode=feature_mode)
    diagnostic = args.pipeline == 'portrait-descriptor'
    # Descriptor-only is a separate diagnostic of complete supplied portraits.
    # It never substitutes for face detection or exports a threshold to the service.
    def extract(content):
        if not diagnostic:
            return pipeline(content)
        image = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError('Invalid portrait')
        return extract_feature(preprocess_face(image))
    gallery, records = {}, []
    def process(row, enrollment=False):
        start = time.perf_counter()
        feature = None
        best, score, error = None, None, ''
        try:
            feature = extract(row['file'].read_bytes())
            if enrollment:
                gallery.setdefault(row['identity'], []).append(feature)
            else:
                best, score, _ = match(gallery, feature)
        except ValueError as exc:
            error = str(exc)
        elapsed = (time.perf_counter() - start) * 1000
        record = {k: row[k] for k in ['path', 'identity', 'split', 'kind', 'pose', 'expression', 'eyes']}
        record.update(detected=feature is not None, prediction=best, similarity=score,
                      error=error, pipeline_ms=elapsed)
        records.append(record)
        return record
    for row in rows:
        if row['split'] == 'enroll':
            process(row, enrollment=True)
    calibration = [process(r) for r in rows if r['split'] == 'calibration']
    threshold, curve = calibrate(calibration)
    selection_hash = None
    if getattr(args, 'selection', None):
        selection_bytes = Path(args.selection).read_bytes()
        selection = json.loads(selection_bytes)
        if (diagnostic or selection['manifest_sha256'] != provenance['manifest_sha256']
                or selection['selected']['backend'] != detector
                or selection['selected']['threshold'] != threshold
                or selection['selected'].get('feature_profile') != getattr(pipeline, 'profile', None)):
            raise ValueError('Selected detector, dataset or calibration threshold changed; do not read test images')
        selection_hash = sha256(selection_bytes)
    frozen = {'threshold': threshold, 'selection': 'calibration only; FAR <= 0.05, then minimum known errors, then lower FAR/higher threshold',
              'manifest_sha256': provenance['manifest_sha256'], 'pipeline': args.pipeline,
              'created_before_test_extraction': True, 'created_at': datetime.now(timezone.utc).isoformat(),
              'detector': None if diagnostic else detector,
              'feature_profile': getattr(pipeline, 'profile', None),
              'feature_mode': feature_mode,
              'development_selection_sha256': selection_hash,
              'production_use': False}
    write_json(out / 'frozen_threshold.json', frozen)
    # Only now process the historical test partition; it is reused development data, not new independent evidence.
    test = [process(r) for r in rows if r['split'] == 'test']
    test_metrics = summarize(test, threshold) if threshold is not None else None
    cal_metrics = summarize(calibration, threshold) if threshold is not None else None
    usable = threshold is not None and cal_metrics['known_correct'] > 0
    result = {'status': 'EXPERIMENT_COMPLETED', 'generated_at': datetime.now(timezone.utc).isoformat(),
              'dataset': provenance, 'pipeline': args.pipeline,
              'scope': 'Complete portrait preprocessing/LBP/matching diagnostic; NO detection' if diagnostic else f'Service FacePipeline: decode -> {detector} -> custom preprocessing -> uniform LBP -> cosine',
              'detector': None if diagnostic else detector,
              'feature_profile': getattr(pipeline, 'profile', None),
              'feature_mode': feature_mode,
              'test_is_new_independent_evidence': False,
              'comparison_scope': 'Previously inspected CMU data reused for development comparison; test is a partition name, not new independent validation',
              'device': {'platform': platform.platform(), 'machine': platform.machine(), 'python': platform.python_version(),
                         'opencv': cv2.__version__, 'numpy': np.__version__, 'target_raspberry_pi': False},
              'selected_threshold': threshold, 'calibration': cal_metrics, 'held_out_test': test_metrics,
              'calibration_has_correct_accepts': usable,
              'gallery_enrollment': {r: {'attempted': sum(x['identity'] == r and x['split'] == 'enroll' for x in rows),
                                        'accepted': len(gallery.get(r, []))} for r in sorted({x['identity'] for x in rows if x['kind'] == 'known'})},
              'extraction': {'attempted': len(records), 'successful': sum(r['detected'] for r in records),
                             'failed': sum(not r['detected'] for r in records)},
              'probe_pipeline_latency_ms': latency(calibration + test),
              'latency_scope': 'disk read + decode + detection (service mode only) + preprocessing + LBP + matching; includes failed attempts; excludes HTTP and actuators',
              'feature_dimensions': 2891, 'production_gallery_changed': False, 'production_threshold_exported': False,
              'notes': ['Failed detections are retained and count as rejections, including unknown failures in FAR denominator.',
                        'Conditional-on-detection metrics accompany full denominators; low FAR alone is not useful recognition.',
                        'Known enrollment failures may leave empty identities; none are silently excluded.',
                        'Historical low-resolution controlled data; no session-disjoint or live-camera/device claim.',
                        'Public educational permission is not participant consent or confirmation of teacher acceptance.',
                        'Descriptor diagnostic does not prove end-to-end service recognition or door access.']}
    write_json(out / 'face_eval_result.json', result)
    write_csv(out / 'per_image_results.csv', records, ['path','identity','split','kind','pose','expression','eyes','detected','prediction','similarity','error','pipeline_ms'])
    write_csv(out / 'calibration_curve.csv', curve, ['threshold','accuracy','far','frr','known_identification_accuracy','known_count','unknown_count','known_correct','known_rejected','wrong_identity','unknown_accepted','known_detection_failures','unknown_detection_failures'])
    print(json.dumps({k: result[k] for k in ['status','pipeline','selected_threshold','extraction','calibration','held_out_test','probe_pipeline_latency_ms']}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('prepare')
    p.add_argument('--cache', default=str(DEFAULT_CACHE))
    p.add_argument('--data-dir', default=str(DEFAULT_CACHE / 'dataset'))
    p.add_argument('--accept-educational-use', action='store_true')
    p.set_defaults(action=prepare)
    p = commands.add_parser('evaluate')
    p.add_argument('--data-dir', default=str(DEFAULT_CACHE / 'dataset'))
    p.add_argument('--output-dir', required=True)
    p.add_argument('--pipeline', choices=['service','portrait-descriptor'], default='service')
    p.add_argument('--detector', choices=['haar','haar-small','yunet','yunet-07','yunet-06'], default='haar',
                   help='Explicit detector; Haar default reproduces the historical benchmark, service now defaults to YuNet')
    p.add_argument('--selection', help='Frozen development selection JSON; verify it before reading test images')
    p.add_argument('--feature-mode',choices=['bbox-lbp','aligned-lbp','bbox-root-lbp','aligned-root-lbp'],default='bbox-lbp')
    p.set_defaults(action=evaluate)
    args = parser.parse_args()
    args.action(args)


if __name__ == '__main__':
    main()
