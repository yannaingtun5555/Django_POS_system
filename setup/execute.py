import subprocess
import time
import webbrowser
import signal
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPOSE_DIR = os.path.join(BASE_DIR, "config")

def run_compose(cmd):
    return subprocess.run(
        ["docker", "compose"] + cmd,
        cwd=COMPOSE_DIR
    )

def cleanup(signal_received=None, frame=None):
    print("\n🛑 Stopping containers...")
    run_compose(["down"])
    sys.exit(0)

# Handle exit signals
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

print("🚀 Starting POS system...")

run_compose(["up", "-d", "--build"])

# Wait a bit (you can upgrade to health check later)
time.sleep(5)

print("🌐 Opening browser...")
webbrowser.open("http://localhost:8000")  # Django
#webbrowser.open("http://localhost:8501")  # Streamlit

print("✅ POS running. Press CTRL+C to stop.")

# Keep alive
while True:
    time.sleep(1)