#!/usr/bin/env python3
"""
Quick script to verify focus_warning asset frames.
Shows first and middle frame to confirm it's the right animation.
"""
import os
from pathlib import Path
from PIL import Image

assets_dir = Path("interface/lcd/assets/focus_warning")

if not assets_dir.exists():
    print(f"❌ {assets_dir} does not exist!")
    exit(1)

frames = sorted(assets_dir.glob("*.png"))
print(f"Found {len(frames)} frames in focus_warning")

if len(frames) == 0:
    print("❌ No frames found!")
    exit(1)

# Show first frame
first_frame = Image.open(frames[0])
print(f"\n📸 First frame: {frames[0].name}")
print(f"   Size: {first_frame.size}")
print(f"   Mode: {first_frame.mode}")

# Show middle frame
mid_idx = len(frames) // 2
mid_frame = Image.open(frames[mid_idx])
print(f"\n📸 Middle frame: {frames[mid_idx].name}")
print(f"   Size: {mid_frame.size}")
print(f"   Mode: {mid_frame.mode}")

# Check if frames are identical (would indicate wrong asset)
if list(first_frame.getdata()) == list(mid_frame.getdata()):
    print("\n⚠️  WARNING: First and middle frames are IDENTICAL!")
    print("   This might be the wrong animation (static idle face?)")
else:
    print("\n✅ Frames are different - animation should work")

# Show first frame for visual inspection
print("\nOpening first frame for visual inspection...")
first_frame.show()
