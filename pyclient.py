"""
This script serves as a Python client to connect to the TORCS SCRC server in manual mode 
and log telemetry data to a CSV file.
Functionality:
- Connects to the TORCS SCRC server using UDP sockets.
- Sends initialization and control commands to the server.
- Receives telemetry data from the server and logs it to a CSV file.
- Supports configurable parameters such as host IP, port, bot ID, maximum episodes, steps, track, and stage.
- Handles server responses for shutdown and restart commands.
- Uses a driver module for manual control and telemetry parsing.
Usage:
- Run the script with appropriate command-line arguments to configure the connection and logging behavior.
"""
import sys
import argparse
import socket
import csv
import time
import os
import driver  # Assuming driver.py is available
from datetime import datetime

if __name__ == '__main__':
    pass

# Define directory structure
DATASET_DIR = "dataset"
MODES = ["manual", "ruleai", "learning"]

# Configure argument parser
parser = argparse.ArgumentParser(description='Python client to connect to the TORCS SCRC server in manual mode and log telemetry data to a CSV file.')
parser.add_argument('--host', action='store', dest='host_ip', default='localhost',
                    help='Host IP address (default: localhost)')
parser.add_argument('--port', action='store', type=int, dest='host_port', default=3001,
                    help='Host port number (default: 3001)')
parser.add_argument('--id', action='store', dest='id', default='SCR',
                    help='Bot ID (default: SCR)')
parser.add_argument('--maxEpisodes', action='store', dest='max_episodes', type=int, default=1,
                    help='Maximum number of learning episodes (default: 1)')
parser.add_argument('--maxSteps', action='store', dest='max_steps', type=int, default=0,
                    help='Maximum number of steps (default: 0)')
parser.add_argument('--track', action='store', dest='track', default=None,
                    help='Name of the track')
parser.add_argument('--stage', action='store', dest='stage', type=int, default=3,
                    help='Stage (0 - Warm-Up, 1 - Qualifying, 2 - Race, 3 - Unknown)')
parser.add_argument('--mode', action='store', dest='mode', default='manual',
                    choices=MODES,
                    help='Operation mode: manual, ruleai, or learning (default: manual)')

arguments = parser.parse_args()

# Print summary
print('Connecting to server host ip:', arguments.host_ip, '@ port:', arguments.host_port)
print('Bot ID:', arguments.id)
print('Maximum episodes:', arguments.max_episodes)
print('Maximum steps:', arguments.max_steps)
print('Track:', arguments.track)
print('Stage:', arguments.stage)
print('*********************************************')
print('Press "s" to start logging, "e" to stop logging')
print('Press "q" to quit')
print('*********************************************')

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
except socket.error as msg:
    print('Could not make a socket.')
    sys.exit(-1)

# One second timeout
sock.settimeout(1.0)

# Create directory structure if it doesn't exist
def create_directory_structure():
    if not os.path.exists(DATASET_DIR):
        os.makedirs(DATASET_DIR)
    for mode in MODES:
        mode_path = os.path.join(DATASET_DIR, mode)
        if not os.path.exists(mode_path):
            os.makedirs(mode_path)

# Generate timestamped filename
def get_timestamped_filename(mode):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{mode}_data_{timestamp}.csv"

# Define file path
LOG_FILE = os.path.join(DATASET_DIR, arguments.mode, get_timestamped_filename(arguments.mode))

# Initialize CSV file
def initialize_csv_file():
    # Create directory structure
    create_directory_structure()
    
    # Create file with headers
    with open(LOG_FILE, "w", newline="") as file:
        writer = csv.writer(file)
        header = [
            "Step", "Time",
            # Car State Fields
            "SpeedX", "SpeedY", "SpeedZ", "TrackPos", "Angle", "RPM", "Gear_State",
            "CurLapTime", "DistFromStart", "DistRaced", "Fuel",
            "Damage", "RacePos",
            # Car Control Fields
            "Accel", "Brake", "Steer", "Gear_Control", "Clutch", "Meta",
            # Additional Metrics
            "IsAutoShifting", "LastManualShiftTime", "SteerDirection", "IsStopped"
        ]
        writer.writerow(header)

initialize_csv_file()

shutdownClient = False
curEpisode = 0
verbose = False
MAX_RECONNECT_ATTEMPTS = 30  # Maximum number of reconnection attempts
RECONNECT_DELAY = 1.0  # Delay between reconnection attempts in seconds

# Instantiate Driver for manual control only
d = driver.Driver(arguments.stage)
d.logging_enabled = True  # Enable logging by default

# Add these variables at the top with other global variables
last_reconnect_message = 0
reconnect_attempts = 0
RECONNECT_MESSAGE_INTERVAL = 5  # seconds between messages

while not shutdownClient:
    while True:
        if verbose:
            print('Sending id to server:', arguments.id)
        buf = arguments.id + d.init()
        if verbose:
            print('Sending init string to server:', buf)
        
        try:
            sock.sendto(buf.encode(), (arguments.host_ip, arguments.host_port))
        except socket.error as msg:
            print("Failed to send data...Exiting...")
            sys.exit(-1)
            
        try:
            buf, addr = sock.recvfrom(1000)
            buf = buf.decode()
        except socket.error as msg:
            current_time = time.time()
            if current_time - last_reconnect_message >= RECONNECT_MESSAGE_INTERVAL:
                reconnect_attempts += 1
                if reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
                    print("Maximum reconnection attempts reached. Exiting...")
                    sys.exit(-1)
                print(f"Connection lost - Attempting to reconnect (Attempt {reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS})...")
                last_reconnect_message = current_time
            time.sleep(RECONNECT_DELAY)
            continue
    
        if '***identified***' in buf:
            if reconnect_attempts > 0:
                print('Successfully reconnected to server')
                reconnect_attempts = 0
            else:
                print('Successfully connected to server')
            break

    currentStep = 0
    print(f"\nStarting data collection in {arguments.mode} mode...")
    
    while True:
        # Check if driver wants to quit
        if d.should_quit:
            print("Quit signal received from driver")
            shutdownClient = True
            break

        # Wait for an answer from server
        buf = None
        try:
            buf, addr = sock.recvfrom(1000)
            buf = buf.decode()
        except socket.error as msg:
            current_time = time.time()
            if current_time - last_reconnect_message >= RECONNECT_MESSAGE_INTERVAL:
                reconnect_attempts += 1
                if reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
                    print("Maximum reconnection attempts reached. Exiting...")
                    sys.exit(-1)
                print(f"Connection lost - Attempting to reconnect (Attempt {reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS})...")
                last_reconnect_message = current_time
            time.sleep(RECONNECT_DELAY)
            continue
        
        if verbose:
            print('Received:', buf)
        
        if buf and '***shutdown***' in buf:
            d.onShutDown()
            shutdownClient = True
            print('Server requested shutdown')
            break
        
        if buf and '***restart***' in buf:
            d.onRestart()
            print('Server requested restart')
            break

        # Log telemetry data
        try:
            telemetry = d.state.parser.parse(buf)
            if telemetry:
                row = [
                    currentStep,
                    time.time(),
                    # Car State Values
                    telemetry.get("speedX", [0])[0],
                    telemetry.get("speedY", [0])[0],
                    telemetry.get("speedZ", [0])[0],
                    telemetry.get("trackPos", [0])[0],
                    telemetry.get("angle", [0])[0],
                    telemetry.get("rpm", [0])[0],
                    telemetry.get("gear", [0])[0],
                    telemetry.get("curLapTime", [0])[0],
                    telemetry.get("distFromStart", [0])[0],
                    telemetry.get("distRaced", [0])[0],
                    telemetry.get("fuel", [0])[0],
                    telemetry.get("damage", [0])[0],
                    telemetry.get("racePos", [0])[0],
                    # Car Control Values
                    d.control.accel,
                    d.control.brake,
                    d.control.steer,
                    d.control.gear,
                    d.control.clutch,
                    d.control.meta,
                    # Additional Metrics
                    d.is_auto_shifting,
                    d.last_manual_shift_time,
                    d.last_steer_direction,
                    d.is_stopped
                ]
                
                with open(LOG_FILE, "a", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(row)
                
                # Print progress every 100 steps
                if currentStep % 100 == 0:
                    print(f"Step {currentStep}: Logging data...")
        except Exception as e:
            print(f"Error processing telemetry data: {str(e)}")
            continue
        
        currentStep += 1
        if currentStep != arguments.max_steps:
            if buf:
                buf = d.drive(buf)
        else:
            buf = '(meta 1)'
        
        if verbose:
            print('Sending:', buf)
        
        if buf:
            try:
                sock.sendto(buf.encode(), (arguments.host_ip, arguments.host_port))
            except socket.error as msg:
                print("Failed to send data...Exiting...")
                sys.exit(-1)
    
    curEpisode += 1
    
    if curEpisode == arguments.max_episodes:
        shutdownClient = True

sock.close()

# Print completion message
if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
    print(f"\nSession completed. Total steps: {currentStep}")
    print(f"Data saved to: {LOG_FILE}")
