#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lbp_face.py
===========
第5-6周人脸识别 —— 自研关键步骤②：LBP 特征提取 + 余弦相似度比对 + 阈值判定

背景（为什么自研 LBP 替代/补充库方案）：
    综II现有 face_api.py 使用 DeepFace 的 ArcFace 模型提取特征（需下载数百 MB
    模型、依赖 GPU 或较慢 CPU）。在树莓派门禁场景下，需要一个轻量、可离线、
    可解释的本地特征方案。LBP（局部二值模式）提取人脸纹理特征，与预处理后的
    直方图均衡化图像配合，对光照变化鲁棒，纯 numpy 实现即可运行。

本模块实现（全部自研）：
    1. 均匀模式 LBP（uniform LBP）：对每个像素计算 8 邻域二值模式，
       58 个统一模式映射到 0~57，非统一模式映射到 58，得到 59 维直方图；
    2. 分块直方图：将 112x112 人脸分成 7x7=49 块，每块 59 维直方图，
       级联成 49*59=2891 维特征向量（含块空间信息，判别力更强）；
    3. L2 归一化 + 余弦相似度比对；
    4. 阈值判定：Sim_max >= theta -> 通过；否则拒绝（失败不放行）。

用法（自测冒烟）：
    python scripts/lbp_face.py
"""

import numpy as np
from functools import lru_cache

CELL_SIZE = 16          # 分块尺寸
GRID = 7                # 分块网格 7x7
UNIFORM_BINS = 59       # 均匀模式 LBP 直方图维度


@lru_cache(maxsize=1)
def _uniform_mapping_table():
    """58 个均匀模式 + 一个非均匀桶，值域始终为 0..58。"""
    table = np.full(256, 58, dtype=np.int32)
    next_label = 0
    for i in range(256):
        bits = [(i >> k) & 1 for k in range(8)]
        transitions = sum(bits[k] != bits[(k + 1) % 8] for k in range(8))
        if transitions <= 2:
            table[i] = next_label
            next_label += 1
    table.flags.writeable = False
    return table


def lbp_histogram(gray):
    """计算均匀模式 LBP 的 59 维直方图（自研）"""
    h, w = gray.shape
    table = _uniform_mapping_table()
    # 8 邻域偏移（顺时针，含边界保护）
    offsets = [(-1, -1), (-1, 0), (-1, 1), (0, 1),
               (1, 1), (1, 0), (1, -1), (0, -1)]
    center = gray[1:h - 1, 1:w - 1].astype(np.int32)
    code = np.zeros_like(center, dtype=np.int32)
    for bit, (dy, dx) in enumerate(offsets):
        neighbor = gray[1 + dy:h - 1 + dy, 1 + dx:w - 1 + dx].astype(np.int32)
        code |= ((neighbor >= center).astype(np.int32) << bit)
    mapped = table[code]
    hist = np.bincount(mapped.ravel(), minlength=UNIFORM_BINS).astype(np.float64)
    return hist


def extract_feature(gray):
    """分块 LBP 特征：7x7 块各 59 维 -> 2891 维，L2 归一化"""
    if gray.shape != (112, 112):
        raise ValueError("LBP requires a preprocessed 112x112 grayscale image")
    feats = []
    cell = gray.shape[0] // GRID
    for gy in range(GRID):
        for gx in range(GRID):
            block = gray[gy * cell:(gy + 1) * cell, gx * cell:(gx + 1) * cell]
            feats.append(lbp_histogram(block))
    vec = np.concatenate(feats)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def cosine_similarity(a, b):
    """余弦相似度（a、b 均为 L2 归一化向量）"""
    return float(np.dot(a, b))


def match(gallery, probe_feature):
    """与注册库比对：返回 (最佳身份, 最高相似度, 全部相似度)"""
    best_id, best_sim = None, -1.0
    sims = {}
    for person_id, feats in gallery.items():
        if not feats:
            continue
        s = max(cosine_similarity(probe_feature, f) for f in feats)
        sims[person_id] = s
        if s > best_sim:
            best_sim, best_id = s, person_id
    return best_id, best_sim, sims


def decide(best_sim, threshold):
    """阈值判定：Sim >= theta -> 通过（识别为对应身份）；否则拒绝（失败不放行）"""
    return best_sim >= threshold


if __name__ == "__main__":
    # 自测冒烟：生成两张随机“人脸纹理图”，验证特征维度与相似度计算
    rng = np.random.default_rng(42)
    a = rng.integers(0, 256, (112, 112), dtype=np.uint8)
    b = rng.integers(0, 256, (112, 112), dtype=np.uint8)
    fa, fb = extract_feature(a), extract_feature(b)
    print("特征维度：%d（%d 块 x %d 维）" % (fa.shape[0], GRID * GRID, UNIFORM_BINS))
    print("余弦相似度（无关图对）：%.4f" % cosine_similarity(fa, fb))
    print("余弦相似度（同图自比）：%.4f" % cosine_similarity(fa, fa))
    gallery = {"A01": [fa, fb]}
    best, sim, _ = match(gallery, fa)
    print("比对结果：best=%s sim=%.4f -> 阈值0.60判定：%s"
          % (best, sim, "通过" if decide(sim, 0.60) else "拒绝"))
