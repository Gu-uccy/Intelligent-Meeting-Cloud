# -*- coding: utf-8 -*-
"""性能测试（第 11 周必做项）：可重复执行，输出通过率、响应时间、吞吐与资源占用。

用法：
    python performance_test.py --base http://127.0.0.1:5000 --rounds 3 --seq 100 --threads 20 --per-thread 50

输出：
    results/性能测试结果.csv     逐轮指标
    results/性能测试结果.md      可直接贴进测试报告
    results/性能测试结果.json    原始数据（含每轮分位值）

判定阈值（可改，必须写明依据）：
    P95 ≤ 100 ms、错误率 ≤ 1%、吞吐 ≥ 200 req/s
    —— 依据：前端轮询周期 3 s、单次页面最多 1 个请求，100 ms 已远小于轮询间隔。
"""
import argparse
import csv
import json
import os
import statistics
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime

THRESHOLDS = {"p95_ms": 100.0, "error_rate_pct": 1.0, "rps": 200.0}


def http_get(base, path, timeout=10):
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(base.rstrip("/") + path, timeout=timeout) as r:
            r.read()
            return r.status, (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError as e:
        e.read()
        return e.code, (time.perf_counter() - t0) * 1000
    except Exception:
        return -1, (time.perf_counter() - t0) * 1000


def pct(values, p):
    if not values:
        return 0.0
    v = sorted(values)
    k = max(0, min(len(v) - 1, int(round((len(v) - 1) * p))))
    return round(v[k], 2)


def find_proc(pattern="unified_meeting_room_system.py"):
    """定位被测服务进程（无 psutil 时返回 None，不阻塞测试）。"""
    try:
        import psutil
    except Exception:
        return None
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = " ".join(p.info.get("cmdline") or [])
            if pattern in cmd:
                return p
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def cpu_seconds(proc):
    if proc is None:
        return None
    try:
        t = proc.cpu_times()
        return t.user + t.system
    except Exception:
        return None


def resource_of(proc):
    """采样目标服务进程的 RSS（MB）；CPU 百分比由整轮耗时内的 CPU 时间差计算。"""
    if proc is None:
        return None
    try:
        return {"pid": proc.pid, "rss_mb": round(proc.memory_info().rss / (1024 * 1024), 1)}
    except Exception:
        return None


def run_round(base, rnd, seq_n, threads, per_thread):
    proc = find_proc()
    cpu0 = cpu_seconds(proc)
    seq, seq_err = [], 0
    for _ in range(seq_n):
        st, ms = http_get(base, "/api/current")
        if st == 200:
            seq.append(ms)
        else:
            seq_err += 1

    lat = []
    err = [0]
    lock = threading.Lock()

    def worker(n):
        for _ in range(n):
            st, ms = http_get(base, "/api/current")
            with lock:
                if st == 200:
                    lat.append(ms)
                else:
                    err[0] += 1

    ts = [threading.Thread(target=worker, args=(per_thread,)) for _ in range(threads)]
    t0 = time.perf_counter()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    dur = time.perf_counter() - t0

    res_before = resource_of(proc)
    if res_before is not None and cpu0 is not None:
        cpu1 = cpu_seconds(proc)
        if cpu1 is not None and dur > 0:
            res_before["cpu_pct"] = round((cpu1 - cpu0) / dur * 100.0, 1)
    total = threads * per_thread
    record = {
        "round": rnd,
        "started_at": datetime.now().strftime("%H:%M:%S"),
        "sequential": {
            "n": len(seq), "errors": seq_err,
            "avg_ms": round(statistics.mean(seq), 2) if seq else 0.0,
            "p50_ms": pct(seq, 0.5), "p95_ms": pct(seq, 0.95), "max_ms": round(max(seq), 2) if seq else 0.0,
            "pass_rate_pct": round(100.0 * len(seq) / seq_n, 1) if seq_n else 0.0,
        },
        "concurrent": {
            "threads": threads, "per_thread": per_thread, "total": total,
            "success": len(lat), "errors": err[0],
            "duration_s": round(dur, 2),
            "rps": round(len(lat) / dur, 2) if dur else 0.0,
            "avg_ms": round(statistics.mean(lat), 2) if lat else 0.0,
            "p95_ms": pct(lat, 0.95), "p99_ms": pct(lat, 0.99),
            "max_ms": round(max(lat), 2) if lat else 0.0,
            "pass_rate_pct": round(100.0 * len(lat) / total, 1) if total else 0.0,
        },
        "resource": res_before,
    }
    return record


def judge(record):
    c = record["concurrent"]
    s = record["sequential"]
    reasons = []
    if s["p95_ms"] > THRESHOLDS["p95_ms"] or c["p95_ms"] > THRESHOLDS["p95_ms"]:
        reasons.append("P95 超阈值")
    err_rate = 100.0 * (c["errors"] + s["errors"]) / max(1, (c["total"] + s["n"]))
    if err_rate > THRESHOLDS["error_rate_pct"]:
        reasons.append("错误率 %.2f%% 超阈值" % err_rate)
    if c["rps"] < THRESHOLDS["rps"]:
        reasons.append("吞吐低于阈值")
    return ("通过" if not reasons else "不通过"), reasons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5000")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--seq", type=int, default=100)
    ap.add_argument("--threads", type=int, default=20)
    ap.add_argument("--per-thread", type=int, default=50)
    ap.add_argument("--outdir", default="results")
    args = ap.parse_args()

    rounds = []
    for i in range(1, args.rounds + 1):
        print("第 %d/%d 轮 ..." % (i, args.rounds))
        r = run_round(args.base, i, args.seq, args.threads, args.per_thread)
        r["verdict"], r["reasons"] = judge(r)
        rounds.append(r)
        print("  顺序 avg %.2f ms / P95 %.2f ms | 并发 %.1f req/s / P95 %.2f ms / 错误 %d → %s" % (
            r["sequential"]["avg_ms"], r["sequential"]["p95_ms"],
            r["concurrent"]["rps"], r["concurrent"]["p95_ms"], r["concurrent"]["errors"], r["verdict"]))

    os.makedirs(args.outdir, exist_ok=True)
    csv_path = os.path.join(args.outdir, "性能测试结果.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["轮次", "顺序次数", "顺序通过率%", "顺序avg_ms", "顺序P95_ms",
                    "并发线程", "并发每线程", "并发成功", "并发错误", "并发通过率%",
                    "吞吐req/s", "并发avg_ms", "并发P95_ms", "并发P99_ms", "并发max_ms",
                    "服务RSS_MB", "服务CPU%", "判定"])
        for r in rounds:
            s, c = r["sequential"], r["concurrent"]
            res = r["resource"] or {}
            w.writerow([r["round"], s["n"], s["pass_rate_pct"], s["avg_ms"], s["p95_ms"],
                        c["threads"], c["per_thread"], c["success"], c["errors"], c["pass_rate_pct"],
                        c["rps"], c["avg_ms"], c["p95_ms"], c["p99_ms"], c["max_ms"],
                        res.get("rss_mb", "n/a"), res.get("cpu_pct", "n/a"), r["verdict"]])

    md_path = os.path.join(args.outdir, "性能测试结果.md")
    lines = ["# 性能测试结果（自动生成）", "",
             "- 执行时间：%s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             "- 目标：`%s` / `GET /api/current`" % args.base,
             "- 轮次：%d，顺序 %d 次，并发 %d×%d" % (len(rounds), args.seq, args.threads, args.per_thread),
             "- 判定阈值：P95 ≤ %.0f ms，错误率 ≤ %.1f%%，吞吐 ≥ %.0f req/s" % (
                 THRESHOLDS["p95_ms"], THRESHOLDS["error_rate_pct"], THRESHOLDS["rps"]),
             "",
             "| 轮次 | 顺序 avg(ms) | 顺序 P95(ms) | 顺序通过率 | 吞吐(req/s) | 并发 P95(ms) | 并发 P99(ms) | 错误数 | 并发通过率 | RSS(MB) | 判定 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rounds:
        s, c = r["sequential"], r["concurrent"]
        res = r["resource"] or {}
        lines.append("| %d | %.2f | %.2f | %.1f%% | %.1f | %.2f | %.2f | %d | %.1f%% | %s | %s |" % (
            r["round"], s["avg_ms"], s["p95_ms"], s["pass_rate_pct"], c["rps"],
            c["p95_ms"], c["p99_ms"], c["errors"], c["pass_rate_pct"], res.get("rss_mb", "n/a"), r["verdict"]))
    if rounds:
        c0 = rounds[0]["concurrent"]
        lines += ["", "稳定性判断：3 轮 P95 极差 %.2f ms（%.1f%%），错误数合计 %d，结论：%s" % (
            round(max(r["concurrent"]["p95_ms"] for r in rounds) - min(r["concurrent"]["p95_ms"] for r in rounds), 2),
            round((max(r["concurrent"]["p95_ms"] for r in rounds) - min(r["concurrent"]["p95_ms"] for r in rounds)) /
                  max(1e-9, statistics.mean([r["concurrent"]["p95_ms"] for r in rounds])) * 100.0, 1),
            sum(r["concurrent"]["errors"] for r in rounds),
            "服务性能稳定，可支撑 3 s 轮询" if all(r["verdict"] == "通过" for r in rounds) else "存在不达标轮次，需复测")]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    json_path = os.path.join(args.outdir, "性能测试结果.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   "target": args.base, "thresholds": THRESHOLDS, "rounds": rounds},
                  f, ensure_ascii=False, indent=2)

    print("已写入：%s / %s / %s" % (csv_path, md_path, json_path))
    return 0 if all(r["verdict"] == "通过" for r in rounds) else 1


if __name__ == "__main__":
    raise SystemExit(main())
