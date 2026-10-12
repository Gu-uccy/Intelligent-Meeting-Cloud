#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_raw_data.py
====================
第3周课堂实践作业1 —— 原始数据生成脚本（可重复运行）

数据来源说明：
    本脚本生成的数据基于本组综II（智能会议室物联网监测控制系统）的真实数据特征：
    - 字段结构与综II综合传感器系统 /api/export/csv 导出格式一致
      （时间、时间戳、温度(°C)、湿度(%)、距离(cm)、人体检测、光照、烟雾、
       制冷、加热、加湿、除湿、照明、报警、自动模式），并增加“会议室”列；
    - 数值范围与 unified_meeting_room_system.py / integrated_sensor_system.py
      中的传感器模拟逻辑一致：
        温度 10~40°C（实验实测约 26.3~33.0°C）
        湿度 10~95%（实验实测约 26.3~30.3%）
        光照 0~255、烟雾 0~200、距离 2~450cm
    - 会议室编号与数据库 meeting_room.room_code 一致：301、302、501
      （501 在数据库中 status=2 处于维修状态，因此占用率明显偏低）；
    - 为完成“数据清洗与质量检查”练习，按教学要求注入少量脏数据
      （重复记录、缺失值、异常值、命名不统一、时间格式不统一、占用状态不统一），
      每类脏数据在本脚本中明确生成，并写入 脏数据注入清单.json 以便核对。

用法：
    python scripts/generate_raw_data.py

输出：
    data/raw/原始数据样例.csv        原始（含脏数据）数据
    data/raw/脏数据注入清单.json      注入的脏数据明细（用于对照清洗结果）
"""

import csv
import json
import random
from datetime import datetime, timedelta

random.seed(20260901)  # 固定随机种子，保证可复现

# ---------------------------------------------------------------
# 1. 基本参数（与综II传感器系统一致）
# ---------------------------------------------------------------
ROOMS = ["301", "302", "501"]
START_DATE = datetime(2026, 9, 1)     # 数据起始日期
DAY_COUNT = 28                        # 共 4 周
OPEN_HOUR = 8                         # 监测开始 08:00
CLOSE_HOUR = 22                       # 监测结束 22:00（不含22:00整点）
SAMPLE_MINUTES = 5                    # 每 5 分钟一条采样
ROOM_USAGE_FACTOR = {"301": 1.0, "302": 0.8, "501": 0.15}  # 501 维修中占用率低

RAW_HEADERS = [
    "时间", "时间戳", "会议室", "温度(°C)", "湿度(%)", "光照", "烟雾",
    "距离(cm)", "人体检测", "占用状态", "制冷", "加热", "加湿", "除湿",
    "照明", "报警", "自动模式",
]

# 清洗后统一字段名（与 docs/state-object.md 字段约定一致）
UNIFIED_HEADERS = [
    "timestamp", "room_id", "temperature", "humidity", "light", "smoke",
    "distance", "motion", "occupancy", "cooling", "heating", "humidifier",
    "dehumidifier", "lighting", "alarm", "auto_mode",
]


# ---------------------------------------------------------------
# 2. 传感器数值生成（参数与项目代码 read_dht_sensor 等逻辑一致）
# ---------------------------------------------------------------
def gen_temperature(hour, room):
    """温度：08时约 26℃，午后随房间使用升高，上限 40℃（与模拟逻辑 clamp 一致）"""
    base = 26.0 + (hour - 8) * 0.45
    if room == "501":
        base -= 0.8  # 维修房间无人，温度略低
    value = base + random.uniform(-1.2, 1.2) + random.uniform(-0.3, 0.3)
    return round(max(10, min(40, value)), 1)


def gen_humidity(hour, room, temperature):
    """湿度：与温度负相关，40~60 为舒适区间，模拟逻辑 clamp 10~95"""
    base = 52.0 - (temperature - 26.0) * 1.6
    value = base + random.uniform(-3.5, 3.5) + random.uniform(-0.5, 0.5)
    return round(max(10, min(95, value)), 1)


def gen_light(hour, occupied):
    """光照：0~255，白天高、有人且无自然光时开灯"""
    if occupied:
        value = 120 + random.uniform(-20, 40)
    elif 8 <= hour < 18:
        value = 80 + random.uniform(-30, 40)
    else:
        value = 20 + random.uniform(-10, 25)
    return round(max(0, min(255, value)))


def gen_smoke():
    """烟雾：平时 0~90，3% 概率触发报警 130~200（与模拟逻辑一致）"""
    if random.random() < 0.03:
        return random.randint(130, 200)
    return round(max(0, min(90, 20 + random.uniform(-4, 4))))


def gen_distance(occupied):
    """距离：有人时靠近门禁（2~120cm），无人时 120~250cm"""
    if occupied:
        return round(random.uniform(8, 120), 1)
    return round(random.uniform(120, 250), 1)


def gen_occupancy_prob(dt, room):
    """按工作日时段与房间使用强度生成“有人”概率（业务口径）"""
    weekday = dt.weekday()  # 0=周一
    hour = dt.hour
    if weekday >= 5:  # 周末
        p = 0.08
    elif hour in (9, 10, 11):
        p = 0.85
    elif hour in (14, 15, 16, 17):
        p = 0.80
    elif hour in (18, 19):
        p = 0.45
    elif hour == 12:
        p = 0.35
    elif hour == 13:
        p = 0.50
    elif hour == 8:
        p = 0.30
    else:  # 20、21 时
        p = 0.25
    return p * ROOM_USAGE_FACTOR[room]


def gen_device_states(temp, humidity, light_value, smoke_value, occupied):
    """设备状态：与 unified_meeting_room_system.py apply_auto_control 的
    自动控制逻辑一致（TEMP_MIN=20, TEMP_MAX=26, HUMIDITY_MIN=40, HUMIDITY_MAX=60）"""
    cooling = temp > 27
    heating = temp < 19
    humidifier = humidity < 37
    dehumidifier = humidity > 63
    lighting = bool(occupied and light_value < 50)
    alarm = smoke_value > 100
    auto_mode = True
    return cooling, heating, humidifier, dehumidifier, lighting, alarm, auto_mode


# ---------------------------------------------------------------
# 3. 生成干净数据（用于注入脏数据前的底稿）
# ---------------------------------------------------------------
def build_clean_rows():
    rows = []
    idx = 0
    for day in range(DAY_COUNT):
        date = START_DATE + timedelta(days=day)
        for room in ROOMS:
            t = datetime(date.year, date.month, date.day, OPEN_HOUR, 0, 0)
            while t.hour < CLOSE_HOUR:
                temp = gen_temperature(t.hour, room)
                occupied = random.random() < gen_occupancy_prob(t, room)
                humidity = gen_humidity(t.hour, room, temp)
                light_value = gen_light(t.hour, occupied)
                smoke = gen_smoke()
                distance = gen_distance(occupied)
                motion = 1 if occupied else 0
                cooling, heating, humidifier, dehumidifier, lighting, alarm, auto_mode = \
                    gen_device_states(temp, humidity, light_value, smoke, occupied)
                rows.append({
                    "time": t.strftime("%H:%M:%S"),
                    "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
                    "room": room,
                    "temperature": temp,
                    "humidity": humidity,
                    "light": light_value,
                    "smoke": smoke,
                    "distance": distance,
                    "motion": motion,
                    "occupancy": "1" if occupied else "0",
                    "cooling": cooling,
                    "heating": heating,
                    "humidifier": humidifier,
                    "dehumidifier": dehumidifier,
                    "lighting": lighting,
                    "alarm": alarm,
                    "auto_mode": auto_mode,
                })
                idx += 1
                t += timedelta(minutes=SAMPLE_MINUTES)
    return rows


# ---------------------------------------------------------------
# 4. 脏数据注入
# ---------------------------------------------------------------
def inject_dirty(rows):
    dirty_manifest = []

    def record(kind, desc, ref_index):
        dirty_manifest.append({"kind": kind, "description": desc, "ref_row_index": ref_index})

    # 4.1 重复记录：随机抽取 40 行整体复制
    dup_targets = random.sample(range(len(rows)), 40)
    duplicated = []
    for i in dup_targets:
        duplicated.append(dict(rows[i]))
        record("重复记录", "与第 %d 行完全相同的重复行" % i, i)
    rows.extend(duplicated)

    # 4.2 会议室编号不统一（301/302/501 的别名写法）
    alias_map = {"301": ["room-301", "3F301", "301号"], "302": ["room-302", "302室"], "501": ["room-501", "5F501"]}
    alias_targets = random.sample(range(len(rows)), 36)
    for i in alias_targets:
        room = rows[i]["room"]
        alias = random.choice(alias_map[room])
        rows[i]["room"] = alias
        record("命名不统一", "会议室编号 '%s' 写成 '%s'" % (room, alias), i)

    # 4.3 时间格式不统一
    time_targets = random.sample(range(len(rows)), 30)
    for k, i in enumerate(time_targets):
        ts = datetime.strptime(rows[i]["timestamp"], "%Y-%m-%d %H:%M:%S")
        if k % 3 == 0:
            rows[i]["timestamp"] = ts.strftime("%Y/%m/%d %H:%M")
            record("时间格式", "写成 %Y/%m/%d %H:%M 格式", i)
        elif k % 3 == 1:
            rows[i]["timestamp"] = ts.strftime("%m/%d/%Y %H:%M")
            record("时间格式", "写成 %m/%d/%Y %H:%M 格式（月/日/年）", i)
        else:
            rows[i]["timestamp"] = ts.strftime("%Y-%m-%dT%H:%M")
            record("时间格式", "写成 ISO %Y-%m-%dT%H:%M 格式", i)

    # 4.4 缺失值（温度、湿度、距离、占用状态）
    miss_temp = random.sample(range(len(rows)), 24)
    for i in miss_temp:
        rows[i]["temperature"] = ""
        record("缺失值", "温度缺失", i)
    miss_hum = random.sample(range(len(rows)), 22)
    for i in miss_hum:
        rows[i]["humidity"] = ""
        record("缺失值", "湿度缺失", i)
    miss_dist = random.sample(range(len(rows)), 16)
    for i in miss_dist:
        rows[i]["distance"] = ""
        record("缺失值", "距离缺失", i)
    miss_occ = random.sample(range(len(rows)), 28)
    for i in miss_occ:
        rows[i]["occupancy"] = ""
        record("缺失值", "占用状态缺失", i)

    # 4.5 异常值（温度超出 0~50 合理范围等）
    anom_temp = [85.0, -5.0, 52.0, 58.0, -1.0]
    anom_targets = random.sample(range(len(rows)), len(anom_temp))
    for i, v in zip(anom_targets, anom_temp):
        rows[i]["temperature"] = v
        record("异常值", "温度 %s°C（超出 0~50 合理范围）" % v, i)
    anom_hum = [120.0, -3.0, 105.0]
    anom_targets = random.sample(range(len(rows)), len(anom_hum))
    for i, v in zip(anom_targets, anom_hum):
        rows[i]["humidity"] = v
        record("异常值", "湿度 %s%%（超出 0~100 合理范围）" % v, i)
    anom_dist = [999.0, -1.0, 800.0]
    anom_targets = random.sample(range(len(rows)), len(anom_dist))
    for i, v in zip(anom_targets, anom_dist):
        rows[i]["distance"] = v
        record("异常值", "距离 %scm（超出 2~450 合理范围）" % v, i)
    anom_light = [320, 280]
    anom_targets = random.sample(range(len(rows)), len(anom_light))
    for i, v in zip(anom_targets, anom_light):
        rows[i]["light"] = v
        record("异常值", "光照 %s（超出 0~255 合理范围）" % v, i)
    anom_smoke = [350]
    anom_targets = random.sample(range(len(rows)), len(anom_smoke))
    for i, v in zip(anom_targets, anom_smoke):
        rows[i]["smoke"] = v
        record("异常值", "烟雾 %s（超出 0~200 合理范围）" % v, i)

    # 4.6 占用状态写法不统一（有人/无人、true/false、2）
    occ_aliases = ["有人", "true", "无人", "false", "2"]
    occ_targets = random.sample(range(len(rows)), 26)
    for i in occ_targets:
        rows[i]["occupancy"] = random.choice(occ_aliases)
        record("占用状态不统一", "占用状态写成 '%s'" % rows[i]["occupancy"], i)

    # 打乱行顺序（模拟系统日志落库的原始顺序）
    random.shuffle(rows)
    return rows, dirty_manifest


def to_raw_row(r):
    """按综II导出 CSV 的列顺序（中文表头）输出。
    注意：占用状态列原样输出（可能为 1/0/有人/无人/true/false/2 或空），
    由清洗脚本统一，从而真实模拟“同义不同名”的脏数据场景。"""
    return [
        r["time"], r["timestamp"], r["room"], r["temperature"], r["humidity"],
        r["light"], r["smoke"], r["distance"],
        "有人" if r["motion"] == 1 else "无人",
        str(r["occupancy"]),
        "开" if r["cooling"] else "关",
        "开" if r["heating"] else "关",
        "开" if r["humidifier"] else "关",
        "开" if r["dehumidifier"] else "关",
        "开" if r["lighting"] else "关",
        "开" if r["alarm"] else "关",
        "自动" if r["auto_mode"] else "手动",
    ]


def main():
    import os
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base, "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)

    clean_rows = build_clean_rows()
    rows, manifest = inject_dirty([dict(r) for r in clean_rows])

    raw_path = os.path.join(raw_dir, "原始数据样例.csv")
    with open(raw_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(RAW_HEADERS)
        for r in rows:
            writer.writerow(to_raw_row(r))

    manifest_path = os.path.join(raw_dir, "脏数据注入清单.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "说明": "本清单记录向原始数据中注入的教学脏数据明细，用于与清洗脚本输出对照核验",
            "干净底稿行数": len(clean_rows),
            "注入后总行数": len(rows),
            "脏数据合计": len(manifest),
            "明细": manifest,
        }, f, ensure_ascii=False, indent=2)

    print("干净底稿记录数：", len(clean_rows))
    print("注入后原始记录数：", len(rows))
    print("注入脏数据条数：", len(manifest))
    print("原始数据已保存：", raw_path)
    print("脏数据清单已保存：", manifest_path)


if __name__ == "__main__":
    main()
