#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
face_dataset_selftest.py
========================
自研人脸链路的可复现识别测试（真实人脸照片，不是合成特征向量）。

数据来源（公开示例照片，已脱敏，仅用于算法验证）：
    A 身份：scikit-image 内置 astronaut（NASA 公开照片）
    B 身份：matplotlib 内置 grace_hopper（美国海军公开照片）
    负样本：scikit-image 内置 coffee / chelsea（无人脸图像 → 必须被拒绝）

两种指标口径（很重要，很多报告在这里算错）：
    1) 1:N 识别（/api/face/verify）：探针是谁、Top-1 是否报对 → 用来算识别准确率；
       这个口径**不能**用来算 FAR，因为底库里的每个人都是「合法身份」。
    2) 1:1 核身（/api/face/ticket、/api/face/unlock）：我声称自己是 A，
       系统判「这张脸是不是 A」→ 只有这个口径能算 FAR/FRR。
       冒名样本 = 用 B 的照片声称自己是 A。

做法：
    1. 每人注册 4 张（原图 + 3 张受控增强：亮度/对比度/旋转/噪声/JPEG）；
    2. 每人取 3 张新增强图做「本人探针」，另用对方图像做「冒名探针」；
    3. 直接读 /verify 返回的 per-identity 相似度，离线扫阈值算 FAR/FRR，避免采样偏差；
    4. 再用 /api/face/ticket 实测「当前自动阈值下的业务判定」（通过/拒绝）。

用法（服务需先启动）：
    python MachineLearning/human_face/tools/face_dataset_selftest.py
输出：
    week5/results/face_realdata_result.json
    week5/results/face_realdata_threshold_curve.csv
"""

import csv
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_JSON = REPO_ROOT / "week5" / "results" / "face_realdata_result.json"
OUT_CSV = REPO_ROOT / "week5" / "results" / "face_realdata_threshold_curve.csv"
SERVICE = "http://127.0.0.1:%s" % os.environ.get("FACE_API_PORT", "5001")

rng = np.random.default_rng(20261113)
ENROLL_COUNT = 4


# ---------------------------------------------------------------------------
# 数据准备：真实人脸 + 受控增强
# ---------------------------------------------------------------------------
def load_sources():
    from skimage import data
    import matplotlib.cbook as cbook

    astronaut = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    hopper = cv2.imread(str(cbook.get_sample_data("grace_hopper.jpg").name))
    negatives = [
        ("coffee", cv2.cvtColor(data.coffee(), cv2.COLOR_RGB2BGR)),
        ("chelsea", cv2.cvtColor(data.chelsea(), cv2.COLOR_RGB2BGR)),
    ]
    return {"astronaut": astronaut, "grace_hopper": hopper}, negatives


def augment(img, index):
    """同一人的第 index 张（index=0 为原图），模拟光照/角度/噪声/压缩差异"""
    if index == 0:
        return img.copy()
    out = img.copy()
    alpha = [1.0, 0.82, 1.18, 0.92, 0.75, 1.25, 0.95][index % 7]
    beta = [0, -25, 18, 12, -34, 26, 6][index % 7]
    out = cv2.convertScaleAbs(out, alpha=alpha, beta=beta)
    angle = [0, -7, 6, -4, 8, -9, 3][index % 7]
    if angle:
        h, w = out.shape[:2]
        matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        out = cv2.warpAffine(out, matrix, (w, h), borderMode=cv2.BORDER_REPLICATE)
    noise = rng.normal(0, 4.0, out.shape).astype(np.float32)
    out = np.clip(out.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", out, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
    if ok:
        out = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    return out


def to_jpeg_bytes(img):
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    if not ok:
        raise RuntimeError("JPEG 编码失败")
    return buf.tobytes()


# ---------------------------------------------------------------------------
# HTTP（手工 multipart，避免引入 requests 依赖）
# ---------------------------------------------------------------------------
def post_multipart(url, fields, file_bytes, filename="probe.jpg"):
    boundary = "----dsface%s" % uuid.uuid4().hex
    parts = []
    for key, value in fields.items():
        parts.append(
            ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
             % (boundary, key, value)).encode("utf-8"))
    parts.append(
        ("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"%s\"\r\n"
         "Content-Type: image/jpeg\r\n\r\n" % (boundary, filename)).encode("utf-8"))
    parts.append(file_bytes)
    parts.append(("\r\n--%s--\r\n" % boundary).encode("utf-8"))
    body = b"".join(parts)
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"error": raw}


def call_enroll(identity, img):
    return post_multipart(SERVICE + "/api/face/enroll",
                          {"login_account": identity, "identity": identity},
                          to_jpeg_bytes(img), "%s.jpg" % identity)


def call_verify(img):
    return post_multipart(SERVICE + "/api/face/verify", {}, to_jpeg_bytes(img))


def call_ticket(claimed_account, img):
    return post_multipart(SERVICE + "/api/face/ticket",
                          {"login_account": claimed_account, "purpose": "booking"},
                          to_jpeg_bytes(img))


def call_health():
    with urllib.request.urlopen(SERVICE + "/health", timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# 指标
# ---------------------------------------------------------------------------
def metrics_at(threshold, genuine, impostor):
    tp = sum(1 for s in genuine if s >= threshold)
    fn = len(genuine) - tp
    fp = sum(1 for s in impostor if s >= threshold)
    tn = len(impostor) - fp
    total = tp + fn + fp + tn
    return {
        "threshold": round(threshold, 4),
        "accuracy": round((tp + tn) / total, 4) if total else 0.0,
        "far": round(fp / (fp + tn), 4) if (fp + tn) else 0.0,
        "frr": round(fn / (fn + tp), 4) if (fn + tp) else 0.0,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def main():
    print("服务地址：%s" % SERVICE)
    try:
        info0 = call_health()
    except Exception as exc:                                    # noqa: BLE001
        print("无法连接人脸服务：%s\n请先启动 MachineLearning/human_face/face_service_lbp.py" % exc)
        sys.exit(2)
    print("服务健康：%s" % json.dumps(
        {k: info0[k] for k in ("gallery_identities", "gallery_faces", "threshold",
                               "threshold_source", "require_face_detection")},
        ensure_ascii=False))

    sources, negatives = load_sources()
    identities = list(sources.keys())

    # ---------- 1) 注册 ----------
    enroll_report = {}
    for identity in identities:
        rows = []
        for i in range(ENROLL_COUNT):
            code, payload = call_enroll(identity, augment(sources[identity], i))
            rows.append({"index": i, "http": code, "enrolled": payload.get("enrolled"),
                         "error": payload.get("error")})
            if code != 200:
                print("  ⚠ 注册失败 %s#%d: %s" % (identity, i, payload))
        enroll_report[identity] = rows

    info = call_health()
    print("注册后：身份=%d 人脸=%d 自动阈值=%.4f（%s）" % (
        info["gallery_identities"], info["gallery_faces"], info["threshold"],
        info["threshold_source"]))
    print("阈值标定依据：%s" % info["threshold_detail"])

    # ---------- 2) 探针 ----------
    genuine_1n_correct, genuine_1n_total = 0, 0
    genuine_11, impostor_11 = [], []
    probes, ticket_tests = [], []

    for idx, identity in enumerate(identities):
        other = identities[(idx + 1) % len(identities)]

        for k in range(ENROLL_COUNT, ENROLL_COUNT + 3):
            img = augment(sources[identity], k)
            code, payload = call_verify(img)
            scores = payload.get("scores") or {}
            genuine_1n_total += 1
            if payload.get("identity") == identity:
                genuine_1n_correct += 1
            score_11 = float(scores.get(identity, 0.0))
            genuine_11.append(score_11)
            probes.append({
                "probe": "%s#%d" % (identity, k), "http": code,
                "top1": payload.get("identity"), "top1_score": payload.get("confidence"),
                "own_account_score": round(score_11, 4), "kind": "genuine",
                "expected": identity,
            })
            # 业务口径实测：本人刷脸取凭据，应通过
            tcode, tpayload = call_ticket(identity, img)
            ticket_tests.append({"case": "本人刷脸取凭据 %s#%d" % (identity, k),
                                 "http": tcode, "granted": tpayload.get("granted"),
                                 "reason": tpayload.get("error"),
                                 "expect": "granted"})

        # 冒名：用 other 的脸，声称自己是 identity
        for k in range(ENROLL_COUNT, ENROLL_COUNT + 2):
            img = augment(sources[other], k)
            code, payload = call_verify(img)
            scores = payload.get("scores") or {}
            score_11 = float(scores.get(identity, 0.0))
            impostor_11.append(score_11)
            probes.append({
                "probe": "impostor:%s#%d" % (other, k), "http": code,
                "top1": payload.get("identity"), "top1_score": payload.get("confidence"),
                "claimed_account": identity, "claimed_score": round(score_11, 4),
                "kind": "impostor", "expected": "not-" + identity,
            })
            tcode, tpayload = call_ticket(identity, img)
            ticket_tests.append({"case": "冒名(%s)声称 %s#%d" % (other, identity, k),
                                 "http": tcode, "granted": tpayload.get("granted"),
                                 "reason": tpayload.get("error"),
                                 "expect": "denied"})

    # ---------- 3) 负样本：无人脸图像必须被拒 ----------
    negative_report = []
    for name, img in negatives:
        code, payload = call_verify(img)
        negative_report.append({"image": name, "http": code,
                                "matched": payload.get("matched"),
                                "error": payload.get("error"),
                                "confidence": payload.get("confidence"),
                                "rejected": code != 200 or not payload.get("matched")})

    # ---------- 4) 阈值扫描（1:1 口径） ----------
    curve = [metrics_at(t / 100.0, genuine_11, impostor_11) for t in range(40, 100, 5)]
    feasible = [row for row in curve if row["far"] <= 0.05]
    best = max(feasible, key=lambda r: (r["accuracy"], -r["frr"])) if feasible else curve[0]
    at_auto = metrics_at(info["threshold"], genuine_11, impostor_11)

    result = {
        "mode": "real_face_public_samples",
        "note": ("真实人脸照片（scikit-image 的 astronaut、matplotlib 的 grace_hopper），"
                 "非本组同学照片；用于验证自研 LBP 链路的真实判别力与 fail-closed 行为。"
                 "本组同学实测请用 webcam 注册后运行 tools/face_live_eval.py。"),
        "algorithm": info["algorithm"],
        "dependencies": info["dependencies"],
        "service": {k: info[k] for k in ("gallery_identities", "gallery_faces", "threshold",
                                         "threshold_source", "threshold_detail",
                                         "require_face_detection")},
        "enroll": enroll_report,
        "one_to_n": {"correct": genuine_1n_correct, "total": genuine_1n_total,
                     "accuracy": round(genuine_1n_correct / genuine_1n_total, 4)
                     if genuine_1n_total else 0.0},
        "one_to_one": {
            "genuine_scores": sorted(round(s, 4) for s in genuine_11),
            "impostor_scores": sorted(round(s, 4) for s in impostor_11),
            "genuine_min": round(min(genuine_11), 4) if genuine_11 else None,
            "impostor_max": round(max(impostor_11), 4) if impostor_11 else None,
        },
        "probes": probes,
        "business_ticket_tests": ticket_tests,
        "negative_images": negative_report,
        "threshold_curve": curve,
        "best_threshold_by_far05": best,
        "at_auto_threshold": at_auto,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(curve[0].keys()))
        writer.writeheader()
        writer.writerows(curve)

    # ---------- 输出 ----------
    print("\n=== 1:N 识别（验证「认得出是谁」）===")
    print("  Top-1 正确 %d/%d  准确率 %.4f" % (
        genuine_1n_correct, genuine_1n_total, result["one_to_n"]["accuracy"]))
    print("\n=== 1:1 核身分数（验证「是否本人」）===")
    print("  本人分数：%s" % result["one_to_one"]["genuine_scores"])
    print("  冒名分数：%s" % result["one_to_one"]["impostor_scores"])
    print("  本人 min=%.4f  冒名 max=%.4f  可分间隙=%.4f" % (
        result["one_to_one"]["genuine_min"], result["one_to_one"]["impostor_max"],
        result["one_to_one"]["genuine_min"] - result["one_to_one"]["impostor_max"]))

    print("\n=== 业务实测定（ticket 接口，当前阈值 %.4f）===" % info["threshold"])
    for row in ticket_tests:
        flag = "OK" if ((row["expect"] == "granted") == bool(row["granted"])) else "❌不一致"
        print("  [%s] %-34s granted=%s %s" % (flag, row["case"], row["granted"],
                                              row["reason"] or ""))

    print("\n=== 负样本（无人脸图像，必须拒绝）===")
    for row in negative_report:
        print("  [%s] %-8s http=%s matched=%s error=%s" % (
            "OK" if row["rejected"] else "❌放行", row["image"], row["http"],
            row["matched"], row["error"]))

    print("\n=== 阈值曲线（1:1 口径）===")
    for row in curve:
        print("  θ=%.2f acc=%.4f FAR=%.4f FRR=%.4f (TP%d FP%d FN%d TN%d)" % (
            row["threshold"], row["accuracy"], row["far"], row["frr"],
            row["tp"], row["fp"], row["fn"], row["tn"]))
    print("\n最优（FAR≤0.05）: %s" % json.dumps(best, ensure_ascii=False))
    print("当前自动阈值 %.4f: %s" % (info["threshold"], json.dumps(at_auto, ensure_ascii=False)))
    print("\n结果已写入：\n  %s\n  %s" % (OUT_JSON, OUT_CSV))

    # 断言式自检：负样本必须被拒；本人必须全过；冒名必须全拒
    problems = []
    if not all(row["rejected"] for row in negative_report):
        problems.append("存在无人脸图像被放行")
    genuine_tickets = [t for t in ticket_tests if t["expect"] == "granted"]
    impostor_tickets = [t for t in ticket_tests if t["expect"] == "denied"]
    if not all(t["granted"] for t in genuine_tickets):
        problems.append("存在本人刷脸被拒")
    if any(t["granted"] for t in impostor_tickets):
        problems.append("存在冒名被放行（严重）")
    if problems:
        print("\n自检未通过：%s" % "；".join(problems))
        sys.exit(1)
    print("\n自检通过：负样本全拒、本人全过、冒名全拒。")


if __name__ == "__main__":
    main()
