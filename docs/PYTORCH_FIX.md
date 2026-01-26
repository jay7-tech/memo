# Fixing PyTorch DLL Error on Windows

## The Error

```
OSError: [WinError 127] The specified procedure could not be found. 
Error loading "C:\MINICONDA\Lib\site-packages\torch\lib\shm.dll"
```

## Quick Fix: Use Lite Demo (No PyTorch Required)

Run the lightweight demo instead:

```bash
python demo_features_lite.py
```

This demonstrates all new features (logging, config, motion detection, context) **without requiring PyTorch/YOLO**.

---

## Permanent Fix: Reinstall PyTorch

### Option 1: Reinstall PyTorch (CPU Only)

```bash
# Uninstall existing
pip uninstall torch torchvision

# Install CPU version
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Option 2: Install Visual C++ Redistributables

PyTorch requires Microsoft Visual C++ 2019 Redistributable:

1. Download from: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
2. Install `vc_redist.x64.exe`
3. Restart computer
4. Try again

### Option 3: Use Conda Environment

If using conda, create a clean environment:

```bash
# Create new environment
conda create -n memo python=3.10
conda activate memo

# Install PyTorch via conda (recommended)
conda install pytorch torchvision cpuonly -c pytorch

# Install other requirements
pip install -r requirements.txt
```

### Option 4: Downgrade PyTorch

Try an older stable version:

```bash
pip uninstall torch torchvision
pip install torch==2.0.0 torchvision==0.15.0
```

---

## Why This Happens

**Mixed Installation:**
- Conda installs its own Python runtime
- pip installs packages that may expect different DLLs
- Result: DLL version mismatch

**Solution:**
- Use **either** conda **or** pip, not both
- For MEMO, we recommend **pip** for simplicity

---

## Testing If Fixed

```bash
python -c "import torch; print(f'PyTorch {torch.__version__} works!')"
```

If this prints the version, PyTorch is fixed.

Then run:
```bash
python demo_features.py  # Full demo with YOLO
```

---

## Alternative: Skip PyTorch Entirely

For Raspberry Pi deployment, you'll want TFLite models anyway (not PyTorch).

**What works without PyTorch:**
✅ Motion detection
✅ Context awareness  
✅ Logging system
✅ Configuration
✅ Dashboard (if flask works)

**What needs PyTorch:**
❌ YOLO object detection
❌ Pose estimation
❌ Face recognition (facenet-pytorch)

**Migration Plan:**
1. Use `demo_features_lite.py` for testing foundation
2. For Pi4B, convert models to TFLite (Phase 2)
3. Replace torch-based modules with TFLite versions

---

## Summary

| Solution | Time | Difficulty |
|----------|------|------------|
| **Use demo_features_lite.py** | 0 min | ✅ Easy |
| Install VC++ Redistributables | 5 min | ✅ Easy |
| Reinstall PyTorch (CPU) | 2 min | ⚠️ Medium |
| Create conda environment | 10 min | ⚠️ Medium |
| Skip PyTorch (use TFLite) | Later | 🔴 Advanced |

**Recommendation:** Start with `demo_features_lite.py` to test new features immediately!
