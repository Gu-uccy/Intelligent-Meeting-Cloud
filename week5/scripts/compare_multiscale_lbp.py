"""Prespecified multiscale comparison; calibration chooses, test never chooses."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

import cmu_faces as cmu
sys.path.insert(0,str(cmu.ROOT/'MachineLearning/human_face'))
from face_api import FacePipeline
from face_detection import MODEL_SHA256
from lbp_face import MULTISCALE_BRANCHES,match


def compare(args):
    out=Path(args.output_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use a new empty multiscale directory')
    rows,provenance=cmu.load_manifest(Path(args.data_dir).resolve())
    out.mkdir(parents=True,exist_ok=True)
    development=[r for r in rows if r['split']=='enroll']+[r for r in rows if r['split']=='calibration']
    candidates=[]
    for variant in MULTISCALE_BRANCHES:
        pipeline=FacePipeline(detector_backend='yunet-06',feature_mode='aligned-root-lbp',alignment_scale=.85,lbp_grid=4,lbp_variant=variant)
        gallery,records={},[]
        for row in development:
            started=time.perf_counter();feature=prediction=score=None;error=''
            try:
                feature=pipeline(row['file'].read_bytes())
                if row['split']=='enroll':
                    gallery.setdefault(row['identity'],[]).append(feature)
                else:
                    prediction,score,_=match(gallery,feature)
            except ValueError as exc:
                error=str(exc)
            records.append({k:row[k] for k in ['path','identity','split','kind','pose','expression','eyes']}|{
                'detected':feature is not None,'prediction':prediction,'similarity':score,'error':error,
                'pipeline_ms':(time.perf_counter()-started)*1000})
        probes=[r for r in records if r['split']=='calibration']
        threshold,_=cmu.calibrate(probes)
        item={'backend':'yunet-06','feature_mode':'aligned-root-lbp','alignment_scale':.85,'lbp_grid':4,'lbp_variant':variant,
              'feature_profile':pipeline.profile,'feature_dimensions':pipeline.feature_dimensions,'threshold':threshold,
              'calibration':cmu.summarize(probes,threshold) if threshold is not None else None,
              'development_extraction':dict(Counter(str(r['detected']) for r in records))}
        candidates.append(item)
        target=out/'candidates'/variant;target.mkdir(parents=True)
        cmu.write_json(target/'calibration.json',item)
        cmu.write_csv(target/'development_results.csv',records,list(records[0]))
        print(json.dumps({'variant':variant,'calibration':item['calibration']}),flush=True)
    # Reject-all can meet FAR=0 while recognizing nobody; it is not a usable candidate.
    eligible=[r for r in candidates if r['threshold'] is not None and r['calibration']['known_correct']>0]
    if not eligible:
        raise ValueError('No calibrated multiscale candidate')
    order=list(MULTISCALE_BRANCHES)
    selected=min(eligible,key=lambda r:(-r['calibration']['known_correct'],r['calibration']['unknown_accepted'],
                                       r['calibration']['wrong_identity'],order.index(r['lbp_variant'])))
    result={'scope':'Previously seen CMU development comparison; not independent validation',
        'manifest_sha256':provenance['manifest_sha256'],'model_sha256':MODEL_SHA256,
        'protocol_sha256':cmu.sha256(Path(args.protocol).read_bytes()),'test_features_extracted_in_selection_stage':0,
        'selected':selected,'candidates':candidates}
    cmu.write_json(out/'selection.json',result)
    print(json.dumps({'selected':selected},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',default=str(cmu.DEFAULT_CACHE/'dataset'))
    parser.add_argument('--output-dir',required=True)
    parser.add_argument('--protocol',required=True)
    compare(parser.parse_args())
