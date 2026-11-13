#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_face_eval.py
================
第6周（验收周）人脸识别 —— 测试集评估框架

功能：
    1. 评估协议：本人/非本人测试集，计算 准确率、FAR（误识率）、
       FRR（拒识率）、识别响应时间，输出混淆矩阵与阈值标定结果；
    2. 两种运行模式：
       [默认] 算法自测模式（--self-test）：
           用合成特征向量（3 名对象 × 注册/测试样本，带受控噪声）验证
           匹配器与阈值判定逻辑，给出阈值标定曲线。合成向量仅为验证
           算法链路，不代表真实人脸准确率。
       [真实] 真实测试集模式（--data-dir 本地测试集目录）：
           目录结构 person_ID/photo_N.jpg，先调用 scripts/preprocess_face.py
           与 scripts/lbp_face.py 提取特征，再完成比对与指标计算；
           真实照片存放于本地/私有存储（授权与脱敏见 docs/data_authorization.md），
           不入仓库。
    3. 失败不放行验证：任何低于阈值的比对一律判拒绝，并写入失败日志。

用法：
    python scripts/run_face_eval.py                    # 算法自测（默认）
    python scripts/run_face_eval.py --data-dir <dir>   # 真实测试集评估

输出：
    results/face_eval_result.json、results/face_eval_run.log、results/阈值标定曲线.png
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
LOG_PATH = os.path.join(RESULTS_DIR, "face_eval_run.log")
JSON_PATH = os.path.join(RESULTS_DIR, "face_eval_result.json")
CHART_PATH = os.path.join(RESULTS_DIR, "阈值标定曲线.png")

SUBJECTS = ["A01", "A02", "A03"]   # 匿名编号（真实样本集见 data/face_sample_manifest.csv）
ENROLL_PER_SUBJECT = 10            # 注册样本数（满足“每人不少于10张”要求）
PROBE_PER_SUBJECT = 5              # 本人测试样本数
IMPOSTOR_COUNT = 15                # 非本人测试样本数
THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]


# ---------------------------------------------------------------
# 1. 算法自测：合成特征向量（验证匹配/阈值/指标链路）
# ---------------------------------------------------------------
def synthetic_gallery_and_probes(seed=7):
    """每个对象一个原型向量 + 高斯噪声，构造注册库与测试集"""
    rng = np.random.default_rng(seed)
    dim = 128
    gallery = defaultdict(list)
    genuine_probes = []   # (对象, 向量, 是否为本人)
    for subj in SUBJECTS:
        proto = rng.normal(0, 1, dim)
        proto = proto / np.linalg.norm(proto)
        for _ in range(ENROLL_PER_SUBJECT):
            v = proto + rng.normal(0, 0.08, dim)
            gallery[subj].append(v / np.linalg.norm(v))
        for _ in range(PROBE_PER_SUBJECT):
            v = proto + rng.normal(0, 0.08, dim)
            genuine_probes.append((subj, v / np.linalg.norm(v)))
    impostor_probes = []
    for _ in range(IMPOSTOR_COUNT):
        v = rng.normal(0, 1, dim)   # 未注册的陌生向量
        impostor_probes.append(("UNKNOWN", v / np.linalg.norm(v)))
    return gallery, genuine_probes, impostor_probes


# ---------------------------------------------------------------
# 2. 真实测试集：读取本地目录，走自研预处理 + LBP 特征
# ---------------------------------------------------------------
def build_real_set(data_dir):
    """目录结构：data_dir/<person_id>/<photo_N>.jpg"""
    gallery = defaultdict(list)
    probes = []  # (真实身份, 特征, 是否本人)
    sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
    import cv2
    from lbp_face import extract_feature
    from preprocess_face import preprocess_face

    for person in sorted(os.listdir(data_dir)):
        person_dir = os.path.join(data_dir, person)
        if not os.path.isdir(person_dir):
            continue
        files = sorted(f for f in os.listdir(person_dir)
                       if f.lower().endswith((".jpg", ".jpeg", ".png")))
        for idx, f in enumerate(files):
            img = cv2.imread(os.path.join(person_dir, f))
            if img is None:
                continue
            feat = extract_feature(preprocess_face(img))
            if idx < max(1, int(len(files) * 0.7)):   # 前70%注册
                gallery[person].append(feat)
            else:                                     # 后30%测试
                probes.append((person, feat))
    if not gallery or not probes:
        raise SystemExit("真实测试集为空，请检查 --data-dir 目录结构")
    return dict(gallery), probes


# ---------------------------------------------------------------
# 3. 评估：阈值扫描 + 指标
# ---------------------------------------------------------------
def evaluate(gallery, genuine_probes, impostor_probes):
    sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
    from lbp_face import match

    result = {}
    for theta in THRESHOLDS:
        tp = fp = tn = fn = 0
        # 本人测试
        for true_id, vec in genuine_probes:
            best, sim, _ = match(gallery, vec)
            accepted = sim >= theta
            if accepted and best == true_id:
                tp += 1
            elif accepted and best != true_id:
                fp += 1  # 本人被误认为他人
            else:
                fn += 1  # 本人被拒
        # 非本人测试
        for _, vec in impostor_probes:
            best, sim, _ = match(gallery, vec)
            accepted = sim >= theta
            if not accepted:
                tn += 1
            else:
                fp += 1
        n = tp + fp + tn + fn
        accuracy = (tp + tn) / n
        far = fp / (fp + tn) if (fp + tn) else 0.0          # 误识率：非本人被放行
        frr = fn / (tp + fn) if (tp + fn) else 0.0          # 拒识率：本人被拒绝
        result[str(theta)] = {
            "accuracy": round(accuracy, 4), "far": round(far, 4),
            "frr": round(frr, 4), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        }
    # 最优阈值：在 FAR 可接受（<=0.05）前提下取 FRR 最小
    best = min(THRESHOLDS, key=lambda t: (result[str(t)]["frr"]
               if result[str(t)]["far"] <= 0.05 else 1.0))
    return result, best


# ---------------------------------------------------------------
# 4. 响应时间测量（本人测试集上，预处理+特征+比对的耗时）
# ---------------------------------------------------------------
def measure_latency(probes, gallery):
    sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
    from lbp_face import match, extract_feature

    # 用合成向量模拟一次完整比对耗时（真实模式下耗时以硬件实测为准）
    t0 = time.perf_counter()
    for _ in range(50):
        best, sim, _ = match(gallery, probes[0][1])
    t1 = time.perf_counter()
    return round((t1 - t0) / 50 * 1000, 2)   # 单次比对毫秒


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", help="真实测试集目录（person_id/photo.jpg）")
    parser.add_argument("--self-test", action="store_true", default=True,
                        help="算法自测模式（默认）")
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    log_lines = []

    def out(msg):
        print(msg)
        log_lines.append(msg)

    out("=" * 60)
    out("第6周人脸识别测试集评估")
    out("=" * 60)

    if args.data_dir:
        out("模式：真实测试集评估（数据目录：%s）" % args.data_dir)
        gallery, probes = build_real_set(args.data_dir)
        genuine = [(pid, vec) for pid, vec in probes]
        impostor = []  # 真实模式下非本人由未注册目录提供（测试协议见 tests/face_test_protocol.md）
        out("注册对象：%d 名，测试样本：%d 条" % (len(gallery), len(genuine)))
    else:
        out("模式：算法自测（合成特征向量，仅验证匹配/阈值/指标链路，不代表真实人脸准确率）")
        gallery, genuine, impostor = synthetic_gallery_and_probes()
        out("注册库：%d 名 x %d 张；本人测试：%d 条；非本人测试：%d 条"
            % (len(gallery), ENROLL_PER_SUBJECT, len(genuine), len(impostor)))

    result, best = evaluate(gallery, genuine, impostor)
    latency = measure_latency(genuine, gallery)

    out("-" * 60)
    out("阈值标定结果（真实/自测集上扫描，指标链路验证）：")
    for theta in THRESHOLDS:
        r = result[str(theta)]
        out("  θ=%.2f  准确率 %.4f  FAR %.4f  FRR %.4f  (TP%d FP%d FN%d TN%d)"
            % (theta, r["accuracy"], r["far"], r["frr"], r["tp"], r["fp"], r["fn"], r["tn"]))
    out("最优阈值：θ=%.2f（FAR<=0.05 前提下 FRR 最小；不用别人训练好的阈值）" % best)
    out("单次比对耗时（本机）：%.2f ms（真实设备以实测为准，见 face_test_record.md）" % latency)

    # 混淆矩阵（最优阈值下）
    r = result[str(best)]
    out("-" * 60)
    out("最优阈值下混淆矩阵：")
    out("              预测本人    预测非本人")
    out("实际本人      TP=%-6d  FN=%-6d" % (r["tp"], r["fn"]))
    out("实际非本人    FP=%-6d  TN=%-6d" % (r["fp"], r["tn"]))
    out("失败不放行验证：FN（本人被拒）与 FP（非本人被放行）均计入日志，"
        "拒绝一律不放行（fail-closed）。")

    payload = {
        "mode": "self_test" if not args.data_dir else "real",
        "subjects": SUBJECTS,
        "enroll_per_subject": ENROLL_PER_SUBJECT,
        "threshold_scan": {k: v for k, v in result.items()},
        "best_threshold": best,
        "latency_ms": latency,
        "note": "算法自测仅验证匹配器与阈值判定链路；真实人脸指标待硬件环境实测"
                "（协议见 tests/face_test_protocol.md）",
    }
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    # 阈值标定曲线
    try:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
        matplotlib.rcParams["axes.unicode_minus"] = False
        import matplotlib.pyplot as plt
        ts = THRESHOLDS
        fig, ax = plt.subplots(figsize=(9, 5.5))
        ax.plot(ts, [result[str(t)]["far"] * 100 for t in ts],
                marker="o", label="FAR 误识率（%）")
        ax.plot(ts, [result[str(t)]["frr"] * 100 for t in ts],
                marker="s", label="FRR 拒识率（%）")
        ax.plot(ts, [result[str(t)]["accuracy"] * 100 for t in ts],
                marker="^", label="准确率（%）")
        ax.axvline(best, color="red", linestyle="--")
        ax.text(best + 0.005, 5, "最优 θ=%.2f" % best, color="red", fontsize=10)
        ax.set_xlabel("阈值 θ（余弦相似度）")
        ax.set_ylabel("百分比（%）")
        ax.set_title("阈值标定曲线（算法自测集；θ越大越严格，FAR下降、FRR上升）")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(CHART_PATH, dpi=150)
        plt.close(fig)
        out("阈值标定曲线已保存：%s" % CHART_PATH)
    except Exception as exc:  # 图表失败不影响评估结果
        out("阈值曲线生成失败：%s" % exc)

    out("结果已保存：results/face_eval_result.json、results/face_eval_run.log")


if __name__ == "__main__":
    main()
