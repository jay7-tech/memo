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
        <title>MEMO // NEURAL INTERFACE</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #020406;
                --panel: rgba(15, 20, 28, 0.7);
                --accent: #00f2ff;
                --accent-dim: rgba(0, 242, 255, 0.2);
                --secondary: #ff00ff;
                --text: #e0e6ed;
                --text-dim: #8a95a5;
                --border: rgba(255, 255, 255, 0.08);
                --glass: rgba(255, 255, 255, 0.03);
            }

            * { box-sizing: border-box; }
            body { 
                font-family: 'Outfit', sans-serif; 
                background: var(--bg); 
                background-image: 
                    radial-gradient(circle at 10% 10%, rgba(0, 242, 255, 0.08) 0%, transparent 40%),
                    radial-gradient(circle at 90% 90%, rgba(255, 0, 255, 0.08) 0%, transparent 40%);
                color: var(--text); 
                margin: 0; padding: 0; min-height: 100vh;
                overflow-x: hidden;
            }

            /* Glassmorphism utility */
            .glass {
                background: var(--panel);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid var(--border);
                border-radius: 16px;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
            }

            .header {
                height: 70px;
                padding: 0 40px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-bottom: 1px solid var(--border);
                background: rgba(2, 4, 6, 0.8);
                backdrop-filter: blur(10px);
                position: sticky; top: 0; z-index: 1000;
            }

            .logo {
                font-size: 1.4rem;
                font-weight: 600;
                letter-spacing: 4px;
                color: #fff;
                display: flex;
                align-items: center;
                gap: 15px;
            }

            .logo span { color: var(--accent); }

            .status-orbit {
                width: 12px; height: 12px;
                background: var(--accent);
                border-radius: 50%;
                box-shadow: 0 0 15px var(--accent);
                position: relative;
            }

            .status-orbit::after {
                content: '';
                position: absolute;
                inset: -4px;
                border: 1px solid var(--accent);
                border-radius: 50%;
                animation: rotate 4s linear infinite;
            }

            @keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

            .main-layout {
                display: grid;
                grid-template-columns: 1fr 380px;
                gap: 25px;
                padding: 25px;
                max-width: 1600px;
                margin: 0 auto;
            }

            /* Video Section */
            .video-hub {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }

            .feed-container {
                position: relative;
                width: 100%;
                aspect-ratio: 16/9;
                background: #000;
                border-radius: 20px;
                overflow: hidden;
                border: 1px solid var(--border);
            }

            .feed-container img {
                width: 100%; height: 100%; object-fit: contain;
            }

            /* Neural HUD SVG */
            .hud-overlay {
                position: absolute;
                inset: 0;
                pointer-events: none;
                z-index: 10;
            }

            .hud-corner {
                position: absolute;
                width: 40px; height: 40px;
                border: 2px solid var(--accent-dim);
            }
            .tl { top: 20px; left: 20px; border-right: none; border-bottom: none; }
            .tr { top: 20px; right: 20px; border-left: none; border-bottom: none; }
            .bl { bottom: 20px; left: 20px; border-right: none; border-top: none; }
            .br { bottom: 20px; right: 20px; border-left: none; border-top: none; }

            .scanning-bar {
                position: absolute;
                left: 0; width: 100%;
                height: 2px;
                background: linear-gradient(90deg, transparent, var(--accent), transparent);
                opacity: 0.3;
                animation: scan 3s linear infinite;
            }
            @keyframes scan { 0% { top: 10%; } 100% { top: 90%; } }

            /* Terminal Area */
            .command-center {
                padding: 20px;
                flex-grow: 1;
            }

            .terminal-window {
                height: 280px;
                background: rgba(0,0,0,0.5);
                border-radius: 12px;
                padding: 15px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                overflow-y: auto;
                border: 1px solid rgba(255,255,255,0.05);
                margin-bottom: 15px;
                scrollbar-width: thin;
                scrollbar-color: var(--accent) transparent;
            }

            .terminal-window::-webkit-scrollbar { width: 4px; }
            .terminal-window::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 10px; }

            .log-line { margin-bottom: 8px; animation: fadeIn 0.3s ease-out; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
            
            .t-time { color: var(--text-dim); margin-right: 10px; font-size: 0.75rem; }
            .t-ai { color: var(--accent); font-weight: 700; }
            .t-alert { color: var(--secondary); text-shadow: 0 0 10px var(--secondary); }

            .input-wrapper {
                display: flex; gap: 10px;
            }

            .neuro-input {
                flex: 1;
                background: rgba(255,255,255,0.05);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 14px 20px;
                color: #fff;
                font-family: 'Outfit', sans-serif;
                outline: none;
                transition: all 0.3s ease;
            }

            .neuro-input:focus { border-color: var(--accent); background: rgba(0, 242, 255, 0.05); }

            .neuro-btn {
                padding: 0 25px;
                background: var(--accent);
                color: #000;
                border: none;
                border-radius: 12px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            .neuro-btn:active { transform: scale(0.95); }

            /* Sidebar Blocks */
            .sidebar { display: flex; flex-direction: column; gap: 20px; }

            .telemetry-card { padding: 20px; }
            .chart-container { height: 120px; margin-top: 15px; }

            .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px; }
            .stat-item {
                background: rgba(255,255,255,0.02);
                padding: 12px; border-radius: 12px;
                border: 1px solid var(--border);
            }
            .stat-label { font-size: 0.7rem; color: var(--text-dim); text-transform: uppercase; margin-bottom: 5px; }
            .stat-value { font-family: 'JetBrains Mono'; font-weight: 700; color: var(--accent); }

            .enity-tag {
                display: inline-block;
                padding: 4px 10px;
                background: var(--accent-dim);
                border: 1px solid var(--accent);
                color: var(--accent);
                border-radius: 6px;
                font-size: 0.75rem;
                margin: 3px;
                animation: pulse-tag 2s infinite;
            }
            @keyframes pulse-tag { 0% { opacity: 0.8; } 50% { opacity: 1; } 100% { opacity: 0.8; } }

            h4 { margin: 0; font-weight: 400; letter-spacing: 1px; color: var(--text-dim); font-size: 0.9rem; }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">
                <div class="status-orbit"></div>
                MEMO <span>// NEURAL INTERFACE</span>
            </div>
            <div id="quick-telemetry" style="display: flex; gap: 30px; font-family: 'JetBrains Mono'; font-size: 0.8rem;">
                <div style="color: var(--text-dim)">P5_X64_HOST: <span style="color: var(--accent)">ACTIVE</span></div>
                <div style="color: var(--text-dim)">LATENCY: <span id="ping" style="color: var(--accent)">-- ms</span></div>
            </div>
        </div>

        <div class="main-layout">
            <!-- Left Side: Logic & Vision -->
            <div class="video-hub">
                <div class="feed-container glass">
                    <img src="/video_feed" alt="Neural Feed">
                    <div class="hud-overlay">
                        <div class="hud-corner tl"></div><div class="hud-corner tr"></div>
                        <div class="hud-corner bl"></div><div class="hud-corner br"></div>
                        <div class="scanning-bar"></div>
                        
                        <!-- HUD Labels -->
                        <div style="position: absolute; top: 35px; left: 50px; font-family: 'JetBrains Mono'; font-size: 0.7rem; color: var(--accent); opacity: 0.6;">
                            [ VIEWPORT_01 ] // AI_VISION_ACTIVE<br>
                            RESOLUTION: 640x480 // FPS_SYNC: OK
                        </div>
                    </div>
                </div>

                <div class="command-center glass">
                    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 12px;">
                        <h4>NEURAL COMMAND LINK</h4>
                        <div style="font-size: 0.7rem; color: var(--text-dim);">SYSTEM_BUS_V1.2</div>
                    </div>
                    <div class="terminal-window" id="terminal"></div>
                    <form class="input-wrapper" id="cmd-form">
                        <input type="text" id="cmd-input" class="neuro-input" placeholder="Transmit instruction to MEMO..." autocomplete="off">
                        <button type="submit" class="neuro-btn">SEND</button>
                    </form>
                </div>
            </div>

            <!-- Right Side: Telemetry -->
            <div class="sidebar">
                <div class="telemetry-card glass">
                    <h4>SYSTEM TELEMETRY</h4>
                    <div class="stat-grid">
                        <div class="stat-item">
                            <div class="stat-label">Neural FPS</div>
                            <div class="stat-value" id="fps-val">0.0</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Core Load</div>
                            <div class="stat-value" id="cpu-val">0%</div>
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="perfChart"></canvas>
                    </div>
                </div>

                <div class="telemetry-card glass">
                    <h4>COGNITIVE STATE</h4>
                    <div class="stat-grid" style="grid-template-columns: 1fr;">
                        <div class="stat-item">
                            <div class="stat-label">Identity Profile</div>
                            <div class="stat-value" id="identity-val">--</div>
                        </div>
                    </div>
                    <div class="stat-grid">
                        <div class="stat-item">
                            <div class="stat-label">Focus Shield</div>
                            <div id="focus-st" style="font-weight: 700;">OFF</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Gesture Mode</div>
                            <div style="color: var(--text-dim); font-size: 0.8rem;">READY</div>
                        </div>
                    </div>
                </div>

                <!-- Entity Detection Hidden
                <div class="telemetry-card glass">
                    <h4>ENTITY DETECTION</h4>
                    <div id="objects-list" style="margin-top: 10px; min-height: 60px;">
                        <span style="color: var(--text-dim); font-size: 0.8rem;">No subjects in proximity.</span>
                    </div>
                </div>
                -->

                <!-- Quick Action Shortcuts -->
                 <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <button onclick="sendCmd('f')" class="glass" style="padding: 12px; color: #fff; cursor: pointer; font-size: 0.8rem; border: 1px solid var(--border);">TOGGLE FOCUS</button>
                    <button onclick="sendCmd('v')" class="glass" style="padding: 12px; color: #fff; cursor: pointer; font-size: 0.8rem; border: 1px solid var(--border);">TOGGLE VOICE</button>
                    <button onclick="sendCmd('s')" class="glass" style="padding: 12px; color: #fff; cursor: pointer; font-size: 0.8rem; border: 1px solid var(--border);">SNAP PHOTO</button>
                    <button onclick="sendCmd('status')" class="glass" style="padding: 12px; color: #fff; cursor: pointer; font-size: 0.8rem; border: 1px solid var(--border);">STATUS CHECK</button>
                </div>
            </div>
        </div>

        <script>
            const socket = io();
            const terminal = document.getElementById('terminal');
            
            // Performance Chart
            const ctx = document.getElementById('perfChart').getContext('2d');
            const perfChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: Array(20).fill(''),
                    datasets: [{
                        label: 'FPS',
                        data: Array(20).fill(0),
                        borderColor: '#00f2ff',
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 0
                    }, {
                        label: 'CPU',
                        data: Array(20).fill(0),
                        borderColor: '#ff00ff',
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { 
                        y: { display: false, min: 0, max: 100 },
                        x: { display: false }
                    }
                }
            });

            let lastPing = Date.now();
            socket.on('stats_update', function(data) {
                // Update text stats
                document.getElementById('fps-val').innerText = data.fps;
                document.getElementById('cpu-val').innerText = data.cpu + '%';
                document.getElementById('ping').innerText = (Date.now() - lastPing) + ' ms';
                lastPing = Date.now();
                
                document.getElementById('identity-val').innerText = data.identity || (data.human_present ? "UNIDENTIFIED" : "IDLE");
                document.getElementById('focus-st').innerText = data.focus_mode ? "REINFORCED" : "DEACTIVATED";
                document.getElementById('focus-st').style.color = data.focus_mode ? "#ff00ff" : "var(--text-dim)";
                
                // Entity tags
                const objContainer = document.getElementById('objects-list');
                if(data.objects && data.objects.length) {
                    objContainer.innerHTML = data.objects.map(o => `<span class="enity-tag">${o.toUpperCase()}</span>`).join('');
                } else {
                    objContainer.innerHTML = '<span style="color: var(--text-dim); font-size: 0.8rem;">No subjects in proximity.</span>';
                }

                // Update chart
                perfChart.data.datasets[0].data.push(data.fps * 2); // Scale for visual
                perfChart.data.datasets[0].data.shift();
                perfChart.data.datasets[1].data.push(data.cpu);
                perfChart.data.datasets[1].data.shift();
                perfChart.update('none');
            });

            socket.on('new_log', function(entry) {
                const div = document.createElement('div');
                div.className = 'log-line';
                const typeClass = entry.type === 'ai' ? 't-ai' : (entry.type === 'alert' ? 't-alert' : '');
                div.innerHTML = `<span class="t-time">${entry.time}</span> <span class="${typeClass}">[${entry.type.toUpperCase()}]</span> <span>${entry.msg}</span>`;
                terminal.appendChild(div);
                if (terminal.childNodes.length > 50) terminal.removeChild(terminal.firstChild);
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

            // Init greeting
            setTimeout(() => {
                const welcome = document.createElement('div');
                welcome.className = 'log-line';
                welcome.innerHTML = `<span class="t-time">${new Date().toLocaleTimeString()}</span> <span class="t-ai">[SYSTEM]</span> <span>NEURAL INTERFACE LINK ESTABLISHED.</span>`;
                terminal.appendChild(welcome);
            }, 500);
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

