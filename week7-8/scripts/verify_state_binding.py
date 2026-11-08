# -*- coding: utf-8 -*-
"""状态字段校验：拉取 /api/current，逐项核对《状态字段表》的字段、类型与派生规则。

用法：
    python verify_state_binding.py --base http://127.0.0.1:5000

输出：
    控制台对照表 + results/状态字段校验结果.json
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime

REQUIRED_TOP = {
    "temperature": float,
    "humidity": float,
    "distance": float,
    "motion": bool,
    "presence": bool,
    "motion_count": int,
    "last_motion": str,
    "light": (int, float),
    "smoke": (int, float),
    "door_open": bool,
    "door_source": str,
    "devices": dict,
    "temp_min": (int, float),
    "temp_max": (int, float),
    "humidity_min": (int, float),
    "humidity_max": (int, float),
    "timestamp": str,
}

REQUIRED_DEVICES = {
    "cooling": bool, "heating": bool, "humidifier": bool, "dehumidifier": bool,
    "lighting": bool, "lighting_brightness": (int, float), "lighting_source": str,
    "alarm": bool, "presence": bool, "door_open": bool, "door_source": str,
    "auto_mode": bool,
}

# 前端当前硬编码的阈值（Room3D/index.vue:794-797, 140）
UI_THRESHOLDS = {"temp_hot": 28, "temp_cold": 18, "humidity_wet": 68, "humidity_dry": 35, "smoke_alarm": 60}


def fetch(base, path, timeout=6):
    url = base.rstrip("/") + path
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, str(e).encode("utf-8")


def type_ok(value, expected):
    if isinstance(value, bool) and expected in (int, float):
        return False
    if isinstance(value, bool):
        return expected is bool
    return isinstance(value, expected)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5000")
    ap.add_argument("--out", default=os.path.join("results", "状态字段校验结果.json"))
    args = ap.parse_args()

    status, raw = fetch(args.base, "/api/current")
    report = {
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "base": args.base,
        "http_status": status,
        "field_checks": [],
        "derived": {},
        "threshold_compare": {},
        "conclusion": "",
    }

    if status != 200:
        report["conclusion"] = "FAIL：接口不可用，无法校验状态绑定（status=%s）" % status
        print(report["conclusion"])
        _dump(args.out, report)
        return 1

    data = json.loads(raw.decode("utf-8"))
    ok_all = True

    for name, expected in REQUIRED_TOP.items():
        present = name in data
        type_pass = present and type_ok(data[name], expected)
        ok_all = ok_all and present and type_pass
        report["field_checks"].append({
            "field": name, "present": present, "type_ok": bool(type_pass),
            "value": data.get(name) if not isinstance(data.get(name), dict) else "object",
        })

    devices = data.get("devices") or {}
    for name, expected in REQUIRED_DEVICES.items():
        present = name in devices
        type_pass = present and type_ok(devices[name], expected)
        ok_all = ok_all and present and type_pass
        report["field_checks"].append({
            "field": "devices." + name, "present": present, "type_ok": bool(type_pass),
            "value": devices.get(name),
        })

    # 派生规则（与 Room3D roomState 一致）
    occupied = bool(data.get("motion") or data.get("presence"))
    people_count = 0 if not occupied else max(1, min(8, int(data.get("people_count") or data.get("motion_count") or 1)))
    door_open = bool(data.get("door_open") if data.get("door_open") is not None else devices.get("door_open"))
    report["derived"] = {
        "people.occupied": occupied,
        "people.count": people_count,
        "door.open": door_open,
        "climate.temperature": data.get("temperature"),
        "climate.humidity": data.get("humidity"),
    }

    # 阈值口径对比（前端硬编码 vs 接口下发）
    api_th = {
        "temp_min": data.get("temp_min"), "temp_max": data.get("temp_max"),
        "humidity_min": data.get("humidity_min"), "humidity_max": data.get("humidity_max"),
        "smoke_alarm_backend": 100,
    }
    mismatches = []
    if api_th["temp_max"] is not None and api_th["temp_max"] != UI_THRESHOLDS["temp_hot"]:
        mismatches.append("温度上限：接口 %s / 前端 %s" % (api_th["temp_max"], UI_THRESHOLDS["temp_hot"]))
    if api_th["temp_min"] is not None and api_th["temp_min"] != UI_THRESHOLDS["temp_cold"]:
        mismatches.append("温度下限：接口 %s / 前端 %s" % (api_th["temp_min"], UI_THRESHOLDS["temp_cold"]))
    if api_th["humidity_max"] is not None and api_th["humidity_max"] != UI_THRESHOLDS["humidity_wet"]:
        mismatches.append("湿度上限：接口 %s / 前端 %s" % (api_th["humidity_max"], UI_THRESHOLDS["humidity_wet"]))
    if api_th["humidity_min"] is not None and api_th["humidity_min"] != UI_THRESHOLDS["humidity_dry"]:
        mismatches.append("湿度下限：接口 %s / 前端 %s" % (api_th["humidity_min"], UI_THRESHOLDS["humidity_dry"]))
    mismatches.append("烟雾报警：后端 100 / 前端 %s（两端口径不同）" % UI_THRESHOLDS["smoke_alarm"])
    report["threshold_compare"] = {"api": api_th, "ui": UI_THRESHOLDS, "mismatches": mismatches}

    report["conclusion"] = "PASS：字段齐全且类型一致" if ok_all else "FAIL：存在缺失或类型不符字段"
    if ok_all and mismatches:
        report["conclusion"] += "；但阈值口径存在 %d 处不一致（需整改，见 D-04/D-06）" % len(mismatches)

    print("=" * 68)
    print("状态字段校验  %s" % report["checked_at"])
    print("=" * 68)
    failed = [c for c in report["field_checks"] if not (c["present"] and c["type_ok"])]
    print("字段总数：%d，异常：%d" % (len(report["field_checks"]), len(failed)))
    for c in failed:
        print("  ✗ %s present=%s type_ok=%s value=%s" % (c["field"], c["present"], c["type_ok"], c["value"]))
    print("派生：", json.dumps(report["derived"], ensure_ascii=False))
    print("阈值不一致：")
    for m in mismatches:
        print("  - " + m)
    print("结论：" + report["conclusion"])

    _dump(args.out, report)
    return 0 if ok_all else 1


def _dump(path, obj):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print("已写入：%s" % path)


if __name__ == "__main__":
    sys.exit(main())
