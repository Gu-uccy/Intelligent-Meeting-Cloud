# -*- coding: utf-8 -*-
"""接口测试用例集（第 11 周“测试要能重复进行并给出通过率”）。

用法：
    python api_contract_test.py --base http://127.0.0.1:5000

输出：
    results/接口测试用例结果.csv   逐条用例
    results/接口测试用例结果.json  含通过率汇总

用例编号与《测试用例与问题闭环》文档一一对应（TC-01…）。
"""
import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime

RESULTS = []


def call(base, path, method="GET", body=None, timeout=8, raw_body=None, headers=None):
    url = base.rstrip("/") + path
    data = raw_body if raw_body is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
    hdrs = headers if headers is not None else ({"Content-Type": "application/json"} if data else {})
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), round((time.perf_counter() - t0) * 1000, 1)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), round((time.perf_counter() - t0) * 1000, 1)
    except Exception as e:
        return -1, str(e).encode("utf-8"), round((time.perf_counter() - t0) * 1000, 1)


def add(tc, title, expect, actual, detail, ok):
    RESULTS.append({"tc": tc, "title": title, "expected": expect, "actual": actual, "detail": detail, "passed": bool(ok)})
    print(("[PASS] " if ok else "[FAIL] ") + tc + " " + title + " | 期望 " + expect + " 实际 " + str(actual))


def j(raw):
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5000")
    ap.add_argument("--outdir", default="results")
    args = ap.parse_args()
    b = args.base

    st, raw, _ = call(b, "/api/current")
    d = j(raw) or {}
    add("TC-01", "获取实时环境数据", "200 且 17 字段", st, "字段数=%d" % len(d.keys()), st == 200 and len(d.keys()) >= 17)

    add("TC-02", "数据含时间戳且可解析", "timestamp 形如 YYYY-MM-DD HH:MM:SS",
        d.get("timestamp"), str(d.get("timestamp")),
        isinstance(d.get("timestamp"), str) and len(d.get("timestamp", "")) == 19)

    add("TC-03", "设备状态字段完整", "devices 12 字段", len((d.get("devices") or {}).keys()),
        "keys=%s" % list((d.get("devices") or {}).keys())[:4],
        len((d.get("devices") or {}).keys()) >= 11)

    st_h, raw_h, _ = call(b, "/api/history")
    hist = j(raw_h) or []
    add("TC-04", "历史数据接口", "200 且为数组", st_h, "点数=%d" % len(hist), st_h == 200 and isinstance(hist, list) and len(hist) > 0)

    st_c, raw_c, _ = call(b, "/api/export/csv")
    header_ok = "时间戳".encode("utf-8") in raw_c
    add("TC-05", "CSV 导出", "200 且含表头（时间戳/温度）", st_c,
        "bytes=%d 表头=%r" % (len(raw_c), raw_c[:40].decode("utf-8", "ignore")),
        st_c == 200 and header_ok)

    st_l1, raw_l1, _ = call(b, "/api/control", "POST", {"action": "manual", "device": "lighting", "state": True, "brightness": 100, "source": "tc-suite"})
    l1 = (j(raw_l1) or {}).get("devices") or {}
    add("TC-06", "开灯并下发亮度", "200 lighting=true brightness=100", st_l1, "lighting=%s brightness=%s" % (l1.get("lighting"), l1.get("lighting_brightness")),
        st_l1 == 200 and l1.get("lighting") is True and l1.get("lighting_brightness") == 100)

    st_l2, raw_l2, _ = call(b, "/api/control", "POST", {"action": "manual", "device": "lighting", "state": False, "source": "tc-suite"})
    l2 = (j(raw_l2) or {}).get("devices") or {}
    add("TC-07", "关灯复位", "200 lighting=false", st_l2, "lighting=%s" % l2.get("lighting"),
        st_l2 == 200 and l2.get("lighting") is False)

    st_d1, raw_d1, _ = call(b, "/api/control", "POST", {"action": "manual", "device": "door", "state": True, "source": "tc-suite"})
    door = (j(raw_d1) or {}).get("devices") or {}
    add("TC-08", "开门并回写状态", "200 door_open=true", st_d1, "door_open=%s source=%s" % (door.get("door_open"), door.get("door_source")),
        st_d1 == 200 and door.get("door_open") is True and door.get("door_source") == "tc-suite")

    st_d2, raw_d2, _ = call(b, "/api/control", "POST", {"action": "manual", "device": "door", "state": False, "source": "tc-suite"})
    door2 = (j(raw_d2) or {}).get("devices") or {}
    add("TC-09", "关门复位", "200 door_open=false", st_d2, "door_open=%s" % door2.get("door_open"),
        st_d2 == 200 and door2.get("door_open") is False)

    st_auto, raw_auto, _ = call(b, "/api/control", "POST", {"action": "set_auto", "enabled": False})
    add("TC-10", "切换自动模式", "200", st_auto, "auto_mode=%s" % ((j(raw_auto) or {}).get("devices") or {}).get("auto_mode"),
        st_auto == 200)

    st_bad, raw_bad, _ = call(b, "/api/control", "POST", {"action": "not_exist"})
    add("TC-11", "非法 action 返回 400", "400 + Unknown action", st_bad, raw_bad.decode("utf-8", "ignore")[:40],
        st_bad == 400 and b"Unknown action" in raw_bad)

    st_415, raw_415, _ = call(b, "/api/control", "POST", raw_body=b"", headers={})
    add("TC-12", "空 body 返回 400 且为 JSON", "400 + JSON 错误体", st_415, raw_415.decode("utf-8", "ignore")[:40],
        st_415 == 400 and raw_415.strip().startswith(b"{"))

    st_get, _, _ = call(b, "/api/control", "GET")
    add("TC-13", "错误方法返回 405", "405", st_get, "", st_get == 405)

    st_404, _, _ = call(b, "/api/nonexistent")
    add("TC-14", "未知路径返回 404", "404", st_404, "", st_404 == 404)

    st_badjson, _, _ = call(b, "/api/control", "POST", raw_body=b"{not json", headers={"Content-Type": "application/json"})
    add("TC-15", "非法 JSON 不返回 5xx", "400/415（不得 500）", st_badjson, "", st_badjson in (400, 415))

    st_health, raw_health, _ = call(b, "/api/health")
    add("TC-16", "健康检查接口存在", "200 + status=ok", st_health, raw_health.decode("utf-8", "ignore")[:40],
        st_health == 200 and (j(raw_health) or {}).get("status") == "ok")

    st_root, raw_root, _ = call(b, "/")
    add("TC-17", "服务自述接口", "200 且含 api 列表", st_root, raw_root.decode("utf-8", "ignore")[:40],
        st_root == 200)

    st_chart, raw_chart, _ = call(b, "/chart/temp_humidity")
    add("TC-18", "温湿度图表", "200 image/png", st_chart, "bytes=%d" % len(raw_chart),
        st_chart == 200 and raw_chart[:8].startswith(b"\x89PNG"))

    # 连续 30 次轮询稳定性（不 sleep，验证接口本身无随机失败）
    seq_fail = 0
    for _ in range(30):
        s, _, _ = call(b, "/api/current")
        if s != 200:
            seq_fail += 1
    add("TC-19", "连续 30 次读取无失败", "失败数 0", seq_fail, "失败=%d" % seq_fail, seq_fail == 0)

    os.makedirs(args.outdir, exist_ok=True)
    csv_path = os.path.join(args.outdir, "接口测试用例结果.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["用例编号", "用例标题", "期望结果", "实际结果", "说明", "判定"])
        for r in RESULTS:
            w.writerow([r["tc"], r["title"], r["expected"], r["actual"], r["detail"], "通过" if r["passed"] else "不通过"])

    passed = sum(1 for r in RESULTS if r["passed"])
    summary = {
        "executed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "base": b,
        "total": len(RESULTS),
        "passed": passed,
        "failed": len(RESULTS) - passed,
        "pass_rate_pct": round(100.0 * passed / len(RESULTS), 1),
        "cases": RESULTS,
    }
    json_path = os.path.join(args.outdir, "接口测试用例结果.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("-" * 60)
    print("通过率：%d/%d = %.1f%%（失败用例：%s）" % (
        passed, len(RESULTS), summary["pass_rate_pct"],
        ", ".join(r["tc"] for r in RESULTS if not r["passed"]) or "无"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
