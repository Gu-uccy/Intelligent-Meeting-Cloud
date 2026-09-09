#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 树莓派智能温湿度控制系统 - 集成光敏、烟雾、人体红外传感器

import time
import json
import os
import socket
import threading
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Micro Hei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt

from flask import Flask, render_template, jsonify, send_file, request, Response
import csv
import io

try:
    import board
    import adafruit_dht
    import RPi.GPIO as GPIO
    import smbus
    ON_RASPBERRY_PI = True
except (ImportError, NotImplementedError):
    ON_RASPBERRY_PI = False
    print("警告: 未检测到树莓派环境，使用模拟传感器数据运行")

if not ON_RASPBERRY_PI:
    import random

os.system('pkill -f libgpiod') if ON_RASPBERRY_PI else None
time.sleep(1)

data_lock = threading.Lock()

current_temp = None
current_humidity = None
current_light = 128
current_smoke = 0
current_presence = False
last_alarm_time = 0
last_presence_time = 0

TEMP_MIN = 20
TEMP_MAX = 26
HUMIDITY_MIN = 40
HUMIDITY_MAX = 60

history_data = []
max_history_points = 100

devices = {
    'cooling': False,
    'heating': False,
    'humidifier': False,
    'dehumidifier': False,
    'lighting': False,
    'lighting_brightness': 0,
    'alarm': False,
    'presence': False,
    'auto_mode': True
}

DHT_PIN = None
PIR_PIN = 17
BUZZER_PIN = 18
PCF8591_ADDR = 0x48

if ON_RASPBERRY_PI:
    DHT_PIN = board.D5

LOG_FILE = "data/sensor_log.txt"
PLOT_DIR = "plots"

os.makedirs("data", exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)
os.makedirs("templates", exist_ok=True)

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

dht_device = None
pwm_channels = {}


def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")


def setup_sensors():
    global dht_device

    if ON_RASPBERRY_PI:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        try:
            dht_device = adafruit_dht.DHT11(DHT_PIN)
            log_message("DHT11传感器初始化成功")
        except Exception as e:
            log_message(f"DHT11传感器初始化失败: {e}")
            return False

        try:
            GPIO.setup(PIR_PIN, GPIO.IN)
            log_message("PIR人体红外传感器初始化成功 (GPIO17)")
        except Exception as e:
            log_message(f"PIR传感器初始化失败: {e}")

        try:
            GPIO.setup(BUZZER_PIN, GPIO.OUT)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
            log_message("蜂鸣报警器初始化成功 (GPIO18)")
        except Exception as e:
            log_message(f"蜂鸣报警器初始化失败: {e}")

        try:
            bus = smbus.SMBus(1)
            bus.write_byte(PCF8591_ADDR, 0x40)
            bus.read_byte(PCF8591_ADDR)
            log_message("PCF8591 A/D转换模块初始化成功")
        except Exception as e:
            log_message(f"PCF8591初始化失败: {e}")
    else:
        log_message("非树莓派环境，使用模拟模式")

    return True


def set_buzzer(enabled):
    if not ON_RASPBERRY_PI:
        return

    try:
        GPIO.output(BUZZER_PIN, GPIO.HIGH if enabled else GPIO.LOW)
    except Exception as e:
        log_message(f"蜂鸣报警器控制失败: {e}")


def read_sensor():
    global current_temp, current_humidity

    if ON_RASPBERRY_PI and dht_device is not None:
        for _ in range(5):
            try:
                temperature = dht_device.temperature
                humidity = dht_device.humidity

                if temperature is not None and humidity is not None:
                    current_temp = round(temperature, 1)
                    current_humidity = round(humidity, 1)
                    return current_temp, current_humidity
            except RuntimeError as e:
                log_message(f"DHT11读取错误: {e}")
                time.sleep(2)
            except Exception as e:
                log_message(f"DHT11未知错误: {e}")
                time.sleep(2)

        log_message("传感器读取失败，使用上次有效值")
        return current_temp, current_humidity
    else:
        if current_temp is None:
            current_temp = 25.0 + random.uniform(-2, 2)
        if current_humidity is None:
            current_humidity = 50.0 + random.uniform(-5, 5)
        return current_temp, current_humidity


def simulate_environment():
    global current_temp, current_humidity

    with data_lock:
        if current_temp is None or current_humidity is None:
            current_temp = 25.0
            current_humidity = 50.0

        temp = current_temp
        humidity = current_humidity

        if devices['cooling']:
            temp -= 0.2
        if devices['heating']:
            temp += 0.2
        if devices['humidifier']:
            humidity += 0.3
        if devices['dehumidifier']:
            humidity -= 0.3

        temp += random.uniform(-0.1, 0.1) if not ON_RASPBERRY_PI else 0
        humidity += random.uniform(-0.15, 0.15) if not ON_RASPBERRY_PI else 0

        temp = round(max(10, min(40, temp)), 1)
        humidity = round(max(10, min(95, humidity)), 1)

        current_temp = temp
        current_humidity = humidity


def control_devices():
    global devices

    TEMP_HYSTERESIS = 1.0
    HUMIDITY_HYSTERESIS = 3.0

    with data_lock:
        temp = current_temp
        humidity = current_humidity

    if temp is None or humidity is None:
        return

    if not devices['auto_mode']:
        return

    if temp > TEMP_MAX + TEMP_HYSTERESIS:
        devices['cooling'] = True
        devices['heating'] = False
    elif temp < TEMP_MIN - TEMP_HYSTERESIS:
        devices['heating'] = True
        devices['cooling'] = False
    elif TEMP_MIN <= temp <= TEMP_MAX:
        devices['cooling'] = False
        devices['heating'] = False

    if humidity > HUMIDITY_MAX + HUMIDITY_HYSTERESIS:
        devices['dehumidifier'] = True
        devices['humidifier'] = False
    elif humidity < HUMIDITY_MIN - HUMIDITY_HYSTERESIS:
        devices['humidifier'] = True
        devices['dehumidifier'] = False
    elif HUMIDITY_MIN <= humidity <= HUMIDITY_MAX:
        devices['dehumidifier'] = False
        devices['humidifier'] = False


def read_light_sensor():
    global current_light

    if ON_RASPBERRY_PI:
        try:
            bus = smbus.SMBus(1)
            bus.write_byte(PCF8591_ADDR, 0x40)
            bus.read_byte(PCF8591_ADDR)
            value = bus.read_byte(PCF8591_ADDR)
            light_value = 255 - value
            current_light = light_value
            return light_value
        except Exception as e:
            log_message(f"读取光敏电阻错误: {e}")
            return current_light
    else:
        if current_light is None:
            current_light = 128
        current_light += random.uniform(-3, 3)
        current_light = round(max(0, min(255, current_light)))
        return current_light


def control_lighting(light_value):
    global devices
    presence_aware = devices.get('presence', True)

    LIGHT_THRESHOLD_LOW = 50
    LIGHT_THRESHOLD_HIGH = 150

    if light_value < LIGHT_THRESHOLD_LOW:
        if not devices['lighting'] or not presence_aware:
            devices['lighting'] = True
            brightness = 100 - int((light_value / LIGHT_THRESHOLD_LOW) * 100)
            brightness = max(10, min(100, brightness))
            devices['lighting_brightness'] = brightness
            log_message(f"光线不足 ({light_value})，开灯，亮度：{brightness}%")
    elif light_value > LIGHT_THRESHOLD_HIGH:
        if devices['lighting']:
            devices['lighting'] = False
            devices['lighting_brightness'] = 0
            log_message(f"光线充足 ({light_value})，关灯")


def read_smoke_sensor():
    global current_smoke

    if ON_RASPBERRY_PI:
        try:
            bus = smbus.SMBus(1)
            bus.write_byte(PCF8591_ADDR, 0x41)
            bus.read_byte(PCF8591_ADDR)
            value = bus.read_byte(PCF8591_ADDR)
            current_smoke = value
            return value
        except Exception as e:
            log_message(f"读取烟雾传感器错误: {e}")
            return current_smoke
    else:
        current_smoke += random.uniform(-2, 2)
        current_smoke = round(max(0, min(255, current_smoke)))
        if random.random() < 0.02:
            current_smoke = random.uniform(120, 200)
        return current_smoke


def send_alert_email(smoke_value):
    try:
        import smtplib

        SMTP_SERVER = "smtp.qq.com"
        SMTP_PORT = 587
        FROM_EMAIL = "alert@example.com"
        TO_EMAIL = "admin@example.com"
        PASSWORD = "your_password"

        subject = "会议室烟雾警报！"
        body = f"""警告！检测到会议室内烟雾浓度异常！

当前烟雾值: {smoke_value}
触发时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

请立即检查会议室状况！
        """
        message = f"Subject: {subject}\n\n{body}"

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(FROM_EMAIL, PASSWORD)
            server.sendmail(FROM_EMAIL, TO_EMAIL, message)

        log_message("警报邮件已发送！")
        return True
    except Exception as e:
        log_message(f"发送邮件错误: {e}")
        return False


def check_smoke_alarm(smoke_value):
    global devices

    SMOKE_THRESHOLD = 100
    ALARM_COOLDOWN = 300

    current_time = time.time()

    if smoke_value > SMOKE_THRESHOLD:
        devices['alarm'] = True
        set_buzzer(True)
        log_message(f"烟雾浓度异常 ({smoke_value})，触发报警！")

        if not hasattr(check_smoke_alarm, 'last_alarm_time') or \
           current_time - check_smoke_alarm.last_alarm_time > ALARM_COOLDOWN:
            if send_alert_email(smoke_value):
                check_smoke_alarm.last_alarm_time = current_time
    else:
        devices['alarm'] = False
        set_buzzer(False)


def read_pir_sensor():
    global current_presence

    if ON_RASPBERRY_PI:
        try:
            GPIO.setup(PIR_PIN, GPIO.IN)
            pir_state = GPIO.input(PIR_PIN)
            presence = pir_state == 1
            current_presence = presence
            return presence
        except Exception as e:
            log_message(f"读取人体红外传感器错误: {e}")
            return current_presence
    else:
        presence = random.random() < 0.15
        current_presence = presence
        return presence


def control_by_presence(presence):
    global devices, TEMP_MIN, TEMP_MAX

    current_time = time.time()

    if presence:
        control_by_presence.last_presence_time = current_time
        devices['presence'] = True

        if current_light < 80:
            if not devices['lighting'] and devices.get('lighting_brightness', 0) < 50:
                devices['lighting'] = True
                devices['lighting_brightness'] = 80
                log_message("检测到有人且光线不足，自动开灯")

        if not hasattr(control_by_presence, 'TEMP_ORIG_MIN'):
            control_by_presence.TEMP_ORIG_MIN = TEMP_MIN
            control_by_presence.TEMP_ORIG_MAX = TEMP_MAX
        TEMP_MIN = control_by_presence.TEMP_ORIG_MIN
        TEMP_MAX = control_by_presence.TEMP_ORIG_MAX
    else:
        devices['presence'] = False

        if hasattr(control_by_presence, 'last_presence_time'):
            time_since = current_time - control_by_presence.last_presence_time

            if time_since > 300:
                devices['lighting'] = False
                devices['lighting_brightness'] = 0
                log_message("无人超过5分钟，自动关灯")

                if not hasattr(control_by_presence, 'TEMP_ORIG_MIN'):
                    control_by_presence.TEMP_ORIG_MIN = TEMP_MIN
                    control_by_presence.TEMP_ORIG_MAX = TEMP_MAX
                TEMP_MIN = control_by_presence.TEMP_ORIG_MIN - 2
                TEMP_MAX = control_by_presence.TEMP_ORIG_MAX + 2


def update_history(temp, humidity, light_value=None, smoke_value=None, presence=None):
    global history_data

    current_time = datetime.now().strftime("%H:%M:%S")
    full_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data_point = {
        "time": current_time,
        "timestamp": full_timestamp,
        "temperature": round(temp, 1) if temp else 0,
        "humidity": round(humidity, 1) if humidity else 0,
        "light": light_value if light_value is not None else current_light,
        "smoke": smoke_value if smoke_value is not None else current_smoke,
        "presence": 1 if (presence if presence is not None else current_presence) else 0,
        "cooling": devices['cooling'],
        "heating": devices['heating'],
        "humidifier": devices['humidifier'],
        "dehumidifier": devices['dehumidifier'],
        "lighting": devices['lighting'],
        "alarm": devices['alarm'],
        "auto_mode": devices['auto_mode']
    }

    history_data.append(data_point)

    if len(history_data) > max_history_points:
        history_data.pop(0)


def generate_charts():
    if len(history_data) < 2:
        return

    timestamps = [d["time"] for d in history_data]
    temperatures = [d["temperature"] for d in history_data]
    humidities = [d["humidity"] for d in history_data]
    lights = [d.get("light", 0) for d in history_data]
    smokes = [d.get("smoke", 0) for d in history_data]
    presences = [d.get("presence", 0) for d in history_data]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    color_temp = '#dc3545'
    ax1.set_ylabel('温度 (°C)', color=color_temp, fontsize=12)
    l1, = ax1.plot(timestamps, temperatures, color=color_temp, marker='o',
                   markersize=2, linewidth=1.5, label='温度')
    ax1.tick_params(axis='y', labelcolor=color_temp)

    ax1b = ax1.twinx()
    color_hum = '#0d6efd'
    ax1b.set_ylabel('湿度 (%)', color=color_hum, fontsize=12)
    l2, = ax1b.plot(timestamps, humidities, color=color_hum, marker='s',
                    markersize=2, linewidth=1.5, label='湿度')
    ax1b.tick_params(axis='y', labelcolor=color_hum)

    lines1 = [l1, l2]
    ax1.legend(lines1, [l.get_label() for l in lines1], loc='upper left')
    ax1.set_title('温湿度趋势图', fontsize=14, fontweight='bold')
    xticks = range(0, len(timestamps), max(1, len(timestamps)//8))
    ax1.set_xticks([timestamps[i] for i in xticks])
    ax1.set_xticklabels([timestamps[i] for i in xticks], rotation=45, fontsize=8)

    color_light = '#ffc107'
    ax2.set_ylabel('光照/烟雾', fontsize=12)
    l3, = ax2.plot(timestamps, lights, color=color_light, marker='.',
                   markersize=2, linewidth=1.5, label='光照强度')
    color_smoke = '#6f42c1'
    l4, = ax2.plot(timestamps, smokes, color=color_smoke, marker='.',
                   markersize=2, linewidth=1.5, label='烟雾浓度')
    ax2.fill_between(range(len(timestamps)), 0, [v*0.5 for v in presences],
                     alpha=0.2, color='#fd7e14', step='post', label='人体检测')

    lines2 = [l3, l4]
    ax2.legend(lines2 + [plt.Rectangle((0,0),1,1,fc='#fd7e14',alpha=0.2)],
               [l.get_label() for l in lines2] + ['人体检测'], loc='upper left')
    ax2.set_title('光照/烟雾/人体检测趋势图', fontsize=14, fontweight='bold')
    ax2.set_xticks([timestamps[i] for i in xticks])
    ax2.set_xticklabels([timestamps[i] for i in xticks], rotation=45, fontsize=8)

    plt.tight_layout()
    file_path = f"{PLOT_DIR}/sensor_chart.png"
    plt.savefig(file_path, dpi=100, bbox_inches='tight')
    plt.close(fig)
    log_message("综合趋势图已更新")


def sensor_thread_function():
    global current_temp, current_humidity, current_light, current_smoke, current_presence
    last_chart_update = 0

    while True:
        temp, humidity = read_sensor()

        simulate_environment()

        control_devices()

        light_value = read_light_sensor()
        control_lighting(light_value)

        smoke_value = read_smoke_sensor()
        check_smoke_alarm(smoke_value)

        presence = read_pir_sensor()
        control_by_presence(presence)

        with data_lock:
            current_temp, current_humidity = temp, humidity
            current_light = light_value
            current_smoke = smoke_value
            current_presence = presence

        update_history(temp, humidity, light_value, smoke_value, presence)

        log_message(
            f"温度:{temp:.1f}°C 湿度:{humidity:.1f}% "
            f"光照:{light_value} 烟雾:{smoke_value} "
            f"有人:{'是' if presence else '否'} "
            f"制冷:{devices['cooling']} 加热:{devices['heating']} "
            f"灯光:{devices['lighting']} 报警:{devices['alarm']}"
        )

        current_time = time.time()
        if current_time - last_chart_update > 60:
            generate_charts()
            last_chart_update = current_time

        time.sleep(3)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/current')
def get_current_data():
    with data_lock:
        data = {
            "temperature": current_temp,
            "humidity": current_humidity,
            "light": current_light,
            "smoke": current_smoke,
            "presence": current_presence,
            "devices": devices,
            "temp_min": TEMP_MIN,
            "temp_max": TEMP_MAX,
            "humidity_min": HUMIDITY_MIN,
            "humidity_max": HUMIDITY_MAX,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    return jsonify(data)


@app.route('/api/history')
def get_history_data():
    return jsonify(history_data)


@app.route('/api/control', methods=['POST'])
def manual_control():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid request"}), 400

    action = data.get('action')

    if action == 'set_auto':
        devices['auto_mode'] = data.get('enabled', True)
        log_message(f"自动模式: {'开启' if devices['auto_mode'] else '关闭'}")
    elif action == 'set_params':
        global TEMP_MIN, TEMP_MAX, HUMIDITY_MIN, HUMIDITY_MAX
        if 'temp_min' in data:
            TEMP_MIN = int(data['temp_min'])
        if 'temp_max' in data:
            TEMP_MAX = int(data['temp_max'])
        if 'humidity_min' in data:
            HUMIDITY_MIN = int(data['humidity_min'])
        if 'humidity_max' in data:
            HUMIDITY_MAX = int(data['humidity_max'])
        log_message(f"参数已更新: 温度{TEMP_MIN}-{TEMP_MAX}°C, 湿度{HUMIDITY_MIN}-{HUMIDITY_MAX}%")
    elif action == 'manual':
        device_name = data.get('device')
        state = data.get('state', False)
        if device_name in devices:
            devices[device_name] = state
            if device_name == 'alarm':
                set_buzzer(state)
            log_message(f"手动控制: {device_name} = {state}")

    return jsonify({"success": True, "devices": devices})


@app.route('/chart/sensor')
def chart_sensor():
    file_path = f"{PLOT_DIR}/sensor_chart.png"
    if not os.path.exists(file_path):
        generate_charts()
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/png')
    return jsonify({"error": "Chart not available"}), 503


@app.route('/api/export/csv')
def export_csv():
    if not history_data:
        return jsonify({"error": "No data to export"}), 503

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['时间', '时间戳', '温度(°C)', '湿度(%)', '光照', '烟雾', '人体检测',
                     '制冷', '加热', '加湿', '除湿', '照明', '报警', '自动模式'])

    for record in history_data:
        writer.writerow([
            record.get('time', ''),
            record.get('timestamp', ''),
            record.get('temperature', ''),
            record.get('humidity', ''),
            record.get('light', ''),
            record.get('smoke', ''),
            '有人' if record.get('presence', 0) else '无人',
            '开' if record.get('cooling', False) else '关',
            '开' if record.get('heating', False) else '关',
            '开' if record.get('humidifier', False) else '关',
            '开' if record.get('dehumidifier', False) else '关',
            '开' if record.get('lighting', False) else '关',
            '开' if record.get('alarm', False) else '关',
            '自动' if record.get('auto_mode', False) else '手动'
        ])

    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=climate_data.csv',
                             'Content-Type': 'text/csv; charset=utf-8-sig'})


def create_template_files():
    os.makedirs('templates', exist_ok=True)
    template_path = os.path.join('templates', 'index.html')
    if not os.path.exists(template_path):
        _MINIMAL_HTML = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>智能温湿度控制系统</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css" rel="stylesheet">
<style>
body{padding-top:20px;background-color:#f8f9fa}
.card{border-radius:10px;box-shadow:0 4px 6px rgba(0,0,0,0.1);margin-bottom:20px}
.card-header{background-color:#6c757d;color:white;border-radius:10px 10px 0 0!important}
.display-value{font-size:2.5rem;font-weight:300}
.temperature{color:#dc3545}.humidity{color:#0d6efd}.light{color:#ffc107}.smoke{color:#6f42c1}
.timestamp{font-size:.8rem;color:#6c757d}
.device-indicator{width:12px;height:12px;border-radius:50%;display:inline-block;margin-right:5px}
.device-on{background-color:#198754}.device-off{background-color:#6c757d}
.export-btn{display:flex;align-items:center;gap:5px}
.presence-active{color:#fd7e14;font-weight:bold}
@media(max-width:768px){.display-value{font-size:2rem}}
</style>
</head>
<body>
<div class="container">
<h1 class="text-center mb-3">智能温湿度控制系统</h1>
<div class="text-center mb-3"><span class="timestamp" id="last-updated">--</span></div>
<div class="row mb-3"><div class="col text-center"><div class="btn-group">
<button id="auto-on-btn" class="btn btn-success" onclick="setAutoMode(true)">自动</button>
<button id="auto-off-btn" class="btn btn-outline-danger" onclick="setAutoMode(false)">手动</button>
</div></div></div>
<div class="row">
<div class="col-md-6"><div class="card"><div class="card-header">参数设置</div><div class="card-body"><div class="row">
<div class="col-6"><label>温度:<span id="temp-range-label">20-26C</span></label>
<input type="range" class="form-range" id="temp-min" min="10" max="30" value="20" onchange="updateParams()">
<input type="range" class="form-range" id="temp-max" min="15" max="40" value="26" onchange="updateParams()"></div>
<div class="col-6"><label>湿度:<span id="hum-range-label">40-60%</span></label>
<input type="range" class="form-range" id="humidity-min" min="10" max="80" value="40" onchange="updateParams()">
<input type="range" class="form-range" id="humidity-max" min="30" max="95" value="60" onchange="updateParams()"></div>
</div></div></div></div>
<div class="col-md-6"><div class="card"><div class="card-header">设备状态</div><div class="card-body"><div class="row">
<div class="col-4 mb-2"><span class="device-indicator" id="cooling-ind"></span>制冷<span id="cooling-status">关闭</span></div>
<div class="col-4 mb-2"><span class="device-indicator" id="heating-ind"></span>加热<span id="heating-status">关闭</span></div>
<div class="col-4 mb-2"><span class="device-indicator" id="humidifier-ind"></span>加湿<span id="humidifier-status">关闭</span></div>
<div class="col-4 mb-2"><span class="device-indicator" id="dehumidifier-ind"></span>除湿<span id="dehumidifier-status">关闭</span></div>
<div class="col-4 mb-2"><span class="device-indicator" id="lighting-ind"></span>照明<span id="lighting-status">关闭</span></div>
<div class="col-4 mb-2"><span class="device-indicator" id="alarm-ind"></span>报警<span id="alarm-status">关闭</span></div>
</div></div></div></div>
</div>
<div class="row">
<div class="col-md-3"><div class="card"><div class="card-header"><i class="bi bi-thermometer-half"></i>温度</div><div class="card-body text-center"><div class="display-value temperature" id="current-temp">--</div><div>C</div></div></div></div>
<div class="col-md-3"><div class="card"><div class="card-header"><i class="bi bi-droplet-half"></i>湿度</div><div class="card-body text-center"><div class="display-value humidity" id="current-hum">--</div><div>%</div></div></div></div>
<div class="col-md-3"><div class="card"><div class="card-header"><i class="bi bi-sun"></i>光照</div><div class="card-body text-center"><div class="display-value light" id="current-light">--</div><div>0-255</div></div></div></div>
<div class="col-md-3"><div class="card"><div class="card-header"><i class="bi bi-cloud"></i>烟雾</div><div class="card-body text-center"><div class="display-value smoke" id="current-smoke">--</div><div>0-255</div></div></div></div>
</div>
<div class="row mb-3">
<div class="col-md-6"><div class="card"><div class="card-header"><i class="bi bi-person"></i>人体检测</div><div class="card-body text-center"><h3 id="presence-status" class="presence-active">--</h3></div></div></div>
<div class="col-md-6"><div class="card"><div class="card-header">数据导出</div><div class="card-body text-center"><a href="/api/export/csv" class="btn btn-success export-btn">导出CSV</a></div></div></div>
</div>
<div class="card"><div class="card-header">趋势图</div><div class="card-body text-center"><img id="sensor-chart" src="/chart/sensor" class="img-fluid" alt="chart"></div></div>
</div>
<script>
function updateUI(){
fetch('/api/current').then(r=>r.json()).then(d=>{
document.getElementById('current-temp').textContent=d.temperature?d.temperature.toFixed(1):'--';
document.getElementById('current-hum').textContent=d.humidity?d.humidity.toFixed(1):'--';
document.getElementById('current-light').textContent=d.light!=null?d.light:'--';
document.getElementById('current-smoke').textContent=d.smoke!=null?d.smoke:'--';
document.getElementById('presence-status').textContent=d.presence?'有人':'无人';
document.getElementById('last-updated').textContent=d.timestamp;
document.getElementById('temp-range-label').textContent=d.temp_min+'-'+d.temp_max+'C';
document.getElementById('hum-range-label').textContent=d.humidity_min+'-'+d.humidity_max+'%';
var s=d.devices;
['cooling','heating','humidifier','dehumidifier','lighting','alarm'].forEach(function(n){
var i=document.getElementById(n+'-ind'),t=document.getElementById(n+'-status');
if(i)i.className='device-indicator '+(s[n]?'device-on':'device-off');
if(t)t.textContent=s[n]?'开启':'关闭'});
document.getElementById('auto-on-btn').className=s.auto_mode?'btn btn-success':'btn btn-outline-success';
document.getElementById('auto-off-btn').className=s.auto_mode?'btn btn-outline-danger':'btn btn-danger'})}
function setAutoMode(e){
fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'set_auto',enabled:e})}).then(updateUI)}
function updateParams(){
var a=parseInt(document.getElementById('temp-min').value),b=parseInt(document.getElementById('temp-max').value),c=parseInt(document.getElementById('humidity-min').value),d=parseInt(document.getElementById('humidity-max').value);
fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'set_params',temp_min:a,temp_max:b,humidity_min:c,humidity_max:d})})}
setInterval(updateUI,2000);setInterval(function(){document.getElementById('sensor-chart').src='/chart/sensor?t='+new Date().getTime()},60000);updateUI();
</script>
</body>
</html>"""
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(_MINIMAL_HTML)
        log_message("模板文件已创建")
    else:
        log_message("模板文件已存在，跳过创建")


def cleanup_resources():
    try:
        if ON_RASPBERRY_PI and 'GPIO' in dir():
            set_buzzer(False)
            GPIO.cleanup()
        log_message("资源已释放，程序结束")
    except Exception as e:
        log_message(f"清理资源时出错: {e}")


def _find_available_port(preferred=None):
    if preferred is None:
        preferred = [8080, 9090, 5001, 3000]
    for p in preferred:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(('127.0.0.1', p))
        s.close()
        if result != 0:
            return p
    return 5001


def main():
    log_message("智能温湿度控制系统启动...")

    create_template_files()

    if not setup_sensors():
        log_message("传感器初始化失败")
        return

    sensor_thread = threading.Thread(target=sensor_thread_function, daemon=True)
    sensor_thread.start()

    try:
        host_ip = '0.0.0.0'
        port = _find_available_port([8080, 9090, 5001, 3000])
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
