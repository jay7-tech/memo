from flask import Flask, render_template_string, Response, jsonify
import cv2
import threading
import time

app = Flask(__name__)

# Shared state
output_frame = None
lock = threading.Lock()
scene_state_ref = None

def set_scene_state(state):
    global scene_state_ref
    scene_state_ref = state

def update_frame(frame):
    global output_frame
    with lock:
        output_frame = frame.copy()

def generate():
    global output_frame
    while True:
        with lock:
            if output_frame is None:
                # wait a bit
                time.sleep(0.1)
                continue
            
            # Encode
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
            if not flag:
                continue
        
        # Yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encodedImage) + b'\r\n')
        time.sleep(0.1) # low FPS stream (10fps max)

@app.route("/")
def index():
    return render_template_string("""
    <html>
    <head>
        <title>MEMO Intelligence Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #0a0a0a; color: #eee; text-align: center; margin: 0; padding: 20px; }
            h1 { color: #00ffcc; text-transform: uppercase; letter-spacing: 4px; font-weight: 300; margin-bottom: 30px; }
            .container { display: flex; flex-wrap: wrap; justify-content: center; gap: 30px; }
            .video-box { 
                border: 1px solid #333; 
                box-shadow: 0 0 30px rgba(0, 255, 204, 0.1); 
                border-radius: 8px;
                overflow: hidden;
                width: 640px;
                max-width: 100%;
            }
            img { width: 100%; display: block; }
            .stats { 
                background: #111; 
                padding: 30px; 
                border-radius: 12px; 
                text-align: left; 
                min-width: 300px;
                border: 1px solid #222;
            }
            h2 { border-bottom: 2px solid #333; padding-bottom: 10px; margin-top: 0; color: #aaa; font-size: 1.2em; }
            .stat-item { margin: 15px 0; font-size: 1.1em; display: flex; justify-content: space-between; }
            .label { color: #666; }
            .value { color: #fff; font-weight: bold; font-family: 'Courier New', monospace; }
            .controls { margin-top: 30px; text-align: center; }
            button { 
                background: linear-gradient(135deg, #111, #222); 
                color: #00ffcc; 
                border: 1px solid #444; 
                padding: 12px 24px; 
                cursor: pointer; 
                border-radius: 4px;
                font-size: 1em;
                transition: all 0.3s ease;
            }
            button:hover { 
                background: #00ffcc; 
                color: #000;
                box-shadow: 0 0 15px rgba(0,255,204,0.5);
            }
            
            #status-dot {
                display: inline-block; width: 10px; height: 10px; background: #333; border-radius: 50%; margin-right: 8px;
            }
            .active { background: #0f0 !important; box-shadow: 0 0 8px #0f0; }
        </style>
        <script>
            function fetchStats() {
                fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('human-present').innerText = data.human_present ? "DETECTED" : "ABSENT";
                    document.getElementById('human-dot').className = data.human_present ? "active" : "";
                    
                    document.getElementById('identity').innerText = data.identity || "Unknown";
                    
                    document.getElementById('focus-mode').innerText = data.focus_mode ? "ACTIVE" : "INACTIVE";
                    document.getElementById('focus-mode').style.color = data.focus_mode ? "#ff3366" : "#666";
                    
                    // Format objects
                    let objs = data.objects;
                    if(objs.length === 0) objs = ["None"];
                    document.getElementById('objects').innerText = objs.join(", ");
                });
            }
            setInterval(fetchStats, 1000);
            
            function toggleFocus() { fetch('/api/toggle/focus'); }
        </script>
    </head>
    <body>
        <h1>MEMO Interface</h1>
        <div class="container">
            <div class="video-box">
                <img src="/video_feed">
            </div>
            <div class="stats">
                <h2>Intelligence Data</h2>
                <div class="stat-item">
                    <span class="label">Presence:</span> 
                    <span><span id="human-dot" id="status-dot"></span><span class="value" id="human-present">...</span></span>
                </div>
                <div class="stat-item"><span class="label">Identity:</span> <span class="value" id="identity">...</span></div>
                <div class="stat-item"><span class="label">Focus System:</span> <span class="value" id="focus-mode">...</span></div>
                <div class="stat-item" style="flex-direction: column; align-items: flex-start;">
                    <span class="label" style="margin-bottom: 5px;">Visual Memory:</span> 
                    <span class="value" id="objects" style="font-size: 0.9em; color: #888;">...</span>
                </div>
                
                <div class="controls">
                     <button onclick="toggleFocus()">TOGGLE FOCUS SHIELD</button>
                     <p style="margin-top: 15px; font-size: 0.8em; color: #444;">DASHBOARD V1.0</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def api_stats():
    if scene_state_ref:
        # Extract serializable data
        # We need to map keys carefully
        data = {
            'human_present': scene_state_ref.human['present'],
            'identity': scene_state_ref.human['identity'],
            'focus_mode': scene_state_ref.focus_mode,
            'objects': list(scene_state_ref.objects.keys())
        }
        return jsonify(data)
    return jsonify({})

@app.route("/api/toggle/focus")
def toggle_focus():
    if scene_state_ref:
        scene_state_ref.focus_mode = not scene_state_ref.focus_mode
        return jsonify({"status": "success", "new_state": scene_state_ref.focus_mode})
    return jsonify({"status": "error"})

def start_server():
    # Run slightly quiet
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    print(">> SYSTEM: Dashboard running at http://localhost:5000")
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Dashboard Error: {e}")
