from flask import Flask, render_template_string, Response, jsonify, request
from flask_socketio import SocketIO, emit
import cv2
import threading
import time
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'memo_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Shared state
output_frame = None
lock = threading.Lock()
scene_state_ref = None
logs_queue = []

def set_scene_state(state):
    global scene_state_ref
    scene_state_ref = state

def add_log(message, type="info"):
    global logs_queue
    timestamp = time.strftime("%H:%M:%S")
    log_entry = {"time": timestamp, "msg": message, "type": type}
    logs_queue.append(log_entry)
    if len(logs_queue) > 50:
        logs_queue.pop(0)
    socketio.emit('new_log', log_entry)

def update_frame(frame):
    global output_frame
    with lock:
        output_frame = frame.copy()

def generate():
    global output_frame
    while True:
        with lock:
            if output_frame is None:
                time.sleep(0.01)
                continue
            
            # Use lower quality for higher FPS over network
            # Encode with 70% quality to reduce bandwidth
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if not flag:
                continue
        
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encodedImage) + b'\r\n')
        time.sleep(0.005)

@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MEMO Neural Interface</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #050608;
                --card-bg: rgba(16, 18, 23, 0.8);
                --accent: #00f2ff;
                --accent-glow: rgba(0, 242, 255, 0.4);
                --text: #e0e6ed;
                --danger: #ff3366;
                --border: rgba(255, 255, 255, 0.08);
            }

            body { 
                font-family: 'Outfit', sans-serif; 
                background: var(--bg); 
                background-image: 
                    radial-gradient(circle at 20% 20%, rgba(0, 242, 255, 0.05) 0%, transparent 40%),
                    radial-gradient(circle at 80% 80%, rgba(255, 51, 102, 0.05) 0%, transparent 40%);
                color: var(--text); 
                margin: 0; 
                padding: 0;
                overflow-x: hidden;
                min-height: 100vh;
            }

            .header {
                padding: 20px 40px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-bottom: 1px solid var(--border);
                backdrop-filter: blur(10px);
                position: sticky;
                top: 0;
                z-index: 100;
            }

            .logo {
                font-size: 1.5rem;
                font-weight: 600;
                letter-spacing: 2px;
                color: var(--accent);
                display: flex;
                align-items: center;
                gap: 15px;
            }

            .logo-dot {
                width: 12px;
                height: 12px;
                background: var(--accent);
                border-radius: 50%;
                box-shadow: 0 0 15px var(--accent);
                animation: pulse 2s infinite;
            }

            @keyframes pulse {
                0% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.5; transform: scale(1.2); }
                100% { opacity: 1; transform: scale(1); }
            }

            .main-grid {
                display: grid;
                grid-template-columns: 1fr 380px;
                gap: 25px;
                padding: 25px;
                max-width: 1600px;
                margin: 0 auto;
            }

            @media (max-width: 1100px) {
                .main-grid { grid-template-columns: 1fr; }
            }

            .glass-card {
                background: var(--card-bg);
                backdrop-filter: blur(12px);
                border: 1px solid var(--border);
                border-radius: 16px;
                padding: 20px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            }

            .video-container {
                position: relative;
                border-radius: 12px;
                overflow: hidden;
                border: 1px solid var(--border);
                background: #000;
                aspect-ratio: 16/9;
            }

            .video-container img {
                width: 100%;
                height: 100%;
                object-fit: contain;
            }

            .hud-overlay {
                position: absolute;
                top: 0; left: 0; width: 100%; height: 100%;
                pointer-events: none;
                border: 1px solid rgba(0, 242, 255, 0.1);
                box-sizing: border-box;
            }

            .scanline {
                width: 100%;
                height: 2px;
                background: rgba(0, 242, 255, 0.1);
                position: absolute;
                top: -2px;
                animation: scan 4s linear infinite;
            }

            @keyframes scan {
                0% { top: 0%; }
                100% { top: 100%; }
            }

            .side-panel {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }

            .stat-group {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .stat-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                background: rgba(255,255,255,0.03);
                border-radius: 8px;
            }

            .stat-label { color: #888; font-size: 0.9rem; }
            .stat-value { font-weight: 500; font-family: 'JetBrains Mono', monospace; }
            .stat-value.active { color: var(--accent); }
            .stat-value.focus { color: var(--danger); text-shadow: 0 0 10px var(--danger); }

            .terminal {
                background: #000;
                border: 1px solid rgba(0,242,255,0.2);
                border-radius: 8px;
                height: 300px;
                overflow-y: auto;
                padding: 15px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }

            .log-entry { display: flex; gap: 10px; }
            .log-time { color: #555; }
            .log-type-ai { color: #a855f7; }
            .log-type-info { color: #22c55e; }
            .log-type-alert { color: var(--danger); }

            .input-box {
                margin-top: 15px;
                display: flex;
                gap: 10px;
            }

            input {
                flex: 1;
                background: rgba(255,255,255,0.05);
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 12px;
                color: #fff;
                font-family: inherit;
                outline: none;
                transition: border-color 0.3s;
            }

            input:focus { border-color: var(--accent); }

            button {
                background: var(--accent);
                color: #000;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }

            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 15px var(--accent-glow);
            }

            .pill {
                padding: 4px 10px;
                border-radius: 20px;
                font-size: 0.8rem;
                background: rgba(0, 242, 255, 0.1);
                color: var(--accent);
                border: 1px solid var(--accent-glow);
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">
                <div class="logo-dot"></div>
                MEMO <span style="font-weight: 300; opacity: 0.6;">NEURAL HUD</span>
            </div>
            <div id="system-stats" style="display: flex; gap: 20px; font-size: 0.9rem; color: #666;">
                <span>CPU: <span class="stat-value" id="cpu-val">0%</span></span>
                <span>FPS: <span class="stat-value" id="fps-val">0.0</span></span>
            </div>
        </div>

        <div class="main-grid">
            <div class="side-panel">
                <div class="video-container">
                    <img src="/video_feed">
                    <div class="hud-overlay">
                        <div class="scanline"></div>
                    </div>
                </div>
                
                <div class="glass-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3 style="margin: 0; font-weight: 600;">System Console</h3>
                        <span class="pill">REAL-TIME</span>
                    </div>
                    <div class="terminal" id="terminal">
                        <div class="log-entry">
                            <span class="log-time">[System]</span>
                            <span class="log-msg">Neural interface synchronized. Waiting for telemetry...</span>
                        </div>
                    </div>
                    <form class="input-box" id="cmd-form">
                        <input type="text" id="cmd-input" placeholder="Enter command (e.g. 'focus on', 'where is bottle')..." autocomplete="off">
                        <button type="submit">SEND</button>
                    </form>
                </div>
            </div>

            <div class="side-panel">
                <div class="glass-card">
                    <h3 style="margin-top: 0; margin-bottom: 20px; font-weight: 600;">Neural Telemetry</h3>
                    <div class="stat-group">
                        <div class="stat-row">
                            <span class="stat-label">System State</span>
                            <span class="stat-value active" id="identity">WAITING...</span>
                        </div>
                        <div class="stat-row">
                            <span class="stat-label">Focus Shield</span>
                            <span class="stat-value" id="focus-st">DISABLED</span>
                        </div>
                        <div class="stat-row">
                            <span class="stat-label">Entities Observed</span>
                            <span class="stat-value" id="objects">None</span>
                        </div>
                    </div>
                    <div style="margin-top: 25px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        <button onclick="sendCmd('focus on')" style="background: rgba(255, 51, 102, 0.1); color: #ff3366; border: 1px solid rgba(255, 51, 102, 0.2);">FOCUS ON</button>
                        <button onclick="sendCmd('focus off')" style="background: rgba(255, 255, 255, 0.05); color: #fff; border: 1px solid var(--border);">FOCUS OFF</button>
                    </div>
                </div>

                <div class="glass-card">
                    <h3 style="margin-top: 0; margin-bottom: 15px; font-weight: 600;">Memory Bank</h3>
                    <div style="font-size: 0.9rem; color: #888; line-height: 1.6;" id="objects-detail">
                        Scanning environment for persistent objects...
                    </div>
                </div>
            </div>
        </div>

        <script>
            const socket = io();
            const terminal = document.getElementById('terminal');

            socket.on('stats_update', function(data) {
                document.getElementById('cpu-val').innerText = data.cpu + '%';
                document.getElementById('fps-val').innerText = data.fps;
                
                document.getElementById('identity').innerText = data.identity || (data.human_present ? "UNIDENTIFIED" : "IDLE");
                document.getElementById('identity').style.color = data.human_present ? "#00f2ff" : "#555";
                
                const focusSt = document.getElementById('focus-st');
                focusSt.innerText = data.focus_mode ? "SHIELD ACTIVE" : "DISABLED";
                focusSt.className = "stat-value " + (data.focus_mode ? "focus" : "");
                
                document.getElementById('objects').innerText = data.objects.length;
                document.getElementById('objects-detail').innerText = data.objects.length ? "Detecting: " + data.objects.join(", ") : "No significant entities found.";
            });

            socket.on('new_log', function(entry) {
                const div = document.createElement('div');
                div.className = 'log-entry';
                div.innerHTML = `
                    <span class="log-time">[${entry.time}]</span>
                    <span class="log-type-${entry.type}">${entry.type.toUpperCase()}:</span>
                    <span class="log-msg">${entry.msg}</span>
                `;
                terminal.appendChild(div);
                terminal.scrollTop = terminal.scrollHeight;
            });

            function sendCmd(text) {
                fetch('/api/command', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: text})
                });
            }

            document.getElementById('cmd-form').onsubmit = function(e) {
                e.preventDefault();
                const input = document.getElementById('cmd-input');
                if(input.value) {
                    sendCmd(input.value);
                    input.value = '';
                }
            };
        </script>
    </body>
    </html>
    """)

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route("/api/command", methods=['POST'])
def api_command():
    cmd = request.json.get('command')
    if cmd and scene_state_ref:
        # We can't directly process here, so we push to event bus via a global handler setup in main.py
        # For now, we'll use a queue or shared flag
        scene_state_ref.pending_commands.put(cmd)
        add_log(f"Received command: {cmd}", "info")
        return jsonify({"status": "queued"})
    return jsonify({"status": "error"})

def start_server():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Run a background thread to broadcast stats via SocketIO
    def stats_broadcaster():
        while True:
            if scene_state_ref:
                from core import get_perf_monitor
                perf = get_perf_monitor()
                stats = perf.get_stats()
                
                data = {
                    'human_present': scene_state_ref.human['present'],
                    'identity': scene_state_ref.human['identity'],
                    'focus_mode': scene_state_ref.focus_mode,
                    'objects': list(scene_state_ref.objects.keys()),
                    'cpu': stats['cpu'],
                    'fps': stats['fps'],
                    'memory': stats['memory']
                }
                socketio.emit('stats_update', data)
            time.sleep(0.5) # Update stats twice a second (low overhead)
            
    threading.Thread(target=stats_broadcaster, daemon=True).start()
    
    print(">> SYSTEM: Neural Dashboard live at http://localhost:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)

