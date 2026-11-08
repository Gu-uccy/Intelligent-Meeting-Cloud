# -*- coding: utf-8 -*-
"""接口冒烟测试：按《接口冻结清单 api-v1.0》校验路径、参数、返回字段与错误处理。

用法：
    python check_interfaces.py --base http://127.0.0.1:5000

覆盖：
    1. GET /api/current 200 + 17 字段
    2. GET /api/history 200 数组
    3. GET /api/export/csv 200/503
    4. POST /api/control 门开/门关 往返一致
    5. POST /api/control 灯开/灯关 往返一致
    6. POST /api/control 非法 action -> 400
    7. POST /api/control 空 body -> 400
    8. GET  /api/control -> 405
    9. GET  /api/not-exist -> 404
   10. 顺序 100 次 + 并发 20×50 延迟统计

输出：
    results/接口冒烟结果.json
"""
import argparse
import json
import os
import statistics
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime

CASES = []


def call(base, path, method="GET", body=None, timeout=8):
    url = base.rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read(), (time.perf_counter() - t0) * 1000
    except Exception as e:
        return -1, str(e).encode("utf-8"), (time.perf_counter() - t0) * 1000


def record(name, expected, status, detail="", ok=None):
    passed = (status in expected) if ok is None else ok
    CASES.append({"case": name, "expected": expected, "actual_status": status, "detail": detail, "passed": passed})
    print(("[PASS] " if passed else "[FAIL] ") + name + "  status=" + str(status) + ("  " + detail if detail else ""))


def json_of_200(raw):
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def percentile(values, p):
    if not values:
        return None
    v = sorted(values)
    k = max(0, min(len(v) - 1, int(round((len(v) - 1) * p))))
    return round(v[k], 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5000")
    ap.add_argument("--out", default=os.path.join("results", "接口冒烟结果.json"))
    ap.add_argument("--skip-perf", action="store_true")
    args = ap.parse_args()

    st, raw, ms = call(args.base, "/api/current")
    body = json_of_200(raw) if st == 200 else None
    fields = len(body.keys()) if isinstance(body, dict) else 0
    record("GET /api/current", [200], st, "字段数=%d 耗时=%.1fms" % (fields, ms), ok=(st == 200 and fields >= 17))

    st_h, raw_h, _ = call(args.base, "/api/history")
    hist = json_of_200(raw_h)
    record("GET /api/history", [200], st_h, "点数=%s" % (len(hist) if isinstance(hist, list) else "n/a"), ok=(st_h == 200 and isinstance(hist, list)))

    st_c, raw_c, _ = call(args.base, "/api/export/csv")
    record("GET /api/export/csv", [200, 503], st_c, "bytes=%d" % len(raw_c))

    st_d1, raw_d1, _ = call(args.base, "/api/control", "POST", {"action": "manual", "device": "door", "state": True, "source": "if-smoke"})
    d1 = json_of_200(raw_d1) or {}
    door_open_1 = (d1.get("devices") or {}).get("door_open")
    record("POST /api/control 开门", [200], st_d1, "door_open=%s" % door_open_1, ok=(st_d1 == 200 and door_open_1 is True))

    st_d2, raw_d2, _ = call(args.base, "/api/control", "POST", {"action": "manual", "device": "door", "state": False, "source": "if-smoke"})
    d2 = json_of_200(raw_d2) or {}
    door_open_2 = (d2.get("devices") or {}).get("door_open")
    record("POST /api/control 关门", [200], st_d2, "door_open=%s" % door_open_2, ok=(st_d2 == 200 and door_open_2 is False))

    st_l1, raw_l1, _ = call(args.base, "/api/control", "POST", {"action": "manual", "device": "lighting", "state": True, "brightness": 60, "source": "if-smoke"})
    l1 = json_of_200(raw_l1) or {}
    lighting_1 = (l1.get("devices") or {}).get("lighting")
    record("POST /api/control 开灯", [200], st_l1, "lighting=%s brightness=%s" % (lighting_1, (l1.get("devices") or {}).get("lighting_brightness")), ok=(st_l1 == 200 and lighting_1 is True))

    st_l2, raw_l2, _ = call(args.base, "/api/control", "POST", {"action": "manual", "device": "lighting", "state": False, "source": "if-smoke"})
    l2 = json_of_200(raw_l2) or {}
    record("POST /api/control 关灯", [200], st_l2, "lighting=%s" % (l2.get("devices") or {}).get("lighting"), ok=(st_l2 == 200 and (l2.get("devices") or {}).get("lighting") is False))

    st_bad, raw_bad, _ = call(args.base, "/api/control", "POST", {"action": "unknown_action"})
    record("POST /api/control 非法 action", [400], st_bad, raw_bad.decode("utf-8", "ignore")[:60])

    st_null, raw_null, _ = call(args.base, "/api/control", "POST", None)
    record("POST /api/control 空 body", [400], st_null, raw_null.decode("utf-8", "ignore")[:60])

    st_m, _, _ = call(args.base, "/api/control", "GET")
    record("GET /api/control", [405], st_m)

    st_404, _, _ = call(args.base, "/api/not-exist")
    record("GET /api/not-exist", [404], st_404)

    perf = {}
    if not args.skip_perf:
        seq = []
        for _ in range(100):
            s, _, dt = call(args.base, "/api/current")
            if s == 200:
                seq.append(dt)
        perf["sequential"] = {
            "n": len(seq), "avg_ms": round(statistics.mean(seq), 2) if seq else None,
            "p50_ms": percentile(seq, 0.5), "p95_ms": percentile(seq, 0.95),
            "max_ms": round(max(seq), 2) if seq else None,
        }

        lat = []
        err = [0]
        lock = threading.Lock()

        def worker(n):
            for _ in range(n):
                s, _, dt = call(args.base, "/api/current", timeout=10)
                with lock:
                    if s == 200:
                        lat.append(dt)
                    else:
                        err[0] += 1

        t0 = time.perf_counter()
        ts = [threading.Thread(target=worker, args=(50,)) for _ in range(20)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        dur = time.perf_counter() - t0
        perf["concurrent"] = {
            "threads": 20, "per_thread": 50, "success": len(lat), "errors": err[0],
            "duration_s": round(dur, 2), "rps": round(len(lat) / dur, 2) if dur else None,
            "avg_ms": round(statistics.mean(lat), 2) if lat else None,
            "p95_ms": percentile(lat, 0.95), "p99_ms": percentile(lat, 0.99),
            "max_ms": round(max(lat), 2) if lat else None,
        }

    passed = sum(1 for c in CASES if c["passed"])
    summary = {
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "base": args.base,
        "total": len(CASES),
        "passed": passed,
        "pass_rate": round(100.0 * passed / len(CASES), 1),
        "cases": CASES,
        "perf": perf,
        "snapshot": body,
    }
    _dump(args.out, summary)
    print("-" * 68)
    print("通过 %d/%d（%.1f%%）" % (summary["passed"], summary["total"], summary["pass_rate"]))
    if perf:
        print("顺序 100 次：avg %.2f ms / p95 %.2f ms" % (perf["sequential"]["avg_ms"], perf["sequential"]["p95_ms"]))
        print("并发 20 x 50：%d 成功 / %d 失败，%.1f req/s，p95 %.2f ms" % (
            perf["concurrent"]["success"], perf["concurrent"]["errors"],
            perf["concurrent"]["rps"], perf["concurrent"]["p95_ms"]))
    return 0 if passed == len(CASES) else 1


def _dump(path, obj):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print("已写入：%s" % path)


if __name__ == "__main__":
    raise SystemExit(main())
