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
        
        # Try opening the requested source
        if not self._open_source(self.src, width, height):
            # If failed and source was 0, try auto-scanning indices 1-10
            if self.src == 0:
                print(f"[Camera] Source 0 failed. Auto-scanning other indices...")
                found = False
                for i in range(1, 10):
                    print(f"[Camera] Trying index {i}...")
                    if self._open_source(i, width, height):
                        print(f"[Camera] ✓ Found working camera at index {i}")
                        self.src = i
                        found = True
                        break
                
                if not found:
                    raise RuntimeError(f"Could not open any camera source (Scanned 0-9)")
            else:
                raise RuntimeError(f"Could not open camera source {source}")

    def _open_source(self, source, width, height):
        """Helper to attempt opening a source."""
        try:
            if isinstance(source, int):
                # Windows: Use DirectShow
                if __import__("os").name == "nt":
                    self.cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
                # Linux/Pi: Enforce V4L2 (User Recommendation)
                else:
                    self.cap = cv2.VideoCapture(source, cv2.CAP_V4L2)
                    # Force MJPG for better framerate on Pi if possible, or standard YUYV
                    # self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            else:
                self.cap = cv2.VideoCapture(source)
            
            if not self.cap.isOpened():
                return False
                
            # Set params
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Read one frame to confirm it's real
            ret, _ = self.cap.read()
            if not ret:
                self.cap.release()
                return False
                
            return True
        except:
            return False

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
