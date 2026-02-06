
import os
import time
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Define Assets Path
ASSETS_DIR = Path("interface/lcd/assets")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

def ensure_clean_dir(name):
    path = ASSETS_DIR / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()
    return path

def create_frame(size=(128, 128), color=(0, 0, 0)):
    return Image.new("RGB", size, color)

def save_frames(name, frames):
    d = ensure_clean_dir(name)
    print(f"Generating '{name}' ({len(frames)} frames)...")
    for i, img in enumerate(frames):
        img.save(d / f"{i:03d}.png")

def gen_classic_warning():
    """Generates the Red Exclamation Mark (Focus Warning)."""
    frames = []
    # Color Palette
    BG = (0, 0, 0)
    MAIN = (255, 0, 0) # RED
    WHITE = (255, 255, 255)
    
    for i in range(10): # 10 frames loop
        img = create_frame(color=BG)
        draw = ImageDraw.Draw(img)
        
        # Draw Triangle
        # Center 64, 64
        # Pulse size
        pulse = abs(5 * (i - 5)) / 5 # 0..1..0
        scale = 1.0 + (pulse * 0.1)
        
        # Triangle Points
        # Top: 64, 20
        # BL: 20, 100
        # BR: 108, 100
        
        cx, cy = 64, 64
        coords = [
            (64, 20),
            (20, 100),
            (108, 100)
        ]
        
        # Apply scale if fancy, or just draw
        draw.polygon(coords, outline=MAIN, width=3)
        
        # Exclamation
        draw.rectangle([60, 40, 68, 70], fill=MAIN)
        draw.ellipse([60, 78, 68, 86], fill=MAIN)
        
        # Flash Text
        if i % 4 < 2:
            draw.text((35, 110), "NO PHONE", fill=WHITE)
            
        frames.append(img)
        
    save_frames("focus_warning", frames)

def gen_scan():
    """Generates Green Scanning Eyes."""
    frames = []
    BG = (0, 0, 0)
    SCAN_COLOR = (0, 255, 100)
    
    for i in range(10):
        img = create_frame(color=BG)
        draw = ImageDraw.Draw(img)
        
        # Draw Eyes (Rects)
        # Left: 30, 50, 50, 70
        # Right: 78, 50, 98, 70
        
        # Scan line moving up/down
        y_scan = 50 + (i * 2)
        
        draw.rectangle([30, 50, 50, 70], outline=SCAN_COLOR)
        draw.rectangle([78, 50, 98, 70], outline=SCAN_COLOR)
        
        # Scan line
        draw.line([20, y_scan, 108, y_scan], fill=(0, 100, 0))
        
        frames.append(img)
        
    save_frames("focus_scan", frames)

def gen_idle():
    """Generates Idle Center Eye."""
    frames = []
    for i in range(5):
        img = create_frame()
        draw = ImageDraw.Draw(img)
        # Simple Circle
        draw.ellipse([50, 50, 78, 78], outline=(0, 255, 255))
        draw.ellipse([60, 60, 68, 68], fill=(0, 255, 255))
        frames.append(img)
    save_frames("idle_center", frames)

if __name__ == "__main__":
    print("=== FIXED ASSET GENERATOR ===")
    try:
        gen_classic_warning()
        gen_scan()
        gen_idle()
        print("\n✅ Success! Missing assets generated.")
        print("Folder: interface/lcd/assets/focus_warning")
    except Exception as e:
        print(f"\n❌ process failed: {e}")
