#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clean_data.py
=============
第3周课堂实践作业1 —— 会议室数据清洗与质量检查（可重复运行）

功能（对应课堂要求）：
    1. 读取 CSV 原始数据（data/raw/原始数据样例.csv）；
    2. 统一字段名称（中文导出表头 -> 与 docs/state-object.md 一致的中英文字段名）；
    3. 统一时间格式（兼容多种写法）并按时间升序排列；
    4. 统一会议室编号（301 / room-301 / 3F301 / 301号 / 302室 / 5F501 -> 301/302/501）；
    5. 统一占用状态（有人/无人/true/false/1/0 -> 1/0，非法值置缺失并统计）；
    6. 删除重复记录；
    7. 检查缺失值（温度、湿度、距离、占用状态等）；
    8. 检查异常值（温度<0或>50 置缺失并标记，湿度/光照/烟雾/距离超出合理范围同样处理）；
    9. 输出清洗后数据文件（clean_data_v1.csv 为正式数据版本，
       clean_sensor_data.csv 为第3周提交要求命名的同一份数据）；
    10. 输出清洗前后对比与数据质量统计（控制台 + docs/cleaning_run_log.txt + results/quality_report.json）。

用法：
    python scripts/clean_data.py

验收依据：见 docs/data_quality_report.md 与《课堂实践作业1》验收标准表。
"""

import json
import os
from collections import Counter

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATH = os.path.join(BASE_DIR, "data", "raw", "原始数据样例.csv")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

V1_PATH = os.path.join(PROCESSED_DIR, "clean_data_v1.csv")      # 正式数据版本（第4周数据分析使用）
CLEAN_PATH = os.path.join(PROCESSED_DIR, "clean_sensor_data.csv")  # 第3周提交要求文件名
LOG_PATH = os.path.join(DOCS_DIR, "cleaning_run_log.txt")
JSON_PATH = os.path.join(RESULTS_DIR, "quality_report.json")

# 原始 CSV 中文表头（与综II /api/export/csv 导出格式一致）
COLUMN_MAP = {
    "时间": "time",
    "时间戳": "timestamp",
    "会议室": "room_id",
    "温度(°C)": "temperature",
    "湿度(%)": "humidity",
    "光照": "light",
    "烟雾": "smoke",
    "距离(cm)": "distance",
    "人体检测": "motion_raw",
    "占用状态": "occupancy_raw",
    "制冷": "cooling",
    "加热": "heating",
    "加湿": "humidifier",
    "除湿": "dehumidifier",
    "照明": "lighting",
    "报警": "alarm",
    "自动模式": "auto_mode",
}

# 会议室编号别名 -> 标准编号（与数据库 meeting_room.room_code 一致）
ROOM_ALIAS = {
    "301": "301", "room-301": "301", "3f301": "301", "301号": "301", "301室": "301",
    "302": "302", "room-302": "302", "302室": "302", "302号": "302",
    "501": "501", "room-501": "501", "5f501": "501", "501室": "501",
}

# 占用状态别名 -> 0/1
OCCUPANCY_ALIAS = {
    "1": 1, "0": 0,
    "有人": 1, "无人": 0,
    "true": 1, "false": 0,
    "是": 1, "否": 0,
}

TIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%m/%d/%Y %H:%M",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
]

# 传感器合理范围（与综II模拟逻辑一致）
RANGES = {
    "temperature": (0, 50),      # 课堂要求：温度<0 或 >50 记为异常
    "humidity": (0, 100),
    "light": (0, 255),
    "smoke": (0, 200),
    "distance": (2, 450),
}


def parse_timestamp(value):
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    for fmt in TIME_FORMATS:
        try:
            return pd.Timestamp(pd.to_datetime(text, format=fmt, errors="raise"))
        except (ValueError, TypeError):
            continue
    return pd.NaT


def normalize_room(value):
    key = str(value).strip().lower()
    return ROOM_ALIAS.get(key, key)  # 未在别名表内的保留原值，由后续检查统一报出


def normalize_occupancy(value):
    key = str(value).strip().lower()
    if key in OCCUPANCY_ALIAS:
        return OCCUPANCY_ALIAS[key]
    return None  # 非法值 -> 缺失


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    stats = {}
    lines = []

    def out(msg):
        print(msg)
        lines.append(msg)

    # ---------- 1. 读取原始数据 ----------
    df = pd.read_csv(RAW_PATH, encoding="utf-8-sig")
    before_count = len(df)
    out("=" * 60)
    out("会议室数据清洗与质量检查")
    out("=" * 60)
    out("原始数据文件：%s" % RAW_PATH)
    out("清洗前记录数：%d" % before_count)
    stats["before_count"] = before_count

    # ---------- 2. 统一字段名称 ----------
    df = df.rename(columns=COLUMN_MAP)
    # 保留统一字段顺序（与 state-object / 数据字典一致）
    df = df[[
        "time", "timestamp", "room_id", "temperature", "humidity", "light",
        "smoke", "distance", "motion_raw", "occupancy_raw",
        "cooling", "heating", "humidifier", "dehumidifier",
        "lighting", "alarm", "auto_mode",
    ]]
    out("字段名称统一完成：中文导出表头 -> %d 个统一英文字段" % len(COLUMN_MAP))

    # ---------- 3. 统一时间格式 ----------
    before_invalid_time = int(df["timestamp"].isna().sum())
    df["timestamp"] = df["timestamp"].map(parse_timestamp)
    invalid_time = int(df["timestamp"].isna().sum())
    out("时间格式统一完成：无法解析的时间记录 %d 条（置为缺失）" % invalid_time)
    stats["invalid_time_after_parse"] = invalid_time
    stats["invalid_time_before_parse"] = before_invalid_time

    # ---------- 4. 统一会议室编号 ----------
    df["room_id"] = df["room_id"].map(normalize_room)
    unknown_rooms = sorted(set(df["room_id"]) - {"301", "302", "501"})
    if unknown_rooms:
        out("警告：仍存在无法归一的会议室编号：%s" % unknown_rooms)
        df.loc[df["room_id"].isin(unknown_rooms), "room_id"] = None
    out("会议室编号统一完成：301 / 302 / 501")

    # ---------- 5. 统一占用状态 ----------
    occ_raw = df["occupancy_raw"].fillna("").astype(str).str.strip()
    occ_missing_mask = occ_raw == ""  # 空值视为缺失（兼容 pandas 的 NaN/pd.NA）
    df["occupancy"] = df["occupancy_raw"].map(normalize_occupancy)
    df.loc[occ_missing_mask, "occupancy"] = None
    missing_occupancy = int(occ_missing_mask.sum())
    invalid_occupancy = int(df["occupancy"].isna().sum()) - missing_occupancy
    df["occupancy"] = df["occupancy"].astype("Int64")
    out("占用状态统一完成：缺失 %d 条、非法值 %d 条（仅接受 有人/无人/true/false/1/0）"
        % (missing_occupancy, invalid_occupancy))
    stats["missing_occupancy"] = missing_occupancy
    stats["invalid_occupancy"] = invalid_occupancy

    # motion（人体检测）：有人/无人 -> 1/0
    df["motion"] = df["motion_raw"].map({"有人": 1, "无人": 0}).astype("Int64")

    # ---------- 6. 删除重复记录 ----------
    dup_mask = df.duplicated(subset=["timestamp", "room_id", "temperature", "humidity",
                                     "light", "smoke", "distance", "motion", "occupancy"])
    dup_count = int(dup_mask.sum())
    df = df[~dup_mask].copy()
    out("删除重复记录：%d 条" % dup_count)
    stats["duplicates_removed"] = dup_count

    # ---------- 7. 检查缺失值 ----------
    missing_before = df[["temperature", "humidity", "light", "smoke", "distance",
                         "motion", "occupancy", "timestamp"]].isna().sum().to_dict()
    missing_before = {k: int(v) for k, v in missing_before.items()}
    out("缺失值统计（去重后、异常处理前）：%s" % missing_before)
    stats["missing_before_anomaly"] = missing_before

    # ---------- 8. 检查异常值（温度<0或>50 等超出合理范围 -> 置缺失并标记） ----------
    anomaly_counts = {}
    for col, (low, high) in RANGES.items():
        if col not in df.columns:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        mask = (numeric < low) | (numeric > high)
        cnt = int(mask.sum())
        anomaly_counts[col] = cnt
        if cnt > 0:
            df.loc[mask, col] = None
    out("异常值检查（温度超出0~50、湿度超出0~100、光照超出0~255、"
        "烟雾超出0~200、距离超出2~450 均置为缺失）：%s" % anomaly_counts)
    stats["anomalies_marked"] = anomaly_counts

    # 数值列统一为 float
    for col in ["temperature", "humidity", "light", "smoke", "distance"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # ---------- 9. 缺失值统计（最终）与缺失率 ----------
    missing_after = df[["temperature", "humidity", "light", "smoke", "distance",
                        "motion", "occupancy", "timestamp"]].isna().sum().to_dict()
    missing_after = {k: int(v) for k, v in missing_after.items()}
    out("缺失值统计（清洗后）：%s" % missing_after)
    stats["missing_after"] = missing_after

    # ---------- 10. 按时间升序排列 ----------
    df = df.sort_values("timestamp", na_position="last").reset_index(drop=True)
    out("已按时间升序排列")

    after_count = len(df)
    out("清洗后记录数：%d" % after_count)
    stats["after_count"] = after_count

    # ---------- 11. 输出清洗结果 ----------
    final = df[[
        "timestamp", "room_id", "temperature", "humidity", "light", "smoke",
        "distance", "motion", "occupancy", "cooling", "heating", "humidifier",
        "dehumidifier", "lighting", "alarm", "auto_mode",
    ]].copy()
    final["timestamp"] = final["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    final.to_csv(V1_PATH, index=False, encoding="utf-8-sig")
    final.to_csv(CLEAN_PATH, index=False, encoding="utf-8-sig")
    out("清洗结果已保存：")
    out("  %s （正式数据版本 clean_data_v1.csv，供第4周数据分析使用）" % V1_PATH)
    out("  %s （第3周提交要求文件名，与 v1 内容一致）" % CLEAN_PATH)

    # ---------- 12. 清洗前后对比统计 ----------
    out("=" * 60)
    out("清洗前后对比")
    out("=" * 60)
    out("清洗前记录数：%d" % before_count)
    out("清洗后记录数：%d" % after_count)
    out("删除重复记录：%d" % dup_count)
    out("异常值置缺失：%s" % anomaly_counts)
    out("非法占用状态置缺失：%d" % invalid_occupancy)
    out("非法/无法解析时间置缺失：%d" % invalid_time)
    out("缺失值汇总（清洗后）：%s" % missing_after)
    stats["summary"] = {
        "before_count": before_count,
        "after_count": after_count,
        "duplicates_removed": dup_count,
        "anomalies_marked": anomaly_counts,
        "invalid_occupancy": invalid_occupancy,
        "invalid_time": invalid_time,
        "missing_after": missing_after,
        "room_distribution": Counter(final["room_id"].dropna().tolist()),
        "occupancy_distribution": Counter(final["occupancy"].dropna().tolist()),
    }

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    out("运行日志已保存：%s" % LOG_PATH)
    out("质量统计已保存：%s" % JSON_PATH)


if __name__ == "__main__":
    main()
