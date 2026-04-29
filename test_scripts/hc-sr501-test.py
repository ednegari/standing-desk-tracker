#!/usr/bin/python3

import RPi.GPIO as GPIO
import time

PIR_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)

print("PIR test running (Ctrl+C to stop)")
print("Stabilizing (30 sec)...")

for i in range(6):
    time.sleep(5)
    print(f"{(i+1)*5} seconds elapsed")

print("Ready")

motion_state = False

try:
    while True:
        current_state = GPIO.input(PIR_PIN)

        if current_state == 1 and not motion_state:
            print(f"{time.strftime('%H:%M:%S')} - MOTION DETECTED")
            motion_state = True

        elif current_state == 0 and motion_state:
            print(f"{time.strftime('%H:%M:%S')} - NO MOTION")
            motion_state = False

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nStopped")

finally:
    GPIO.cleanup()

