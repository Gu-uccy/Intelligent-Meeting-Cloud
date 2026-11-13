#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 树莓派智能门禁系统 - 集成超声波传感器、USB摄像头人脸识别与舵机控制

import cv2
import time
import os
import numpy as np
import threading

try:
    import RPi.GPIO as GPIO
    ON_RASPBERRY_PI = True
except (ImportError, NotImplementedError):
    ON_RASPBERRY_PI = False
    print("警告: 未检测到树莓派环境，GPIO和摄像头功能将受限")

current_dir = os.getcwd()

for directory in ['photos', 'videos']:
    dir_path = os.path.join(current_dir, directory)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"已创建{directory}目录: {dir_path}")

cascade_file = None
possible_paths = [
    '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
    '/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
    '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml',
    '/usr/local/share/opencv/haarcascades/haarcascade_frontalface_default.xml',
    '/usr/local/lib/python3.9/dist-packages/cv2/data/haarcascade_frontalface_default.xml',
    '/usr/lib/python3/dist-packages/cv2/data/haarcascade_frontalface_default.xml',
    os.path.join(os.path.dirname(cv2.__file__), 'data', 'haarcascade_frontalface_default.xml'),
    os.path.join(current_dir, 'haarcascade_frontalface_default.xml')
]

for path in possible_paths:
    if os.path.exists(path):
        cascade_file = path
        print(f"找到人脸级联分类器: {path}")
        break

if cascade_file is None:
    print("警告: 无法找到人脸级联分类器文件")
    print("请手动下载haarcascade_frontalface_default.xml文件到当前目录")
    print("下载地址: https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml")

face_detector = None
if cascade_file:
    face_detector = cv2.CascadeClassifier(cascade_file)
    if face_detector.empty():
        print("错误: 无法加载人脸检测器数据")
        face_detector = None
    else:
        print("人脸检测器加载成功")

SERVO_PIN = 18
TRIG = 23
ECHO = 24

door_locked = True
auto_close_thread = None
distance_check_active = True
DISTANCE_THRESHOLD = 100


def setup_gpio():
    global door_locked

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


servo_pwm = None


def set_servo_angle(angle):
    if not ON_RASPBERRY_PI or servo_pwm is None:
        print(f"模拟: 舵机转动到{angle}度")
        return

    duty = 2.5 + (angle / 180.0) * 10.0
    servo_pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    servo_pwm.ChangeDutyCycle(0)


def measure_distance():
    if not ON_RASPBERRY_PI:
        import random
        dist = random.uniform(30, 200)
        return round(dist, 1)

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

        if 2 <= distance <= 450:
            return round(distance, 1)
        else:
            return round(distance, 1)
    except Exception as e:
        print(f"距离测量错误: {e}")
        return -1


def open_door():
    global door_locked
    if not door_locked:
        print("门已经处于打开状态")
        return

    set_servo_angle(90)
    door_locked = False
    print("门已打开 (舵机旋转到90度)")


def close_door():
    global door_locked
    if door_locked:
        print("门已经处于关闭状态")
        return

    set_servo_angle(0)
    door_locked = True
    print("门已关闭 (舵机旋转到0度)")


def auto_lock_door(delay=20):
    global door_locked, auto_close_thread

    print(f"将在{delay}秒后自动关门...")
    time.sleep(delay)

    if not door_locked:
        close_door()
    else:
        print("门已经被其他方式关闭")

    auto_close_thread = None


def initialize_camera():
    if not ON_RASPBERRY_PI:
        print("模拟模式: 摄像头初始化跳过")
        return None

    try:
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("错误: 无法打开摄像头")
            return None

        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FPS, 30)

        for _ in range(5):
            camera.read()

        print("摄像头初始化成功")
        return camera
    except Exception as e:
        print(f"摄像头初始化失败: {e}")
        return None


def face_recognition_process():
    global door_locked, auto_close_thread

    if face_detector is None:
        print("错误: 人脸检测器未加载，无法进行人脸识别")
        return False

    camera = initialize_camera()
    if camera is None:
        return False

    face_detected = False
    max_attempts = 10
    photo_filename = None

    try:
        for attempt in range(max_attempts):
            ret, frame = camera.read()
            if not ret:
                print(f"第{attempt+1}次拍照失败")
                time.sleep(0.3)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)

            faces = face_detector.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(80, 80),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            if len(faces) > 0:
                print(f"检测到 {len(faces)} 张人脸!")

                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                timestamp = time.strftime("%Y%m%d_%H%M%S")
                photo_filename = f"photos/face_{timestamp}.jpg"
                cv2.imwrite(photo_filename, frame)
                print(f"人脸照片已保存: {photo_filename}")

                face_detected = True
                break
            else:
                print(f"第{attempt+1}次未检测到人脸")

            time.sleep(0.5)

    finally:
        camera.release()
        print("摄像头已释放")

    if face_detected and door_locked:
        open_door()

        global auto_close_thread
        auto_close_thread = threading.Thread(target=auto_lock_door, args=(20,), daemon=True)
        auto_close_thread.start()

        return True

    return False


def distance_monitor():
    global distance_check_active

    print(f"距离监测已启动，检测阈值: {DISTANCE_THRESHOLD} cm")
    print("按 Ctrl+C 停止监测")

    detection_count = 0
    CONFIRMATION_COUNT = 3

    try:
        while distance_check_active:
            distance = measure_distance()

            if 0 < distance < DISTANCE_THRESHOLD:
                detection_count += 1
                print(f"检测到接近! 距离: {distance:.1f} cm ({detection_count}/{CONFIRMATION_COUNT})")

                if detection_count >= CONFIRMATION_COUNT:
                    print("确认有人接近，触发人脸识别...")
                    detection_count = 0
                    face_recognition_process()
                    time.sleep(5)
            else:
                if detection_count > 0:
                    print(f"距离: {distance:.1f} cm (已离开检测区域)")
                detection_count = 0

            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n距离监测已停止")


def test_distance_sensor():
    print("\n超声波距离传感器测试:")
    print("按 Ctrl+C 停止测试")

    try:
        while True:
            distance = measure_distance()
            if distance > 0:
                print(f"当前距离: {distance:.1f} cm")
            else:
                print("距离测量失败")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n测试已停止")


def test_door_control():
    global door_locked

    print("\n门控制测试:")
    while True:
        print("\n1. 开门")
        print("2. 关门")
        print("3. 返回主菜单")
        choice = input("请选择操作(1-3): ").strip()

        if choice == '1':
            open_door()
        elif choice == '2':
            close_door()
        elif choice == '3':
            break
        else:
            print("无效选择，请重试")


def test_face_recognition():
    print("\n人脸识别测试:")
    if face_detector is None:
        print("错误: 人脸检测器未加载")
        return

    result = face_recognition_process()
    if result:
        print("人脸识别成功!")
    else:
        print("人脸识别失败或未检测到人脸")


def main_menu():
    global distance_check_active, auto_close_thread

    monitor_thread = None

    while True:
        print("\n" + "=" * 50)
        print("   树莓派智能门禁系统")
        print("=" * 50)
        print(f"距离检测阈值: {DISTANCE_THRESHOLD} cm")
        print(f"门状态: {'锁定' if door_locked else '打开'}")
        print(f"系统监控: {'运行中' if monitor_thread and monitor_thread.is_alive() else '已停止'}")
        print("-" * 50)
        print("1. 启动智能门禁监控系统")
        print("2. 停止监控系统")
        print("3. 测试超声波距离传感器")
        print("4. 测试门控制")
        print("5. 测试人脸识别")
        print("6. 开门")
        print("7. 关门")
        print("8. 设置检测阈值")
        print("0. 退出系统")
        print("-" * 50)

        choice = input("请选择操作(0-8): ").strip()

        if choice == '1':
            if monitor_thread and monitor_thread.is_alive():
                print("监控系统已在运行中")
            else:
                distance_check_active = True
                monitor_thread = threading.Thread(target=distance_monitor, daemon=True)
                monitor_thread.start()
                time.sleep(0.5)

        elif choice == '2':
            if monitor_thread and monitor_thread.is_alive():
                distance_check_active = False
                monitor_thread.join(timeout=3)
                print("监控系统已停止")
            else:
                print("监控系统未在运行")

        elif choice == '3':
            test_distance_sensor()

        elif choice == '4':
            test_door_control()

        elif choice == '5':
            test_face_recognition()

        elif choice == '6':
            open_door()

        elif choice == '7':
            close_door()

        elif choice == '8':
            try:
                new_threshold = int(input(f"请输入新的检测阈值 (当前: {DISTANCE_THRESHOLD} cm): ").strip())
                if 10 <= new_threshold <= 500:
                    DISTANCE_THRESHOLD = new_threshold
                    print(f"检测阈值已更新为: {DISTANCE_THRESHOLD} cm")
                else:
                    print("阈值范围应在10-500之间")
            except ValueError:
                print("请输入有效数字")

        elif choice == '0':
            print("正在退出系统...")
            distance_check_active = False
            if monitor_thread and monitor_thread.is_alive():
                monitor_thread.join(timeout=3)
            break

        else:
            print("无效选择，请重试")


def cleanup_gpio():
    if not ON_RASPBERRY_PI:
        return

    try:
        if servo_pwm:
            servo_pwm.stop()
        GPIO.cleanup()
        print("GPIO资源已清理")
    except Exception as e:
        print(f"清理GPIO时出错: {e}")


if __name__ == "__main__":
    print("树莓派智能门禁系统 - 集成超声波传感器、USB摄像头人脸识别与舵机控制")
    print(f"距离检测阈值: {DISTANCE_THRESHOLD} cm")

    setup_gpio()

    door_locked = True
    if ON_RASPBERRY_PI:
        close_door()
    else:
        print("模拟模式: 门初始化为关闭状态")

    photos_dir = os.path.join(current_dir, 'photos')
    videos_dir = os.path.join(current_dir, 'videos')
    for d in [photos_dir, videos_dir]:
        if not os.access(d, os.W_OK):
            print(f"警告: 目录 {d} 可能没有写入权限")

    main_menu()

    cleanup_gpio()
    print("系统已退出")
