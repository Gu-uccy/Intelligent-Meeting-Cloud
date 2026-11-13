#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_baseline_to_state.py
===========================
第4周项目实践 —— 把基线预测结果接到“统一状态对象”（结果可见性联动）

背景（第4周检查三）：
    基线预测结果需要在 Web / 接口 / 3D 中至少一处能看到。
    本脚本把基线模型的预测占用状态写入统一状态对象（与第3周 mock/state.json
    同构），3D 场景（Room3D）和 Web 环境监测页可直接消费该对象：
      occupancy（有人/无人）驱动 3D 场景人员模型与 Web 占用指示灯。

做法：
    1. 读取 clean_data_v1.csv，重算历史同时段平均占用率规则（与 baseline_model.py 一致）；
    2. 对“当前小时”（默认 10 时，可用 --hour 覆盖）预测 301/302/501 的占用状态；
    3. 输出 results/baseline_predictions.json（预测明细）；
    4. 输出 results/state_with_baseline.json（统一状态对象，字段与
       ../week3/mock/state.json 完全一致，occupancy 由预测结果给出，
       source 仍为 mock，quality=normal），供 3D/Web 端消费。

用法：
    python scripts/publish_baseline_to_state.py [--hour 10]
"""

import argparse
import json
import os
from datetime import datetime, timedelta, timezone

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "clean_data_v1.csv")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
THRESHOLD = 0.5
HOURS = list(range(8, 22))
ROOMS = ["301", "302", "501"]


def load_rules():
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    df["room_id"] = df["room_id"].astype(str).str.strip()  # 防止被推断为数值
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    df = df[df["hour"].isin(HOURS) & df["occupancy"].notna()].copy()
    df["date"] = df["timestamp"].dt.date.astype(str)
    train = df[df["date"] <= "2026-09-21"]
    grouped = train.groupby(["room_id", "hour"])["occupancy"].mean().reset_index()
    grouped["prediction"] = (grouped["occupancy"] > THRESHOLD).astype(int)
    rules = {
        (str(row["room_id"]), int(row["hour"])): int(row["prediction"])
        for _, row in grouped.iterrows()
    }
    return rules


def build_state(room_id, occupancy, hour, now):
    """生成与第3周统一状态对象同构的对象（设备状态为占位默认值）"""
    return {
        "timestamp": now,
        "room_id": room_id,
        "occupancy": bool(occupancy),
        "temperature": 24.6 if room_id == "301" else (26.8 if room_id == "302" else 22.1),
        "humidity": 48.0 if room_id == "301" else (39.0 if room_id == "302" else 55.0),
        "light": 128 if room_id == "301" else (35 if room_id == "302" else 18),
        "smoke": 20,
        "distance": 56.7 if room_id == "301" else (180.2 if room_id == "302" else 220.0),
        "door_status": "closed",
        "devices": {
            "lighting": "on" if (occupancy and room_id == "301") else "off",
            "cooling": "off",
            "heating": "off",
            "humidifier": "off",
            "dehumidifier": "off",
            "alarm": "off",
        },
        "source": "mock",
        "quality": "normal",
        "occupancy_predicted": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hour", type=int, default=10,
                        help="预测的小时（08-21，默认 10）")
    args = parser.parse_args()
    if args.hour not in HOURS:
        raise SystemExit("hour 必须在 8~21 之间")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    rules = load_rules()
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    predictions = []
    states = {}
    for room in ROOMS:
        pred = rules.get((room, args.hour), 0)
        predictions.append({"room_id": room, "hour": args.hour,
                            "prediction": pred,
                            "rule": "历史 %d:00 平均占用率 > 0.5" % args.hour})
        states[room] = build_state(room, pred, args.hour, now)

    with open(os.path.join(RESULTS_DIR, "baseline_predictions.json"), "w", encoding="utf-8") as f:
        json.dump({"hour": args.hour, "predictions": predictions}, f,
                  ensure_ascii=False, indent=2)
    with open(os.path.join(RESULTS_DIR, "state_with_baseline.json"), "w", encoding="utf-8") as f:
        json.dump({
            "_meta": {
                "说明": "第4周基线预测写入的统一状态对象（与第3周 mock/state.json 同构），"
                        "occupancy 由基线模型预测给出，供 3D/Web 端消费",
                "source": "mock",
                "rooms": ROOMS,
                "predicted_hour": args.hour,
            },
            "rooms": states,
        }, f, ensure_ascii=False, indent=2)

    print("预测结果（%d:00）：" % args.hour)
    for p in predictions:
        print("  会议室 %s -> occupancy=%s" % (p["room_id"], "有人" if p["prediction"] else "无人"))
    print("已保存：results/baseline_predictions.json、results/state_with_baseline.json")


if __name__ == "__main__":
    main()
