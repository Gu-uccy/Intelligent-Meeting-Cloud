#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 树莓派智能门禁系统 - 集成MQTT通信
# 功能: 超声波距离检测 + USB摄像头人脸识别 + 舵机门控 + MQTT数据上报

import cv2
import time
import os
import numpy as np
import threading
import json

try:
    import RPi.GPIO as GPIO
    ON_RASPBERRY_PI = True
except (ImportError, NotImplementedError):
    ON_RASPBERRY_PI = False
    print("警告: 未检测到树莓派环境")

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False
    print("警告: paho-mqtt未安装，MQTT功能被禁用")

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_PRESENCE_TOPIC = "home/meetingroom/presence"
MQTT_DISTANCE_TOPIC = "home/meetingroom/distance"
MQTT_FACE_TOPIC = "home/meetingroom/face_detected"
MQTT_DOOR_TOPIC = "home/meetingroom/door_control"
MQTT_DOOR_STATE_TOPIC = "home/meetingroom/door_state"

SERVO_PIN = 18
TRIG = 23
ECHO = 24

door_locked = True
auto_close_thread = None
distance_check_active = True
DISTANCE_THRESHOLD = 100

current_dir = os.getcwd()
for d in ['photos', 'videos']:
    os.makedirs(os.path.join(current_dir, d), exist_ok=True)

cascade_file = None
possible_paths = [
    '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
    '/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
    '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml',
    os.path.join(os.path.dirname(cv2.__file__), 'data', 'haarcascade_frontalface_default.xml'),
    os.path.join(current_dir, 'haarcascade_frontalface_default.xml'),
    os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'haarcascade_frontalface_default.xml')
]

for path in possible_paths:
    if os.path.exists(path):
        cascade_file = path
        print(f"找到人脸级联分类器: {path}")
        break

face_detector = None
if cascade_file:
    face_detector = cv2.CascadeClassifier(cascade_file)
    if not face_detector.empty():
        print("人脸检测器加载成功")
    else:
        print("错误: 无法加载人脸检测器数据")

client = None
if HAS_MQTT:
    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        def on_message(client, userdata, msg):
            global door_locked
            payload = msg.payload.decode().strip().lower()
            print(f"收到MQTT门控指令: {payload}")
            if payload == "open" and door_locked:
                open_door()
            elif payload == "close" and not door_locked:
                close_door()

        client.on_message = on_message
        client.subscribe(MQTT_DOOR_TOPIC)
        print(f"MQTT已连接到 {MQTT_BROKER}:{MQTT_PORT}，已订阅 {MQTT_DOOR_TOPIC}")
    except Exception as e:
        print(f"MQTT连接失败: {e}")
        client = None


def publish_mqtt(topic, payload):
    if client:
        try:
            client.publish(topic, json.dumps(payload) if isinstance(payload, dict) else payload)
        except Exception as e:
            print(f"MQTT发布失败: {e}")


servo_pwm = None


def setup_gpio():
    if not ON_RASPBERRY_PI:
        print("模拟模式: GPIO初始化跳过")
        return True

    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(SERVO_PIN, GPIO.OUT)
        GPIO.setup(TRIG, GPIO.OUT)
        GPIO.setup(ECHO, GPIO.IN)
        GPIO.output(TRIG, GPIO.LOW)

        global servo_pwm
        servo_pwm = GPIO.PWM(SERVO_PIN, 50)
        servo_pwm.start(2.5)
        print("GPIO初始化成功")
        return True
    except Exception as e:
        print(f"GPIO初始化失败: {e}")
        return False


def set_servo_angle(angle):
    if not ON_RASPBERRY_PI or servo_pwm is None:
        print(f"模拟: 舵机{angle}度")
        return
    duty = 2.5 + (angle / 180.0) * 10.0
    servo_pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    servo_pwm.ChangeDutyCycle(0)


def measure_distance():
    if not ON_RASPBERRY_PI:
        import random
        return round(random.uniform(20, 250), 1)

    try:
        GPIO.output(TRIG, GPIO.LOW)
        time.sleep(0.002)
        GPIO.output(TRIG, GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(TRIG, GPIO.LOW)

        pulse_start = time.time()
        timeout_start = time.time()

        while GPIO.input(ECHO) == GPIO.LOW:
            pulse_start = time.time()
            if pulse_start - timeout_start > 0.1:
                return -1

        pulse_end = time.time()
        timeout_start = time.time()

        while GPIO.input(ECHO) == GPIO.HIGH:
            pulse_end = time.time()
            if pulse_end - timeout_start > 0.1:
                return -1

        pulse_duration = pulse_end - pulse_start
        distance = (pulse_duration * 34300) / 2
        return round(distance, 1) if 2 <= distance <= 450 else round(distance, 1)
    except Exception as e:
        print(f"测距错误: {e}")
        return -1


def open_door():
    global door_locked
    if not door_locked:
        return
    set_servo_angle(90)
    door_locked = False
    print("门已打开")
    publish_mqtt(MQTT_DOOR_STATE_TOPIC, "open")


def close_door():
    global door_locked
    if door_locked:
        return
    set_servo_angle(0)
    door_locked = True
    print("门已关闭")
    publish_mqtt(MQTT_DOOR_STATE_TOPIC, "closed")


def auto_lock_door(delay=20):
    global door_locked, auto_close_thread
    time.sleep(delay)
    if not door_locked:
        close_door()
    auto_close_thread = None


def initialize_camera():
    if not ON_RASPBERRY_PI:
        return None
    try:
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            return None
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        for _ in range(5):
            camera.read()
        return camera
    except Exception:
        return None


def face_recognition_process():
    global door_locked, auto_close_thread

    if face_detector is None:
        print("人脸检测器未加载")
        return False

    camera = initialize_camera()
    if camera is None:
        return False

    face_detected = False
    max_attempts = 10

    try:
        for attempt in range(max_attempts):
            ret, frame = camera.read()
            if not ret:
                time.sleep(0.3)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)

            faces = face_detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            if len(faces) > 0:
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                timestamp = time.strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(f"photos/face_{timestamp}.jpg", frame)
                print(f"检测到人脸! 已保存 photos/face_{timestamp}.jpg")

                publish_mqtt(MQTT_FACE_TOPIC, "on")
                face_detected = True
                break

            time.sleep(0.5)
    finally:
        camera.release()

    if face_detected and door_locked:
        open_door()
        global auto_close_thread
        auto_close_thread = threading.Thread(target=auto_lock_door, args=(20,), daemon=True)
        auto_close_thread.start()
        publish_mqtt(MQTT_FACE_TOPIC, "on")
        return True

    publish_mqtt(MQTT_FACE_TOPIC, "off")
    return False


def distance_monitor():
    global distance_check_active

    print(f"距离监测已启动，阈值: {DISTANCE_THRESHOLD} cm")
    detection_count = 0
    CONFIRMATION_COUNT = 3

    while distance_check_active:
        distance = measure_distance()

        publish_mqtt(MQTT_DISTANCE_TOPIC, {"distance": distance, "unit": "cm"})

        if 0 < distance < DISTANCE_THRESHOLD:
            detection_count += 1
            print(f"接近中! 距离:{distance:.1f}cm ({detection_count}/{CONFIRMATION_COUNT})")

            if detection_count >= CONFIRMATION_COUNT:
                publish_mqtt(MQTT_PRESENCE_TOPIC, "present")
                print("确认有人接近，触发人脸识别...")
                detection_count = 0
                face_recognition_process()
                time.sleep(5)
        else:
            if detection_count > 0:
                publish_mqtt(MQTT_PRESENCE_TOPIC, "absent")
            detection_count = 0

        time.sleep(0.5)


def main_menu():
    global distance_check_active
    monitor_thread = None

    while True:
        print("\n" + "=" * 50)
        print("   树莓派智能门禁系统 (MQTT版)")
        print("=" * 50)
        status = '运行中' if monitor_thread and monitor_thread.is_alive() else '已停止'
        print(f"监控状态: {status} | 门: {'锁定' if door_locked else '打开'} | 阈值: {DISTANCE_THRESHOLD}cm")
        print("-" * 50)
        print("1. 启动监控  2. 停止监控  3. 开门  4. 关门")
        print("5. 测距测试  6. 人脸识别测试  7. 设置阈值  0. 退出")

        choice = input("选择: ").strip()

        if choice == '1':
            if not (monitor_thread and monitor_thread.is_alive()):
                distance_check_active = True
                monitor_thread = threading.Thread(target=distance_monitor, daemon=True)
                monitor_thread.start()
                time.sleep(0.5)
            else:
                print("监控已在运行")
        elif choice == '2':
            distance_check_active = False
            if monitor_thread:
                monitor_thread.join(timeout=3)
            print("监控已停止")
        elif choice == '3':
            open_door()
        elif choice == '4':
            close_door()
        elif choice == '5':
            print("距离测试 (Ctrl+C停止):")
            try:
                while True:
                    d = measure_distance()
                    print(f"距离: {d:.1f} cm" if d > 0 else "测量失败")
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pass
        elif choice == '6':
            face_recognition_process()
        elif choice == '7':
            try:
                t = int(input(f"新阈值 (10-500, 当前{DISTANCE_THRESHOLD}): "))
                if 10 <= t <= 500:
                    DISTANCE_THRESHOLD = t
            except ValueError:
                pass
        elif choice == '0':
            distance_check_active = False
            if monitor_thread:
                monitor_thread.join(timeout=3)
            break


def cleanup():
    if ON_RASPBERRY_PI:
        try:
            if servo_pwm:
                servo_pwm.stop()
            GPIO.cleanup()
        except Exception:
            pass
    if client:
        client.loop_stop()
        client.disconnect()
    print("资源已释放")


if __name__ == "__main__":
    print("树莓派智能门禁系统 (MQTT版)")
    setup_gpio()
    door_locked = True
    if ON_RASPBERRY_PI:
        close_door()
    publish_mqtt(MQTT_DOOR_STATE_TOPIC, "closed")
    main_menu()
    cleanup()
    print("系统已退出")
