import os
import re
import tempfile
from pathlib import Path

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"

from deepface import DeepFace
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("FACE_DB_PATH", BASE_DIR / "id")).resolve()
MODEL_NAME = os.environ.get("FACE_MODEL_NAME", "ArcFace")
DETECTOR_BACKEND = os.environ.get("FACE_DETECTOR", "retinaface")
DISTANCE_METRIC = os.environ.get("FACE_DISTANCE_METRIC", "cosine")
THRESHOLD = float(os.environ.get("FACE_THRESHOLD", "0.8"))

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

app = Flask(__name__)
CORS(app)


def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def normalize_identity(value):
    raw_value = str(value or "").strip()
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw_value).strip("_")
    return normalized[:64]


def clear_deepface_cache():
    for cache_file in DB_PATH.glob("*.pkl"):
        try:
            cache_file.unlink()
        except OSError:
            pass


def save_upload_to_temp(image):
    suffix = Path(secure_filename(image.filename)).suffix.lower()
    with tempfile.NamedTemporaryFile(prefix="face_", suffix=suffix, delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        image.save(temp_file)
    return temp_path, suffix


def read_face_upload():
    if "image" not in request.files:
        return None, None, (jsonify({
            "matched": False,
            "error": "Missing upload field: image",
        }), 400)

    image = request.files["image"]
    if not image.filename:
        return None, None, (jsonify({
            "matched": False,
            "error": "Empty filename",
        }), 400)

    if not allowed_file(image.filename):
        return None, None, (jsonify({
            "matched": False,
            "error": "Unsupported image type",
        }), 400)

    return image, Path(secure_filename(image.filename)).suffix.lower(), None


def find_best_match(image_path):
    dfs = DeepFace.find(
        img_path=str(image_path),
        db_path=str(DB_PATH),
        model_name=MODEL_NAME,
        detector_backend=DETECTOR_BACKEND,
        distance_metric=DISTANCE_METRIC,
        threshold=THRESHOLD,
        enforce_detection=True,
    )

    if not dfs or dfs[0].empty:
        return {
            "matched": False,
            "identity": None,
            "distance": None,
            "threshold": THRESHOLD,
        }

    best_match = dfs[0].iloc[0]
    return {
        "matched": True,
        "identity": str(best_match["identity"]),
        "distance": float(best_match["distance"]),
        "threshold": THRESHOLD,
    }


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "db_path": str(DB_PATH),
        "model_name": MODEL_NAME,
        "detector_backend": DETECTOR_BACKEND,
        "distance_metric": DISTANCE_METRIC,
        "threshold": THRESHOLD,
    })


@app.post("/api/face/verify")
def verify_face():
    image, _, error_response = read_face_upload()
    if error_response:
        return error_response

    try:
        temp_path, _ = save_upload_to_temp(image)
        result = find_best_match(temp_path)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({
            "matched": False,
            "error": str(exc),
        }), 422
    except Exception as exc:
        return jsonify({
            "matched": False,
            "error": f"Face verification failed: {exc}",
        }), 500
    finally:
        if "temp_path" in locals() and temp_path.exists():
            temp_path.unlink()


@app.post("/api/face/enroll")
def enroll_face():
    image, suffix, error_response = read_face_upload()
    if error_response:
        return error_response

    identity = normalize_identity(
        request.form.get("identity")
        or request.form.get("login_account")
        or request.form.get("username")
        or request.form.get("user_id")
    )
    if not identity:
        return jsonify({
            "enrolled": False,
            "error": "Missing identity, login_account, username, or user_id",
        }), 400

    try:
        DB_PATH.mkdir(parents=True, exist_ok=True)
        temp_path, suffix = save_upload_to_temp(image)

        DeepFace.extract_faces(
            img_path=str(temp_path),
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True,
        )

        for old_file in DB_PATH.glob(f"{identity}.*"):
            if old_file.suffix.lower() in ALLOWED_EXTENSIONS:
                old_file.unlink()

        target_path = DB_PATH / f"{identity}{suffix or '.jpg'}"
        target_path.write_bytes(temp_path.read_bytes())
        clear_deepface_cache()

        return jsonify({
            "enrolled": True,
            "identity": identity,
            "file": str(target_path),
            "db_path": str(DB_PATH),
        })
    except ValueError as exc:
        return jsonify({
            "enrolled": False,
            "error": str(exc),
        }), 422
    except Exception as exc:
        return jsonify({
            "enrolled": False,
            "error": f"Face enrollment failed: {exc}",
        }), 500
    finally:
        if "temp_path" in locals() and temp_path.exists():
            temp_path.unlink()


if __name__ == "__main__":
    port = int(os.environ.get("FACE_API_PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=False)
