# -*- coding: utf-8 -*-
"""心跳检测与断连重连验证脚本（第 9 周工程化 2 的测试手段）。

用法：
    # 1) 正常态：连续监测 60 s，每 3 s 一次
    python health_check_monitor.py --base http://127.0.0.1:5000 --duration 60 --interval 3

    # 2) 断连态：指向不存在的端口，验证“能否识别断连”
    python health_check_monitor.py --base http://127.0.0.1:5999 --duration 20 --interval 3 --tag outage

输出：
    results/心跳监测_<tag>.csv    每次探测的 status / 延迟 / 数据新鲜度
    results/心跳监测_<tag>.json   汇总：可用率、最长中断、判定

判定口径（与前端断连态一致）：
    - 连续 2 次探测失败 → 判定“断连”（进入红色横幅态）
    - 200 但 timestamp 落后 > 15 s → 判定“数据陈旧”（应提示数据不可用）
"""
import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime


def probe(base, path="/api/current", timeout=5):
    url = base.rstrip("/") + path
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read()
            return r.status, round((time.perf_counter() - t0) * 1000, 1), body
    except urllib.error.HTTPError as e:
        return e.code, round((time.perf_counter() - t0) * 1000, 1), e.read()
    except Exception as e:
        return -1, round((time.perf_counter() - t0) * 1000, 1), str(e).encode("utf-8")


def stale_seconds(body):
    """返回 timestamp 与当前时间的差（秒），解析失败返回 None。"""
    try:
        payload = json.loads(body.decode("utf-8"))
        ts = payload.get("timestamp")
        return round((datetime.now() - datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")).total_seconds(), 1)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5000")
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--interval", type=float, default=3.0)
    ap.add_argument("--tag", default="normal")
    ap.add_argument("--outdir", default="results")
    args = ap.parse_args()

    rows = []
    consecutive_fail = 0
    max_consecutive_fail = 0
    disconnected_events = 0
    stale_events = 0
    t_end = time.time() + args.duration

    print("开始监测 %s，时长 %ds，间隔 %.1fs" % (args.base, args.duration, args.interval))
    while time.time() < t_end:
        st, ms, body = probe(args.base)
        age = stale_seconds(body) if st == 200 else None
        ok = st == 200 and (age is None or age <= 15)
        if st != 200:
            consecutive_fail += 1
            max_consecutive_fail = max(max_consecutive_fail, consecutive_fail)
            if consecutive_fail == 2:
                disconnected_events += 1
        else:
            consecutive_fail = 0
        if st == 200 and age is not None and age > 15:
            stale_events += 1

        rows.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "status": st,
            "latency_ms": ms,
            "sensor_age_s": age,
            "consecutive_fail": consecutive_fail,
            "verdict": "OK" if ok else ("DISCONNECTED" if st != 200 else "STALE"),
        })
        print("  %s status=%s latency=%sms age=%ss → %s" % (
            rows[-1]["time"], st, ms, age, rows[-1]["verdict"]))
        time.sleep(args.interval)

    os.makedirs(args.outdir, exist_ok=True)
    csv_path = os.path.join(args.outdir, "心跳监测_%s.csv" % args.tag)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["time", "status", "latency_ms", "sensor_age_s", "consecutive_fail", "verdict"])
        w.writeheader()
        w.writerows(rows)

    total = len(rows)
    ok_n = sum(1 for r in rows if r["verdict"] == "OK")
    lat = [r["latency_ms"] for r in rows if r["status"] == 200]
    summary = {
        "monitored_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "base": args.base,
        "duration_s": args.duration,
        "interval_s": args.interval,
        "probes": total,
        "ok": ok_n,
        "availability_pct": round(100.0 * ok_n / total, 1) if total else 0.0,
        "disconnect_events": disconnected_events,
        "max_consecutive_failures": max_consecutive_fail,
        "stale_events": stale_events,
        "latency_avg_ms": round(sum(lat) / len(lat), 2) if lat else None,
        "latency_max_ms": max(lat) if lat else None,
        "conclusion": "",
    }
    if args.tag == "outage":
        summary["conclusion"] = ("监测逻辑正确识别断连：连续失败 %d 次、触发 %d 次断连判定" %
                                 (max_consecutive_fail, disconnected_events)
                                 if disconnected_events > 0 else "未能识别断连，监测逻辑存在缺陷")
    else:
        summary["conclusion"] = ("服务可用率 %.1f%%，无断连事件" % summary["availability_pct"]
                                 if summary["availability_pct"] >= 99.0 else
                                 "存在失败探测，需排查")

    json_path = os.path.join(args.outdir, "心跳监测_%s.json" % args.tag)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("-" * 60)
    print("探测 %d 次，可用率 %.1f%%，断连事件 %d，最长连续失败 %d，结论：%s" % (
        total, summary["availability_pct"], disconnected_events, max_consecutive_fail, summary["conclusion"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
