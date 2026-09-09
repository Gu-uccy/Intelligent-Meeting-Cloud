#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 会议室环境监测系统 - 集成温湿度、超声波距离、人体红外传感器

import time
import json
import os
import socket
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Micro Hei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt

from flask import Flask, render_template, jsonify, send_file, Response, request
from threading import Thread
import csv
import io

try:
    import board
    import adafruit_dht
    import RPi.GPIO as GPIO
    ON_RASPBERRY_PI = True
except (ImportError, NotImplementedError):
    ON_RASPBERRY_PI = False
    print("警告: 未检测到树莓派环境，使用模拟传感器数据运行")

if not ON_RASPBERRY_PI:
    import random

os.system('pkill -f libgpiod') if ON_RASPBERRY_PI else None
time.sleep(1)

current_temp = None
current_humidity = None
current_distance = None
current_motion = False
last_motion_time = 0
motion_count = 0
history_data = []
max_history_points = 100
devices = {
    "lighting": False,
    "lighting_brightness": 0,
    "lighting_source": "manual",
    "presence": False,
    "auto_mode": False,
}

DHT_PIN = None
PIR_PIN = 21
ULTRASONIC_TRIG = 17
ULTRASONIC_ECHO = 18
LED_PINS = {'Red': 19, 'Green': 27, 'Blue': 22}

if ON_RASPBERRY_PI:
    DHT_PIN = board.D5

LOG_FILE = "data/sensor_log.txt"
PLOT_DIR = "plots"

os.makedirs("data", exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)
os.makedirs("templates", exist_ok=True)

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

pwm_channels = {}
dht_device = None


def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")


# =============================================
# 【任务1】实现DHT11传感器的初始化
# =============================================
def setup_sensors():
    global dht_device

    if ON_RASPBERRY_PI:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # 任务1: DHT11传感器初始化
        try:
            dht_device = adafruit_dht.DHT11(DHT_PIN)
            log_message("DHT11传感器初始化成功")
        except Exception as e:
            log_message(f"DHT11传感器初始化失败: {e}")
            return False

        # 任务2: PIR传感器初始化 - 设置为输入模式
        try:
            GPIO.setup(PIR_PIN, GPIO.IN)
            log_message("PIR传感器初始化成功")
        except Exception as e:
            log_message(f"PIR传感器初始化失败: {e}")
            return False

        # 任务3: 超声波传感器初始化 - TRIG设为输出，ECHO设为输入
        try:
            GPIO.setup(ULTRASONIC_TRIG, GPIO.OUT)
            GPIO.setup(ULTRASONIC_ECHO, GPIO.IN)
            GPIO.output(ULTRASONIC_TRIG, GPIO.LOW)
            log_message("HC-SR04超声波传感器初始化成功")
        except Exception as e:
            log_message(f"超声波传感器初始化失败: {e}")
            return False

        # 任务4: RGB LED初始化 - 设置引脚为输出并创建PWM实例
        try:
            for color, pin in LED_PINS.items():
                GPIO.setup(pin, GPIO.OUT)
                pwm = GPIO.PWM(pin, 100)
                pwm.start(0)
                pwm_channels[color] = pwm
            log_message("RGB LED初始化成功")
        except Exception as e:
            log_message(f"RGB LED初始化失败: {e}")
            return False
    else:
        log_message("非树莓派环境，跳过GPIO初始化，使用模拟模式")
        log_message("DHT11传感器模拟初始化成功")
        log_message("PIR传感器模拟初始化成功")
        log_message("HC-SR04超声波传感器模拟初始化成功")
        log_message("RGB LED模拟初始化成功")

    return True


# =============================================
# 【任务5】实现RGB LED颜色控制
# =============================================
def set_color(color):
    if not ON_RASPBERRY_PI:
        return

    color_map = {
        'red': (100, 0, 0),
        'green': (0, 100, 0),
        'blue': (0, 0, 100),
        'yellow': (100, 100, 0),
        'purple': (100, 0, 100),
        'cyan': (0, 100, 100),
        'white': (100, 100, 100),
        'off': (0, 0, 0),
    }

    r, g, b = color_map.get(color, (0, 0, 0))

    if 'Red' in pwm_channels:
        pwm_channels['Red'].ChangeDutyCycle(r)
    if 'Green' in pwm_channels:
        pwm_channels['Green'].ChangeDutyCycle(g)
    if 'Blue' in pwm_channels:
        pwm_channels['Blue'].ChangeDutyCycle(b)


# =============================================
# 【任务6】实现DHT11温湿度数据读取
# =============================================
def set_rgb_brightness(enabled, brightness=100):
    if not ON_RASPBERRY_PI:
        return

    duty = max(0, min(100, int(brightness if enabled else 0)))
    if 'Red' in pwm_channels:
        pwm_channels['Red'].ChangeDutyCycle(duty)
    if 'Green' in pwm_channels:
        pwm_channels['Green'].ChangeDutyCycle(duty)
    if 'Blue' in pwm_channels:
        pwm_channels['Blue'].ChangeDutyCycle(duty)


def set_lighting_state(enabled, brightness=None, source="manual"):
    devices["lighting"] = bool(enabled)
    if brightness is None:
        brightness = 100 if enabled else 0
    devices["lighting_brightness"] = max(0, min(100, int(brightness)))
    devices["lighting_source"] = source
    set_rgb_brightness(devices["lighting"], devices["lighting_brightness"])


def read_dht_sensor():
    global current_temp, current_humidity

    if ON_RASPBERRY_PI and dht_device is not None:
        try:
            temperature = dht_device.temperature
            humidity = dht_device.humidity

            if temperature is not None and humidity is not None:
                current_temp = temperature
                current_humidity = humidity
                return temperature, humidity
            else:
                log_message("DHT11读取返回空值")
        except RuntimeError as e:
            log_message(f"DHT11读取错误: {e}")
        except Exception as e:
            log_message(f"DHT11未知错误: {e}")

        return current_temp, current_humidity
    else:
        if current_temp is None:
            current_temp = 25.0 + random.uniform(-2, 2)
        if current_humidity is None:
            current_humidity = 50.0 + random.uniform(-5, 5)

        current_temp += random.uniform(-0.3, 0.3)
        current_humidity += random.uniform(-0.5, 0.5)

        current_temp = round(max(0, min(50, current_temp)), 1)
        current_humidity = round(max(20, min(90, current_humidity)), 1)

        return current_temp, current_humidity


# =============================================
# 【任务7】实现超声波距离测量
# =============================================
def read_distance_sensor():
    global current_distance

    if ON_RASPBERRY_PI:
        try:
            GPIO.output(ULTRASONIC_TRIG, GPIO.LOW)
            time.sleep(0.002)

            GPIO.output(ULTRASONIC_TRIG, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(ULTRASONIC_TRIG, GPIO.LOW)

            pulse_start = time.time()
            timeout_start = time.time()

            while GPIO.input(ULTRASONIC_ECHO) == GPIO.LOW:
                pulse_start = time.time()
                if pulse_start - timeout_start > 0.1:
                    log_message("超声波传感器超时 (未检测到回波开始)")
                    return current_distance

            pulse_end = time.time()
            timeout_start = time.time()

            while GPIO.input(ULTRASONIC_ECHO) == GPIO.HIGH:
                pulse_end = time.time()
                if pulse_end - timeout_start > 0.1:
                    log_message("超声波传感器超时 (回波信号过长)")
                    return current_distance

            pulse_duration = pulse_end - pulse_start
            distance = (pulse_duration * 34000) / 2

            if 2 <= distance <= 450:
                current_distance = round(distance, 1)
            else:
                log_message(f"超声波测量超出范围: {distance:.1f}cm")

            return current_distance

        except Exception as e:
            log_message(f"超声波传感器读取错误: {e}")
            return current_distance
    else:
        if current_distance is None:
            current_distance = 100.0 + random.uniform(-30, 30)

        current_distance += random.uniform(-2, 2)
        current_distance = round(max(2, min(450, current_distance)), 1)
        return current_distance


# =============================================
# 【任务8】实现人体移动检测
# =============================================
def read_pir_sensor():
    global current_motion, last_motion_time, motion_count

    if ON_RASPBERRY_PI:
        try:
            motion_detected = GPIO.input(PIR_PIN) == GPIO.HIGH

            if motion_detected and not current_motion:
                motion_count += 1
                last_motion_time = time.time()
                devices["presence"] = True
                log_message("检测到人体移动")

            if motion_detected:
                current_motion = True
            else:
                current_motion = False
                devices["presence"] = False

            return current_motion

        except Exception as e:
            log_message(f"PIR传感器读取错误: {e}")
            return current_motion
    else:
        motion_detected = random.random() < 0.1

        if motion_detected and not current_motion:
            motion_count += 1
            last_motion_time = time.time()
            log_message("检测到人体移动 (模拟)")

        current_motion = motion_detected
        devices["presence"] = current_motion
        return current_motion


# =============================================
# 读取所有传感器数据并更新历史记录
# =============================================
def read_all_sensors():
    global history_data

    temp, humidity = read_dht_sensor()
    distance = read_distance_sensor()
    motion = read_pir_sensor()

    if temp is not None and humidity is not None and distance is not None:
        current_time = datetime.now().strftime("%H:%M:%S")
        full_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data_point = {
            "time": current_time,
            "timestamp": full_timestamp,
            "temperature": temp,
            "humidity": humidity,
            "distance": distance,
            "motion": 1 if motion else 0
        }

        history_data.append(data_point)

        if len(history_data) > max_history_points:
            history_data = history_data[-max_history_points:]

        log_message(
            f"当前读数: 温度 {temp:.1f}°C, 湿度 {humidity:.1f}%, "
            f"距离 {distance:.1f}cm, 有人: {'是' if motion else '否'}"
        )
        return True

    return False


# =============================================
# 【任务9】实现温湿度趋势图生成
# =============================================
def generate_temperature_humidity_chart():
    if len(history_data) < 2:
        return

    timestamps = [d["time"] for d in history_data]
    temperatures = [d["temperature"] for d in history_data]
    humidities = [d["humidity"] for d in history_data]

    fig, ax1 = plt.subplots(figsize=(10, 6))

    color_temp = '#dc3545'
    ax1.set_xlabel('时间', fontsize=12)
    ax1.set_ylabel('温度 (°C)', color=color_temp, fontsize=12)
    line1, = ax1.plot(timestamps, temperatures, color=color_temp, marker='o',
                      markersize=3, linewidth=1.5, label='温度')
    ax1.tick_params(axis='y', labelcolor=color_temp)
    ax1.set_ylim(min(temperatures) - 2, max(temperatures) + 2)

    ax2 = ax1.twinx()
    color_hum = '#0d6efd'
    ax2.set_ylabel('湿度 (%)', color=color_hum, fontsize=12)
    line2, = ax2.plot(timestamps, humidities, color=color_hum, marker='s',
                      markersize=3, linewidth=1.5, label='湿度')
    ax2.tick_params(axis='y', labelcolor=color_hum)
    ax2.set_ylim(min(humidities) - 5, max(humidities) + 5)

    lines = [line1, line2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', fontsize=10)

    xticks_indices = range(0, len(timestamps), max(1, len(timestamps) // 10))
    ax1.set_xticks([timestamps[i] for i in xticks_indices])
    ax1.set_xticklabels([timestamps[i] for i in xticks_indices], rotation=45, fontsize=8)

    plt.title('温湿度趋势图', fontsize=14, fontweight='bold')
    fig.tight_layout()

    file_path = f"{PLOT_DIR}/temp_humidity_chart.png"
    plt.savefig(file_path, dpi=100, bbox_inches='tight')
    plt.close(fig)
    log_message("温湿度趋势图已更新")


# =============================================
# 【任务10】实现距离和运动趋势图生成
# =============================================
def generate_distance_motion_chart():
    if len(history_data) < 2:
        return

    timestamps = [d["time"] for d in history_data]
    distances = [d["distance"] for d in history_data]
    motions = [d["motion"] for d in history_data]

    fig, ax1 = plt.subplots(figsize=(10, 6))

    color_dist = '#198754'
    ax1.set_xlabel('时间', fontsize=12)
    ax1.set_ylabel('距离 (cm)', color=color_dist, fontsize=12)
    line1, = ax1.plot(timestamps, distances, color=color_dist, marker='o',
                      markersize=3, linewidth=1.5, label='距离')
    ax1.tick_params(axis='y', labelcolor=color_dist)
    ax1.set_ylim(max(0, min(distances) - 10), max(distances) + 10)

    ax2 = ax1.twinx()
    color_mot = '#fd7e14'
    ax2.set_ylabel('人体检测', color=color_mot, fontsize=12)
    line2, = ax2.fill_between(range(len(timestamps)), 0, motions, alpha=0.3,
                               color=color_mot, step='post', label='人体检测')
    ax2.set_ylim(0, 1.5)
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(['无人', '有人'])
    ax2.tick_params(axis='y', labelcolor=color_mot)

    lines = [line1, line2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', fontsize=10)

    xticks_indices = range(0, len(timestamps), max(1, len(timestamps) // 10))
    ax1.set_xticks([timestamps[i] for i in xticks_indices])
    ax1.set_xticklabels([timestamps[i] for i in xticks_indices], rotation=45, fontsize=8)

    plt.title('距离和运动趋势图', fontsize=14, fontweight='bold')
    fig.tight_layout()

    file_path = f"{PLOT_DIR}/distance_motion_chart.png"
    plt.savefig(file_path, dpi=100, bbox_inches='tight')
    plt.close(fig)
    log_message("距离和运动趋势图已更新")


def generate_all_charts():
    generate_temperature_humidity_chart()
    generate_distance_motion_chart()


def sensor_thread_function():
    last_chart_update = 0

    while True:
        read_all_sensors()

        current_time = time.time()
        if current_time - last_chart_update > 60:
            generate_all_charts()
            last_chart_update = current_time

        time.sleep(3)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/current')
def get_current_data():
    global current_temp, current_humidity, current_distance, current_motion, last_motion_time, motion_count

    if current_temp is None or current_humidity is None or current_distance is None:
        return jsonify({"error": "Sensor data not available"}), 503

    last_motion_str = '从未'
    if last_motion_time > 0:
        time_diff = time.time() - last_motion_time
        if time_diff < 60:
            last_motion_str = f"{int(time_diff)} 秒前"
        elif time_diff < 3600:
            last_motion_str = f"{int(time_diff / 60):.0f} 分钟前"
        else:
            last_motion_str = datetime.fromtimestamp(last_motion_time).strftime("%Y-%m-%d %H:%M:%S")

    return jsonify({
        "temperature": current_temp,
        "humidity": current_humidity,
        "distance": current_distance,
        "motion": current_motion,
        "presence": current_motion,
        "motion_count": motion_count,
        "last_motion": last_motion_str,
        "devices": devices,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route('/api/history')
def get_history_data():
    return jsonify(history_data)


@app.route('/api/control', methods=['POST'])
def manual_control():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid request"}), 400

    action = data.get("action")
    if action == "manual":
        device = data.get("device")
        state = bool(data.get("state", False))
        if device == "lighting":
            set_lighting_state(
                state,
                data.get("brightness", 100 if state else 0),
                data.get("source", "manual"),
            )
            log_message(f"Manual lighting control: {state}")
            return jsonify({"success": True, "devices": devices})
        return jsonify({"error": "Unsupported device"}), 400

    if action == "set_auto":
        devices["auto_mode"] = bool(data.get("enabled", False))
        return jsonify({"success": True, "devices": devices})

    return jsonify({"error": "Unknown action"}), 400


@app.route('/chart/temp_humidity')
def chart_temp_humidity():
    file_path = f"{PLOT_DIR}/temp_humidity_chart.png"
    if not os.path.exists(file_path):
        generate_temperature_humidity_chart()

    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/png')
    else:
        return jsonify({"error": "Chart not available"}), 503


@app.route('/chart/distance_motion')
def chart_distance_motion():
    file_path = f"{PLOT_DIR}/distance_motion_chart.png"
    if not os.path.exists(file_path):
        generate_distance_motion_chart()

    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/png')
    else:
        return jsonify({"error": "Chart not available"}), 503


# =============================================
# 【任务11】实现CSV数据导出功能
# =============================================
@app.route('/api/export/csv')
def export_csv():
    if not history_data:
        return jsonify({"error": "No data to export"}), 503

    try:
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(['时间', '时间戳', '温度(°C)', '湿度(%)', '距离(cm)', '人体检测'])

        for record in history_data:
            writer.writerow([
                record.get('time', ''),
                record.get('timestamp', ''),
                record.get('temperature', ''),
                record.get('humidity', ''),
                record.get('distance', ''),
                '有人' if record.get('motion', 0) == 1 else '无人'
            ])

        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=sensor_data.csv',
                'Content-Type': 'text/csv; charset=utf-8-sig'
            }
        )
    except Exception as e:
        log_message(f"CSV导出失败: {e}")
        return jsonify({"error": "CSV export failed"}), 500


def create_template_files():
    os.makedirs('templates', exist_ok=True)

    html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>会议室环境监测系统</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            padding-top: 20px;
            background-color: #f8f9fa;
        }
        .card {
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        .card-header {
            background-color: #6c757d;
            color: white;
            border-radius: 10px 10px 0 0 !important;
        }
        .display-value {
            font-size: 2.5rem;
            font-weight: 300;
        }
        .temperature {
            color: #dc3545;
        }
        .humidity {
            color: #0d6efd;
        }
        .distance {
            color: #198754;
        }
        .motion {
            color: #fd7e14;
        }
        .timestamp {
            font-size: 0.8rem;
            color: #6c757d;
        }
        .chart-container {
            position: relative;
            height: 350px;
        }
        .sensor-icon {
            font-size: 2rem;
            margin-right: 15px;
        }
        .export-btn {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .motion-indicator {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: inline-block;
            margin-left: 10px;
            background-color: gray;
        }
        .motion-active {
            background-color: yellow;
        }
        .motion-inactive {
            background-color: blue;
        }
        @media (max-width: 768px) {
            .display-value {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="text-center mb-4">会议室环境监测系统 <span id="motion-indicator" class="motion-indicator motion-inactive"></span></h1>

        <div class="row">
            <div class="col-md-3">
                <div class="card">
                    <div class="card-header d-flex align-items-center">
                        <i class="bi bi-thermometer-half sensor-icon"></i>
                        <span>温度</span>
                    </div>
                    <div class="card-body text-center">
                        <div class="display-value temperature" id="current-temperature">--</div>
                        <div>摄氏度 (°C)</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card">
                    <div class="card-header d-flex align-items-center">
                        <i class="bi bi-droplet-half sensor-icon"></i>
                        <span>湿度</span>
                    </div>
                    <div class="card-body text-center">
                        <div class="display-value humidity" id="current-humidity">--</div>
                        <div>相对湿度 (%)</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card">
                    <div class="card-header d-flex align-items-center">
                        <i class="bi bi-rulers sensor-icon"></i>
                        <span>距离</span>
                    </div>
                    <div class="card-body text-center">
                        <div class="display-value distance" id="current-distance">--</div>
                        <div>厘米 (cm)</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card">
                    <div class="card-header d-flex align-items-center">
                        <i class="bi bi-person-badge sensor-icon"></i>
                        <span>人体检测</span>
                    </div>
                    <div class="card-body text-center">
                        <div class="display-value motion" id="motion-status">--</div>
                        <div>检测到的运动次数: <span id="motion-count">0</span></div>
                        <div>最近一次运动: <span id="last-motion">从未</span></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-3">
            <div class="col text-end">
                <a href="/api/export/csv" class="btn btn-success export-btn">
                    <i class="bi bi-file-earmark-excel"></i> 导出CSV
                </a>
            </div>
        </div>

        <div class="row">
            <div class="col-12">
                <div class="card chart-container">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>温湿度趋势图</span>
                        <span class="timestamp" id="last-updated">最后更新时间: --</span>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <img id="temp-humidity-chart" src="/chart/temp_humidity" class="img-fluid" alt="温湿度趋势图">
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-12">
                <div class="card chart-container">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>距离和运动趋势图</span>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <img id="distance-motion-chart" src="/chart/distance_motion" class="img-fluid" alt="距离和运动趋势图">
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span>环境参数说明</span>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-3">
                        <h5><i class="bi bi-thermometer-half text-danger"></i> 温度</h5>
                        <p>会议室的理想温度应保持在20-25°C之间，以确保舒适度和工作效率。</p>
                    </div>
                    <div class="col-md-3">
                        <h5><i class="bi bi-droplet-half text-primary"></i> 湿度</h5>
                        <p>相对湿度以40-60%为宜，过高或过低都会影响人体舒适度和设备性能。</p>
                    </div>
                    <div class="col-md-3">
                        <h5><i class="bi bi-rulers text-success"></i> 距离</h5>
                        <p>显示超声波传感器测量的距离，可用于监测会议室中距离传感器最近物体的距离。</p>
                    </div>
                    <div class="col-md-3">
                        <h5><i class="bi bi-person-badge text-warning"></i> 人体检测</h5>
                        <p>显示会议室中是否检测到人员活动，可用于统计使用情况和自动化控制。</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function updateCurrentData() {
            fetch('/api/current')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('current-temperature').textContent = data.temperature.toFixed(1);
                    document.getElementById('current-humidity').textContent = data.humidity.toFixed(1);
                    document.getElementById('current-distance').textContent = data.distance.toFixed(1);
                    document.getElementById('motion-status').textContent = data.motion ? '有人' : '无人';
                    document.getElementById('motion-count').textContent = data.motion_count;
                    document.getElementById('last-motion').textContent = data.last_motion;

                    const indicator = document.getElementById('motion-indicator');
                    if (data.motion) {
                        indicator.className = 'motion-indicator motion-active';
                        document.getElementById('motion-status').className = 'display-value motion';
                    } else {
                        indicator.className = 'motion-indicator motion-inactive';
                        document.getElementById('motion-status').className = 'display-value motion';
                    }

                    document.getElementById('last-updated').textContent = '最后更新时间: ' + data.timestamp;
                })
                .catch(error => console.error('Error fetching current data:', error));
        }

        function refreshCharts() {
            const timestamp = new Date().getTime();
            document.getElementById('temp-humidity-chart').src = `/chart/temp_humidity?t=${timestamp}`;
            document.getElementById('distance-motion-chart').src = `/chart/distance_motion?t=${timestamp}`;
        }

        setInterval(updateCurrentData, 2000);
        setInterval(refreshCharts, 60000);

        updateCurrentData();
    </script>
</body>
</html>'''

    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    log_message("模板文件创建成功")


def cleanup_resources():
    try:
        if ON_RASPBERRY_PI:
            for pwm in pwm_channels.values():
                if pwm:
                    pwm.stop()
            GPIO.cleanup()
        log_message("资源已释放，程序结束")
    except Exception as e:
        log_message(f"清理资源时出错: {e}")


# =============================================
# 【任务12】运行Web服务器
# =============================================
def main():
    if ON_RASPBERRY_PI:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

    log_message("会议室环境监测系统启动...")

    create_template_files()

    if not setup_sensors():
        log_message("传感器初始化失败，程序退出")
        cleanup_resources()
        return

    sensor_thread = Thread(target=sensor_thread_function, daemon=True)
    sensor_thread.start()

    try:
        host_ip = '0.0.0.0'
        ports_to_try = [5000, 9090, 5001, 3000]
        port = 5000
        for p in ports_to_try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = s.connect_ex(('127.0.0.1', p))
            s.close()
            if result != 0:
                port = p
                break

        if ON_RASPBERRY_PI:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))
                host_ip = s.getsockname()[0]
                s.close()
            except Exception:
                host_ip = '127.0.0.1'

        log_message(f"Web服务器启动于 http://{host_ip}:{port}")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        log_message("Web服务器已停止")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("程序已停止")
    except Exception as e:
        log_message(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if ON_RASPBERRY_PI:
            os.system('pkill -f libgpiod')
        cleanup_resources()
