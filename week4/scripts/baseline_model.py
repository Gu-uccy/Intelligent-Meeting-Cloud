#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
baseline_model.py
=================
第4周项目实践 —— 基线预测模型（阈值基线）

业务问题：会议室某个时段是否“有人使用”？
基线做法（阈值基线）：历史同一小时的平均占用率 > 0.5 -> 预测“有人”。

口径：
    小时占用率 = 该小时(08:00-22:00)内 occupancy=1（有人）的采样数 ÷ 该小时有效采样总数；
    小时标签 = 1（有人）当且仅当小时占用率 > 0.5。
切分：
    按时间切分：2026-09-01 ~ 09-21 为历史（训练规则），2026-09-22 ~ 09-28 为测试；
    训练：对每个（会议室, 小时）计算历史 21 天该小时的平均占用率，>0.5 则预测“有人”；
    测试：对测试期每个（会议室, 日期, 小时）样本，按规则给出预测并与实际标签比较。
样本量：测试期样本 = 7 天 × 14 小时 × 3 会议室 = 294 个整点小时样本。

输出指标：准确率、有人类精确率/召回率、有人判对/无人判对数量、F1；
输出文件：results/baseline_result.json、results/baseline_run.log。

用法：
    python scripts/baseline_model.py
"""

import json
import os
from collections import defaultdict

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "clean_data_v1.csv")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

TRAIN_END = "2026-09-21"   # 历史期截止
TEST_START = "2026-09-22"  # 测试期开始
TEST_END = "2026-09-28"    # 测试期结束
THRESHOLD = 0.5            # 历史同时段平均占用率阈值
HOURS = list(range(8, 22))  # 监测时段 08:00-22:00（不含22:00）


def load_data():
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date.astype(str)
    df["hour"] = df["timestamp"].dt.hour
    # 只保留监测时段与有效占用状态
    df = df[df["hour"].isin(HOURS) & df["occupancy"].notna()].copy()
    return df


def build_hour_samples(df):
    """按（会议室, 日期, 小时）聚合：小时占用率 = 有人采样数 / 有效采样总数"""
    grouped = df.groupby(["room_id", "date", "hour"], as_index=False).agg(
        occupied_count=("occupancy", "sum"),
        total_count=("occupancy", "size"),
    )
    grouped["rate"] = grouped["occupied_count"] / grouped["total_count"]
    grouped["label"] = (grouped["rate"] > 0.5).astype(int)
    return grouped


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    log_lines = []

    def out(msg):
        print(msg)
        log_lines.append(msg)

    out("=" * 60)
    out("第4周基线预测：阈值基线（历史同时段平均占用率 > 0.5 -> 判有人）")
    out("=" * 60)

    df = load_data()
    out("数据源：%s" % DATA_PATH)
    out("有效采样数：%d（08:00-22:00，占用状态有效）" % len(df))

    samples = build_hour_samples(df)
    train = samples[(samples["date"] <= TRAIN_END)].copy()
    test = samples[(samples["date"] >= TEST_START) & (samples["date"] <= TEST_END)].copy()

    out("切分方式：按时间切分（历史 %s ~ %s，测试 %s ~ %s）"
        % ("2026-09-01", TRAIN_END, TEST_START, TEST_END))
    out("训练样本（会议室×日期×小时）：%d" % len(train))
    out("测试样本：%d（= 7天 × 14小时 × 3会议室）" % len(test))

    # 训练：每个（会议室, 小时）的历史平均占用率
    rule = train.groupby(["room_id", "hour"])["rate"].mean().reset_index()
    rule["predict_rule"] = (rule["rate"] > THRESHOLD).astype(int)

    merged = test.merge(
        rule[["room_id", "hour", "predict_rule"]],
        on=["room_id", "hour"], how="left",
    )
    merged["prediction"] = merged["predict_rule"].fillna(0).astype(int)

    y_true = merged["label"].values
    y_pred = merged["prediction"].values

    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())

    accuracy = (tp + tn) / len(y_true)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    out("-" * 60)
    out("测试集指标（样本量 n=%d）：" % len(y_true))
    out("  准确率 Accuracy = %.4f" % accuracy)
    out("  有人判对 TP = %d，无人判对 TN = %d" % (tp, tn))
    out("  有人误判无人 FN = %d，无人误判有人 FP = %d" % (fn, fp))
    out("  有人类精确率 Precision = %.4f" % precision)
    out("  有人类召回率 Recall = %.4f" % recall)
    out("  F1 = %.4f" % f1)
    out("  有人真实占比 = %.4f" % (y_true.mean()))
    out("-" * 60)
    out("按会议室指标：")
    for room in sorted(merged["room_id"].unique()):
        sub = merged[merged["room_id"] == room]
        t = sub["label"].values
        p = sub["prediction"].values
        acc = ((t == p).sum()) / len(t)
        out("  会议室 %s：测试样本 %d，准确率 %.4f" % (room, len(t), acc))

    result = {
        "model": "threshold_baseline",
        "rule": "历史同时段(会议室x小时)平均占用率 > 0.5 -> 判有人",
        "split": {"train": "2026-09-01~2026-09-21", "test": "2026-09-22~2026-09-28"},
        "sample_size": int(len(y_true)),
        "train_sample_size": int(len(train)),
        "metrics": {
            "accuracy": round(accuracy, 4),
            "precision_occupied": round(precision, 4),
            "recall_occupied": round(recall, 4),
            "f1": round(f1, 4),
            "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "occupied_rate_in_test": round(float(y_true.mean()), 4),
        },
    }

    with open(os.path.join(RESULTS_DIR, "baseline_result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(os.path.join(RESULTS_DIR, "baseline_run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    out("结果已保存：results/baseline_result.json、results/baseline_run.log")


if __name__ == "__main__":
    main()
