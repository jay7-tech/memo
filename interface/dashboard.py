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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>MEMO // NEURAL INTERFACE v4.0</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #f8fafc;
                --panel: #ffffff;
                --accent: #10b981;
                --accent-dim: rgba(16, 185, 129, 0.1);
                --text-main: #1e293b;
                --text-side: #64748b;
                --border: #e2e8f0;
                --danger: #ef4444;
                --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            }

            * { box-sizing: border-box; }
            ::-webkit-scrollbar { width: 6px; }
            ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }

            body { 
                font-family: 'Outfit', sans-serif; 
                background: var(--bg);
                color: var(--text-main); 
                margin: 0; padding: 0; 
                height: 100vh;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }

            .header {
                height: 64px;
                background: var(--panel);
                border-bottom: 1px solid var(--border);
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 32px;
                box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                z-index: 10;
            }

            .main-stage {
                flex: 1;
                display: grid;
                grid-template-columns: 1fr 380px;
                gap: 24px;
                padding: 24px;
                min-height: 0;
                max-width: 1600px;
                margin: 0 auto;
                width: 100%;
            }

            .vision-container {
                display: flex;
                flex-direction: column;
                gap: 20px;
                min-height: 0;
            }

            .logo { font-weight: 700; font-size: 1.25rem; letter-spacing: -0.5px; display: flex; align-items: center; gap: 10px; color: var(--text-main); }
            .dot { width: 10px; height: 10px; background: var(--accent); border-radius: 3px; }

            .card {
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: 20px;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                box-shadow: var(--shadow);
            }

            .vision-box {
                flex: 1;
                background: #000;
                border-radius: 20px;
                position: relative;
                overflow: hidden;
                border: 4px solid var(--panel);
                box-shadow: var(--shadow);
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .feed-img { width: 100%; height: 100%; object-fit: contain; }
            
            .overlay-badge {
                position: absolute; top: 15px; left: 15px;
                background: rgba(0,0,0,0.6);
                backdrop-filter: blur(4px);
                padding: 6px 12px;
                border-radius: 6px;
                font-family: 'JetBrains Mono';
                font-size: 0.7rem;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .status-dot { width: 8px; height: 8px; border-radius: 50%; background: #64748b; }
            .status-dot.active { background: var(--accent); box-shadow: 0 0 8px var(--accent); }

            .terminal-box { height: 220px; padding: 16px; }
            #terminal {
                flex: 1;
                overflow-y: auto;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.8rem;
                color: var(--text-main);
                margin-bottom: 10px;
            }
            .log-item { margin-bottom: 6px; line-height: 1.4; word-break: break-all; }
            .log-item span { opacity: 0.6; margin-right: 8px; font-size: 0.7rem; }
            
            .sidebar { display: flex; flex-direction: column; gap: 16px; }
            
            .stat-block { padding: 16px; }
            .stat-header {
                font-size: 0.7rem;
                font-weight: 700;
                color: var(--text-side);
                letter-spacing: 1px;
                margin-bottom: 12px;
                text-transform: uppercase;
            }

            /* Controls */
            .control-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
            }
            .c-btn {
                background: var(--bg);
                border: 1px solid var(--border);
                color: var(--text-main);
                padding: 12px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.75rem;
                cursor: pointer;
                transition: 0.2s;
            }
            .c-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }
            .c-btn.danger:hover { border-color: var(--danger); color: var(--danger); background: rgba(239, 68, 68, 0.1); }
            .c-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }

            canvas { max-height: 120px; width: 100%; }

            .input-group { display: flex; gap: 8px; }
            input {
                flex: 1;
                background: var(--bg);
                border: 1px solid var(--border);
                color: var(--text-main);
                padding: 8px 12px;
                border-radius: 8px;
                font-family: inherit;
                outline: none;
            }
            input:focus { border-color: var(--accent); }
            .send-btn { background: var(--accent); border: none; color: white; border-radius: 8px; padding: 0 16px; cursor: pointer; font-weight: 600; }
        </style>
    </head>
    <body onload="init()">
        <header class="header">
            <div class="logo">
                <div class="dot"></div>
                MEMO <span style="opacity: 0.5; font-weight: 400; font-size: 0.9rem;"> // DASHBOARD 2.0</span>
            </div>
            <div style="font-size: 0.8rem; font-family: 'JetBrains Mono'; color: var(--text-side);">
                LATENCY: <span id="ping" style="color: var(--accent)">--</span>ms
            </div>
        </header>

        <main class="main-stage">
            <div class="vision-container">
                <div class="vision-box">
                    <img src="/video_feed" class="feed-img">
                    <div class="overlay-badge">
                        <div id="vision-dot" class="status-dot"></div>
                        <span id="vision-text">VISION SLEEP</span>
                    </div>
                </div>

                <div class="card terminal-box">
                    <div class="stat-header">NEURAL LOGS</div>
                    <div id="terminal"></div>
                    <form class="input-group" id="cmd-form">
                        <input type="text" id="cmd-input" placeholder="Enter command..." autocomplete="off">
                        <button type="submit" class="send-btn">PCT</button>
                    </form>
                </div>
            </div>

            <div class="sidebar">
                <!-- Status Card -->
                <div class="card stat-block">
                    <div class="stat-header">SYSTEM STATUS</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 0.8rem;">
                        <div>
                            <div style="color: var(--text-side); font-size: 0.7rem;">IDENTITY</div>
                            <div id="status-id" style="font-weight: 600; font-size: 1rem;">--</div>
                        </div>
                        <div>
                            <div style="color: var(--text-side); font-size: 0.7rem;">FOCUS MODE</div>
                            <div id="status-focus" style="font-weight: 600; font-size: 1rem;">OFF</div>
                        </div>
                    </div>
                </div>

                <!-- Controls -->
                <div class="card stat-block">
                    <div class="stat-header">COMMAND CENTER</div>
                    <div class="control-grid">
                        <button id="btn-wake" class="c-btn" onclick="sendCmd('scan')">VISION WAKE</button>
                        <button id="btn-stop-scan" class="c-btn danger" onclick="sendCmd('stop scan')">VISION SLEEP</button>
                        
                        <button id="btn-voice" class="c-btn" onclick="sendCmd('voice toggle')">VOICE INPUT</button>
                        <button id="btn-buzz" class="c-btn" style="background:#fce7f3; color:#ec4899; border-color:#fbcfe8;" onclick="sendCmd('buzz')">⚡ BUZZ NEWS</button>

                        <button id="btn-sleep" class="c-btn danger" onclick="sendCmd('sleep')">SYSTEM SLEEP 💤</button>
                        <button id="btn-logs" class="c-btn" onclick="sendCmd('logs on')">DEBUG LOGS</button>
                        
                        <button id="btn-focus-on" class="c-btn" onclick="sendCmd('focus on')">FOCUS ON</button>
                        <button id="btn-focus-off" class="c-btn" onclick="sendCmd('focus off')">FOCUS OFF</button>
                    </div>
                </div>

                <!-- ... (Perception Log) ... -->

                <!-- Graphs -->
                <div class="card stat-block" style="flex: 1; display:flex; flex-direction:column; min-height: 200px;">
                    <div class="stat-header">SYSTEM PERFORMANCE</div>
                    <div style="flex: 1; display: flex; justify-content: space-around; align-items: center;">
                        
                        <!-- CPU Circle -->
                        <div class="circle-container">
                            <div class="circle-box">
                                <svg class="progress-ring" width="100" height="100">
                                    <circle class="track" cx="50" cy="50" r="40"/>
                                    <circle id="cpu-ring" class="progress" cx="50" cy="50" r="40" stroke="#10b981"/>
                                </svg>
                                <div class="circle-text" id="cpu-val">--</div>
                            </div>
                            <div class="circle-label">CPU %</div>
                        </div>

                        <!-- FPS Circle -->
                        <div class="circle-container">
                            <div class="circle-box">
                                <svg class="progress-ring" width="100" height="100">
                                    <circle class="track" cx="50" cy="50" r="40"/>
                                    <circle id="fps-ring" class="progress" cx="50" cy="50" r="40" stroke="#6366f1"/>
                                </svg>
                                <div class="circle-text" id="fps-val">--</div>
                            </div>
                            <div class="circle-label">FPS</div>
                        </div>

                    </div>
                </div>
            </div>
        </main>

        <style>
            .circle-container { text-align: center; }
            .circle-box { position: relative; width: 100px; height: 100px; margin: 0 auto 8px auto; }
            .progress-ring { transform: rotate(-90deg); transform-origin: 50% 50%; }
            circle { fill: transparent; stroke-width: 8; stroke-linecap: round; }
            .track { stroke: #e2e8f0; }
            .progress { 
                stroke-dasharray: 251.2; /* 2 * PI * 40 */
                stroke-dashoffset: 251.2;
                transition: stroke-dashoffset 0.5s ease-in-out;
            }
            .circle-text {
                position: absolute; top: 0; left: 0; width: 100%; height: 100%;
                display: flex; align-items: center; justify-content: center;
                font-size: 1.5rem; font-weight: 700; color: var(--text-main);
            }
            .circle-label { font-size: 0.75rem; color: var(--text-side); font-weight: 600; }
        </style>

        <script>
            const socket = io();
            const terminal = document.getElementById('terminal');
            const perceptionLog = document.getElementById('perception-log');
            
            // Circle Config
            const radius = 40;
            const circumference = 2 * Math.PI * radius;
            
            function setProgress(id, value, max) {
                const ring = document.getElementById(id);
                const valEl = document.getElementById(id.replace('ring', 'val'));
                
                // Clamp value
                if (value > max) value = max;
                if (value < 0) value = 0;
                
                const brightness = value / max;
                const offset = circumference - (brightness * circumference);
                
                ring.style.strokeDashoffset = offset;
                valEl.innerText = Math.round(value);
            }

            // Init not needed for simple JS
            function init() {} 

            // Helper to toggle active class
            function toggleBtn(id, active) {
                const btn = document.getElementById(id);
                if (btn) {
                    if (active) btn.classList.add('active');
                    else btn.classList.remove('active');
                }
            }

            // ... (Circle Logic) ...

            let lastPing = Date.now();
            socket.on('stats_update', (data) => {
                // Update Ping
                document.getElementById('ping').innerText = Date.now() - lastPing;
                lastPing = Date.now();

                // Update Status text
                const vDot = document.getElementById('vision-dot');
                const vText = document.getElementById('vision-text');
                if (data.vision_active) {
                    vDot.classList.add('active');
                    vText.innerText = "VISION ACTIVE";
                    vText.style.color = "#10b981";
                } else {
                    vDot.classList.remove('active');
                    vText.innerText = "VISION SLEEP";
                    vText.style.color = "#94a3b8";
                }

                document.getElementById('status-id').innerText = (data.identity || "Scanning...").toUpperCase();
                
                const focusEl = document.getElementById('status-focus');
                focusEl.innerText = data.focus_mode ? "Active" : "Standby";
                focusEl.style.color = data.focus_mode ? "#10b981" : "#94a3b8";
                
                // Update Button States
                toggleBtn('btn-wake', data.vision_active);
                toggleBtn('btn-stop-scan', !data.vision_active);
                toggleBtn('btn-voice', data.voice_active);
                
                // System Sleep: If Vision OFF and Voice OFF? Or explicit state?
                // For simplicity, let's say if Vision is OFF, we might be sleeping.
                // But better: Check if both are off?
                const isSystemSleep = (!data.vision_active && !data.voice_active);
                const sleepBtn = document.getElementById('btn-sleep');
                if (isSystemSleep) {
                     sleepBtn.classList.add('active');
                     sleepBtn.innerText = "WAKE UP ☀️";
                     sleepBtn.onclick = () => sendCmd('wake');
                     sleepBtn.classList.remove('danger'); // Make it Green
                     sleepBtn.style.background = "#10b981";
                     sleepBtn.style.color = "white";
                } else {
                     sleepBtn.classList.remove('active');
                     sleepBtn.innerText = "SYSTEM SLEEP 💤";
                     sleepBtn.onclick = () => sendCmd('sleep');
                     sleepBtn.classList.add('danger');
                     sleepBtn.style.background = ""; // Reset
                     sleepBtn.style.color = "";
                }
                
                toggleBtn('btn-focus-on', data.focus_mode);
                toggleBtn('btn-focus-off', !data.focus_mode);
                
                // Logic for Logs Button (Clicking toggles it, but we need state)
                // Assuming data.verbose_logging is sent
                const logsBtn = document.getElementById('btn-logs');
                if (data.verbose_logging) {
                    logsBtn.classList.add('active');
                    logsBtn.innerText = "LOGS ACTIVE";
                    logsBtn.onclick = () => sendCmd('logs off');
                } else {
                    logsBtn.classList.remove('active');
                    logsBtn.innerText = "DEBUG LOGS";
                    logsBtn.onclick = () => sendCmd('logs on');
                }

                // Update Circles
                setProgress('cpu-ring', data.cpu, 100);
                setProgress('fps-ring', data.fps, 30); 
            });

            socket.on('new_log', (entry) => {
                const div = document.createElement('div');
                div.className = 'log-item';
                div.innerHTML = `<span>${entry.time}</span> ${entry.msg}`;
                terminal.appendChild(div);
                terminal.scrollTop = terminal.scrollHeight;
            });

            socket.on('perception_log', (entry) => {
                const div = document.createElement('div');
                div.style.marginBottom = "4px";
                div.innerHTML = `<span style="opacity:0.5; margin-right:6px;">${entry.time}</span> ${entry.msg}`;
                perceptionLog.appendChild(div);
                perceptionLog.scrollTop = perceptionLog.scrollHeight;
            });
            
            // ... sendCmd ...

            function sendCmd(text) {
                fetch('/api/command', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: text})
                });
            }

            document.getElementById('cmd-form').onsubmit = (e) => {
                e.preventDefault();
                const input = document.getElementById('cmd-input');
                if(input.value) { sendCmd(input.value); input.value = ''; }
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
                    'vision_active': getattr(scene_state_ref, 'vision_active', True),
                    'voice_active': getattr(scene_state_ref, 'voice_active', True), # UPDATED
                    'verbose_logging': getattr(scene_state_ref, 'verbose_logging', False),
                    'objects': list(scene_state_ref.objects.keys()),
                    'cpu': stats['cpu'],
                    'fps': stats['fps']
                })
            time.sleep(0.5)
            
    threading.Thread(target=stats_broadcaster, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)

