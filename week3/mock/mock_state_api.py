#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mock_state_api.py
=================
第3周课堂实践作业2 —— 统一会议室状态查询接口（模拟接口）

说明（重要）：
    本接口为【模拟接口】。由于真实后端（Spring Boot 8080）与树莓派传感器服务
    （Flask 5000）需要完整环境才能启动，本接口使用 mock/state.json 中的统一状态
    对象返回数据，并在 source 字段明确标注为 "mock"，不能写成真实树莓派实时数据。
    真实环境下由 Flask 综合传感器系统 /api/current 与门禁系统 door_state 提供
    source 为 "sensor" 的实时数据（见 docs/api-contract.md 的落地映射）。

功能：
    GET  /api/rooms                会议室状态列表（统一状态对象数组）
    GET  /api/rooms/<room_id>/state 指定会议室统一状态对象
    返回统一响应包：{"code": 200, "message": "success", "data": {...}}
    非法会议室编号：{"code": 404, "message": "room not found", "data": null}
    缺少会议室编号：{"code": 400, "message": "room id is required", "data": null}
    非法数据（如温度超出 0~50）：quality 标记为 abnormal，message 提示异常字段。

用法：
    python mock/mock_state_api.py            # 默认端口 5002
    curl http://127.0.0.1:5002/api/rooms/301/state
"""

import json
import os
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(BASE_DIR, "state.json")

app = Flask(__name__)

# 统一响应包：与作业要求一致
def ok(data):
    return jsonify({"code": 200, "message": "success", "data": data})


def fail(code, message):
    return jsonify({"code": code, "message": message, "data": None}), code


def load_state():
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["rooms"]


# 传感器合理范围（与综II系统一致，用于 quality 判断）
RANGES = {
    "temperature": (0.0, 50.0),
    "humidity": (0.0, 100.0),
    "light": (0.0, 255.0),
    "smoke": (0.0, 200.0),
    "distance": (2.0, 450.0),
}


def validate_state(state):
    """处理缺少字段与非法数据：缺失关键字段 -> 400；数值越界 -> quality=abnormal"""
    problems = []
    required = ["room_id", "timestamp", "occupancy", "temperature", "humidity"]
    for field in required:
        if field not in state or state[field] is None:
            return None, "missing field: %s" % field
    for field, (low, high) in RANGES.items():
        value = state.get(field)
        if value is not None:
            try:
                num = float(value)
            except (TypeError, ValueError):
                problems.append("%s is not numeric" % field)
                continue
            if num < low or num > high:
                problems.append("%s=%s out of range [%s, %s]" % (field, num, low, high))
    if problems:
        state = dict(state)
        state["quality"] = "abnormal"
    return state, "; ".join(problems) if problems else None


@app.get("/api/rooms")
def list_rooms():
    rooms = load_state()
    data = [{"room_id": rid, "state": rooms[rid]} for rid in sorted(rooms)]
    return ok(data)


@app.get("/api/rooms/<room_id>/state")
def room_state(room_id):
    room_id = (room_id or "").strip()
    if not room_id:
        return fail(400, "room id is required")
    rooms = load_state()
    if room_id not in rooms:
        return fail(404, "room not found")
    state, problem = validate_state(dict(rooms[room_id]))
    if state is None:
        return fail(400, problem)
    return ok(state)


@app.get("/health")
def health():
    return ok({"status": "ok", "source": "mock", "rooms": sorted(load_state())})


def _now_iso():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")


if __name__ == "__main__":
    port = int(os.environ.get("MOCK_STATE_API_PORT", "5002"))
    print("模拟状态接口启动：http://127.0.0.1:%d" % port)
    print("测试命令示例：")
    print("  curl http://127.0.0.1:%d/api/rooms/301/state" % port)
    print("  curl http://127.0.0.1:%d/api/rooms/R99/state" % port)
    app.run(host="127.0.0.1", port=port, debug=False)
