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
                --shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
            }

            * { box-sizing: border-box; }
            ::-webkit-scrollbar { width: 5px; }
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

            /* --- LUMINA V4.0 LAYOUT --- */
            .header {
                height: 70px;
                background: var(--panel);
                border-bottom: 1px solid var(--border);
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 40px;
                z-index: 100;
            }

            .main-stage {
                flex: 1;
                display: grid;
                grid-template-columns: 1fr 360px;
                gap: 24px;
                padding: 24px;
                min-height: 0;
                max-width: 1800px;
                margin: 0 auto;
                width: 100%;
            }

            .vision-container {
                display: flex;
                flex-direction: column;
                gap: 20px;
                min-height: 0;
            }

            /* --- COMPONENTS --- */
            .logo {
                display: flex;
                align-items: center;
                gap: 12px;
                font-weight: 700;
                font-size: 1.25rem;
                letter-spacing: -0.5px;
            }
            .logo .dot { width: 12px; height: 12px; background: var(--accent); border-radius: 3px; }

            .card {
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: 20px;
                box-shadow: var(--shadow);
                overflow: hidden;
            }

            .vision-box {
                flex: 1;
                background: #000;
                border-radius: 24px;
                position: relative;
                overflow: hidden;
                border: 8px solid var(--panel);
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            }

            .feed-img { width: 100%; height: 100%; object-fit: contain; }

            /* Terminal Area */
            .terminal-box {
                height: 250px;
                display: flex;
                flex-direction: column;
                padding: 20px;
            }

            #terminal {
                flex: 1;
                overflow-y: auto;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                padding-right: 15px;
            }

            .log-item {
                margin-bottom: 12px;
                padding: 8px 12px;
                border-radius: 8px;
                background: #f1f5f9;
                border-left: 4px solid #cbd5e1;
            }
            .log-item.ai { border-left-color: var(--accent); background: var(--accent-dim); color: #065f46; }

            .input-group {
                margin-top: 15px;
                display: flex;
                gap: 10px;
            }
            .input-group input {
                flex: 1;
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 12px 20px;
                font-family: inherit;
                outline: none;
                transition: 0.2s;
            }
            .input-group input:focus { border-color: var(--accent); ring: 2px solid var(--accent-dim); }
            
            .btn {
                background: var(--text-main);
                color: #fff;
                border: none;
                border-radius: 12px;
                padding: 0 24px;
                font-weight: 600;
                cursor: pointer;
                transition: 0.2s;
            }
            .btn:hover { transform: translateY(-1px); opacity: 0.9; }

            /* Right Sidebar */
            .sidebar {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }

            .stat-block {
                padding: 24px;
            }

            .stat-header {
                font-size: 0.75rem;
                font-weight: 700;
                color: var(--text-side);
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .hud-rings {
                display: flex;
                justify-content: space-around;
                margin-bottom: 24px;
            }

            .ring {
                position: relative;
                width: 100px; height: 100px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .ring svg { transform: rotate(-90deg); width: 100%; height: 100%; }
            .ring circle { fill: none; stroke-width: 6; }
            .ring .bg { stroke: #f1f5f9; }
            .ring .bar { 
                stroke: var(--accent); 
                stroke-dasharray: 251; 
                stroke-dashoffset: 251;
                transition: 0.8s cubic-bezier(0.4, 0, 0.2, 1);
                stroke-linecap: round;
            }
            .ring .val { position: absolute; font-weight: 700; font-size: 1.25rem; }

            .cog-item {
                display: flex;
                flex-direction: column;
                gap: 4px;
                padding: 12px 0;
                border-bottom: 1px solid var(--border);
            }
            .cog-item:last-child { border: none; }
            .cog-label { font-size: 0.7rem; color: var(--text-side); text-transform: uppercase; }
            .cog-value { font-weight: 600; font-size: 0.9rem; }

            .control-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                padding: 24px;
            }
            .c-btn {
                background: #f1f5f9;
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 12px;
                font-size: 0.75rem;
                font-weight: 600;
                color: var(--text-main);
                cursor: pointer;
                text-align: center;
                transition: 0.2s;
            }
            .c-btn:hover { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

            .status-badge {
                padding: 4px 10px;
                border-radius: 20px;
                font-size: 0.65rem;
                font-weight: 700;
                background: #f1f5f9;
                color: var(--text-side);
            }
            .status-badge.active { background: #dcfce7; color: #166534; }
        </style>
    </head>
    <body onload="init()">
        <header class="header">
            <div class="logo">
                <div class="dot"></div>
                MEMO <span style="font-weight: 400; color: var(--text-side); font-size: 1rem; margin-left: 8px;"> // Dashboard v4.0</span>
            </div>
            <div style="display: flex; gap: 32px; font-size: 0.85rem; font-weight: 600; color: var(--text-side);">
                <div>LATENCY: <span id="ping" style="color: var(--text-main)">--</span>ms</div>
                <div id="clock" style="color: var(--text-main)">00:00:00</div>
                <div class="status-badge active">SYSTEM READY</div>
            </div>
        </header>

        <main class="main-stage">
            <!-- Left: Vision & Terminal -->
            <div class="vision-container">
                <div class="vision-box">
                    <img src="/video_feed" class="feed-img" alt="Neural Feed">
                    <!-- Clean minimal overlays -->
                    <div style="position: absolute; top: 20px; left: 20px; background: rgba(0,0,0,0.5); padding: 8px 16px; border-radius: 8px; color: #fff; font-size: 0.75rem; font-family: 'JetBrains Mono'; backdrop-filter: blur(4px);">
                        LIVE_FEED // CACHE_READY
                    </div>
                </div>

                <div class="card terminal-box">
                    <div class="stat-header">NEURAL COMMAND LOGS <span class="status-badge" style="font-size: 0.6rem">UPLINK_STABLE</span></div>
                    <div id="terminal"></div>
                    <form class="input-group" id="cmd-form">
                        <input type="text" id="cmd-input" placeholder="Type a command for MEMO..." autocomplete="off">
                        <button type="submit" class="btn" id="send-btn">TRANSMIT</button>
                    </form>
                </div>
            </div>

            <!-- Right: Stats & Controls -->
            <div class="sidebar">
                <div class="card stat-block">
                    <div class="stat-header">SYSTEM PERFORMANCE</div>
                    <div class="hud-rings">
                        <div class="ring">
                            <svg viewBox="0 0 100 100">
                                <circle class="bg" cx="50" cy="50" r="40"></circle>
                                <circle id="cpu-ring" class="bar" cx="50" cy="50" r="40"></circle>
                            </svg>
                            <div class="val" id="cpu-val">0</div>
                            <div style="position: absolute; bottom: -15px; font-size: 0.65rem; color: var(--text-side); font-weight: 600;">CPU %</div>
                        </div>
                        <div class="ring">
                            <svg viewBox="0 0 100 100">
                                <circle class="bg" cx="50" cy="50" r="40"></circle>
                                <circle id="fps-ring" class="bar" cx="50" cy="50" r="40" style="stroke: #6366f1;"></circle>
                            </svg>
                            <div class="val" id="fps-val">0</div>
                            <div style="position: absolute; bottom: -15px; font-size: 0.65rem; color: var(--text-side); font-weight: 600;">FPS</div>
                        </div>
                    </div>
                </div>

                <div class="card stat-block" style="flex: 1;">
                    <div class="stat-header">COGNITIVE PROFILE</div>
                    <div class="cog-item">
                        <span class="cog-label">IDENTIFIED SUBJECT</span>
                        <span class="cog-value" id="cog-id">SEARCHING...</span>
                    </div>
                    <div class="cog-item">
                        <span class="cog-label">FOCUS REINFORCEMENT</span>
                        <span class="cog-value" id="cog-focus">DEACTIVATED</span>
                    </div>
                    <div class="cog-item">
                        <span class="cog-label">CORE BACKEND</span>
                        <span class="cog-value">OLLAMA / TINYLLAMA</span>
                    </div>
                </div>

                <div class="card control-grid">
                    <button onclick="sendCmd('f')" class="c-btn">FORCE FOCUS</button>
                    <button onclick="sendCmd('v')" class="c-btn">MUTE VOICE</button>
                    <button onclick="sendCmd('status')" class="c-btn" style="grid-column: span 2;">RUN DIAGNOSTICS</button>
                </div>
            </div>
        </main>

        <script>
            const socket = io();
            const terminal = document.getElementById('terminal');
            
            function init() {
                setInterval(() => {
                    const now = new Date();
                    document.getElementById('clock').innerText = now.toLocaleTimeString('en-US', { hour12: false });
                }, 1000);
            }

            let lastPing = Date.now();
            socket.on('stats_update', (data) => {
                const cpuRing = document.getElementById('cpu-ring');
                const fpsRing = document.getElementById('fps-ring');
                
                // Circumference = 2 * PI * R (R=40) ≈ 251
                cpuRing.style.strokeDashoffset = 251 - (251 * data.cpu / 100);
                fpsRing.style.strokeDashoffset = 251 - (251 * data.fps / 30 * 100 / 100);

                document.getElementById('cpu-val').innerText = data.cpu;
                document.getElementById('fps-val').innerText = Math.round(data.fps);
                document.getElementById('ping').innerText = Date.now() - lastPing;
                lastPing = Date.now();

                const userId = data.identity || (data.human_present ? "UNIDENTIFIED HUMAN" : "NO SUBJECT");
                document.getElementById('cog-id').innerText = userId.toUpperCase();
                
                const focus = document.getElementById('cog-focus');
                focus.innerText = data.focus_mode ? "REINFORCED" : "DEACTIVATED";
                focus.style.color = data.focus_mode ? "var(--accent)" : "var(--text-side)";
            });

            socket.on('new_log', (entry) => {
                const div = document.createElement('div');
                div.className = `log-item ${entry.type}`;
                div.innerHTML = `
                    <span style="font-size: 0.65rem; color: var(--text-side); margin-right: 8px;">${entry.time}</span>
                    <strong style="font-size: 0.7rem; margin-right: 8px;">[${entry.type.toUpperCase()}]</strong>
                    <span>${entry.msg}</span>
                `;
                terminal.appendChild(div);
                terminal.scrollTop = terminal.scrollHeight;
                if(terminal.childNodes.length > 50) terminal.removeChild(terminal.firstChild);
            });

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

