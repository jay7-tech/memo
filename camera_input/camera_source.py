import cv2
import time
import threading

class CameraSource:
    def __init__(self, source=0, width=640, height=480, rotation=0):
        # Enforce string for URL if it looks like one, or int for index
        self.src = source
        self.rotation = int(rotation)
        
        self.cap = cv2.VideoCapture(self.src)
        
        # Optimize for low latency (may not work on all backends but worth trying)
        # buffer size = 1
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Only for V4L2/GStreamer essentially, but harmless
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera source {source}")

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
