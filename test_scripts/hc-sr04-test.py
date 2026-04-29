#!/usr/bin/python3

import RPi.GPIO as GPIO
import time
import sys

# GPIO setup (BCM mode)
TRIG = 23
ECHO = 25

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def get_distance():
    # Ensure trigger is low
    GPIO.output(TRIG, False)
    time.sleep(0.05)

    # Send 10µs pulse
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    # Wait for echo start
    start_time = time.time()
    timeout = start_time + 0.02
    while GPIO.input(ECHO) == 0:
        start_time = time.time()
        if start_time > timeout:
            return None

    # Wait for echo end
    end_time = time.time()
    timeout = end_time + 0.02
    while GPIO.input(ECHO) == 1:
        end_time = time.time()
        if end_time > timeout:
            return None

    # Calculate distance
    duration = end_time - start_time
    distance_cm = duration * 17150  # speed of sound constant

    return round(distance_cm, 2)

def main():
    interval = None

    if len(sys.argv) > 1:
        try:
            interval = float(sys.argv[1])
        except ValueError:
            print("Invalid interval value")
            sys.exit(1)

    try:
        if interval is None:
            distance = get_distance()
            print(f"Distance: {distance} cm")
        else:
            print(f"Running continuous mode (interval={interval}s). Ctrl+C to stop.")
            while True:
                distance = get_distance()
                print(f"Distance: {distance} cm")
                time.sleep(interval)

    except KeyboardInterrupt:
        print("\nExiting...")

    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
