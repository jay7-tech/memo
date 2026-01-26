# MEMO Advanced Features - Quick Start Guide

## What's New 🎉

### Phase 1 Complete ✅
1. **Production Logging** - Colored console + file rotation
2. **Configuration System** - JSON-based with validation
3. **Custom Exceptions** - Better error handling
4. **Motion Detection** - Wake from idle, security alerts
5. **Context Awareness** - Time-based greetings

## Quick Test

### 1. Install New Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Demo
```bash
python demo_features.py
```

### Keyboard Controls
- `q` - Quit
- `m` - Toggle motion detection
- `r` - Reset motion detector
- `g` - Force greeting
- `c` - Show context summary
- `h` - Show help

## What to Expect

### Logging
- **Console**: Colored output (green=INFO, yellow=WARNING, red=ERROR)
- **File**: `logs/memo_YYYYMMDD.log` (rotates at 10MB)

### Motion Detection
- Wave your hand → See green boxes
- Motion score displayed
- Logs significant motion events

### Context Awareness
- Time-based greeting on start
- Tracks user presence
- Adapts to time of day

### Configuration
- **File**: `config.json`
- Edit to customize behavior
- Auto-validates on load

## Configuration Options

### Enable/Disable Features
```json
{
  "perception": {
    "enable_motion": true,     // Motion detection
    "enable_emotion": false,   // Coming soon
    "enable_gestures": false   // Coming soon
  },
  "system": {
    "logging_level": "INFO",   // DEBUG, INFO, WARNING, ERROR
    "personality_mode": "helpful",  // helpful, sarcastic, cute
    "greeting_enabled": true
  }
}
```

### Camera Settings
```json
{
  "camera": {
    "source": 0,          // 0 = webcam, or IP camera URL
    "width": 640,
    "height": 480,
    "rotation": 0,        // 0, 90, 180, 270
    "fps_target": 15
  }
}
```

## Log Files

Check `logs/memo_YYYYMMDD.log` for detailed information:
- System events
- Performance metrics
- Error traces
- Motion events

## Next Steps

Coming in Phase 2:
- ✨ Emotion detection
- 🖐️ Hand gestures
- 👁️ Eye gaze tracking

Coming in Phase 3:
- 🔊 Wake word ("Hey MEMO")
- 🎭 Personality modes
- 🧠 Conversation memory

## Troubleshooting

### Camera Not Found
```
CameraError: Could not open camera source 0
```
**Fix**: Try different source IDs (0, 1, 2) or IP camera URL in `config.json`

### Missing Dependencies
```
ModuleNotFoundError: No module named 'colorlog'
```
**Fix**: `pip install -r requirements.txt`

### Permission Error (Logs)
```
PermissionError: [Errno 13] Permission denied: 'logs/...'
```
**Fix**: Run from MEMO directory, ensure write permissions

## Performance

Optimized for Raspberry Pi 4B:
- Frame skipping (every 3rd frame)
- Simple motion detection (fast)
- Async logging (non-blocking)
- 12-15 FPS target

**Tip**: For testing on powerful PC, you can:
- Disable `frame_skip` → faster
- Enable `use_mog2` in motion detector → more accurate

---

Made with ❤️ by Jay7-Tech
