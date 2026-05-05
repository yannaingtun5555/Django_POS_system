import subprocess
import webbrowser
import time
import atexit
import signal
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(file))
COMPOSE_DIR = os.path.join(BASE_DIR, "config")

def run(cmd):
    return subprocess.run(cmd, cwd=COMPOSE_DIR)

# 🔥 START DOCKER
def start_docker():
    print("Starting Docker containers...")
    run(["docker", "compose", "up", "-d"])

# 🔥 STOP DOCKER (important cleanup)
def stop_docker():
    print("Stopping Docker containers...")
    run(["docker", "compose", "down"])

# ensure cleanup always happens
atexit.register(stop_docker)

def handle_exit(signum, frame):
    stop_docker()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def wait_for_service():
    # simple delay (you can improve with health check later)
    time.sleep(5)

def open_ui():
    webbrowser.open("http://localhost:8000")  # change to your Django port

def main():
    start_docker()
    wait_for_service()
    open_ui()

    print("POS running... (closing EXE will stop Docker)")

    # keep EXE alive silently
    while True:
        time.sleep(1)

if name == "main":
    main()