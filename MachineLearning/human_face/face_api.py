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
from lbp_face import extract_feature, match


class FacePipeline:
    """Library detection followed by two custom image-processing stages."""
    def __init__(self):
        self.detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def __call__(self, content):
        image = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
        if image is None or image.size > 24_000_000:
            raise ValueError("Invalid or oversized image")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        boxes = self.detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if len(boxes) != 1:
            raise ValueError("Exactly one detectable face is required")
        x, y, w, h = boxes[0]
        return extract_feature(preprocess_face(image[y:y+h, x:x+w]))


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
        FACE_POLICY_PATH=os.environ.get("FACE_POLICY_PATH", ""),
        FACE_DEVICE_URL=os.environ.get("FACE_DEVICE_URL", "http://127.0.0.1:5058"),
    )
    app.config.update(config or {})
    CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
    data_dir = Path(app.config["FACE_DATA_DIR"])
    lock = threading.Lock()
    extract = pipeline or FacePipeline()
    control = controller or (lambda: simulation_door_control(app.config["FACE_DEVICE_URL"]))

    def gallery():
        result = {}
        if data_dir.exists():
            for path in data_dir.glob("*.json"):
                item = json.loads(path.read_text(encoding="utf-8"))
                vectors = [np.asarray(v, dtype=float) for v in item["features"]]
                if any(v.shape != (2891,) or not np.isfinite(v).all() for v in vectors):
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
        return jsonify(status="ok", model_name="custom-uniform-LBP", detector_backend="opencv-haar",
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
                item = json.loads(path.read_text()) if path.exists() else {"features": []}
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
