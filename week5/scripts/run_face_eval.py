"""Leak-free face evaluation. Synthetic tests never represent real accuracy.

Real data: --manifest CSV --data-dir AUTHORIZED_ROOT --authorized
CSV columns: path,identity,split (enroll/calibration/test),kind (known/unknown).
Unknown identities must never occur in enrollment. Calibrate and test separately.
"""
import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
from lbp_face import match

THRESHOLDS = [round(x / 100, 2) for x in range(50, 101, 5)]


def synthetic_gallery_and_probes(seed=7):
    rng = np.random.default_rng(seed)
    gallery, known, unknown = {}, [], []
    for identity in ("A01", "A02", "A03"):
        proto = rng.normal(size=128)
        proto /= np.linalg.norm(proto)
        vectors = []
        for _ in range(15):
            v = proto + rng.normal(0, .08, 128)
            vectors.append(v / np.linalg.norm(v))
        gallery[identity] = vectors[:10]
        known.extend((identity, v) for v in vectors[10:])
    for _ in range(15):
        v = rng.normal(size=128)
        unknown.append(("UNKNOWN", v / np.linalg.norm(v)))
    return gallery, known, unknown


def metrics(gallery, known, unknown, threshold):
    correct = rejected = wrong_identity = false_accept = 0
    for identity, vec in known:
        best, score, _ = match(gallery, vec)
        if score < threshold:
            rejected += 1
        elif best == identity:
            correct += 1
        else:
            wrong_identity += 1
    for _, vec in unknown:
        _, score, _ = match(gallery, vec)
        false_accept += int(score >= threshold)
    total = len(known) + len(unknown)
    return {"accuracy": (correct + len(unknown) - false_accept) / total if total else None,
            "far": false_accept / len(unknown) if unknown else None,
            "frr": rejected / len(known) if known else None,
            "known_correct": correct, "known_rejected": rejected,
            "wrong_identity": wrong_identity, "unknown_accepted": false_accept,
            "unknown_rejected": len(unknown) - false_accept,
            "known_count": len(known), "unknown_count": len(unknown)}


def read_manifest(root, manifest):
    root = Path(root).resolve()
    with Path(manifest).open(encoding="utf-8-sig") as manifest_file:
        rows = list(csv.DictReader(manifest_file))
    if not rows:
        raise ValueError("Empty manifest")
    seen = set()
    for row in rows:
        if row["split"] not in {"enroll", "calibration", "test"} or row["kind"] not in {"known", "unknown"}:
            raise ValueError("Invalid split/kind")
        path = (root / row["path"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Image must be inside the authorized root")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:
            raise ValueError("Duplicate image content across manifest rows")
        seen.add(digest)
        row["file"] = path
    enrolled = {r["identity"] for r in rows if r["split"] == "enroll"}
    unknown = {r["identity"] for r in rows if r["kind"] == "unknown"}
    if len(enrolled) < 3 or enrolled & unknown or any(r["split"] == "enroll" and r["kind"] != "known" for r in rows):
        raise ValueError("Need >=3 enrolled people and completely separate unknown identities")
    for person in enrolled:
        person_rows = [r for r in rows if r["identity"] == person]
        if len(person_rows) < 10 or any(not any(r["split"] == split for r in person_rows) for split in ("enroll", "calibration", "test")):
            raise ValueError("Each known person needs >=10 photos and all three splits")
    if any(r["kind"] == "known" and r["identity"] not in enrolled for r in rows):
        raise ValueError("Known probe has no enrollment")
    for split in ("calibration", "test"):
        if not any(r["split"] == split and r["kind"] == "unknown" for r in rows):
            raise ValueError("Both calibration and test require unknown probes")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir")
    parser.add_argument("--manifest")
    parser.add_argument("--authorized", action="store_true", help="Confirm a recorded authorization/license exists")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output-dir", required=True, help="Use a fresh directory; do not overwrite historical evidence")
    args = parser.parse_args()
    timings = []
    if args.data_dir or args.manifest:
        if not (args.data_dir and args.manifest and args.authorized):
            parser.error("Real evaluation requires --data-dir, --manifest and --authorized")
        rows = read_manifest(args.data_dir, args.manifest)
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "MachineLearning" / "human_face"))
        from face_api import FacePipeline
        pipeline = FacePipeline()
        gallery = {}
        probes = {"calibration": {"known": [], "unknown": []}, "test": {"known": [], "unknown": []}}
        for row in rows:
            if row["split"] == "enroll":
                gallery.setdefault(row["identity"], []).append(pipeline(row["file"].read_bytes()))
        for row in rows:
            if row["split"] != "enroll":
                start = time.perf_counter()
                # Disk read + face detection + custom preprocessing + LBP + matching.
                feature = pipeline(row["file"].read_bytes())
                match(gallery, feature)
                timings.append((time.perf_counter() - start) * 1000)
                probes[row["split"]][row["kind"]].append((row["identity"], feature))
        mode = "authorized_real"
    else:
        gallery, known, unknown = synthetic_gallery_and_probes()
        # Independent seed for test; self-test checks logic, not face performance.
        _, _, test_unknown = synthetic_gallery_and_probes(seed=19)
        probes = {"calibration": {"known": [p for i, p in enumerate(known) if i % 5 < 3], "unknown": unknown[:9]},
                  "test": {"known": [p for i, p in enumerate(known) if i % 5 >= 3], "unknown": test_unknown}}
        mode = "synthetic_logic_only"
    calibration = {str(t): metrics(gallery, **probes["calibration"], threshold=t) for t in THRESHOLDS}
    candidates = [t for t in THRESHOLDS if calibration[str(t)]["far"] is not None and calibration[str(t)]["far"] <= .05]
    best = min(candidates, key=lambda t: (calibration[str(t)]["frr"], calibration[str(t)]["wrong_identity"], -t)) if candidates else None
    payload = {"mode": mode, "device": {"platform": platform.platform(), "machine": platform.machine()},
               "calibration": calibration, "selected_threshold": best,
               "held_out_test": metrics(gallery, **probes["test"], threshold=best) if best is not None else None,
               "pipeline_latency_ms": {"mean": float(np.mean(timings)), "samples": timings} if timings else None,
               "latency_scope": "disk + detection + preprocessing + LBP + matching; excludes HTTP/device control",
               "note": "Synthetic results are not real face accuracy or target-device latency. No acceptable calibration => no release."}
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    target = out / "face_eval_result.json"
    if target.exists():
        raise SystemExit("Output already exists; choose a fresh directory")
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
