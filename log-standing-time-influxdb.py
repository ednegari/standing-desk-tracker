#!/usr/bin/python3

import RPi.GPIO as GPIO
import time
import requests

# =========================================================
# GPIO CONFIGURATION
# =========================================================
# PIR sensor detects motion (presence in room)
PIR_PIN = 17

# HC-SR04 ultrasonic sensor (desk height detection)
TRIG_PIN = 23
ECHO_PIN = 25

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(PIR_PIN, GPIO.IN)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

# =========================================================
# SYSTEM CONFIGURATION
# =========================================================

# Height threshold (cm) distinguishing sitting vs standing
HEIGHT_THRESHOLD_CM = 39

# Time (seconds) before considering user "Away"
PRESENCE_TIMEOUT = 120

# Speed of sound for HC-SR04 distance calculation (cm/s)
SPEED_OF_SOUND = 34300

# How often we write to InfluxDB (even if nothing changes)
HEARTBEAT_INTERVAL = 10

# InfluxDB connection details
INFLUX_URL = "http://localhost:8086/write"
INFLUX_DB = "room_monitor"

# =========================================================
# STARTUP / STABILIZATION
# =========================================================

print("Desk presence tracker starting...")
print("Stabilizing (30 sec)...")

# PIR sensors need warm-up time to stabilize readings
for i in range(6):
    time.sleep(5)
    print(f"{(i+1)*5} seconds elapsed")

print("Ready")

# =========================================================
# STATE TRACKING VARIABLES
# =========================================================

# Tracks last motion detected by PIR
last_motion_time = time.time()

# Tracks last time we wrote to InfluxDB
last_write_time = 0

# Current known system state
state = "Away"

# =========================================================
# HELPER: console + influx logging (ONLY on state change)
# =========================================================
def log_state(new_state):
    """
    Print to console only when state changes.
    Also write to InfluxDB immediately.
    """
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {new_state}")
    write_influx(new_state)

# =========================================================
# INFLUX WRITE FUNCTION
# =========================================================
def write_influx(state):
    """
    Convert human-readable state into numeric value
    and write to InfluxDB.
    """
    state_map = {
        "Away": 0,
        "Present-Sitting": 1,
        "Present-Standing": 2
    }

    value = state_map.get(state, -1)

    # Line protocol format for InfluxDB
    line = f"desk_presence,host=pi4 value={value}"

    try:
        requests.post(
            INFLUX_URL,
            params={"db": INFLUX_DB},
            data=line,
            timeout=1
        )
    except Exception as e:
        print(f"Influx write error: {e}")

# =========================================================
# HC-SR04 DISTANCE MEASUREMENT
# =========================================================
def get_distance_cm():
    """
    Sends ultrasonic pulse and measures echo return time.
    Returns distance in cm or None if invalid reading.
    """

    GPIO.output(TRIG_PIN, False)
    time.sleep(0.02)

    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)

    start = time.time()
    timeout = start + 0.03

    # Wait for echo start
    while GPIO.input(ECHO_PIN) == 0:
        start = time.time()
        if start > timeout:
            return None

    stop = time.time()
    timeout = stop + 0.03

    # Wait for echo end
    while GPIO.input(ECHO_PIN) == 1:
        stop = time.time()
        if stop > timeout:
            return None

    elapsed = stop - start
    return (elapsed * SPEED_OF_SOUND) / 2

# =========================================================
# STABILIZED DISTANCE READING
# =========================================================
def get_stable_distance():
    """
    Takes multiple samples and removes noise/outliers.
    Returns averaged distance or None if unreliable.
    """

    samples = []

    for _ in range(5):
        d = get_distance_cm()
        if d is not None:
            samples.append(d)
        time.sleep(0.02)

    if len(samples) < 3:
        return None

    samples.sort()

    # Remove highest and lowest values (noise reduction)
    samples = samples[1:-1]

    return sum(samples) / len(samples)

# =========================================================
# MAIN LOOP
# =========================================================
try:
    while True:

        # -------------------------------------------------
        # PIR updates "last seen motion" timestamp
        # -------------------------------------------------
        if GPIO.input(PIR_PIN) == 1:
            last_motion_time = time.time()

        # Determine if user is still considered "present"
        is_present = (time.time() - last_motion_time) <= PRESENCE_TIMEOUT

        # -------------------------------------------------
        # Always measure desk height (no dependency on PIR)
        # -------------------------------------------------
        distance = get_stable_distance()

        # -------------------------------------------------
        # Determine system state
        # -------------------------------------------------
        if not is_present:
            new_state = "Away"
        else:
            if distance is None:
                time.sleep(0.5)
                continue

            if distance < HEIGHT_THRESHOLD_CM:
                new_state = "Present-Sitting"
            else:
                new_state = "Present-Standing"

        # -------------------------------------------------
        # Write rules:
        # - Always write every 10 seconds (heartbeat)
        # - Always write immediately on state change
        # -------------------------------------------------
        now = time.time()

        state_changed = (new_state != state)
        heartbeat_due = (now - last_write_time) >= HEARTBEAT_INTERVAL

        if state_changed or heartbeat_due:
            state = new_state
            write_influx(state)
            last_write_time = now

            # ONLY print to console on state change
            if state_changed:
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {state}")

        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopped")

finally:
    GPIO.cleanup()
