import cv2
import time
import threading

class CameraSource:
    def __init__(self, source=0, width=640, height=480, rotation=0):
        # Initialize lock immediately to prevent race conditions
        import threading
        self.lock = threading.Lock()

        # Enforce string for URL if it looks like one, or int for index
        if isinstance(source, str) and source.isdigit():
            source = int(source)
            
        self.src = source
        self.rotation = int(rotation)
        
        if __import__("os").name == "nt":
             # Use DirectShow on Windows
            self.cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        else:
            # Linux/Pi: Use integer index 0 for libcamerify compatibility
            # passing "/dev/video0" as string causes "can't be used to capture by name" error
            # Removing V4L2 enforcement to let libcamerify handle the interception freely
            print(f"[Camera] Opening camera {source} (Auto Backend)...")
            self.cap = cv2.VideoCapture(source)
            
            # --- FALLBACK: GStreamer (libcamerasrc) ---
            # If standard V4L2/Auto fails (common on Pi 5), try GStreamer pipeline
            if not self.cap.isOpened():
                print("[Camera] Auto-backend failed. Trying GStreamer (libcamerasrc)...")
                gst_pipeline = (
                    "libcamerasrc ! video/x-raw, width=640, height=480, framerate=30/1 ! "
                    "videoconvert ! appsink"
                )
                try:
                    self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
                    if self.cap.isOpened():
                        print("[Camera] Success: Connected via GStreamer!")
                except Exception as e:
                    print(f"[Camera] GStreamer failed: {e}")
            
            # Force params (If not GStreamer)
            if not self.cap.get(cv2.CAP_PROP_BACKEND) == cv2.CAP_GSTREAMER:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open /dev/video0 (Check connection or libcamerify)")

        # Optimization: Buffer size 1
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.latest_frame = None
        self.status = False
        self.running = True
        self.status = False
        self.running = True
        self.low_power_mode = False  # Start in active mode
        
        # Start background thread to read frames
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()
        
        # Wait for first frame
        start = time.time()
        while self.latest_frame is None:
            if time.time() - start > 5.0:
                print("Warning: Camera source timed out getting first frame.")
                break
            time.sleep(0.1)

            time.sleep(0.1)

    def set_low_power(self, enabled: bool):
        """Toggle low power mode (1 FPS vs 30 FPS)."""
        self.low_power_mode = enabled
        rate = "1 FPS" if enabled else "30 FPS"
        print(f"[Camera] Power Mode: {'LOW' if enabled else 'HIGH'} ({rate})")

    def _update(self):
        while self.running:
            if self.cap.isOpened():
                # Throttling for Low Power Mode
                if self.low_power_mode:
                    time.sleep(1.0) # 1 FPS
                    
                ret, frame = self.cap.read()
                if ret:
                    # Apply rotation if needed
                    if self.rotation == 90:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                    elif self.rotation == 180:
                        frame = cv2.rotate(frame, cv2.ROTATE_180)
                    elif self.rotation == 270:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                        
                    with self.lock:
                        self.latest_frame = frame
                        self.status = True
                else:
                    self.status = False
                    # potentially reconnect logic here if needed
                    pass
            else:
                time.sleep(0.1)

    def get_frame(self):
        with self.lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def release(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.cap.release()
