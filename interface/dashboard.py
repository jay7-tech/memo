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
        <title>MEMO // NEURAL INTERFACE v2.0</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #05070a;
                --panel: rgba(10, 15, 25, 0.6);
                --accent: #00f2ff;
                --accent-glow: rgba(0, 242, 255, 0.4);
                --secondary: #ff00ff;
                --text: #e0e6ed;
                --text-dim: #6b7c93;
                --border: rgba(0, 242, 255, 0.15);
                --glass-border: rgba(255, 255, 255, 0.05);
            }

            * { box-sizing: border-box; cursor: crosshair; }
            ::-webkit-scrollbar { width: 4px; }
            ::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 10px; }

            body { 
                font-family: 'Outfit', sans-serif; 
                background: var(--bg);
                color: var(--text); 
                margin: 0; padding: 0; min-height: 100vh;
                overflow: hidden;
                background-image: 
                    radial-gradient(circle at 50% 50%, rgba(0, 242, 255, 0.03) 0%, transparent 70%),
                    repeating-linear-gradient(0deg, transparent, transparent 1px, rgba(255,255,255,0.01) 1px, rgba(255,255,255,0.01) 2px);
            }

            /* --- LAYOUT --- */
            .app-container {
                display: grid;
                grid-template-areas: 
                    "header header"
                    "vision telemetry"
                    "terminal telemetry";
                grid-template-columns: 1fr 340px;
                grid-template-rows: 70px 1fr 300px;
                height: 100vh;
                gap: 20px;
                padding: 20px;
                max-width: 1800px;
                margin: 0 auto;
            }

            .header {
                grid-area: header;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 20px;
                background: rgba(10, 15, 25, 0.8);
                border: 1px solid var(--border);
                border-radius: 12px;
                backdrop-filter: blur(10px);
            }

            .vision { 
                grid-area: vision;
                position: relative;
                border: 1px solid var(--border);
                border-radius: 16px;
                overflow: hidden;
                background: #000;
            }

            .terminal { 
                grid-area: terminal;
                display: flex;
                flex-direction: column;
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: 16px;
                padding: 15px;
                backdrop-filter: blur(20px);
            }

            .telemetry { 
                grid-area: telemetry;
                display: flex;
                flex-direction: column;
                gap: 20px;
            }

            /* --- COMPONENTS --- */
            .glass-card {
                background: var(--panel);
                border: 1px solid var(--glass-border);
                border-radius: 16px;
                padding: 20px;
                backdrop-filter: blur(20px);
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }

            .logo {
                font-size: 1.2rem;
                font-weight: 600;
                letter-spacing: 5px;
                color: #fff;
                display: flex;
                align-items: center;
                gap: 15px;
            }
            .logo span { color: var(--accent); opacity: 0.7; font-size: 0.8rem; }

            /* Circular Telemetry */
            .telemetry-circle-container {
                display: flex;
                justify-content: space-around;
                margin-top: 10px;
            }

            .hud-ring {
                position: relative;
                width: 100px; height: 100px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .hud-ring svg {
                position: absolute;
                width: 100%; height: 100%;
                transform: rotate(-90deg);
            }

            .hud-ring circle {
                fill: none;
                stroke-width: 4;
                stroke-linecap: round;
            }

            .hud-ring .bg { stroke: rgba(255,255,255,0.05); }
            .hud-ring .progress { 
                stroke: var(--accent); 
                stroke-dasharray: 283; 
                stroke-dashoffset: 283;
                transition: stroke-dashoffset 0.5s ease;
                filter: drop-shadow(0 0 5px var(--accent));
            }

            .hud-value {
                font-family: 'JetBrains Mono';
                font-size: 1.1rem;
                font-weight: 700;
                color: #fff;
            }
            .hud-label {
                position: absolute;
                bottom: -20px;
                font-size: 0.6rem;
                color: var(--text-dim);
                text-transform: uppercase;
                letter-spacing: 1px;
            }

            /* Video Feed HUD */
            .feed-img { width: 100%; height: 100%; object-fit: contain; opacity: 0.9; }
            .vision-overlay {
                position: absolute;
                inset: 0;
                pointer-events: none;
                background: radial-gradient(circle at 50% 50%, transparent 60%, rgba(0,0,0,0.4) 100%);
            }
            .reticle {
                position: absolute;
                top: 50%; left: 50%;
                transform: translate(-50%, -50%);
                width: 200px; height: 200px;
                border: 1px solid rgba(0, 242, 255, 0.1);
                border-radius: 50%;
            }
            .reticle::before, .reticle::after {
                content: '';
                position: absolute;
                top: 50%; left: 50%;
                background: var(--accent);
            }
            .reticle::before { width: 20px; height: 1px; transform: translate(-50%, -50%); }
            .reticle::after { width: 1px; height: 20px; transform: translate(-50%, -50%); }

            /* Terminal Area */
            #terminal {
                flex: 1;
                overflow-y: auto;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                padding-right: 10px;
            }
            .log-item {
                margin-bottom: 10px;
                padding-left: 15px;
                border-left: 2px solid transparent;
                animation: slideIn 0.3s ease-out;
            }
            .log-item.ai { border-left-color: var(--accent); background: rgba(0, 242, 255, 0.03); }
            .log-item.user { border-left-color: var(--secondary); }
            
            .l-time { color: var(--text-dim); opacity: 0.5; font-size: 0.7rem; margin-right: 8px; }
            .l-tag { font-weight: 700; font-size: 0.75rem; min-width: 60px; display: inline-block; }
            .l-msg { color: #fff; line-height: 1.4; }

            @keyframes slideIn { from { opacity: 0; transform: translateX(-10px); } to { opacity: 1; transform: translateX(0); } }

            .input-box {
                margin-top: 15px;
                display: flex;
                gap: 10px;
            }
            .n-input {
                flex: 1;
                background: rgba(255,255,255,0.03);
                border: 1px solid var(--glass-border);
                border-radius: 8px;
                padding: 12px 15px;
                color: #fff;
                font-family: inherit;
                outline: none;
                transition: 0.3s;
            }
            .n-input:focus { border-color: var(--accent); background: rgba(0, 242, 255, 0.05); }
            .n-btn {
                background: var(--accent);
                color: #000;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-weight: 700;
                cursor: pointer;
            }

            /* Modules */
            .module-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
            }
            .mod-btn {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid var(--glass-border);
                border-radius: 12px;
                padding: 15px;
                color: var(--text-dim);
                font-family: 'JetBrains Mono';
                font-size: 0.7rem;
                text-align: left;
                transition: 0.3s;
                position: relative;
                overflow: hidden;
            }
            .mod-btn:hover {
                background: rgba(0, 242, 255, 0.05);
                border-color: var(--accent);
                color: #fff;
            }
            .mod-btn span {
                display: block;
                font-size: 0.9rem;
                font-weight: 700;
                color: #fff;
                margin-top: 5px;
            }

            .pulsar {
                width: 4px; height: 4px;
                background: var(--accent);
                border-radius: 50%;
                position: absolute;
                top: 15px; right: 15px;
                box-shadow: 0 0 10px var(--accent);
                animation: pulse 1.5s infinite;
            }
            @keyframes pulse { 0% { transform: scale(1); opacity: 1; } 100% { transform: scale(4); opacity: 0; } }

            h5 { margin: 0 0 15px 0; font-size: 0.75rem; letter-spacing: 2px; color: var(--text-dim); text-transform: uppercase; }
        </style>
    </head>
    <body onload="init()">
        <div class="app-container">
            <!-- HEADER -->
            <header class="header">
                <div class="logo">
                    <div style="width: 12px; height: 12px; border: 2px solid var(--accent); border-radius: 50%; box-shadow: 0 0 10px var(--accent);"></div>
                    MEMO <span>// NEURAL INTERFACE v2.0 // PI_MODE_ACTIVE</span>
                </div>
                <div style="display: flex; gap: 40px; font-family: 'JetBrains Mono'; font-size: 0.75rem;">
                    <div style="color: var(--text-dim)">UPLINK: <span style="color: var(--accent)">STABLE</span></div>
                    <div style="color: var(--text-dim)">SYSTEM_LATENCY: <span id="ping" style="color: var(--accent)">--</span>MS</div>
                    <div id="clock" style="color: #fff;">00:00:00</div>
                </div>
            </header>

            <!-- VISION -->
            <main class="vision">
                <img src="/video_feed" class="feed-img" alt="Neural Stream">
                <div class="vision-overlay">
                    <div class="reticle"></div>
                    <!-- Corners -->
                    <div style="position: absolute; top: 20px; left: 20px; border-top: 2px solid var(--accent); border-left: 2px solid var(--accent); width: 30px; height: 30px;"></div>
                    <div style="position: absolute; top: 20px; right: 20px; border-top: 2px solid var(--accent); border-right: 2px solid var(--accent); width: 30px; height: 30px;"></div>
                    <div style="position: absolute; bottom: 20px; left: 20px; border-bottom: 2px solid var(--accent); border-left: 2px solid var(--accent); width: 30px; height: 30px;"></div>
                    <div style="position: absolute; bottom: 20px; right: 20px; border-bottom: 2px solid var(--accent); border-right: 2px solid var(--accent); width: 30px; height: 30px;"></div>
                    
                    <div style="position: absolute; top: 60px; right: 60px; font-family: 'JetBrains Mono'; font-size: 0.65rem; line-height: 1.5; color: var(--accent); text-align: right; opacity: 0.6;">
                        SCAN_FREQ: 2.4GHZ <br>
                        BUFFER_STATE: 100% <br>
                        [ NEURAL_UPLINK ]
                    </div>
                </div>
            </main>

            <!-- TERMINAL -->
            <section class="terminal">
                <h5>Neural Command Link</h5>
                <div id="terminal"></div>
                <form class="input-box" id="cmd-form">
                    <input type="text" id="cmd-input" class="n-input" placeholder="Neural transmit..." autocomplete="off">
                    <button type="submit" class="n-btn">SEND</button>
                </form>
            </section>

            <!-- TELEMETRY -->
            <aside class="telemetry">
                <div class="glass-card">
                    <h5>Telemetry HUD</h5>
                    <div class="telemetry-circle-container">
                        <div class="hud-ring">
                            <svg viewBox="0 0 100 100">
                                <circle class="bg" cx="50" cy="50" r="45"></circle>
                                <circle id="cpu-ring" class="progress" cx="50" cy="50" r="45"></circle>
                            </svg>
                            <div class="hud-value" id="cpu-val">0</div>
                            <div class="hud-label">CPU</div>
                        </div>
                        <div class="hud-ring">
                            <svg viewBox="0 0 100 100">
                                <circle class="bg" cx="50" cy="50" r="45"></circle>
                                <circle id="fps-ring" class="progress" cx="50" cy="50" r="45" style="stroke: var(--secondary); filter: drop-shadow(0 0 5px var(--secondary));"></circle>
                            </svg>
                            <div class="hud-value" id="fps-val">0</div>
                            <div class="hud-label">FPS</div>
                        </div>
                    </div>
                </div>

                <div class="glass-card" style="flex: 1;">
                    <h5>Cognitive Module</h5>
                    <div class="module-grid">
                        <div class="mod-btn">
                            STATUS
                            <span id="cog-status">IDLE</span>
                            <div class="pulsar"></div>
                        </div>
                        <div class="mod-btn">
                            IDENTITY
                            <span id="cog-id">--</span>
                        </div>
                        <div class="mod-btn">
                            FOCUS MODE
                            <span id="cog-focus">OFF</span>
                        </div>
                        <div class="mod-btn">
                            SENSOR_LINK
                            <span>STABLE</span>
                        </div>
                    </div>
                    
                    <h5 style="margin-top: 25px;">Proximal Subjects</h5>
                    <div id="subjects" style="display: flex; flex-wrap: wrap; gap: 8px;">
                        <div style="color: var(--text-dim); font-size: 0.7rem;">Scanning...</div>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <button onclick="sendCmd('f')" class="mod-btn" style="text-align: center;">FORCE_FOCUS</button>
                    <button onclick="sendCmd('v')" class="mod-btn" style="text-align: center;">MUTE_VOICE</button>
                </div>
            </aside>
        </div>

        <script>
            const socket = io();
            const terminal = document.getElementById('terminal');
            
            function init() {
                setInterval(() => {
                    const now = new Date();
                    document.getElementById('clock').innerText = now.toLocaleTimeString('en-GB');
                }, 1000);
            }

            let lastPing = Date.now();
            socket.on('stats_update', (data) => {
                // Update Rings
                const cpuRing = document.getElementById('cpu-ring');
                const fpsRing = document.getElementById('fps-ring');
                
                // Formula: 283 - (283 * percentage / 100)
                cpuRing.style.strokeDashoffset = 283 - (283 * data.cpu / 100);
                fpsRing.style.strokeDashoffset = 283 - (283 * data.fps / 30 * 100 / 100); // Scaled for 30fps

                document.getElementById('cpu-val').innerText = data.cpu;
                document.getElementById('fps-val').innerText = Math.round(data.fps);
                document.getElementById('ping').innerText = Date.now() - lastPing;
                lastPing = Date.now();

                // Cognitive
                document.getElementById('cog-id').innerText = data.identity || (data.human_present ? "UNIDENTIFIED" : "NO_SIGNAL");
                document.getElementById('cog-status').innerText = data.human_present ? "SUBJECT_LOCKED" : "SCANNING...";
                document.getElementById('cog-focus').innerText = data.focus_mode ? "REINFORCED" : "DEACTIVATED";
                document.getElementById('cog-focus').style.color = data.focus_mode ? "var(--secondary)" : "var(--text-dim)";

                // Subjects
                const subContainer = document.getElementById('subjects');
                if(data.objects && data.objects.length) {
                    subContainer.innerHTML = data.objects.map(o => `
                        <div style="padding: 5px 10px; background: rgba(0, 242, 255, 0.1); border: 1px solid var(--accent); color: var(--accent); border-radius: 4px; font-size: 0.65rem; font-family: 'JetBrains Mono';">
                            ${o.toUpperCase()}
                        </div>
                    `).join('');
                } else if (!data.human_present) {
                    subContainer.innerHTML = '<div style="color: var(--text-dim); font-size: 0.7rem;">NO_ENTITIES_LOCALIZED</div>';
                }
            });

            socket.on('new_log', (entry) => {
                const div = document.createElement('div');
                div.className = `log-item ${entry.type}`;
                div.innerHTML = `
                    <span class="l-time">${entry.time}</span>
                    <span class="l-tag" style="color: ${entry.type === 'ai' ? 'var(--accent)' : 'var(--secondary)'}">[${entry.type.toUpperCase()}]</span>
                    <span class="l-msg">${entry.msg}</span>
                `;
                terminal.appendChild(div);
                terminal.scrollTop = terminal.scrollHeight;
                if(terminal.childNodes.length > 30) terminal.removeChild(terminal.firstChild);
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

