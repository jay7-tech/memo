"""
Standalone Dashboard Debugger for Pi
------------------------------------
Run this script to verify if the dashboard can start in isolation.
Usage: python debug_dashboard_standalone.py
"""

import sys
import time
import threading
import socket
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DashDebug")

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

print("\n=== MEMO Dashboard Debugger ===")
print("1. Checking Environment...")

try:
    import cv2
    print("   [OK] cv2 imported")
except ImportError as e:
    print(f"   [FAIL] cv2 missing: {e}")

try:
    from flask import Flask, render_template_string
    from flask_socketio import SocketIO
    print("   [OK] Flask/SocketIO imported")
except ImportError as e:
    print(f"   [FAIL] Flask/SocketIO missing: {e}")
    sys.exit(1)

print("\n2. Checking Port 5000...")
if check_port(5000):
    print("   [WARN] Port 5000 is already in use using! If MEMO is running, stop it first.")
else:
    print("   [OK] Port 5000 is free.")

print("\n3. Initializing Mock Dashboard...")

# --- MOCK DASHBOARD LOGIC (Simplified from interface/dashboard.py) ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'debug_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

@app.route("/")
def index():
    return "MEMO Dashboard Debug Mode - IT WORKS!"

def start_server():
    print("   [INFO] Starting Server on 0.0.0.0:5000...")
    try:
        # Try-catch the run method specifically
        socketio.run(
            app, 
            host="0.0.0.0", 
            port=5000, 
            debug=False, 
            use_reloader=False, 
            allow_unsafe_werkzeug=True
        )
    except TypeError as e:
        print(f"   [ERROR] TypeError in socketio.run: {e}")
        print("   [INFO] Retrying without 'allow_unsafe_werkzeug'...")
        try:
             socketio.run(
                app, 
                host="0.0.0.0", 
                port=5000, 
                debug=False, 
                use_reloader=False
            )
        except Exception as e2:
             print(f"   [FATAL] Retry failed: {e2}")
    except Exception as e:
        print(f"   [FATAL] Server crashed: {e}")

# Start in thread
t = threading.Thread(target=start_server, daemon=True)
t.start()

print("\n4. Keep Alive Loop...")
print("   Please open http://<PI_IP>:5000 in your browser.")
print("   Press Ctrl+C to exit.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n[DONE] Exiting.")
