#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_analysis_charts.py
===========================
第4周项目实践 —— 数据分析图表生成脚本（可重复运行）

数据源：data/processed/clean_data_v1.csv（第3周清洗后的正式数据版本）
业务问题与口径见 docs/week4_analysis_report.md；每张图标题均写明口径。

图表清单（每图回答一个业务问题）：
    1. charts/01_分时段占用率.png
       问题：会议室哪个时段最忙？
       口径：2026-09-01~09-28 期间，每个整点小时(08:00-22:00)内
             occupancy=1（有人）的采样数 ÷ 该小时有效采样总数（3间会议室合并）。
    2. charts/02_各会议室占用强度.png
       问题：三间会议室的占用强度差异如何？
       口径：每会议室“有人”采样数 ÷ 该会议室有效采样总数；并标注总占用小时数。
    3. charts/03_工作日vs周末占用率.png
       问题：工作日与周末的占用差异有多大？
       口径：工作日(周一~周五)占用采样数 ÷ 工作日有效采样总数，对比
             周末(周六、周日)占用采样数 ÷ 周末有效采样总数。
    4. charts/04_温度分布.png
       问题：会议室温度分布是否处于舒适区间？
       口径：清洗后温度字段（异常与缺失已剔除）落在各区间的采样占比，
             区间按 2℃ 分档，标注 20~26℃ 舒适区间。

用法：
    python scripts/generate_analysis_charts.py
"""

import os

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "clean_data_v1.csv")
CHART_DIR = os.path.join(BASE_DIR, "charts")

HOURS = list(range(8, 22))


def load():
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    df["weekday"] = df["timestamp"].dt.weekday  # 0=周一
    return df


def chart_1_occupancy_by_hour(df):
    """分时段占用率柱状图"""
    valid = df[df["occupancy"].notna() & df["hour"].isin(HOURS)].copy()
    grouped = valid.groupby("hour")["occupancy"].agg(["sum", "size"])
    grouped["rate"] = grouped["sum"] / grouped["size"]
    rates = grouped["rate"].reindex(HOURS, fill_value=0)
    peak = rates.idxmax()
    peak_rate = rates.max()

    fig, ax = plt.subplots(figsize=(11, 5.5))
    colors = ["#dc3545" if h == peak else "#0d6efd" for h in HOURS]
    bars = ax.bar([str(h) + ":00" for h in HOURS], rates.values * 100, color=colors)
    ax.set_ylim(0, 100)
    ax.set_ylabel("占用率（%）")
    ax.set_xlabel("小时")
    ax.set_title("分时段占用率（口径：该小时内“有人”采样数 ÷ 该小时有效采样总数，3间会议室合并，2026-09-01~09-28）")
    for bar, rate in zip(bars, rates.values):
        ax.text(bar.get_x() + bar.get_width() / 2, rate * 100 + 1.5,
                "%.0f%%" % (rate * 100), ha="center", fontsize=8)
    ax.axhline(50, color="gray", linestyle="--", linewidth=0.8)
    ax.text(21.5, 52, "50% 参考线", fontsize=8, color="gray")
    ax.annotate("高峰 %d:00 占用率 %.0f%%" % (peak, peak_rate * 100),
                xy=(peak, peak_rate * 100), xytext=(peak - 3, peak_rate * 100 + 15),
                arrowprops=dict(arrowstyle="->"), fontsize=10, color="#dc3545")
    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "01_分时段占用率.png"), dpi=150)
    plt.close(fig)
    print("图1 已保存：分时段占用率，高峰时段 %d:00 占用率 %.1f%%" % (peak, peak_rate * 100))
    return {"peak_hour": int(peak), "peak_rate": round(float(peak_rate), 4)}


def chart_2_room_intensity(df):
    """各会议室占用强度对比"""
    valid = df[df["occupancy"].notna()].copy()
    grouped = valid.groupby("room_id")["occupancy"].agg(["sum", "size"])
    grouped["rate"] = grouped["sum"] / grouped["size"]
    grouped = grouped.sort_values("rate", ascending=False)
    occupied_hours = (grouped["sum"] / 12).round(1)  # 每12条采样=1小时

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bars = ax.bar(grouped.index, grouped["rate"].values * 100, color="#198754")
    ax.set_ylim(0, 100)
    ax.set_ylabel("占用率（%）")
    ax.set_xlabel("会议室编号")
    ax.set_title("各会议室占用强度（口径：每会议室“有人”采样数 ÷ 该会议室有效采样总数，2026-09-01~09-28）")
    for bar, (rid, row) in zip(bars, grouped.iterrows()):
        ax.text(bar.get_x() + bar.get_width() / 2, row["rate"] * 100 + 1.5,
                "%.1f%%\n占用约%.0f小时" % (row["rate"] * 100, occupied_hours[rid]),
                ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "02_各会议室占用强度.png"), dpi=150)
    plt.close(fig)
    print("图2 已保存：各会议室占用强度")
    return {rid: round(float(row["rate"]), 4) for rid, row in grouped.iterrows()}


def chart_3_weekday_vs_weekend(df):
    """工作日 vs 周末占用率"""
    valid = df[df["occupancy"].notna()].copy()
    valid["is_weekend"] = valid["weekday"] >= 5
    grouped = valid.groupby("is_weekend")["occupancy"].agg(["sum", "size"])
    grouped["rate"] = grouped["sum"] / grouped["size"]
    labels = ["工作日（周一至周五）", "周末（周六、周日）"]
    rates = [grouped.loc[False, "rate"], grouped.loc[True, "rate"]]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bars = ax.bar(labels, [r * 100 for r in rates], color=["#0d6efd", "#fd7e14"])
    for bar, r in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, r * 100 + 1.5,
                "%.1f%%" % (r * 100), ha="center", fontsize=12)
    ax.set_ylim(0, 100)
    ax.set_ylabel("占用率（%）")
    ax.set_title("工作日 vs 周末占用率（口径：工作日占用采样数 ÷ 工作日有效采样总数；周末同理，2026-09-01~09-28）")
    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "03_工作日vs周末占用率.png"), dpi=150)
    plt.close(fig)
    print("图3 已保存：工作日 vs 周末占用率")
    return {"weekday_rate": round(float(rates[0]), 4), "weekend_rate": round(float(rates[1]), 4)}


def chart_4_temperature_dist(df):
    """温度分布直方图（2℃分档）"""
    temp = df["temperature"].dropna()
    temp = temp[(temp >= 0) & (temp <= 50)]
    bins = list(range(0, 52, 2))
    labels = ["%d~%d" % (b, b + 2) for b in bins[:-1]]
    counts, _ = np_histogram(temp, bins=bins)
    total = counts.sum()
    pcts = counts / total * 100

    fig, ax = plt.subplots(figsize=(12, 5.5))
    colors = ["#0d6efd"] * len(labels)
    for i, label in enumerate(labels):
        lo, hi = label.split("~")
        if int(lo) >= 20 and int(hi) <= 26:
            colors[i] = "#198754"  # 舒适区间 20~26℃
    bars = ax.bar(labels, pcts, color=colors, width=0.9)
    ax.set_ylabel("采样占比（%）")
    ax.set_xlabel("温度区间（℃）")
    ax.set_title("温度分布（口径：清洗后温度有效采样（0~50℃内）落在各区间的占比，2℃分档，2026-09-01~09-28）")
    comfort = pcts[[i for i, label in enumerate(labels)
                   if 20 <= int(label.split("~")[0]) and int(label.split("~")[1]) <= 26]].sum()
    ax.text(0.99, 0.95, "20~26℃ 舒适区间占比 %.1f%%" % comfort,
            transform=ax.transAxes, ha="right", va="top", fontsize=10,
            bbox=dict(facecolor="white", edgecolor="gray"))
    for bar, p in zip(bars, pcts):
        if p >= 1:
            ax.text(bar.get_x() + bar.get_width() / 2, p + 0.3, "%.1f" % p,
                    ha="center", fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "04_温度分布.png"), dpi=150)
    plt.close(fig)
    print("图4 已保存：温度分布，舒适区间占比 %.1f%%" % comfort)
    return {"comfort_rate": round(float(comfort), 4), "total_valid": int(total)}


def np_histogram(values, bins):
    import numpy as np
    counts, _ = np.histogram(values, bins=bins)
    return counts, _


def main():
    os.makedirs(CHART_DIR, exist_ok=True)
    df = load()
    r1 = chart_1_occupancy_by_hour(df)
    r2 = chart_2_room_intensity(df)
    r3 = chart_3_weekday_vs_weekend(df)
    r4 = chart_4_temperature_dist(df)

    import json
    summary = {
        "data_source": DATA_PATH,
        "charts": ["01_分时段占用率.png", "02_各会议室占用强度.png",
                   "03_工作日vs周末占用率.png", "04_温度分布.png"],
        "chart1_peak": r1,
        "chart2_room_rates": r2,
        "chart3_weekday_weekend": r3,
        "chart4_temp": r4,
    }
    with open(os.path.join(BASE_DIR, "results", "charts_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("图表汇总已保存：results/charts_summary.json")


if __name__ == "__main__":
    main()
