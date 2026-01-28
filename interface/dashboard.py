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
            # Encode with 50% quality to significantly reduce network load on Pi
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            if not flag:
                continue
        
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encodedImage) + b'\r\n')
        time.sleep(0.05) # Target ~20 FPS to save CPU on Pi

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
                --card-bg: rgba(16, 18, 23, 0.9);
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
            }

            .header {
                padding: 15px 40px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-bottom: 1px solid var(--border);
                backdrop-filter: blur(10px);
                position: sticky; top: 0; z-index: 100;
                background: rgba(5, 6, 8, 0.8);
            }

            .logo {
                font-size: 1.2rem;
                font-weight: 600;
                letter-spacing: 2px;
                color: var(--accent);
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .logo-dot {
                width: 10px;
                height: 10px;
                background: var(--accent);
                border-radius: 50%;
                box-shadow: 0 0 10px var(--accent);
                animation: pulse 2s infinite;
            }

            @keyframes pulse {
                0% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.5; transform: scale(1.2); }
                100% { opacity: 1; transform: scale(1); }
            }

            .main-grid {
                display: grid;
                grid-template-columns: 1fr 350px;
                gap: 20px;
                padding: 20px;
                max-width: 1400px;
                margin: 0 auto;
            }

            @media (max-width: 1000px) {
                .main-grid { grid-template-columns: 1fr; }
            }

            .glass-card {
                background: var(--card-bg);
                backdrop-filter: blur(12px);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 15px;
            }

            .video-container {
                position: relative;
                border-radius: 10px;
                overflow: hidden;
                border: 1px solid var(--border);
                background: #000;
                aspect-ratio: 16/9;
                box-shadow: 0 0 20px rgba(0,0,0,0.5);
            }

            .video-container img {
                width: 100%; height: 100%; object-fit: contain;
            }

            .terminal {
                background: #000;
                border: 1px solid rgba(0,242,255,0.1);
                border-radius: 8px;
                height: 250px;
                overflow-y: auto;
                padding: 12px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.8rem;
                line-height: 1.4;
            }

            .log-entry { margin-bottom: 5px; }
            .log-time { color: #444; margin-right: 8px; }
            .log-type-ai { color: #bb86fc; font-weight: 600; }
            .log-type-info { color: #03dac6; }
            .log-type-alert { color: #ff0266; animation: blink 1s infinite; }

            @keyframes blink { 50% { opacity: 0.5; } }

            .input-box {
                margin-top: 10px;
                display: flex;
                gap: 8px;
            }

            input {
                flex: 1;
                background: rgba(255,255,255,0.05);
                border: 1px solid var(--border);
                border-radius: 6px;
                padding: 10px 15px;
                color: #fff;
                outline: none;
                font-size: 0.9rem;
            }

            input:focus { border-color: var(--accent); }

            button {
                background: var(--accent);
                color: #000;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                cursor: pointer;
            }

            .stat-row {
                display: flex; justify-content: space-between;
                padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.03);
            }
            .stat-label { color: #666; font-size: 0.85rem; }
            .stat-value { font-family: 'JetBrains Mono'; font-size: 0.9rem; }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">
                <div class="logo-dot"></div>
                MEMO <span style="opacity: 0.5; font-weight: 300;">V1.2</span>
            </div>
            <div id="telemetry" style="display: flex; gap: 20px; font-size: 0.8rem; color: #444;">
                <span>FPS: <span id="fps-val" style="color: #888;">0.0</span></span>
                <span>CPU: <span id="cpu-val" style="color: #888;">0%</span></span>
            </div>
        </div>

        <div class="main-grid">
            <div style="display: flex; flex-direction: column; gap: 20px;">
                <div class="video-container">
                    <img src="/video_feed">
                </div>
                
                <div class="glass-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <h4 style="margin: 0; text-transform: uppercase; letter-spacing: 1px;">Neural Command Link</h4>
                        <span style="font-size: 0.7rem; color: #444;">TYPE HERE TO CONTROL ROBOT</span>
                    </div>
                    <div class="terminal" id="terminal"></div>
                    <form class="input-box" id="cmd-form">
                        <input type="text" id="cmd-input" placeholder="Type a command (e.g. 'where is bottle')..." autocomplete="off">
                        <button type="submit">SEND</button>
                    </form>
                </div>
            </div>

            <div style="display: flex; flex-direction: column; gap: 20px;">
                <div class="glass-card">
                    <h4 style="margin-top: 0; margin-bottom: 15px;">Telemetry</h4>
                    <div class="stat-row">
                        <span class="stat-label">Identity</span>
                        <span class="stat-value" id="identity" style="color: var(--accent);">IDLE</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Pose</span>
                        <span class="stat-value" id="pose-st">Scanning...</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Focus Shield</span>
                        <span class="stat-value" id="focus-st">OFF</span>
                    </div>
                </div>

                <div class="glass-card">
                    <h4 style="margin-top: 0; margin-bottom: 10px;">Entities</h4>
                    <div id="objects-list" style="font-size: 0.85rem; color: #888;">Scanning...</div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <button onclick="sendCmd('focus on')" style="background: rgba(255, 255, 255, 0.05); color: #fff; border: 1px solid var(--border);">FOCUS ON</button>
                    <button onclick="sendCmd('focus off')" style="background: rgba(255, 255, 255, 0.05); color: #fff; border: 1px solid var(--border);">FOCUS OFF</button>
                </div>
            </div>
        </div>

        <script>
            const socket = io();
            const terminal = document.getElementById('terminal');

            socket.on('stats_update', function(data) {
                document.getElementById('fps-val').innerText = data.fps;
                document.getElementById('cpu-val').innerText = data.cpu + '%';
                
                document.getElementById('identity').innerText = data.identity || (data.human_present ? "UNIDENTIFIED" : "IDLE");
                document.getElementById('focus-st').innerText = data.focus_mode ? "ACTIVE" : "OFF";
                document.getElementById('focus-st').style.color = data.focus_mode ? "#ff3366" : "#666";
                
                if(data.objects && data.objects.length) {
                    document.getElementById('objects-list').innerText = data.objects.join(", ");
                } else {
                    document.getElementById('objects-list').innerText = "None detected";
                }
            });

            socket.on('new_log', function(entry) {
                const div = document.createElement('div');
                div.className = 'log-entry';
                div.innerHTML = `<span class="log-time">[${entry.time}]</span><span class="log-type-${entry.type}">${entry.type.toUpperCase()}:</span> <span>${entry.msg}</span>`;
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
        scene_state_ref.pending_commands.put(cmd)
        add_log(f"WEB_CMD: {cmd}", "info")
        return jsonify({"status": "queued"})
    return jsonify({"status": "error"})

def start_server():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    def stats_broadcaster():
        while True:
            if scene_state_ref:
                from core import get_perf_monitor
                perf = get_perf_monitor()
                stats = perf.get_stats()
                socketio.emit('stats_update', {
                    'human_present': scene_state_ref.human['present'],
                    'identity': scene_state_ref.human['identity'],
                    'focus_mode': scene_state_ref.focus_mode,
                    'objects': list(scene_state_ref.objects.keys()),
                    'cpu': stats['cpu'],
                    'fps': stats['fps']
                })
            time.sleep(0.5)
            
    threading.Thread(target=stats_broadcaster, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)

