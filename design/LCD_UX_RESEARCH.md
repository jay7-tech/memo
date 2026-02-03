# LCD UX Research & Design Strategy: "The Living Interface"

To make the LCD screen the "soul" of the MEMO robot, we must move beyond static icons to dynamic, reactive, and organic behaviors. The screen should feel like a window into the AI's mind.

## 1. Core Design Philosophy: "Digital Organism"
The interface should feel alive, not just a display board.
*   **Constant Motion**: Nothing in nature is perfectly still. Even in "IDLE", there should be subtle "breathing" (brightness pulse) or micro-movements (saccades).
*   **Neon/Cyber Aesthetic**: Utilizing the existing highly saturated, neon-on-black aesthetic to create a high-contrast, premium look that works well on small LCDs.
*   **Instant Reactivity**: The screen must change the *instant* an event happens (Latency < 50ms).

## 2. Functional State Mapping (The "Synk")

We will map every internal system state to a visual expression.

| System State | Visual Expression | Animation Style |
| :--- | :--- | :--- |
| **IDLE** | The "Eyes". Blinking, looking left/right/randomly. | Slow, organic, smooth interpolation. |
| **LISTENING** | Voice Activity Detection (VAD) triggers ear perking or waveform visualization. | High framerate, reactive to volume levels. |
| **THINKING** | When AI is querying Ollama/Gemini. | Fast spinning, throbbing "brain" or "loading" geometric patterns. Color: **Cyan/Blue**. |
| **SPEAKING** | TTS Active. | Mouth movement or amplitude-based brightness modulation of the eyes. |
| **SCANNING** | Vision Pipeline Active (Object Detection). | HUD overlay effect, "Targeting" reticles moving across the eye. Color: **Green**. |
| **FOCUS MODE** | "Locked In". | Sharp, angular "Target" eyes. Minimal movement. Color: **Red**. |
| **ERROR/CONFUSED** | Command failed or low confidence. | Glitch effect, static noise, or a "dizzy" spiral. Color: **Orange**. |
| **SLEEP** | Low power / Night time. | "Zzz" animation or closed eyelids. Dim backlight. |

## 3. Aesthetic Improvements

### A. Transitions (The "Glitch" & "Morph")
Instead of hard cuts between images, we can implement:
*   **Glitch Transition**: For mode changes (e.g., Idle -> Focus), inject 2-3 frames of random pixel noise or chromatic aberration. This fits the "Cyber" theme.
*   **Dissolve**: For emotional shifts (e.g., Neutral -> Happy), use alpha blending (if performance allows).

### B. "Breathing" Backlight
Use the PWM backlight control (if available on Pi) to pulse the screen brightness gently during IDLE states. This simulates breathing.

### C. Color Psychology
*   **Nominal**: Mint Green / Cyan (Calm, Ready)
*   **Active/Work**: Red (Focus, Do Not Disturb)
*   **Social**: Pink/Purple (Love, Happy, Greetings)
*   **Thinking**: Electric Blue (Processing)

## 4. Technical Implementation Plan

To achieve this without blocking the Main Thread:

1.  **Event-Driven Animation Queue**:
    The `LCDManager` needs a priority queue.
    *   *Priority 1 (Critical)*: Focus Mode, Alerts, Wake Word. (Interrupts everything)
    *   *Priority 2 (Normal)*: Thinking, Speaking indicators.
    *   *Priority 3 (Background)*: Idle animations.

2.  **Hooks in `main.py`**:
    *   `command_processor.py` -> Trigger "Thinking" start/stop.
    *   `tts_engine.py` -> Trigger "Speaking" start/stop.
    *   `voice_input.py` -> Trigger "Listening" start/stop.

3.  **Refined Asset Library**:
    We need to generate or create specific animations for:
    *   `listening.gif` (Waveform)
    *   `thinking.gif` (Spinner/Orbit)
    *   `talking.gif` (Mouth/Modulation)

## 5. "Deep Research" - Next Steps

*   **Experiment**: Test if the Pi 4/5 can handle 30fps resizing for "Glitch" effects in Python or if we need pre-rendered frames.
*   **Feedback**: Does the user prefer "Eyes" (Anthromorphic) or "Abstract" (HAL-9000 style) for thinking? -> *Recommendation: Hybrid. Eyes for social, Abstract for tasks.*
