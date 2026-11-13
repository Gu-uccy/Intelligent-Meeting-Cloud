#!/usr/bin/env python3
import time

import RPi.GPIO as GPIO


TRIG = 20
ECHO = 21


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(TRIG, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(ECHO, GPIO.IN)

time.sleep(0.2)
print(f"initial_echo={GPIO.input(ECHO)}")

try:
    for index in range(10):
        GPIO.output(TRIG, GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(TRIG, GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(TRIG, GPIO.LOW)

        wait_start = time.monotonic()
        while GPIO.input(ECHO) == GPIO.LOW:
            if time.monotonic() - wait_start > 0.05:
                print(f"{index}: timeout_wait_echo_high")
                break
        else:
            pulse_start = time.monotonic()
            while GPIO.input(ECHO) == GPIO.HIGH:
                if time.monotonic() - pulse_start > 0.05:
                    print(f"{index}: timeout_wait_echo_low")
                    break
            else:
                pulse_end = time.monotonic()
                distance = (pulse_end - pulse_start) * 34300 / 2
                print(f"{index}: distance_cm={distance:.1f}")
finally:
    GPIO.cleanup()

