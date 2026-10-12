#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect_face_samples.py
=======================
第5周人脸识别 —— 样本采集脚本（运行在采集设备/树莓派上）

功能：
    调用 USB 摄像头采集指定对象的人脸样本，按“对象编号/照片编号”命名，
    存入本地私有存储目录（不入仓库）。目录结构与 face_sample_manifest.csv 一致。

用法：
    python collect_face_samples.py --person A01 --count 12 --out D:/face_data/raw

注意：
    - 采集前必须确认对象已签署授权同意书（docs/data_authorization.md）；
    - 输出目录默认 ~/face_data/raw/<person>/，文件名 subject_<person>_photo_<n>.jpg；
    - 本脚本在无摄像头环境仅打印错误，不影响其他交付物。
"""

import argparse
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--person", required=True, help="对象匿名编号，如 A01")
    parser.add_argument("--count", type=int, default=12, help="采集照片数量（>=10）")
    parser.add_argument("--out", default=os.path.expanduser("~/face_data/raw"),
                        help="本地私有存储根目录")
    args = parser.parse_args()
    if args.count < 10:
        raise SystemExit("每人不少于 10 张照片")

    out_dir = os.path.join(args.out, args.person)
    os.makedirs(out_dir, exist_ok=True)

    try:
        import cv2
    except ImportError:
        raise SystemExit("缺少 opencv-python；采集环境请先 pip install opencv-python")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise SystemExit("无法打开摄像头，请在采集设备上运行")

    saved = 0
    while saved < args.count:
        ok, frame = cap.read()
        if not ok:
            continue
        path = os.path.join(out_dir, "subject_%s_photo_%02d.jpg" % (args.person, saved + 1))
        cv2.imwrite(path, frame)
        saved += 1
        print("已采集 %d/%d：%s" % (saved, args.count, path))
    cap.release()
    print("采集完成：%s（%d 张）" % (out_dir, saved))


if __name__ == "__main__":
    main()
