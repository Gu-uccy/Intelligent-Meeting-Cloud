#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified Flask backend for the Raspberry Pi meeting-room experiments.

This file combines the chapter 7 sensor dashboard and chapter 8 climate-control
dashboard into one service. It uses digital outputs for light and smoke modules,
so it does not require a PCF8591 ADC module.
"""

import csv
import io
import os
import random
import socket
import threading
import time
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["SimHei", "WenQuanYi Micro Hei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt

from flask import Flask, Response, jsonify, send_file
from flask import request

try:
    import board
    import adafruit_dht
    import RPi.GPIO as GPIO

    ON_RASPBERRY_PI = True
except (ImportError, NotImplementedError):
    ON_RASPBERRY_PI = False

    print("警告: 未检测到树莓派环境，使用模拟传感器数据运行")

try:
    import smbus

    HAS_SMBUS = True
except ImportError:
    HAS_SMBUS = False


app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PLOT_DIR = os.path.join(BASE_DIR, "plots")
LOG_FILE = os.path.join(DATA_DIR, "unified_sensor_log.txt")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)


# BCM numbering.
DHT_PIN = board.D5 if ON_RASPBERRY_PI else None
PIR_PIN = 17
BUZZER_PIN = 18
SMOKE_DO_PIN = 24
ULTRASONIC_TRIG = 20
ULTRASONIC_ECHO = 21
RGB_LED_PINS = {"red": 19, "green": 27, "blue": 22}
# Two SG90/TS90A-style servo signals for the left and right door leaves.
# BCM GPIO13/12 are physical pins 33/32 and are unused by the current wiring.
# Power both servos from a separate 5V supply and connect its GND to Pi GND.
SERVO_DOOR_PINS = {
    "left": int(os.environ.get("SERVO_DOOR_LEFT_PIN", os.environ.get("SERVO_DOOR_PIN", "13"))),
    "right": int(os.environ.get("SERVO_DOOR_RIGHT_PIN", "12")),
}
SERVO_FREQUENCY = 50
SERVO_CLOSED_DUTY = float(os.environ.get("SERVO_CLOSED_DUTY", "2.5"))
SERVO_OPEN_DUTY = float(os.environ.get("SERVO_OPEN_DUTY", "7.5"))

# Keep this false until HC-SR04 ECHO is protected with a resistor divider or
# level shifter. ECHO can output 5V, while Raspberry Pi GPIO is 3.3V only.
USE_ULTRASONIC = True

# PCF8591 ADC module. The current chapter 7/8 wiring uses AIN0 for the
# photoresistor module AO. MQ-2 smoke uses DO on GPIO24 until a divider is added.
USE_PCF8591_LIGHT = True
PCF8591_ADDR = 0x48
LIGHT_ANALOG_CHANNEL = 0
LIGHT_ANALOG_INVERT = True

# The current MQ-2 DO wiring reads 0 in clean air on this module, so use HIGH as
# the alarm state for now. Change to 0 if your module's DO LED turns on with LOW.
SMOKE_ALARM_STATE = int(os.environ.get("SMOKE_ALARM_STATE", "1"))

TEMP_MIN = 20
TEMP_MAX = 26
HUMIDITY_MIN = 40
HUMIDITY_MAX = 60

SMOKE_THRESHOLD = 100
LIGHT_LOW_THRESHOLD = 50
LIGHT_HIGH_THRESHOLD = 150
MAX_HISTORY_POINTS = 120

data_lock = threading.Lock()
dht_device = None
pwm_channels = {}
door_servos = {}
i2c_bus = None

current_temp = None
current_humidity = None
current_distance = None
current_motion = False
current_light = 128
current_smoke = 0
last_motion_time = 0
motion_count = 0
history_data = []

devices = {
    "cooling": False,
    "heating": False,
    "humidifier": False,
    "dehumidifier": False,
    "lighting": False,
    "lighting_brightness": 0,
    "lighting_source": "auto",
    "alarm": False,
    "presence": False,
    "door_open": False,
    "door_source": "hardware",
    "auto_mode": True,
}


def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")


def setup_gpio():
    global dht_device, i2c_bus, door_servos

    if not ON_RASPBERRY_PI:
        log_message("非树莓派环境，跳过 GPIO 初始化")
        return True

    os.system("pkill -f libgpiod_pulsein")  # release stale DHT helper processes
    time.sleep(0.5)

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    try:
        dht_device = adafruit_dht.DHT11(DHT_PIN)
        log_message("DHT11 初始化成功 (GPIO5)")
    except Exception as e:
        log_message(f"DHT11 初始化失败: {e}")

    inputs = [
        (PIR_PIN, "PIR 人体红外", GPIO.IN),
        (SMOKE_DO_PIN, "烟雾 DO", GPIO.IN),
    ]
    if USE_ULTRASONIC:
        inputs.append((ULTRASONIC_ECHO, "超声波 ECHO", GPIO.IN))

    for pin, name, mode in inputs:
        try:
            GPIO.setup(pin, mode)
            log_message(f"{name} 初始化成功 (GPIO{pin})")
        except Exception as e:
            log_message(f"{name} 初始化失败: {e}")

    outputs = [
        (BUZZER_PIN, "蜂鸣器"),
    ]
    if USE_ULTRASONIC:
        outputs.append((ULTRASONIC_TRIG, "超声波 TRIG"))

    for pin, name in outputs:
        try:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
            log_message(f"{name} 初始化成功 (GPIO{pin})")
        except Exception as e:
            log_message(f"{name} 初始化失败: {e}")

    for color, pin in RGB_LED_PINS.items():
        try:
            GPIO.setup(pin, GPIO.OUT)
            pwm = GPIO.PWM(pin, 100)
            pwm.start(0)
            pwm_channels[color] = pwm
        except Exception as e:
            log_message(f"RGB LED {color} 初始化失败: {e}")

    for side, pin in SERVO_DOOR_PINS.items():
        try:
            GPIO.setup(pin, GPIO.OUT)
            servo = GPIO.PWM(pin, SERVO_FREQUENCY)
            servo.start(SERVO_CLOSED_DUTY)
            door_servos[side] = servo
            log_message(f"{side} 门舵机初始化成功 (BCM GPIO{pin}, 50Hz)")
        except Exception as e:
            log_message(f"{side} 门舵机初始化失败 (BCM GPIO{pin}): {e}")

    if USE_PCF8591_LIGHT:
        if not HAS_SMBUS:
            log_message("PCF8591 需要 smbus，但当前 Python 环境未安装 smbus")
        else:
            try:
                i2c_bus = smbus.SMBus(1)
                i2c_bus.write_byte(PCF8591_ADDR, 0x40 | LIGHT_ANALOG_CHANNEL)
                i2c_bus.read_byte(PCF8591_ADDR)
                log_message(f"PCF8591 初始化成功 (0x{PCF8591_ADDR:02X}, AIN{LIGHT_ANALOG_CHANNEL})")
            except Exception as e:
                i2c_bus = None
                log_message(f"PCF8591 初始化失败: {e}")

    return True


def set_buzzer(enabled):
    if not ON_RASPBERRY_PI:
        return
    try:
        GPIO.output(BUZZER_PIN, GPIO.HIGH if enabled else GPIO.LOW)
    except Exception as e:
        log_message(f"蜂鸣器控制失败: {e}")


def set_rgb_color(color):
    if not ON_RASPBERRY_PI:
        return

    color_map = {
        "red": (100, 0, 0),
        "green": (0, 100, 0),
        "blue": (0, 0, 100),
        "yellow": (100, 100, 0),
        "purple": (100, 0, 100),
        "cyan": (0, 100, 100),
        "white": (100, 100, 100),
        "off": (0, 0, 0),
    }
    red, green, blue = color_map.get(color, (0, 0, 0))
    for name, duty in {"red": red, "green": green, "blue": blue}.items():
        if name in pwm_channels:
            pwm_channels[name].ChangeDutyCycle(duty)


def set_rgb_brightness(enabled, brightness=100):
    if not ON_RASPBERRY_PI:
        return

    duty = max(0, min(100, int(brightness if enabled else 0)))
    for name in ("red", "green", "blue"):
        if name in pwm_channels:
            pwm_channels[name].ChangeDutyCycle(duty)


def set_door_servo(opened, source="manual"):
    """Move the physical door servo and publish the same state to the API."""
    devices["door_open"] = bool(opened)
    devices["door_source"] = source
    if not ON_RASPBERRY_PI or not door_servos:
        return

    duty = SERVO_OPEN_DUTY if opened else SERVO_CLOSED_DUTY
    try:
        for servo in door_servos.values():
            servo.ChangeDutyCycle(duty)
        time.sleep(0.35)
    except Exception as e:
        log_message(f"门舵机控制失败: {e}")


def set_lighting_state(enabled, brightness=None, source="manual"):
    devices["lighting"] = bool(enabled)
    if brightness is None:
        brightness = 100 if enabled else 0
    devices["lighting_brightness"] = max(0, min(100, int(brightness)))
    devices["lighting_source"] = source


def apply_device_outputs():
    set_buzzer(devices["alarm"])
    if devices["alarm"]:
        set_rgb_color("red")
    else:
        set_rgb_brightness(devices["lighting"], devices["lighting_brightness"])


def read_dht_sensor():
    global current_temp, current_humidity

    if ON_RASPBERRY_PI and dht_device is not None:
        try:
            temperature = dht_device.temperature
            humidity = dht_device.humidity
            if temperature is not None and humidity is not None:
                current_temp = round(temperature, 1)
                current_humidity = round(humidity, 1)
        except RuntimeError as e:
            log_message(f"DHT11 读取重试: {e}")
        except Exception as e:
            log_message(f"DHT11 读取失败: {e}")
        return current_temp, current_humidity

    if current_temp is None:
        current_temp = 25.0
    if current_humidity is None:
        current_humidity = 50.0

    current_temp = round(max(10, min(40, current_temp + random.uniform(-0.25, 0.25))), 1)
    current_humidity = round(max(10, min(95, current_humidity + random.uniform(-0.4, 0.4))), 1)
    return current_temp, current_humidity


def read_distance_sensor():
    global current_distance

    if ON_RASPBERRY_PI and USE_ULTRASONIC:
        try:
            GPIO.output(ULTRASONIC_TRIG, GPIO.LOW)
            time.sleep(0.002)
            GPIO.output(ULTRASONIC_TRIG, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(ULTRASONIC_TRIG, GPIO.LOW)

            start_wait = time.time()
            while GPIO.input(ULTRASONIC_ECHO) == GPIO.LOW:
                if time.time() - start_wait > 0.05:
                    return current_distance
            pulse_start = time.time()

            while GPIO.input(ULTRASONIC_ECHO) == GPIO.HIGH:
                if time.time() - pulse_start > 0.05:
                    return current_distance
            pulse_end = time.time()

            distance = ((pulse_end - pulse_start) * 34000) / 2
            if 2 <= distance <= 450:
                current_distance = round(distance, 1)
        except Exception as e:
            log_message(f"超声波读取失败: {e}")
        return current_distance

    if current_distance is None:
        current_distance = 120.0
    current_distance = round(max(2, min(450, current_distance + random.uniform(-3, 3))), 1)
    return current_distance


def read_pir_sensor():
    global current_motion, last_motion_time, motion_count

    if ON_RASPBERRY_PI:
        try:
            motion = GPIO.input(PIR_PIN) == GPIO.HIGH
        except Exception as e:
            log_message(f"PIR 读取失败: {e}")
            motion = current_motion
    else:
        motion = random.random() < 0.2

    if motion and not current_motion:
        motion_count += 1
        last_motion_time = time.time()
    current_motion = motion
    devices["presence"] = motion
    return motion


def read_light_sensor():
    global current_light

    if ON_RASPBERRY_PI:
        if USE_PCF8591_LIGHT and i2c_bus is not None:
            try:
                i2c_bus.write_byte(PCF8591_ADDR, 0x40 | LIGHT_ANALOG_CHANNEL)
                i2c_bus.read_byte(PCF8591_ADDR)
                raw_value = i2c_bus.read_byte(PCF8591_ADDR)
                current_light = 255 - raw_value if LIGHT_ANALOG_INVERT else raw_value
            except Exception as e:
                log_message(f"PCF8591 光敏读取失败: {e}")
            return current_light

        try:
            log_message("光敏传感器未接入 PCF8591，保持上一次光照值")
        except Exception as e:
            log_message(f"光敏读取失败: {e}")
        return current_light

    current_light = round(max(0, min(255, current_light + random.uniform(-8, 8))))
    return current_light


def read_smoke_sensor():
    global current_smoke

    if ON_RASPBERRY_PI:
        try:
            smoke_alarm = GPIO.input(SMOKE_DO_PIN) == SMOKE_ALARM_STATE
            current_smoke = 180 if smoke_alarm else 20
        except Exception as e:
            log_message(f"烟雾读取失败: {e}")
        return current_smoke

    if random.random() < 0.03:
        current_smoke = random.randint(130, 200)
    else:
        current_smoke = round(max(0, min(90, current_smoke + random.uniform(-4, 4))))
    return current_smoke


def simulate_environment_by_devices():
    global current_temp, current_humidity

    if current_temp is None or current_humidity is None:
        return

    if devices["cooling"]:
        current_temp -= 0.2
    if devices["heating"]:
        current_temp += 0.2
    if devices["humidifier"]:
        current_humidity += 0.3
    if devices["dehumidifier"]:
        current_humidity -= 0.3

    current_temp = round(max(10, min(40, current_temp)), 1)
    current_humidity = round(max(10, min(95, current_humidity)), 1)


def apply_auto_control(temp, humidity, light_value, smoke_value, motion):
    if devices["auto_mode"]:
        if temp is not None:
            if temp > TEMP_MAX + 1:
                devices["cooling"] = True
                devices["heating"] = False
            elif temp < TEMP_MIN - 1:
                devices["heating"] = True
                devices["cooling"] = False
            elif TEMP_MIN <= temp <= TEMP_MAX:
                devices["cooling"] = False
                devices["heating"] = False

        if humidity is not None:
            if humidity > HUMIDITY_MAX + 3:
                devices["dehumidifier"] = True
                devices["humidifier"] = False
            elif humidity < HUMIDITY_MIN - 3:
                devices["humidifier"] = True
                devices["dehumidifier"] = False
            elif HUMIDITY_MIN <= humidity <= HUMIDITY_MAX:
                devices["dehumidifier"] = False
                devices["humidifier"] = False

        if motion and light_value < LIGHT_LOW_THRESHOLD:
            set_lighting_state(True, 100, "auto")
        elif light_value > LIGHT_HIGH_THRESHOLD or not motion:
            set_lighting_state(False, 0, "auto")

    if smoke_value > SMOKE_THRESHOLD:
        devices["alarm"] = True
    elif devices["auto_mode"]:
        devices["alarm"] = False

    apply_device_outputs()


def last_motion_text():
    if last_motion_time <= 0:
        return "从未"

    diff = time.time() - last_motion_time
    if diff < 60:
        return f"{int(diff)} 秒前"
    if diff < 3600:
        return f"{int(diff / 60)} 分钟前"
    return datetime.fromtimestamp(last_motion_time).strftime("%Y-%m-%d %H:%M:%S")


def append_history(temp, humidity, distance, motion, light_value, smoke_value):
    global history_data

    data_point = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "temperature": temp if temp is not None else 0,
        "humidity": humidity if humidity is not None else 0,
        "distance": distance if distance is not None else 0,
        "motion": 1 if motion else 0,
        "motion_count": motion_count,
        "light": light_value,
        "smoke": smoke_value,
        "presence": 1 if motion else 0,
        "cooling": devices["cooling"],
        "heating": devices["heating"],
        "humidifier": devices["humidifier"],
        "dehumidifier": devices["dehumidifier"],
        "lighting": devices["lighting"],
        "alarm": devices["alarm"],
        "auto_mode": devices["auto_mode"],
    }
    history_data.append(data_point)
    history_data = history_data[-MAX_HISTORY_POINTS:]


def generate_temperature_humidity_chart():
    if len(history_data) < 2:
        return

    timestamps = [d["time"] for d in history_data]
    temperatures = [d["temperature"] for d in history_data]
    humidities = [d["humidity"] for d in history_data]

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.set_xlabel("时间")
    ax1.set_ylabel("温度 (°C)", color="#dc3545")
    line1, = ax1.plot(timestamps, temperatures, color="#dc3545", marker="o", markersize=3, label="温度")
    ax1.tick_params(axis="y", labelcolor="#dc3545")

    ax2 = ax1.twinx()
    ax2.set_ylabel("湿度 (%)", color="#0d6efd")
    line2, = ax2.plot(timestamps, humidities, color="#0d6efd", marker="s", markersize=3, label="湿度")
    ax2.tick_params(axis="y", labelcolor="#0d6efd")

    xticks = range(0, len(timestamps), max(1, len(timestamps) // 10))
    ax1.set_xticks([timestamps[i] for i in xticks])
    ax1.set_xticklabels([timestamps[i] for i in xticks], rotation=45, fontsize=8)
    ax1.legend([line1, line2], ["温度", "湿度"], loc="upper left")
    plt.title("温湿度趋势图")
    fig.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "temp_humidity_chart.png"), dpi=100, bbox_inches="tight")
    plt.close(fig)


def generate_distance_motion_chart():
    if len(history_data) < 2:
        return

    timestamps = [d["time"] for d in history_data]
    distances = [d["distance"] for d in history_data]
    motions = [d["motion"] for d in history_data]

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.set_xlabel("时间")
    ax1.set_ylabel("距离 (cm)", color="#198754")
    line1, = ax1.plot(timestamps, distances, color="#198754", marker="o", markersize=3, label="距离")
    ax1.tick_params(axis="y", labelcolor="#198754")

    ax2 = ax1.twinx()
    ax2.set_ylabel("人体检测", color="#fd7e14")
    motion_area = ax2.fill_between(range(len(timestamps)), 0, motions, alpha=0.3, color="#fd7e14", step="post")
    ax2.set_ylim(0, 1.5)
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(["无人", "有人"])

    xticks = range(0, len(timestamps), max(1, len(timestamps) // 10))
    ax1.set_xticks([timestamps[i] for i in xticks])
    ax1.set_xticklabels([timestamps[i] for i in xticks], rotation=45, fontsize=8)
    ax1.legend([line1, motion_area], ["距离", "人体检测"], loc="upper left")
    plt.title("距离和人体检测趋势图")
    fig.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "distance_motion_chart.png"), dpi=100, bbox_inches="tight")
    plt.close(fig)


def generate_climate_chart():
    if len(history_data) < 2:
        return

    timestamps = [d["time"] for d in history_data]
    temperatures = [d["temperature"] for d in history_data]
    humidities = [d["humidity"] for d in history_data]
    lights = [d["light"] for d in history_data]
    smokes = [d["smoke"] for d in history_data]
    presences = [d["presence"] for d in history_data]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    ax1.plot(timestamps, temperatures, color="#dc3545", marker="o", markersize=2, label="温度")
    ax1.plot(timestamps, humidities, color="#0d6efd", marker="s", markersize=2, label="湿度")
    ax1.set_title("温湿度趋势图")
    ax1.legend(loc="upper left")

    ax2.plot(timestamps, lights, color="#ffc107", marker=".", markersize=2, label="光照")
    ax2.plot(timestamps, smokes, color="#6f42c1", marker=".", markersize=2, label="烟雾")
    ax2.fill_between(range(len(timestamps)), 0, [v * 50 for v in presences], alpha=0.2, color="#fd7e14", step="post", label="人体检测")
    ax2.set_title("光照/烟雾/人体检测趋势图")
    ax2.legend(loc="upper left")

    xticks = range(0, len(timestamps), max(1, len(timestamps) // 8))
    for ax in (ax1, ax2):
        ax.set_xticks([timestamps[i] for i in xticks])
        ax.set_xticklabels([timestamps[i] for i in xticks], rotation=45, fontsize=8)

    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "sensor_chart.png"), dpi=100, bbox_inches="tight")
    plt.close(fig)


def generate_all_charts():
    generate_temperature_humidity_chart()
    generate_distance_motion_chart()
    generate_climate_chart()


def sensor_loop():
    last_chart_update = 0

    while True:
        temp, humidity = read_dht_sensor()
        simulate_environment_by_devices()
        distance = read_distance_sensor()
        motion = read_pir_sensor()
        light_value = read_light_sensor()
        smoke_value = read_smoke_sensor()
        apply_auto_control(current_temp, current_humidity, light_value, smoke_value, motion)

        with data_lock:
            append_history(current_temp, current_humidity, distance, motion, light_value, smoke_value)

        log_message(
            f"温度:{current_temp}°C 湿度:{current_humidity}% 距离:{distance}cm "
            f"有人:{'是' if motion else '否'} 光照:{light_value} 烟雾:{smoke_value} "
            f"报警:{devices['alarm']}"
        )

        if time.time() - last_chart_update > 60:
            with data_lock:
                generate_all_charts()
            last_chart_update = time.time()

        time.sleep(3)


@app.route("/")
def index():
    return jsonify({
        "name": "Unified Meeting Room Flask Backend",
        "api": ["/api/current", "/api/history", "/api/control", "/api/export/csv"],
        "charts": ["/chart/temp_humidity", "/chart/distance_motion", "/chart/sensor"],
    })


@app.route("/api/current")
def get_current_data():
    with data_lock:
        if current_temp is None or current_humidity is None:
            return jsonify({"error": "Sensor data not available"}), 503

        return jsonify({
            "temperature": current_temp,
            "humidity": current_humidity,
            "distance": current_distance,
            "motion": current_motion,
            "motion_count": motion_count,
            "last_motion": last_motion_text(),
            "light": current_light,
            "smoke": current_smoke,
            "presence": current_motion,
            "door_open": devices["door_open"],
            "door_source": devices["door_source"],
            "devices": devices,
            "temp_min": TEMP_MIN,
            "temp_max": TEMP_MAX,
            "humidity_min": HUMIDITY_MIN,
            "humidity_max": HUMIDITY_MAX,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })


@app.route("/api/history")
def get_history_data():
    with data_lock:
        return jsonify(history_data)


@app.route("/api/control", methods=["POST"])
def manual_control():
    global TEMP_MIN, TEMP_MAX, HUMIDITY_MIN, HUMIDITY_MAX

    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid request"}), 400

    action = data.get("action")
    with data_lock:
        if action == "set_auto":
            devices["auto_mode"] = data.get("enabled", True)
            log_message(f"自动模式: {'开启' if devices['auto_mode'] else '关闭'}")
        elif action == "set_params":
            if "temp_min" in data:
                TEMP_MIN = int(data["temp_min"])
            if "temp_max" in data:
                TEMP_MAX = int(data["temp_max"])
            if "humidity_min" in data:
                HUMIDITY_MIN = int(data["humidity_min"])
            if "humidity_max" in data:
                HUMIDITY_MAX = int(data["humidity_max"])
            log_message(f"参数已更新: 温度{TEMP_MIN}-{TEMP_MAX}°C, 湿度{HUMIDITY_MIN}-{HUMIDITY_MAX}%")
        elif action == "manual":
            device = data.get("device")
            state = bool(data.get("state", False))
            if device in ("door", "door_open"):
                set_door_servo(state, data.get("source", "manual"))
                devices["auto_mode"] = False
                log_message(f"手动控制: door_open = {state}")
            elif device in devices:
                if device == "lighting":
                    set_lighting_state(
                        state,
                        data.get("brightness", 100 if state else 0),
                        data.get("source", "manual"),
                    )
                    devices["auto_mode"] = False
                else:
                    devices[device] = state
                apply_device_outputs()
                log_message(f"手动控制: {device} = {state}")
        else:
            return jsonify({"error": "Unknown action"}), 400

        return jsonify({"success": True, "devices": devices})


def send_chart(filename):
    path = os.path.join(PLOT_DIR, filename)
    if not os.path.exists(path):
        with data_lock:
            generate_all_charts()
    if os.path.exists(path):
        return send_file(path, mimetype="image/png")
    return jsonify({"error": "Chart not available"}), 503


@app.route("/chart/temp_humidity")
def chart_temp_humidity():
    return send_chart("temp_humidity_chart.png")


@app.route("/chart/distance_motion")
def chart_distance_motion():
    return send_chart("distance_motion_chart.png")


@app.route("/chart/sensor")
def chart_sensor():
    return send_chart("sensor_chart.png")


@app.route("/api/export/csv")
def export_csv():
    with data_lock:
        rows = list(history_data)

    if not rows:
        return jsonify({"error": "No data to export"}), 503

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "时间", "时间戳", "温度(°C)", "湿度(%)", "距离(cm)", "人体检测",
        "光照", "烟雾", "制冷", "加热", "加湿", "除湿", "照明", "报警", "自动模式",
    ])

    for row in rows:
        writer.writerow([
            row.get("time", ""),
            row.get("timestamp", ""),
            row.get("temperature", ""),
            row.get("humidity", ""),
            row.get("distance", ""),
            "有人" if row.get("presence") else "无人",
            row.get("light", ""),
            row.get("smoke", ""),
            "开" if row.get("cooling") else "关",
            "开" if row.get("heating") else "关",
            "开" if row.get("humidifier") else "关",
            "开" if row.get("dehumidifier") else "关",
            "开" if row.get("lighting") else "关",
            "开" if row.get("alarm") else "关",
            "自动" if row.get("auto_mode") else "手动",
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=unified_meeting_room_data.csv",
            "Content-Type": "text/csv; charset=utf-8-sig",
        },
    )


def cleanup_resources():
    try:
        set_buzzer(False)
        set_rgb_color("off")
        for servo in door_servos.values():
            servo.ChangeDutyCycle(0)
            servo.stop()
        if dht_device is not None and hasattr(dht_device, "exit"):
            dht_device.exit()
        if ON_RASPBERRY_PI:
            for pwm in pwm_channels.values():
                pwm.stop()
            GPIO.cleanup()
        log_message("资源已释放，程序结束")
    except Exception as e:
        log_message(f"清理资源时出错: {e}")


def find_available_port(preferred=None):
    if preferred is None:
        preferred = [5000, 8080, 9090, 5001, 3000]
    for port in preferred:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        if result != 0:
            return port
    return 5000


def main():
    log_message("统一智能会议室 Flask 后端启动...")
    setup_gpio()

    sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
    sensor_thread.start()

    port = find_available_port()
    log_message(f"Web服务器启动于 http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("程序已停止")
    finally:
        cleanup_resources()
