#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess_face.py
==================
第5-6周人脸识别 —— 自研关键步骤①：人脸图像预处理

对应综II门禁系统 smart_door_system.py 的预处理逻辑（灰度化 + 直方图均衡化），
本脚本将其独立封装为可复用模块，并增加尺寸归一化，作为“半自主开发”的自研步骤。

预处理流程（输入 -> 输出）：
    原图(BGR/RGB) -> 灰度化 -> 尺寸归一化(resize 112x112) -> 直方图均衡化 -> 预处理图

为什么做预处理（改进理由）：
    1. 光照是识别的最大干扰源。同一人脸在强光/暗光下灰度差异巨大，
       直方图均衡化可拉伸对比度、抹平整体亮度差异；
    2. 尺寸归一化保证后续 LBP 特征维度一致，比对才有意义；
    3. 综II门禁系统已使用 equalizeHist（人脸识别前的图像增强），
       本脚本与其口径一致，验证逻辑见 scripts/run_face_eval.py。

依赖：opencv-python、numpy
用法（命令行冒烟测试）：
    python scripts/preprocess_face.py <图片路径> [--out out.png]
"""

import argparse
import os

import numpy as np

TARGET_SIZE = 112  # 与 face_api.py 使用的 ArcFace 输入尺寸一致


def to_gray(image_bgr):
    """彩色图 -> 灰度图（BGR 权重与 OpenCV cvtColor 一致）"""
    if image_bgr.ndim == 2 and image_bgr.size:
        return image_bgr.astype(np.uint8)
    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3 or not image_bgr.size:
        raise ValueError("Expected a nonempty BGR or grayscale image")
    b = image_bgr[..., 0].astype(np.float32)
    g = image_bgr[..., 1].astype(np.float32)
    r = image_bgr[..., 2].astype(np.float32)
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    return gray.astype(np.uint8)


def resize_face(gray, size=TARGET_SIZE):
    """尺寸归一化：双线性插值到 size x size（纯 numpy 实现）"""
    h, w = gray.shape
    if not h or not w or size < 1:
        raise ValueError("Image and output dimensions must be positive")
    ys = np.clip((np.arange(size) + 0.5) * (h / size) - 0.5, 0, h - 1)
    xs = np.clip((np.arange(size) + 0.5) * (w / size) - 0.5, 0, w - 1)
    y0 = np.floor(ys).astype(int)
    x0 = np.floor(xs).astype(int)
    y1 = np.minimum(y0 + 1, h - 1)
    x1 = np.minimum(x0 + 1, w - 1)
    dy = (ys - y0)[:, None]
    dx = (xs - x0)[None, :]
    img = (gray[y0][:, x0] * (1 - dy) * (1 - dx)
           + gray[y0][:, x1] * (1 - dy) * dx
           + gray[y1][:, x0] * dy * (1 - dx)
           + gray[y1][:, x1] * dy * dx)
    return np.clip(img, 0, 255).astype(np.uint8)


def equalize_hist(gray):
    """全局直方图均衡化（与 OpenCV equalizeHist 等价，纯 numpy 实现）"""
    hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    cdf = hist.cumsum()
    cdf_min = cdf[cdf > 0].min()
    total = gray.size
    if total == cdf_min:
        return gray.copy()
    lut = np.clip(np.rint((cdf - cdf_min) * 255.0 / (total - cdf_min)), 0, 255).astype(np.uint8)
    return lut[gray]


def preprocess_face(image_bgr):
    """完整预处理：灰度化 -> 尺寸归一化 -> 直方图均衡化"""
    gray = to_gray(image_bgr)
    resized = resize_face(gray, TARGET_SIZE)
    enhanced = equalize_hist(resized)
    return enhanced


def load_image(path):
    """读取图片（尽力兼容 BGR 顺序）"""
    import cv2
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit("无法读取图片：%s" % path)
    return img


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", help="输入图片路径")
    parser.add_argument("--out", help="输出预处理图片路径（默认不保存）")
    args = parser.parse_args()

    img = load_image(args.image)
    out = preprocess_face(img)
    print("预处理完成：%s -> %s（灰度 112x112 + 直方图均衡化）"
          % (args.image, args.out or "内存"))
    print("输出形状：%s，像素范围：%d~%d" % (out.shape, out.min(), out.max()))
    if args.out:
        import cv2
        cv2.imwrite(args.out, out)
        print("已保存：%s" % args.out)


if __name__ == "__main__":
    main()
