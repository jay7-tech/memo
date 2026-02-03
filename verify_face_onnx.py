import cv2
import time
import numpy as np
from perception.face_rec_onnx import FaceRecONNX

def verify():
    print("Initializing ONNX Engine...")
    fr = FaceRecONNX()
    
    if fr.detector is None or fr.recognizer is None:
        print("Failed to load models.")
        return

    cap = cv2.VideoCapture(0)
    print("Press 'q' to quit, 'r' to register user 'MemoMaster'.")
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        start = time.time()
        
        try:
            # 1. Detect
            faces = fr.detect(frame)
            
            # 2. Recognize
            name = "Unknown"
            conf = 0.0
            
            if faces is not None and len(faces) > 0:
                # Debug
                # print(f"Faces: {faces.shape}")
                
                # Draw faces
                for face in faces:
                    # Face format: x, y, w, h, ...
                    x, y, w, h = face[0:4].astype(int)
                    x, y, w, h = int(x), int(y), int(w), int(h) # Native int
                    
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Landmarks (Eyes, Nose, Mouth)
                    coords = face[4:14].astype(int).reshape((5, 2))
                    for (lx, ly) in coords:
                        cv2.circle(frame, (int(lx), int(ly)), 2, (255, 0, 0), -1)

                # Recognize largest face
                n, c = fr.recognize(frame)
                if n:
                    name = n
                    conf = c
                
                # ID Text
                display_name = name if name else "Unknown"
                color = (0, 255, 0) if name else (0, 0, 255)
                cv2.putText(frame, f"ID: {display_name} ({conf:.2f})", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # FPS
            fps = 1.0 / (time.time() - start)
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            cv2.imshow("FaceONNX Verify", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                res = fr.register_face(frame, name="MemoMaster")
                print(f"Registration: {res}")
        except Exception as e:
            print(f"Frame Error: {e}")
            import traceback
            traceback.print_exc()
            break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    verify()
