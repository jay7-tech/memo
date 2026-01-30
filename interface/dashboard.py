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
        <title>MEMO // NEURAL INTERFACE v3.0</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #08090d;
                --panel: rgba(15, 17, 30, 0.75);
                --accent: #ae63fb;
                --accent-glow: rgba(174, 99, 251, 0.4);
                --secondary: #4a90e2;
                --text: #f0f4f8;
                --text-dim: #94a3b8;
                --border: rgba(174, 99, 251, 0.2);
                --glass-border: rgba(255, 255, 255, 0.08);
                --super-glass: linear-gradient(135deg, rgba(174, 99, 251, 0.05) 0%, rgba(74, 144, 226, 0.05) 100%);
            }

            * { box-sizing: border-box; cursor: crosshair; }
            ::-webkit-scrollbar { width: 4px; }
            ::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 10px; }

            body { 
                font-family: 'Outfit', sans-serif; 
                background: var(--bg);
                color: var(--text); 
                margin: 0; padding: 0; 
                height: 100vh;
                overflow: hidden;
                background-image: 
                    radial-gradient(circle at 10% 10%, rgba(174, 99, 251, 0.07) 0%, transparent 40%),
                    radial-gradient(circle at 90% 90%, rgba(74, 144, 226, 0.07) 0%, transparent 40%),
                    repeating-linear-gradient(0deg, transparent, transparent 1px, rgba(255,255,255,0.01) 1px, rgba(255,255,255,0.01) 2px);
            }

            /* --- V3.0 SUPERNOVA LAYOUT --- */
            .app-wrapper {
                display: flex;
                flex-direction: column;
                height: 100vh;
                padding: 15px;
                gap: 15px;
                max-width: 1920px;
                margin: 0 auto;
            }

            .header {
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 25px;
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: 14px;
                backdrop-filter: blur(20px);
            }

            .main-content {
                flex: 1;
                display: grid;
                grid-template-rows: 1fr 280px;
                gap: 15px;
                min-height: 0;
            }

            /* --- VISION MAIN STAGE --- */
            .vision-stage {
                position: relative;
                background: #000;
                border: 1.5px solid var(--border);
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 0 40px rgba(0,0,0,0.8), inset 0 0 100px rgba(174, 99, 251, 0.05);
            }

            .feed-img {
                width: 100%; height: 100%; object-fit: contain;
                filter: contrast(1.1) brightness(1.05);
            }

            .hud-frame {
                position: absolute;
                inset: 0;
                pointer-events: none;
                z-index: 10;
            }

            .hud-label-top {
                position: absolute;
                top: 25px; left: 35px;
                font-family: 'JetBrains Mono';
                font-size: 0.75rem;
                color: var(--accent);
                letter-spacing: 2px;
                text-shadow: 0 0 10px var(--accent-glow);
            }

            /* --- BOTTOM CONTROL PANEL --- */
            .control-panel {
                display: grid;
                grid-template-columns: 1fr 400px;
                gap: 15px;
            }

            .terminal-glass {
                background: var(--panel);
                border: 1px solid var(--glass-border);
                border-radius: 18px;
                padding: 20px;
                backdrop-filter: blur(30px);
                position: relative;
                display: flex;
                flex-direction: column;
            }

            .telemetry-glass {
                background: var(--panel);
                border: 1px solid var(--glass-border);
                border-radius: 18px;
                padding: 20px;
                backdrop-filter: blur(30px);
                display: flex;
                flex-direction: column;
                gap: 15px;
            }

            /* --- COMPONENTS --- */
            .logo {
                font-size: 1.1rem;
                font-weight: 600;
                letter-spacing: 6px;
                color: #fff;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .logo b { color: var(--accent); }

            #terminal {
                flex: 1;
                overflow-y: auto;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.82rem;
                padding-right: 15px;
            }

            .log-row {
                margin-bottom: 12px;
                animation: fadeIn 0.4s ease;
                display: flex;
                gap: 15px;
            }
            .l-time { color: var(--text-dim); font-size: 0.7rem; width: 60px; }
            .l-content { line-height: 1.5; color: #fff; }
            .log-row.ai .l-content { color: var(--accent); font-weight: 500; }

            @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

            .input-box {
                display: flex;
                gap: 12px;
                margin-top: 15px;
            }
            .neuro-input {
                flex: 1;
                background: rgba(255,255,255,0.03);
                border: 1px solid var(--glass-border);
                border-radius: 10px;
                padding: 14px 20px;
                color: #fff;
                font-family: inherit;
                outline: none;
                transition: 0.3s;
            }
            .neuro-input:focus { border-color: var(--accent); box-shadow: 0 0 15px var(--accent-glow); }
            
            .neuro-btn {
                background: linear-gradient(135deg, var(--accent) 0%, var(--secondary) 100%);
                color: #fff;
                border: none;
                border-radius: 10px;
                padding: 0 30px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            .neuro-btn:hover { filter: brightness(1.2); transform: translateY(-2px); }

            /* Circular HUD 3.0 */
            .hud-ring-group {
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
            }
            .ring-stat {
                position: relative;
                width: 90px; height: 90px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .ring-stat svg {
                position: absolute;
                transform: rotate(-90deg);
                width: 100%; height: 100%;
            }
            .ring-stat circle { fill: none; stroke-width: 5; }
            .ring-stat .bg { stroke: rgba(255,255,255,0.05); }
            .ring-stat .bar { 
                stroke: var(--accent); 
                stroke-dasharray: 251; 
                stroke-dashoffset: 251;
                transition: 0.6s ease-out;
            }
            .stat-label { position: absolute; font-family: 'JetBrains Mono'; font-weight: 700; font-size: 1rem; }

            .cog-card {
                background: rgba(255,255,255,0.02);
                border: 1px solid var(--glass-border);
                border-radius: 12px;
                padding: 15px;
            }
            .cog-row {
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
            }
            .cog-label { font-size: 0.65rem; color: var(--text-dim); text-transform: uppercase; }
            .cog-value { font-family: 'JetBrains Mono'; font-size: 0.8rem; font-weight: 600; }

            .super-controls {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin-top: 10px;
            }
            .sc-btn {
                background: rgba(174, 99, 251, 0.1);
                border: 1px solid rgba(174, 99, 251, 0.3);
                border-radius: 10px;
                padding: 12px;
                color: #fff;
                font-size: 0.7rem;
                font-weight: 600;
                cursor: pointer;
                transition: 0.3s;
                text-align: center;
            }
            .sc-btn:hover { background: var(--accent); border-color: #fff; }

            h6 { margin: 0 0 10px 0; font-size: 0.7rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1.5px; }
        </style>
    </head>
    <body onload="init()">
        <div class="app-wrapper">
            <!-- HEADER -->
            <header class="header">
                <div class="logo">
                     <div style="width: 16px; height: 16px; background: conic-gradient(from 180deg at 50% 50%, var(--accent) 0deg, var(--secondary) 360deg); border-radius: 4px; animation: rotate 4s linear infinite;"></div>
                    MEMO <b>// SUPERNOVA v3.0</b>
                </div>
                <div style="display: flex; gap: 40px; font-family: 'JetBrains Mono'; font-size: 0.75rem;">
                    <div style="color: var(--text-dim)">CORE: <span style="color: var(--accent)">STABLE</span></div>
                    <div style="color: var(--text-dim)">UPLINK: <span id="ping" style="color: var(--accent)">--</span>ms</div>
                    <div id="clock" style="color: #fff;">00:00:00</div>
                </div>
            </header>

            <div class="main-content">
                <!-- VISION STAGE -->
                <section class="vision-stage">
                    <img src="/video_feed" class="feed-img" alt="Neural Feed">
                    <div class="hud-frame">
                        <div class="hud-label-top">[ NEURAL_FEED_ACTIVE ] // MODE: FOCUS_AWARE</div>
                        
                        <!-- HUD Corners 3.0 -->
                        <div style="position: absolute; top: 40px; left: 40px; width: 60px; height: 60px; border-top: 1.5px solid var(--accent); border-left: 1.5px solid var(--accent); opacity: 0.5;"></div>
                        <div style="position: absolute; top: 40px; right: 40px; width: 60px; height: 60px; border-top: 1.5px solid var(--secondary); border-right: 1.5px solid var(--secondary); opacity: 0.5;"></div>
                        <div style="position: absolute; bottom: 40px; left: 40px; width: 60px; height: 60px; border-bottom: 1.5px solid var(--secondary); border-left: 1.5px solid var(--secondary); opacity: 0.5;"></div>
                        <div style="position: absolute; bottom: 40px; right: 40px; width: 60px; height: 60px; border-bottom: 1.5px solid var(--accent); border-right: 1.5px solid var(--accent); opacity: 0.5;"></div>
                        
                        <!-- Telemetry Overlay -->
                        <div style="position: absolute; bottom: 60px; right: 60px; background: rgba(0,0,0,0.4); backdrop-filter: blur(5px); padding: 15px; border-radius: 10px; border: 1px solid var(--glass-border); line-height: 1.6; font-family: 'JetBrains Mono'; font-size: 0.7rem; color: #fff;">
                            SCAN_TARGET: <span id="hud-id">SEARCHING...</span> <br>
                            ENVIRONMENT: NOMINAL <br>
                            UPLINK: 2.4GB/S
                        </div>
                    </div>
                </section>

                <!-- BOTTOM CONTROLS -->
                <div class="control-panel">
                    <div class="terminal-glass">
                        <h6>Neural Command Console</h6>
                        <div id="terminal"></div>
                        <form class="input-box" id="cmd-form">
                            <input type="text" id="cmd-input" class="neuro-input" placeholder="Execute neural transmit..." autocomplete="off">
                            <button type="submit" class="neuro-btn">TRANSMIT</button>
                        </form>
                    </div>

                    <div class="telemetry-glass">
                        <h6>Telemetry & Cognitive</h6>
                        <div class="hud-ring-group">
                            <div class="ring-stat">
                                <svg viewBox="0 0 100 100">
                                    <circle class="bg" cx="50" cy="50" r="40"></circle>
                                    <circle id="cpu-ring" class="bar" cx="50" cy="50" r="40"></circle>
                                </svg>
                                <div class="stat-label" id="cpu-val">0</div>
                                <div style="position: absolute; bottom: -10px; font-size: 0.6rem; color: var(--text-dim);">CPU</div>
                            </div>
                            <div class="ring-stat">
                                <svg viewBox="0 0 100 100">
                                    <circle class="bg" cx="50" cy="50" r="40"></circle>
                                    <circle id="fps-ring" class="bar" cx="50" cy="50" r="40" style="stroke: var(--secondary)"></circle>
                                </svg>
                                <div class="stat-label" id="fps-val">0</div>
                                <div style="position: absolute; bottom: -10px; font-size: 0.6rem; color: var(--text-dim);">FPS</div>
                            </div>
                        </div>

                        <div class="cog-card">
                            <div class="cog-row">
                                <span class="cog-label">System Identity</span>
                                <span class="cog-value" id="cog-id">IDLE</span>
                            </div>
                            <div class="cog-row">
                                <span class="cog-label">Focus State</span>
                                <span class="cog-value" id="cog-focus">OFF</span>
                            </div>
                            <div class="cog-row">
                                <span class="cog-label">Neural Health</span>
                                <span class="cog-value" style="color: var(--accent)">OPTIMAL</span>
                            </div>
                        </div>

                        <div class="super-controls">
                            <button onclick="sendCmd('f')" class="sc-btn">OVERRIDE_FOCUS</button>
                            <button onclick="sendCmd('v')" class="sc-btn">TOGGLE_VOICE</button>
                        </div>
                    </div>
                </div>
            </div>
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
                
                // Circumference = 2 * PI * R (R=40) ≈ 251
                cpuRing.style.strokeDashoffset = 251 - (251 * data.cpu / 100);
                fpsRing.style.strokeDashoffset = 251 - (251 * data.fps / 30 * 100 / 100);

                document.getElementById('cpu-val').innerText = data.cpu;
                document.getElementById('fps-val').innerText = Math.round(data.fps);
                document.getElementById('ping').innerText = Date.now() - lastPing;
                lastPing = Date.now();

                // Cognitive
                const userId = data.identity || (data.human_present ? "UNIDENTIFIED" : "NO_SIGNAL");
                document.getElementById('cog-id').innerText = userId;
                document.getElementById('hud-id').innerText = userId.toUpperCase();
                document.getElementById('cog-focus').innerText = data.focus_mode ? "REINFORCED" : "DEACTIVATED";
                document.getElementById('cog-focus').style.color = data.focus_mode ? "var(--accent)" : "var(--text-dim)";
            });

            socket.on('new_log', (entry) => {
                const div = document.createElement('div');
                div.className = `log-row ${entry.type}`;
                div.innerHTML = `
                    <div class="l-time">${entry.time}</div>
                    <div class="l-content">${entry.msg}</div>
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

