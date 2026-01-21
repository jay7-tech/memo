# MEMO - Vision-First AI Desktop Companion

**MEMO** (Memory & Environmental Monitoring Observer) is an intelligent, vision-based desktop companion designed to enhance productivity, health, and spatial awareness. It transforms your standard webcam or mobile phone camera into a smart observer that tracks objects, monitors your posture, guards your focus, and recognizes you.

Built with **YOLOv8**, **FaceNet**, and **OpenCV**, MEMO runs entirely locally on your machine, ensuring privacy and speed.

---

## 🚀 Features

### 🧠 **Spatial Memory & Querying**
MEMO "remembers" where it saw objects on your desk.
- **"Where is my bottle?"** → *"The bottle is currently on the left, seen just now."*
- **"Do you see my wallet?"** → *"Yes, I see the wallet."*
- Supports fuzzy matching and synonyms (e.g., "phone" = "cell phone").

### 👤 **Face Recognition & Greeting**
MEMO knows who you are.
- **Personalized Greetings**: *"Hello Jayadeep. Welcome back."*
- **Privacy-First**: Face embeddings are stored locally (`user_embedding.npy`) and never uploaded.
- **Smart Re-Greeting**: Only greets you again if you've been away for a while.

### 📵 **Smart Focus Mode**
Need to get work done? Tell MEMO to guard your focus.
- **Command**: `focus on`
- **Behavior**: If MEMO sees a cell phone in the frame, it verbally scolds you: *"Put the phone away and focus on your work!"*
- **Visuals**: Bounding boxes turn RED when threats (phones) are detected.

### 🧘 **Health & Posture Coach**
MEMO watches out for your physical well-being.
- **Proximity Alert**: If you lean too close to the screen (>55% frame width), it warns: *"You are too close to the screen. Please move back."*
- **Sedentary Alert**: Tracks how long you've been sitting. If > 60 minutes, it reminds you to stretch.

---

## 🛠️ Technology Stack
- **Vision**: YOLOv8 (Object Detection & Pose Estimation), FaceNet (Face Recognition).
- **Core**: OpenCV (Video Processing), NumPy.
- **Audio**: pyttsx3 (Text-to-Speech).
- **Architecture**: Modular Python design (Perception → State → Reasoning → Interface).

---

## 📦 Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/jay7-tech/memo.git
    cd memo
    ```

2.  **Install Dependencies**
    MEMO requires Python 3.8+ and PyTorch.
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Visual C++ Build Tools may be required for some dependencies on Windows.*


## 🎮 Usage

1.  **Run the System**:
    ```bash
    # Default Webcam (Source 0)
    python main.py

    # IP Camera (Example)
    python main.py http://192.168.1.5:8080/video 90
    ```

2.  **Web Dashboard 🌐**:
    Visit **[http://localhost:5000](http://localhost:5000)** to view the live feed and control the system remotely.

3.  **Voice Commands 🗣️**:
    - **Toggle Voice**: Press `v` or type `voice on`.
    - **Commands**:
        - *"Focus on"* / *"Focus off"*
        - *"Register me"*
        - *"Where is my [object]?"*
        - *"Selfie"* (Takes a photo)

4.  **Keyboard Shortcuts**:
    - `q`: Quit
    - `v`: Toggle Voice
    - `f`: Toggle Focus Mode
    - `s`: Take Selfie

---

**Author**: [Jayadeep / Jay7-Tech]
