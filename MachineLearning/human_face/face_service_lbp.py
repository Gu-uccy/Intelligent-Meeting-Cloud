#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
face_service_lbp.py
===================
「刷脸预约 / 刷脸开门」业务人脸服务（端口 5001）。

与综II的 `face_api.py` 的区别（这才是本学期的半自主开发成果）：
    face_api.py   : DeepFace(ArcFace) 一行调用，特征与阈值都来自库，无法解释。
    本服务        : 复用本组 week5/scripts 下自研的两个算法环节 + 自研阈值标定，
                    并把识别结果接到会议室业务（预约凭据 / 刷脸开门）。

自研环节（代码在 week5/scripts，本服务直接 import，保证「业务用的就是自研算法」）：
    ① preprocess_face.preprocess_face : 灰度化 → 双线性 resize(112) → 直方图均衡化（纯 numpy）
    ② lbp_face.extract_feature        : 均匀模式 LBP(256→59) + 7×7 分块 → 2891 维 + L2 归一化
    ③ lbp_face.match / cosine_similarity : 余弦相似度比对（一人多图取最大）
    ④ calibrate_threshold             : 用已注册样本自动标定阈值（类内/类间分离度）

调用的成熟库（报告中需列明名称/版本/用途/输入输出）：
    opencv-python-headless  : 仅用于图像解码(cv2.imdecode) + Haar 人脸检测(cv2.CascadeClassifier)
                              输入：原始图像 bytes / BGR ndarray；输出：人脸框(x,y,w,h)
    numpy                   : 特征向量与矩阵运算
    flask                   : HTTP 服务
    pymysql                 : 写人脸审计日志、核验凭据、读预约（业务闭环）

对外接口：
    GET  /health                    服务状态、底库人数、当前阈值、依赖版本
    POST /api/face/enroll           multipart: image + login_account(或 identity)
                                    注册/追加一张人脸样本（同一账号可多张）
    POST /api/face/verify           multipart: image
                                    1:N 识别（返回 matched/identity/confidence/threshold）
    POST /api/face/ticket           multipart: image + login_account + purpose=booking
                                    刷脸取得「预约凭据」，后端校验凭据后才允许下单
    POST /api/face/unlock           multipart: image + login_account + room_id
                                    刷脸开门：1:1 核身 → 查 MySQL 预约时段 → 驱动门禁 → 审计
    GET  /api/face/audit?limit=20   最近审计日志（给前端展示/答辩取证）
    GET  /api/face/gallery          已注册身份与样本数（不返回图片）

失败不放行（fail-closed）：
    未识别、身份与登录账号不一致、无有效预约、预约时段不匹配 → 一律拒绝并写审计日志，
    只有全部条件满足才调用门禁接口。
"""

import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS

# ----------------------------------------------------------------------------
# 0. 自研算法模块加载（week5/scripts，保持唯一实现，不在本文件复制一份）
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent            # .../MachineLearning/human_face
REPO_ROOT = BASE_DIR.parents[1]                       # .../Intelligent-Meeting-Cloud-main
SELFDEV_DIR = REPO_ROOT / "week5" / "scripts"


def _load_selfdev(module_name, file_name):
    """按文件路径加载 week5/scripts 下的自研模块（目录名含数字，不适合常规 import）。"""
    path = SELFDEV_DIR / file_name
    if not path.exists():
        raise RuntimeError("找不到自研算法模块：%s" % path)
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


preprocess_mod = _load_selfdev("selfdev_preprocess_face", "preprocess_face.py")
lbp_mod = _load_selfdev("selfdev_lbp_face", "lbp_face.py")

preprocess_face = preprocess_mod.preprocess_face       # 自研环节①
extract_feature = lbp_mod.extract_feature              # 自研环节②
cosine_similarity = lbp_mod.cosine_similarity          # 自研环节③

# 成熟库（检测/解码）
import cv2  # noqa: E402

# ----------------------------------------------------------------------------
# 1. 配置
# ----------------------------------------------------------------------------
FACE_DB_PATH = Path(os.environ.get("FACE_DB_PATH", BASE_DIR / "id")).resolve()
FACE_API_PORT = int(os.environ.get("FACE_API_PORT", "5001"))
THRESHOLD_DEFAULT = float(os.environ.get("FACE_THRESHOLD", "0.80"))
DEFAULT_THRESHOLD_MIN = float(os.environ.get("FACE_THRESHOLD_MIN", "0.65"))
DEFAULT_THRESHOLD_MAX = float(os.environ.get("FACE_THRESHOLD_MAX", "0.95"))
# 类间上界之外再留的安全边际（防止「最像的陌生人」被放进来）
INTER_MARGIN = float(os.environ.get("FACE_INTER_MARGIN", "0.06"))
GRACE_MINUTES = int(os.environ.get("FACE_ACCESS_GRACE_MINUTES", "10"))
# 默认要求「必须检测到人脸」——检测不到就拒绝（fail-closed）。
# 现场若因摄像头角度导致检测不稳，可临时设 FACE_REQUIRE_FACE=0 做演示，报告里需说明。
REQUIRE_FACE = os.environ.get("FACE_REQUIRE_FACE", "1") == "1"
TICKET_TTL_SECONDS = int(os.environ.get("FACE_TICKET_TTL", "300"))
SENSOR_BASE = os.environ.get("FACE_SENSOR_BASE", "http://127.0.0.1:5058")

MYSQL = {
    "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.environ.get("MYSQL_PORT", "3307")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DB", "meeting_room_db"),
    "charset": "utf8mb4",
    "cursorclass": None,       # 延迟设置，避免无 pymysql 环境启动失败
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
IDENTITY_RE = re.compile(r"[^A-Za-z0-9_.@-]+")

app = Flask(__name__)
CORS(app)

detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# 内存特征缓存： {identity: [(path, mtime, feature), ...]}
_feature_cache = {}
_threshold_state = {"value": THRESHOLD_DEFAULT, "source": "default", "detail": "尚未标定"}


# ----------------------------------------------------------------------------
# 2. 工具函数
# ----------------------------------------------------------------------------
def log(msg):
    print("[face %s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)


def normalize_identity(value):
    """身份名归一化：登录账号可直接作为身份名；非法字符替换为下划线。"""
    raw = str(value or "").strip()
    identity = IDENTITY_RE.sub("_", raw).strip("_")
    return identity[:64]


def db_connect():
    import pymysql

    kwargs = dict(MYSQL)
    kwargs["cursorclass"] = pymysql.cursors.DictCursor
    return pymysql.connect(**kwargs)


def db_execute(sql, params=None, fetch=False):
    """执行 SQL；失败不抛异常（审计日志不能阻断主流程），但会打印。"""
    try:
        conn = db_connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                rows = cur.fetchall() if fetch else None
            conn.commit()
            return rows
        finally:
            conn.close()
    except Exception as exc:                                  # noqa: BLE001
        log("MySQL 操作失败：%s | sql=%s" % (exc, sql.split("\n")[0][:80]))
        return None


def audit(event, matched, login_account=None, confidence=None, threshold=None,
          room_id=None, detail=None):
    """人脸审计日志：每次识别/注册/开门都落库，满足任务书「日志与审计」。"""
    db_execute(
        "INSERT INTO face_audit_log(event, login_account, matched, confidence, threshold,"
        " room_id, detail, client_ip) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (event, login_account, 1 if matched else 0, confidence, threshold, room_id,
         (detail or "")[:255], request.remote_addr if request else None),
    )


def decode_image(file_storage):
    data = file_storage.read()
    if not data:
        return None
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img


def detect_largest_face(image_bgr):
    """Haar 检测最大人脸；返回 (face_bgr, box)。检测不到时返回 (None, None)。"""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                      minSize=(48, 48))
    if len(faces) == 0:
        return None, None
    x, y, w, h = max(faces, key=lambda f: int(f[2]) * int(f[3]))
    pad = int(0.12 * max(w, h))
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(image_bgr.shape[1], x + w + pad), min(image_bgr.shape[0], y + h + pad)
    return image_bgr[y0:y1, x0:x1], (int(x), int(y), int(w), int(h))


def face_feature(image_bgr):
    """自研链路：检测裁剪 → 预处理 → LBP 特征。返回 (feature, meta)。"""
    face, box = detect_largest_face(image_bgr)
    meta = {"detected": face is not None, "box": box}
    if face is None:
        if REQUIRE_FACE:
            return None, meta
        face = image_bgr            # 回退：整图当人脸（仍会记录 detected=False）
    processed = preprocess_face(face)          # 自研①：灰度 + 112×112 + 均衡化
    feat = extract_feature(processed)          # 自研②：7×7×59 = 2891 维
    meta["feature_dim"] = int(feat.shape[0])
    return feat, meta


def identity_dir(identity):
    return FACE_DB_PATH / identity


def gallery_features(force=False):
    """加载底库特征（带 mtime 缓存）。返回 {identity: [np.ndarray, ...]}"""
    gallery = {}
    if not FACE_DB_PATH.exists():
        return gallery
    for person_dir in sorted(FACE_DB_PATH.iterdir()):
        if not person_dir.is_dir():
            continue
        identity = person_dir.name
        feats = []
        for img_path in sorted(person_dir.iterdir()):
            if img_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            try:
                mtime = img_path.stat().st_mtime
            except OSError:
                continue
            cache = _feature_cache.setdefault(identity, {})
            entry = cache.get(str(img_path))
            if force or not entry or entry[0] != mtime:
                img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
                if img is None:
                    continue
                feat, _ = face_feature(img)
                if feat is None:
                    continue
                cache[str(img_path)] = (mtime, feat)
                entry = cache[str(img_path)]
            feats.append(entry[1])
        if feats:
            gallery[identity] = feats
    return gallery


def calibrate_threshold(gallery=None):
    """用已注册样本自动标定阈值（自研环节④）。

    原则：安全优先（fail-closed）。任务书要求「在 FAR≤0.05 前提下 FRR 最小」，
    小样本下无法直接估计 5% 分位，因此采用「类间上界 + 安全边际」：

        有 ≥2 个身份：θ = max(类间相似度) + 安全边际(默认 0.06)
                      → 边际保证任何「已知他人」都不会被放进（FAR 优先）
        只有 1 个身份：θ = 类内均值 − 0.8×类内标准差（无类间样本，只能按本人波动估）
        样本不足    ：用默认 0.80（保守）

    若 θ 高于类内最小值，说明存在「同一人被增强得差异过大」的样本，
    会把该情况写进 detail 作为数据质量提示，但不为了降 FRR 而牺牲 FAR。
    """
    gallery = gallery if gallery is not None else gallery_features()
    intra, inter = [], []
    identities = list(gallery.keys())
    for identity, feats in gallery.items():
        for i in range(len(feats)):
            for j in range(i + 1, len(feats)):
                intra.append(cosine_similarity(feats[i], feats[j]))
    for a in range(len(identities)):
        for b in range(a + 1, len(identities)):
            for fa in gallery[identities[a]]:
                for fb in gallery[identities[b]]:
                    inter.append(cosine_similarity(fa, fb))

    if inter and intra:
        inter_max = float(max(inter))
        intra_min = float(min(intra))
        candidate = inter_max + INTER_MARGIN
        source = "calibrated-inter-margin"
        detail = ("类间 max=%.4f mean=%.4f n=%d | 类内 min=%.4f mean=%.4f n=%d | θ=类间max+%.2f"
                  % (inter_max, float(np.mean(inter)), len(inter),
                     intra_min, float(np.mean(intra)), len(intra), INTER_MARGIN))
        if candidate > intra_min:
            detail += (" | 警告：θ 高于类内最小值，说明有同人样本差异过大"
                       "（可能增强过强/侧脸），建议补充更稳定的正面样本")
    elif intra:
        intra_mean = float(np.mean(intra))
        intra_std = float(np.std(intra))
        candidate = intra_mean - 0.8 * intra_std
        source = "calibrated-intra-only"
        detail = ("仅 1 个身份，无类间样本：类内 mean=%.4f std=%.4f n=%d | "
                  "θ=mean-0.8*std（需补第 2 个人才能做类间校验）"
                  % (intra_mean, intra_std, len(intra)))
    else:
        _threshold_state.update(value=THRESHOLD_DEFAULT, source="default",
                                detail="每人样本不足 2 张，无法标定，用默认值 %.2f"
                                       % THRESHOLD_DEFAULT)
        return _threshold_state

    value = float(min(DEFAULT_THRESHOLD_MAX, max(DEFAULT_THRESHOLD_MIN, candidate)))
    if abs(value - candidate) > 1e-9:
        detail += " | 已按 [%.2f, %.2f] 截断" % (DEFAULT_THRESHOLD_MIN,
                                                DEFAULT_THRESHOLD_MAX)
    _threshold_state.update(value=round(value, 4), source=source, detail=detail)
    return _threshold_state


def current_threshold():
    return float(_threshold_state["value"])


# ----------------------------------------------------------------------------
# 3. 传感器/门禁联动
# ----------------------------------------------------------------------------
def sensor_control_door(opened, source="face-access"):
    """调用传感器服务 /api/control 驱动门禁（硬件层）。返回 (ok, payload)。"""
    body = json.dumps({
        "action": "manual",
        "device": "door",
        "state": bool(opened),
        "source": source,
    }).encode("utf-8")
    req = urllib.request.Request(
        SENSOR_BASE.rstrip("/") + "/api/control",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8") or "{}")
        return True, payload
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        log("门禁联动失败：%s" % exc)
        return False, {"error": str(exc)}


def sensor_light(state, brightness=None, source="face-access"):
    body = json.dumps({
        "action": "manual",
        "device": "lighting",
        "state": bool(state),
        "brightness": brightness if brightness is not None else (100 if state else 0),
        "source": source,
    }).encode("utf-8")
    req = urllib.request.Request(
        SENSOR_BASE.rstrip("/") + "/api/control",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return True, json.loads(resp.read().decode("utf-8") or "{}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return False, {"error": str(exc)}


# ----------------------------------------------------------------------------
# 4. 业务查询：当前用户在该会议室是否有「正在生效」的预约
# ----------------------------------------------------------------------------
def find_active_reservation(login_account, room_id):
    rows = db_execute(
        "SELECT r.id, r.reservation_no, r.room_id, r.start_time, r.end_time, r.status,"
        "       r.meeting_topic, m.room_code"
        " FROM reservation r"
        " JOIN user u ON u.id = r.user_id"
        " JOIN meeting_room m ON m.id = r.room_id"
        " WHERE u.login_account = %s AND r.room_id = %s AND r.status IN (0, 1)"
        "   AND r.start_time <= DATE_ADD(NOW(), INTERVAL %s MINUTE)"
        "   AND r.end_time   >= DATE_SUB(NOW(), INTERVAL %s MINUTE)"
        " ORDER BY r.start_time DESC LIMIT 1",
        (login_account, room_id, GRACE_MINUTES, GRACE_MINUTES),
        fetch=True,
    )
    return rows[0] if rows else None


# ----------------------------------------------------------------------------
# 5. 路由
# ----------------------------------------------------------------------------
@app.get("/health")
def health():
    gallery = gallery_features()
    return jsonify({
        "status": "ok",
        "service": "face-recognition-selfdev",
        "algorithm": "selfdev uniform-LBP 7x7x59 + cosine + auto threshold",
        "gallery_identities": len(gallery),
        "gallery_faces": sum(len(v) for v in gallery.values()),
        "threshold": current_threshold(),
        "threshold_source": _threshold_state["source"],
        "threshold_detail": _threshold_state["detail"],
        "db_path": str(FACE_DB_PATH),
        "dependencies": {
            "opencv": cv2.__version__,
            "numpy": np.__version__,
        },
        "require_face_detection": REQUIRE_FACE,
        "sensor_base": SENSOR_BASE,
        "grace_minutes": GRACE_MINUTES,
    })


def _read_upload():
    if "image" not in request.files:
        return None, (jsonify({"matched": False, "error": "缺少上传字段 image"}), 400)
    file = request.files["image"]
    if not file.filename:
        return None, (jsonify({"matched": False, "error": "文件名为空"}), 400)
    if Path(file.filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        return None, (jsonify({"matched": False, "error": "不支持的图片格式"}), 400)
    img = decode_image(file)
    if img is None:
        return None, (jsonify({"matched": False, "error": "图片解码失败"}), 400)
    return img, None


@app.post("/api/face/enroll")
def enroll():
    img, error = _read_upload()
    if error:
        return error
    identity = normalize_identity(
        request.form.get("login_account")
        or request.form.get("identity")
        or request.form.get("username")
    )
    if not identity:
        return jsonify({"enrolled": False, "error": "缺少 login_account/identity"}), 400

    feat, meta = face_feature(img)
    if feat is None:
        audit("enroll", False, identity, detail="未检测到人脸（enroll）")
        return jsonify({"enrolled": False, "error": "未检测到人脸，请正对摄像头重试"}), 422

    # 防重复注册：这张脸是否已经是别人？(同类间上界比较，防止一人多账号刷权限)
    gallery_now = gallery_features()
    duplicate_of, duplicate_sim = None, -1.0
    for other_identity, feats in gallery_now.items():
        if other_identity == identity:
            continue
        sim = float(max(cosine_similarity(feat, f) for f in feats))
        if sim > duplicate_sim:
            duplicate_of, duplicate_sim = other_identity, sim
    if duplicate_of and duplicate_sim >= current_threshold():
        audit("enroll", False, identity, duplicate_sim, current_threshold(),
              detail="疑似重复注册：与 %s 相似" % duplicate_of)
        return jsonify({
            "enrolled": False,
            "error": "这张人脸已注册为账号 %s（相似度 %.4f），请勿重复注册" % (
                duplicate_of, duplicate_sim),
            "duplicate_of": duplicate_of,
            "confidence": round(duplicate_sim, 4),
            "threshold": current_threshold(),
        }), 409

    target_dir = identity_dir(identity)
    target_dir.mkdir(parents=True, exist_ok=True)
    existing = [p for p in target_dir.iterdir()
                if p.suffix.lower() in ALLOWED_EXTENSIONS]
    if len(existing) >= 12:                     # 每人最多保留 12 张，避免底库无限膨胀
        existing.sort(key=lambda p: p.stat().st_mtime)
        existing[0].unlink(missing_ok=True)
    index = len([p for p in target_dir.iterdir()
                 if p.suffix.lower() in ALLOWED_EXTENSIONS]) + 1
    target = target_dir / ("%s_%02d.jpg" % (identity, index))
    cv2.imwrite(str(target), img)

    gallery = gallery_features(force=False)
    calibration = calibrate_threshold(gallery)
    audit("enroll", True, identity, detail="注册成功 %s" % target.name)
    log("注册 %s -> %s（阈值 %.4f）" % (identity, target.name, calibration["value"]))
    return jsonify({
        "enrolled": True,
        "identity": identity,
        "file": target.name,
        "faces_for_identity": len(gallery.get(identity, [])),
        "threshold": calibration["value"],
        "threshold_source": calibration["source"],
        "detected": meta["detected"],
    })


@app.post("/api/face/verify")
def verify():
    img, error = _read_upload()
    if error:
        return error
    feat, meta = face_feature(img)
    threshold = current_threshold()
    if feat is None:
        audit("verify", False, None, threshold=threshold, detail="未检测到人脸（verify）")
        return jsonify({"matched": False, "error": "未检测到人脸", "threshold": threshold}), 422

    gallery = gallery_features()
    if not gallery:
        audit("verify", False, None, threshold=threshold, detail="底库为空")
        return jsonify({"matched": False, "error": "人脸底库为空，请先注册", "threshold": threshold}), 409

    best_identity, best_sim = None, -1.0
    per_identity = {}
    for identity, feats in gallery.items():
        sim = max(cosine_similarity(feat, f) for f in feats)
        per_identity[identity] = round(float(sim), 4)
        if sim > best_sim:
            best_identity, best_sim = identity, float(sim)

    matched = best_sim >= threshold
    audit("verify", matched, best_identity, best_sim, threshold,
          detail="检测=%s 维度=%s" % (meta["detected"], meta.get("feature_dim")))
    return jsonify({
        "matched": matched,
        "identity": best_identity if matched else None,
        "best_candidate": best_identity,
        "confidence": round(best_sim, 4),
        # 每个身份的最高相似度：便于 1:1 核身指标（FAR/FRR）离线复算与排障
        "scores": per_identity,
        "threshold": threshold,
        "threshold_source": _threshold_state["source"],
        "detected": meta["detected"],
        "gallery_identities": len(gallery),
    })


@app.post("/api/face/ticket")
def issue_ticket():
    """刷脸换「预约凭据」：1:1 核身（识别身份必须等于当前登录账号）。"""
    img, error = _read_upload()
    if error:
        return error
    account = normalize_identity(
        request.form.get("login_account") or request.form.get("identity"))
    purpose = (request.form.get("purpose") or "booking").strip()
    if not account:
        return jsonify({"granted": False, "error": "缺少 login_account"}), 400

    feat, meta = face_feature(img)
    threshold = current_threshold()
    if feat is None:
        audit("deny", False, account, threshold=threshold, detail="刷脸取票：未检测到人脸")
        return jsonify({"granted": False, "error": "未检测到人脸", "threshold": threshold}), 422

    gallery = gallery_features()
    feats = gallery.get(account)
    if not feats:
        audit("deny", False, account, threshold=threshold,
              detail="该账号未注册人脸，禁止取票")
        return jsonify({"granted": False, "error": "当前账号未注册人脸，请先录入",
                        "threshold": threshold}), 403

    sim = max(cosine_similarity(feat, f) for f in feats)
    if sim < threshold:
        audit("deny", False, account, float(sim), threshold,
              detail="刷脸取票失败：相似度低于阈值")
        return jsonify({"granted": False, "error": "人脸与当前账号不匹配",
                        "confidence": round(float(sim), 4), "threshold": threshold}), 403

    ticket = uuid.uuid4().hex
    expire_at = datetime.now() + timedelta(seconds=TICKET_TTL_SECONDS)
    db_execute(
        "INSERT INTO face_verification(ticket, login_account, purpose, confidence, expire_at)"
        " VALUES (%s,%s,%s,%s,%s)",
        (ticket, account, purpose, round(float(sim), 4), expire_at),
    )
    audit("verify", True, account, float(sim), threshold, detail="签发凭据 purpose=%s" % purpose)
    log("签发凭据 %s -> %s(%s) sim=%.4f" % (ticket[:8], account, purpose, sim))
    return jsonify({
        "granted": True,
        "ticket": ticket,
        "login_account": account,
        "purpose": purpose,
        "confidence": round(float(sim), 4),
        "threshold": threshold,
        "expire_at": expire_at.strftime("%Y-%m-%d %H:%M:%S"),
        "ttl_seconds": TICKET_TTL_SECONDS,
    })


@app.post("/api/face/unlock")
def unlock():
    """刷脸开门：1:1 核身 → 预约时段校验 → 驱动门禁 → 3D 门随之打开（前端轮询）。"""
    img, error = _read_upload()
    if error:
        return error
    account = normalize_identity(
        request.form.get("login_account") or request.form.get("identity"))
    room_id_raw = request.form.get("room_id")
    try:
        room_id = int(room_id_raw)
    except (TypeError, ValueError):
        return jsonify({"granted": False, "error": "缺少或非法的 room_id"}), 400
    if not account:
        return jsonify({"granted": False, "error": "缺少 login_account"}), 400

    feat, meta = face_feature(img)
    threshold = current_threshold()
    if feat is None:
        audit("deny", False, account, threshold=threshold, room_id=room_id,
              detail="刷脸开门：未检测到人脸")
        return jsonify({"granted": False, "door_open": False, "error": "未检测到人脸"}), 422

    gallery = gallery_features()
    feats = gallery.get(account)
    if not feats:
        audit("deny", False, account, threshold=threshold, room_id=room_id,
              detail="账号未注册人脸")
        return jsonify({"granted": False, "door_open": False,
                        "error": "当前账号未注册人脸"}), 403

    sim = float(max(cosine_similarity(feat, f) for f in feats))
    if sim < threshold:
        audit("deny", False, account, sim, threshold, room_id,
              detail="核身失败：相似度 %.4f < 阈值 %.4f" % (sim, threshold))
        return jsonify({"granted": False, "door_open": False,
                        "error": "人脸与当前账号不匹配",
                        "confidence": round(sim, 4), "threshold": threshold}), 403

    reservation = find_active_reservation(account, room_id)
    if not reservation:
        audit("deny", False, account, sim, threshold, room_id,
              detail="无当前时段有效预约（房间 %s）" % room_id)
        return jsonify({
            "granted": False, "door_open": False,
            "error": "当前时段没有该会议室的有效预约，门禁保持关闭",
            "confidence": round(sim, 4), "threshold": threshold,
        }), 403

    ok, sensor_payload = sensor_control_door(True, source="face-access")
    if not ok:
        audit("deny", True, account, sim, threshold, room_id,
              detail="预约有效但门禁驱动失败")
        return jsonify({
            "granted": False, "door_open": False,
            "error": "预约有效，但门禁硬件驱动失败：%s" % sensor_payload.get("error"),
            "reservation": reservation,
        }), 502

    ticket = uuid.uuid4().hex
    db_execute(
        "INSERT INTO face_verification(ticket, login_account, purpose, room_id,"
        " confidence, expire_at) VALUES (%s,%s,%s,%s,%s,%s)",
        (ticket, account, "access", room_id, round(sim, 4),
         datetime.now() + timedelta(seconds=120)),
    )
    audit("access", True, account, sim, threshold, room_id,
          detail="开门成功 预约%s" % reservation.get("reservation_no"))
    log("开门成功 %s @room=%s 预约=%s sim=%.4f" % (
        account, room_id, reservation.get("reservation_no"), sim))
    return jsonify({
        "granted": True,
        "door_open": True,
        "identity": account,
        "confidence": round(sim, 4),
        "threshold": threshold,
        "room_id": room_id,
        "room_code": reservation.get("room_code"),
        "reservation_no": reservation.get("reservation_no"),
        "window": {
            "start_time": str(reservation.get("start_time")),
            "end_time": str(reservation.get("end_time")),
            "grace_minutes": GRACE_MINUTES,
        },
        "ticket": ticket,
        "sensor": sensor_payload,
    })


@app.post("/api/face/lock")
def lock():
    """手动关门（3D 门同步关闭）。"""
    ok, payload = sensor_control_door(False, source="face-access")
    return jsonify({"locked": ok, "sensor": payload}), (200 if ok else 502)


@app.post("/api/face/light")
def light():
    """刷脸开门后的灯光联动（可选）：开门成功后可自动开灯。"""
    state = request.form.get("state", "true").lower() != "false"
    ok, payload = sensor_light(state, source="face-access")
    return jsonify({"lighting": state, "ok": ok, "sensor": payload}), (200 if ok else 502)


@app.get("/api/face/audit")
def audit_list():
    limit = min(int(request.args.get("limit", 20)), 100)
    rows = db_execute(
        "SELECT id, event, login_account, matched, confidence, threshold, room_id,"
        " detail, create_time FROM face_audit_log ORDER BY id DESC LIMIT %s",
        (limit,), fetch=True,
    )
    return jsonify({"items": rows or []})


@app.get("/api/face/gallery")
def gallery_list():
    gallery = gallery_features()
    return jsonify({
        "threshold": current_threshold(),
        "threshold_source": _threshold_state["source"],
        "identities": [{"identity": k, "faces": len(v),
                        "files": [str(p) for p in identity_dir(k).iterdir()
                                  if p.suffix.lower() in ALLOWED_EXTENSIONS]}
                       for k, v in gallery.items()],
    })


@app.post("/api/face/recalibrate")
def recalibrate():
    calibration = calibrate_threshold()
    return jsonify({"threshold": calibration["value"],
                    "source": calibration["source"],
                    "detail": calibration["detail"]})


def _bootstrap():
    FACE_DB_PATH.mkdir(parents=True, exist_ok=True)
    log("底库目录：%s" % FACE_DB_PATH)
    gallery = gallery_features()
    log("已加载 %d 个身份 / %d 张人脸" % (len(gallery), sum(len(v) for v in gallery.values())))
    calibration = calibrate_threshold(gallery)
    log("阈值 %.4f（%s）：%s" % (calibration["value"], calibration["source"],
                                calibration["detail"]))


if __name__ == "__main__":
    _bootstrap()
    log("监听 http://0.0.0.0:%d  传感器服务=%s" % (FACE_API_PORT, SENSOR_BASE))
    app.run(host="0.0.0.0", port=FACE_API_PORT, debug=False, use_reloader=False)
