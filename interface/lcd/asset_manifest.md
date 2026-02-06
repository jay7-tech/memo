
# LCD Asset Manifest

This document maps all graphic assets located in `interface/lcd/assets/`, describing their purpose, usage conditions, and animation timing.

| Asset Folder | Status | Usages (Function / Mode) | Timing (FPS/Duration) | Description |
| :--- | :--- | :--- | :--- | :--- |
| **idle_center** | ✅ Active | `play("idle_center")`<br>`set_speaking()`<br>`set_focus_mode(False)` | **100-150ms** | Default resting state; standard large eyes looking forward (Video Call style). Also used during speech (lips sync simulation). |
| **focus_scan** | ✅ Active | `set_focus_mode(True)` | **100ms** | Binoculars or "Scan" eyes. displayed when Focus Mode is active and monitoring for distractions. |
| **focus_warning** | ✅ Active | `trigger_distraction()` | **60ms** (Fast) | "No Phone" symbol. Triggered immediately when a phone is detected in Focus Mode. |
| **listening** | ✅ Active | `set_listening()` | **80ms** (Fast) | Active listening animation (e.g., eyes wide or pulsating) when Wake Word is detected. |
| **thinking** | ✅ Active | `set_thinking()` | **100ms** | Processing animation (e.g., looking up/around) while querying LLM. |
| **flash** | ✅ Active | `trigger_flash()` | **30ms** (Very Fast) | White flash effect mimicking a camera shutter. |
| **wink** | ✅ Active | `trigger_eureka()` | **60ms** | Playful wink. Used for "Eureka" moments or task completion. |
| **selfie_cam** | ✅ Active | `trigger_selfie()` | **50ms** | Countdown or shutter animation for selfie mode. |
| **sleep** | ⚠️ Unused* | *Reserved* | N/A | Zzz / Sleeping eyes. (Currently `set_clock_mode` uses dynamic drawing instead). |
| **blink** | ⚠️ Unused | *Reserved* | N/A | Standard blink animation. (Idle mode likely has baked-in blinks or uses random frames). |
| **angry** | ⚠️ Unused | *Reserved* | N/A | Expression for negative feedback. |
| **laugh** | ⚠️ Unused | *Reserved* | N/A | Expression for happy feedback. |
| **love** | ⚠️ Unused | *Reserved* | N/A | Hearts/Love expression. |
| **phone** | ⚠️ Unused | *Reserved* | N/A | Generic phone icon (likely superseded by focus_warning). |
| **boot** | ⚠️ Unused | *Reserved* | N/A | Boot-up sequence. |
| **silence** | ⚠️ Unused | *Reserved* | N/A | Muted microphone state. |
| **distraction** | ⚠️ Unused | *Reserved* | N/A | Alternate distraction graphic? (superseded by focus_warning). |
| **idle_left/right**| ⚠️ Unused | *Reserved* | N/A | Look left/right variants. |
| **focus_off** | ⚠️ Unused | *Reserved* | N/A | Transition state when focus mode ends? |
| **focus_police** | ⚠️ Unused | *Reserved* | N/A | Alternate warning graphic? |

*\*Unused: These folders exist but are not explicitly called in the current `manager.py`. They may be used by future features or legacy code.*

## Dynamic Utils
- **Clock Mode**: Does NOT use assets. It uses `PIL.ImageDraw` to render the time and "zZZ" text dynamically on black background.
