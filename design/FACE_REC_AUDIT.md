# Face Recognition Audit & Overhaul Plan

## 1. Current System Analysis (The Failure)
The current implementation uses `facenet_pytorch` (InceptionResnetV1).
- **Bottleneck**: This is a server-grade model (~100MB+ param). On Raspberry Pi (CPU-only), it runs at < 2 FPS, consuming 100% CPU.
- **Accuracy Issue**: "Detects everyone as same user" suggests the embedding space is collapsed or the distance threshold (L2 distance < 0.7) is too loose for the noisy camera input on the Pi.
- **Result**: Laggy, unusable, unreliable.

## 2. Research: The Edge Standard (2025)
For Raspberry Pi 5, the industry standard for robust, real-time face recognition is **MobileFaceNet (ArcFace)** running on **ONNX Runtime**.

| Feature | Current (InceptionResnet) | Proposed (ArcFace ONNX) |
| :--- | :--- | :--- |
| **Model Size** | ~100 MB | **~4 MB** (Micro) |
| **Speed (Pi 5)** | ~1.5 FPS | **~30-60 FPS** |
| **Metric** | Euclidean | Cosine Similarity (ArcFace) |
| **Detection** | Standard Haar/MTCNN | **YuNet (OpenCV DNN)** |
| **Dependencies** | PyTorch (Heavy) | ONNXRuntime (Light) |

## 3. The New Architecture: "MEMO Vision 2.0"

### A. Detection: YuNet (OpenCV Built-in)
We will use `cv2.FaceDetectorYN`. It is pre-installed in OpenCV, robust to lighting/pose, and extremely fast.
- **Input**: 320x320 dynamic resize.
- **Output**: Bounding Box + 5 Landmarks (Eyes, Nose, Mouth).

### B. Recognition: MobileFaceNet (ArcFace)
We will use a quantized `w600k_r50.onnx` or `mobilefacenet.onnx`.
- **Input**: 112x112 aligned crop.
- **Output**: 512-d normalized embedding.
- **Matching**: Dot Product (Cosine Sim). Threshold > 0.35 (Strict).

### C. Logic Enhancements
1.  **Verification (1:1)** vs **Identification (1:N)** optimization.
2.  **Anti-Spoofing**: Simple geometric check (Depth/Pose variance).
3.  **Memory Bank**: Sliding window of embeddings to averaging vectors for stability.

## 4. Implementation Steps
1.  **Download Models**: Fetch `face_detection_yunet_2023mar.onnx` and `w600k_r50.onnx`.
2.  **New `FaceRec` Class**: Rewrite `perception/face_rec_onnx.py` using `onnxruntime` + `cv2.dnn`.
3.  **Pipeline Integration**: Swap the heavy PyTorch class for the new ONNX class in `main.py`.

## 5. Verification
- **Test 1**: Speed test (FPS counter) on Pi.
- **Test 2**: Specificity (Does it distinguish Person A vs Person B?).
- **Test 3**: Stability (Does it hold ID during motion?).
