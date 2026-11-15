"""Classroom face experiment: custom preprocessing/LBP and simulated access.

Default gallery is empty; reservations deny access by default. No liveness
detection: this experiment must not be used as production access security.
"""
import hmac
import json
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import cv2
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parents[1] / "week5" / "scripts"))
from preprocess_face import preprocess_face
from lbp_face import (extract_feature, extract_root_grid_feature, extract_multiscale_feature,
                      multiscale_dimensions, MULTISCALE_BRANCHES, match)
from face_detection import DEFAULT_DETECTOR, create_detector, crop_single_face
from face_alignment import align_single_face

DEFAULT_FEATURE_MODE = 'aligned-root-lbp'
DEFAULT_ALIGNMENT_SCALE = .85
DEFAULT_LBP_GRID = 4
DEFAULT_LBP_VARIANT = 'single'
FEATURE_MODES = ('bbox-lbp','aligned-lbp','bbox-root-lbp','aligned-root-lbp')


class FacePipeline:
    """Library detection followed by two custom image-processing stages."""
    def __init__(self, detector_backend=None, feature_mode=None, alignment_scale=None, lbp_grid=None, lbp_variant=None):
        self.detector = create_detector(detector_backend or os.environ.get('FACE_DETECTOR', DEFAULT_DETECTOR))
        self.feature_mode = feature_mode or os.environ.get('FACE_FEATURE_MODE', DEFAULT_FEATURE_MODE)
        if self.feature_mode not in FEATURE_MODES:
            raise ValueError('Invalid FACE_FEATURE_MODE')
        if self.feature_mode.startswith('aligned') and not hasattr(self.detector,'detect_faces'):
            raise ValueError('Aligned features require a landmark detector')
        mode_defaults=(DEFAULT_ALIGNMENT_SCALE,DEFAULT_LBP_GRID) if self.feature_mode=='aligned-root-lbp' else (1.0,7)
        try:
            self.alignment_scale=float(alignment_scale if alignment_scale is not None else os.environ.get('FACE_ALIGNMENT_SCALE',mode_defaults[0]))
        except (TypeError,ValueError) as exc:
            raise ValueError('Invalid FACE_ALIGNMENT_SCALE') from exc
        raw_grid=lbp_grid if lbp_grid is not None else os.environ.get('FACE_LBP_GRID',mode_defaults[1])
        try:
            grid_number=float(raw_grid)
            self.lbp_grid=int(grid_number)
        except (TypeError,ValueError,OverflowError) as exc:
            raise ValueError('Invalid FACE_LBP_GRID') from exc
        if self.alignment_scale not in (.85,1.0,1.15) or (not self.feature_mode.startswith('aligned') and self.alignment_scale!=1):
            raise ValueError('Invalid FACE_ALIGNMENT_SCALE for this feature mode')
        if grid_number!=self.lbp_grid or self.lbp_grid not in (4,7,8) or ('root' not in self.feature_mode and self.lbp_grid!=7):
            raise ValueError('Invalid FACE_LBP_GRID for this feature mode')
        variant_default=DEFAULT_LBP_VARIANT if self.feature_mode=='aligned-root-lbp' and self.lbp_grid==4 else 'single'
        self.lbp_variant=lbp_variant or os.environ.get('FACE_LBP_VARIANT',variant_default)
        if self.lbp_variant not in MULTISCALE_BRANCHES or (self.lbp_variant!='single' and (self.feature_mode!='aligned-root-lbp' or self.lbp_grid!=4)):
            raise ValueError('Invalid FACE_LBP_VARIANT for this feature mode/grid')
        self.feature_dimensions=self.lbp_grid**2*59
        if self.lbp_variant!='single':
            self.feature_dimensions=multiscale_dimensions(self.lbp_variant)
        self.profile = self.detector.profile
        if self.feature_mode != 'bbox-lbp':
            self.profile = self.profile + '-' + self.feature_mode + '-v1'
        if self.alignment_scale!=1.0 or self.lbp_grid!=7:
            self.profile+=f'-align{self.alignment_scale:g}-grid{self.lbp_grid}-v1'
        if self.lbp_variant!='single':
            self.profile+=f'-{self.lbp_variant}-v1'

    def __call__(self, content):
        if not content:
            raise ValueError("Invalid or oversized image")
        try:
            image = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
        except cv2.error as exc:
            raise ValueError("Invalid or oversized image") from exc
        if image is None or image.size > 24_000_000:
            raise ValueError("Invalid or oversized image")
        crop = (align_single_face(image,self.detector.detect_faces(image),self.alignment_scale) if self.feature_mode.startswith('aligned')
                else crop_single_face(image,self.detector.detect(image)))
        gray = preprocess_face(crop)
        if self.lbp_variant!='single':
            return extract_multiscale_feature(gray,self.lbp_variant)
        return extract_root_grid_feature(gray,self.lbp_grid) if 'root' in self.feature_mode else extract_feature(gray)


def simulation_door_control(base_url):
    """Reject hardware sources before sending any door command."""
    with urlopen(base_url + "/api/health", timeout=3) as response:
        health = json.load(response)
    if health.get("source") != "simulation" or health.get("service") != "meeting-room-sensors":
        raise ValueError("Face demo requires the unified simulation service")
    body = json.dumps({"action": "manual", "device": "door", "state": True, "source": "face-demo"}).encode()
    with urlopen(Request(base_url + "/api/control", data=body,
                         headers={"Content-Type": "application/json"}), timeout=3) as response:
        ack = json.load(response)
    if ack.get("source") != "simulation" or ack.get("success") is not True or ack.get("devices", {}).get("door_open") is not True:
        raise ValueError("Door command was not acknowledged")
    return {"acknowledged": True, "source": "simulation", "state_kind": "commanded"}


def create_app(config=None, pipeline=None, controller=None):
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        FACE_DATA_DIR=os.environ.get("FACE_DATA_DIR", str(BASE_DIR / "local_face_data")),
        FACE_ADMIN_TOKEN=os.environ.get("FACE_ADMIN_TOKEN", ""),
        FACE_THRESHOLD=os.environ.get("FACE_THRESHOLD"),
        FACE_THRESHOLD_PROFILE=os.environ.get("FACE_THRESHOLD_PROFILE", ""),
        FACE_DETECTOR=os.environ.get("FACE_DETECTOR", DEFAULT_DETECTOR),
        FACE_FEATURE_MODE=os.environ.get('FACE_FEATURE_MODE', DEFAULT_FEATURE_MODE),
        FACE_ALIGNMENT_SCALE=os.environ.get('FACE_ALIGNMENT_SCALE'),
        FACE_LBP_GRID=os.environ.get('FACE_LBP_GRID'),
        FACE_LBP_VARIANT=os.environ.get('FACE_LBP_VARIANT'),
        FACE_POLICY_PATH=os.environ.get("FACE_POLICY_PATH", ""),
        FACE_DEVICE_URL=os.environ.get("FACE_DEVICE_URL", "http://127.0.0.1:5058"),
    )
    app.config.update(config or {})
    CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
    data_dir = Path(app.config["FACE_DATA_DIR"])
    lock = threading.Lock()
    extract = pipeline or FacePipeline(app.config['FACE_DETECTOR'],app.config['FACE_FEATURE_MODE'],
                                      app.config['FACE_ALIGNMENT_SCALE'],app.config['FACE_LBP_GRID'],app.config['FACE_LBP_VARIANT'])
    # Injected test extractors do not represent a deployed calibration contract.
    profile = getattr(extract, 'profile', None)
    real_pipeline = isinstance(profile, str)
    profile = profile if real_pipeline else 'injected-test-v1'
    feature_dimensions=getattr(extract,'feature_dimensions',2891)
    feature_dimensions=feature_dimensions if isinstance(feature_dimensions,int) else 2891
    control = controller or (lambda: simulation_door_control(app.config["FACE_DEVICE_URL"]))

    def gallery():
        result = {}
        if data_dir.exists():
            for path in data_dir.glob("*.json"):
                item = json.loads(path.read_text(encoding="utf-8"))
                if item.get('feature_profile') != profile:
                    raise ValueError('人脸特征版本不匹配，请按当前检测流程重新登记和标定')
                vectors = [np.asarray(v, dtype=float) for v in item["features"]]
                if any(v.shape != (feature_dimensions,) or not np.isfinite(v).all() for v in vectors):
                    raise ValueError("Invalid gallery feature")
                result[path.stem] = vectors
        return result

    def authorized(identity, room):
        path = app.config["FACE_POLICY_PATH"]
        if not path:
            return None
        policy = json.loads(Path(path).read_text(encoding="utf-8"))
        if policy.get("mode") != "simulation":
            return None
        now = datetime.now(timezone.utc)
        for booking in policy.get("reservations", []):
            start = datetime.fromisoformat(booking["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(booking["end"].replace("Z", "+00:00"))
            if (booking["room"] == room and identity in booking["identities"]
                    and booking.get("approved") is True and start <= now < end):
                return booking["id"]
        return None

    def admin():
        token = app.config["FACE_ADMIN_TOKEN"]
        return bool(token) and hmac.compare_digest(request.headers.get("X-Face-Admin-Token", ""), token)

    def upload_feature():
        image = request.files.get("image")
        if not image or not image.filename:
            raise ValueError("Missing upload field: image")
        return extract(image.read())

    def audit(event):
        data_dir.mkdir(parents=True, exist_ok=True)
        with (data_dir / "access.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), **event}) + "\n")

    @app.get("/health")
    def health():
        return jsonify(status="ok", model_name="custom-uniform-LBP",
                       detector_backend=extract.detector.backend if real_pipeline else 'injected-test',
                       feature_profile=profile, threshold_profile=app.config['FACE_THRESHOLD_PROFILE'],
                       feature_mode=extract.feature_mode if isinstance(extract, FacePipeline) else 'injected-test',
                       feature_dimensions=feature_dimensions,
                       alignment_scale=extract.alignment_scale if isinstance(extract,FacePipeline) else None,
                       lbp_grid=extract.lbp_grid if isinstance(extract,FacePipeline) else None,
                       lbp_variant=extract.lbp_variant if isinstance(extract,FacePipeline) else None,
                       threshold=app.config["FACE_THRESHOLD"], calibrated=False,
                       mode="simulation-only", enrollment_enabled=bool(app.config["FACE_ADMIN_TOKEN"]),
                       note="Threshold requires authorized calibration; no liveness detection")

    @app.post("/api/face/verify")
    def verify():
        started = time.perf_counter()
        result = {"matched": False, "identity": None, "similarity": None,
                  "threshold": app.config["FACE_THRESHOLD"], "algorithm": "custom-uniform-LBP",
                  "access": {"allowed": False, "reason": "未匹配或未配置有效预约", "mode": "simulation"}}
        status = 200
        try:
            with lock:
                feature = upload_feature()
                threshold = app.config["FACE_THRESHOLD"]
                if threshold is None:
                    raise ValueError("尚未设置授权样本标定阈值，门禁保持关闭")
                threshold = float(threshold)
                if not 0 <= threshold <= 1:
                    raise ValueError("Invalid threshold")
                if real_pipeline and app.config['FACE_THRESHOLD_PROFILE'] != profile:
                    raise ValueError('阈值与当前人脸流程不匹配，请重新标定并设置 FACE_THRESHOLD_PROFILE')
                identity, similarity, _ = match(gallery(), feature)
                result.update(matched=identity is not None and similarity >= threshold,
                              similarity=similarity if identity else None)
                if result["matched"]:
                    result["identity"] = identity
                    booking = authorized(identity, request.form.get("room", "A101"))
                    if booking:
                        audit({"event": "simulation_intent", "identity": identity, "reservation_id": booking})
                        ack = control()
                        if ack.get("acknowledged") is not True or ack.get("source") != "simulation":
                            raise ValueError("设备未确认模拟指令")
                        # Persist the intention before issuing a success response.
                        audit({"event": "simulation_ack", "identity": identity, "reservation_id": booking})
                        result["access"].update(allowed=True, reason="预约核验通过，模拟开门指令已确认",
                                                 reservation_id=booking, device=ack, signed_in=True)
                    else:
                        result["access"]["reason"] = "识别成功，但不在当前有效预约名单中"
        except ValueError as exc:
            result["error"] = str(exc)
            result["access"]["reason"] = str(exc)
            status = 422
        except Exception:
            app.logger.exception("Face access failed")
            result["error"] = "识别、预约或设备服务异常，未确认放行"
            result["access"]["reason"] = result["error"]
            status = 503
        result["pipeline_ms"] = round((time.perf_counter() - started) * 1000, 2)
        try:
            with lock:
                audit({"matched": result["matched"], "identity": result["identity"], **result["access"],
                       "pipeline_ms": result["pipeline_ms"]})
        except OSError:
            result["access"] = {"allowed": False, "reason": "审计日志写入失败，请人工核查模拟设备", "mode": "simulation"}
            status = 503
        return jsonify(result), status

    @app.post("/api/face/enroll")
    def enroll():
        if not admin():
            return jsonify(enrolled=False, error="管理员令牌缺失或无效"), 403
        identity = request.form.get("identity", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identity) or request.form.get("consent") != "true":
            return jsonify(enrolled=False, error="需要匿名编号和有效授权确认"), 400
        try:
            with lock:
                feature = upload_feature()
                data_dir.mkdir(parents=True, exist_ok=True)
                path = data_dir / (identity + ".json")
                item = json.loads(path.read_text()) if path.exists() else {"features": [], 'feature_profile': profile}
                if item.get('feature_profile') != profile:
                    raise ValueError('旧特征版本不匹配，请先删除该身份后重新登记')
                if len(item["features"]) >= 30:
                    raise ValueError("最多保留30条特征；请先删除旧身份数据")
                item["features"].append(feature.tolist())
                temp = path.with_suffix("." + uuid.uuid4().hex + ".tmp")
                temp.write_text(json.dumps(item), encoding="utf-8")
                temp.replace(path)
            return jsonify(enrolled=True, identity=identity, samples=len(item["features"]))
        except ValueError as exc:
            return jsonify(enrolled=False, error=str(exc)), 422

    @app.delete("/api/face/enroll/<identity>")
    def delete(identity):
        if not admin():
            return jsonify(error="管理员令牌缺失或无效"), 403
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identity):
            return jsonify(error="Invalid identity"), 400
        with lock:
            (data_dir / (identity + ".json")).unlink(missing_ok=True)
        return jsonify(deleted=True)

    return app


app = create_app()
if __name__ == "__main__":
    app.run(host=os.environ.get("FACE_HOST", "127.0.0.1"), port=int(os.environ.get("FACE_API_PORT", "5001")))
