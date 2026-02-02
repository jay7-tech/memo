import cv2
import time
import threading

class CameraSource:
    def __init__(self, source=0, width=640, height=480, rotation=0):
        # Initialize lock immediately to prevent race conditions
        import threading
        self.lock = threading.Lock()

        # Enforce string for URL if it looks like one, or int for index
        self.src = source
        self.rotation = int(rotation)
        
        if __import__("os").name == "nt":
             # Use DirectShow on Windows
            self.cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        else:
            # Linux/Pi: FORCE /dev/video0 with V4L2 (User Fix)
            # Auto-scan removed because OpenCV reopening is buggy on Pi
            print(f"[Camera] Opening /dev/video0 with V4L2...")
            self.cap = cv2.VideoCapture("/dev/video0", cv2.CAP_V4L2)
            
            # Force params
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
        self.lock = threading.Lock()

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

    def _update(self):
        while self.running:
            if self.cap.isOpened():
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
