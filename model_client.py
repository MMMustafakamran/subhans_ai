import sys
import argparse
import socket
import csv
import time
import os
from model_driver import ModelDriver

# === Argument Parsing ===
parser = argparse.ArgumentParser(description='Python client to test trained model in TORCS.')
parser.add_argument('--host', dest='host_ip', default='localhost')
parser.add_argument('--port', type=int, dest='host_port', default=3001)
parser.add_argument('--id', dest='id', default='SCR')
parser.add_argument('--maxEpisodes', dest='max_episodes', type=int, default=1)
parser.add_argument('--maxSteps', dest='max_steps', type=int, default=0)
parser.add_argument('--track', dest='track', default=None)
parser.add_argument('--stage', type=int, dest='stage', default=3)
args = parser.parse_args()

print(f"Connecting to TORCS at {args.host_ip}:{args.host_port} | Bot ID: {args.id} | Track: {args.track}")
print("*********************************************")
print('Press "m" to toggle model control')
print('Press "s" to start logging, "e" to stop logging')
print('Press "q" to quit')
print("*********************************************")

# === File Setup ===
TEMP_LOG_FILE = "model_test_run.csv"
MASTER_LOG_FILE = "model_test_data.csv"

header = [
    "Step", "Time", "SpeedX", "SpeedY", "SpeedZ", "TrackPos", "Angle", "RPM", "Gear_State",
    "CurLapTime", "DistFromStart", "DistRaced", "Fuel", "Damage", "RacePos",
    "Accel", "Brake", "Steer", "Gear_Control", "Clutch", "Meta",
    "IsAutoShifting", "LastManualShiftTime", "SteerDirection", "IsStopped",
    "IsModelControl"
]

def initialize_csv():
    with open(TEMP_LOG_FILE, "w", newline="") as f:
        csv.writer(f).writerow(header)
    if not os.path.exists(MASTER_LOG_FILE):
        with open(MASTER_LOG_FILE, "w", newline="") as f:
            csv.writer(f).writerow(header)

initialize_csv()

# === Networking Setup ===
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)
except socket.error:
    print("Could not create socket.")
    sys.exit(-1)

# === Driver Init ===
driver = ModelDriver(args.stage)

shutdown = False
episode = 0
step = 0

while not shutdown:
    while True:
        init_str = args.id + driver.init()
        try:
            sock.sendto(init_str.encode(), (args.host_ip, args.host_port))
            buf, _ = sock.recvfrom(1000)
            if '***identified***' in buf.decode():
                break
        except socket.error:
            continue

    while True:
        if driver.should_quit:
            shutdown = True
            break

        try:
            buf, _ = sock.recvfrom(1000)
            buf = buf.decode()
        except socket.error:
            continue

        if "***shutdown***" in buf:
            driver.onShutDown()
            shutdown = True
            break
        elif "***restart***" in buf:
            driver.onRestart()
            break

        if driver.logging_enabled:
            telemetry = driver.state.parser.parse(buf)
            if telemetry:
                row = [
                    step, time.time(),
                    telemetry.get("speedX", [""])[0],
                    telemetry.get("speedY", [""])[0],
                    telemetry.get("speedZ", [""])[0],
                    telemetry.get("trackPos", [""])[0],
                    telemetry.get("angle", [""])[0],
                    telemetry.get("rpm", [""])[0],
                    telemetry.get("gear", [""])[0],
                    telemetry.get("curLapTime", [""])[0],
                    telemetry.get("distFromStart", [""])[0],
                    telemetry.get("distRaced", [""])[0],
                    telemetry.get("fuel", [""])[0],
                    telemetry.get("damage", [""])[0],
                    telemetry.get("racePos", [""])[0],
                    driver.control.accel,
                    driver.control.brake,
                    driver.control.steer,
                    driver.control.gear,
                    driver.control.clutch,
                    driver.control.meta,
                    driver.is_auto_shifting,
                    driver.last_manual_shift_time,
                    driver.last_steer_direction,
                    driver.is_stopped,
                    driver.use_model  # Model control flag
                ]
                with open(TEMP_LOG_FILE, "a", newline="") as f:
                    csv.writer(f).writerow(row)

        step += 1
        if step != args.max_steps:
            if buf:
                control_msg = driver.drive(buf)
        else:
            control_msg = "(meta 1)"

        try:
            sock.sendto(control_msg.encode(), (args.host_ip, args.host_port))
        except socket.error:
            print("Failed to send control.")
            sys.exit(-1)

    episode += 1
    if episode == args.max_episodes:
        shutdown = True

sock.close()

# === Save data ===
if os.path.exists(TEMP_LOG_FILE) and os.path.getsize(TEMP_LOG_FILE) > 0:
    save = input("Do you want to save this run to model_test_data.csv? (y/n): ")
    if save.strip().lower() == "y":
        with open(TEMP_LOG_FILE, "r") as t:
            data = t.readlines()[1:]
            with open(MASTER_LOG_FILE, "a") as m:
                m.writelines(data)
        print(f"✅ Data saved to {MASTER_LOG_FILE}")
    else:
        print("⚠️ Data discarded.")
    os.remove(TEMP_LOG_FILE)
