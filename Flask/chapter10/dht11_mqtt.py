#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# DHT11温湿度传感器 - MQTT发布程序
# 将温湿度数据采集并通过MQTT发布到Home Assistant

import time
import json

try:
    import Adafruit_DHT
    HAS_DHT = True
except ImportError:
    HAS_DHT = False
    print("警告: Adafruit_DHT未安装，使用模拟数据")

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False
    print("警告: paho-mqtt未安装，MQTT功能被禁用")

DHT_PIN = 17
sensor = Adafruit_DHT.DHT11 if HAS_DHT else None

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "home/sensors/dht11"

client = None
if HAS_MQTT:
    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        print(f"MQTT已连接到 {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"MQTT连接失败: {e}")
        client = None


def read_dht11():
    if HAS_DHT:
        humidity, temperature = Adafruit_DHT.read_retry(sensor, DHT_PIN)
        if humidity is not None and temperature is not None:
            return round(temperature, 1), round(humidity, 1)
        else:
            print('DHT11读取失败')
            return None, None
    else:
        import random
        temp = 25.0 + random.uniform(-2, 2)
        hum = 50.0 + random.uniform(-5, 5)
        return round(temp, 1), round(hum, 1)


def loop():
    while True:
        temperature, humidity = read_dht11()

        if temperature is not None and humidity is not None:
            print(f'温度={temperature:.1f}°C  湿度={humidity:.1f}%')

            payload = json.dumps({
                "temperature": temperature,
                "humidity": humidity
            })

            if client:
                try:
                    client.publish(MQTT_TOPIC, payload)
                except Exception as e:
                    print(f"MQTT发布失败: {e}")
        else:
            print('读取失败，等待下次重试...')

        time.sleep(60)


if __name__ == '__main__':
    print("DHT11 MQTT数据采集服务启动中...")
    print(f"MQTT主题: {MQTT_TOPIC}")
    print(f"数据更新间隔: 60秒")

    try:
        loop()
    except KeyboardInterrupt:
        print("\n程序已停止")
    finally:
        if client:
            client.loop_stop()
            client.disconnect()
