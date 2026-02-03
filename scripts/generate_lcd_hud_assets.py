import os
import math
from PIL import Image, ImageDraw, ImageFont

# High Resolution Source -> Downscale for AA (Super Sampling)
SRC_SIZE = (512, 512)
OUT_SIZE = (128, 128)
ASSETS_DIR = "interface/lcd/assets"

# THEME COLORS
# Neon Cyan
C_NEON = (0, 255, 255)
C_NEON_DIM = (0, 100, 100)
# Danger Red
C_WARN = (255, 20, 20)
C_WARN_DIM = (100, 10, 10)
# Void
C_BLACK = (0, 0, 0)
C_WHITE = (255, 255, 255)

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def save_frames(name, frames):
    path = os.path.join(ASSETS_DIR, name)
    ensure_dir(path)
    for i, img in enumerate(frames):
        # Resize with LANCZOS for Anti-Aliasing
        if img.size != OUT_SIZE:
            img = img.resize(OUT_SIZE, Image.Resampling.LANCZOS)
        img.save(os.path.join(path, f"frame_{i:03d}.png"))
    print(f"Generated {name} ({len(frames)} frames)")

def draw_hud_ring(draw, cx, cy, r, width, color, start_ang=0, end_ang=360):
    draw.arc([cx-r, cy-r, cx+r, cy+r], start=start_ang, end=end_ang, fill=color, width=width)

# --- 1. Focus Mode (Replaced "Police" with "Iron Man HUD") ---
# The folder name stays 'focus_police' to match manager.py, but the look is pure sci-fi.
def gen_focus_hud():
    frames = []
    cx, cy = 256, 256
    
    for i in range(20): 
        img = Image.new('RGB', SRC_SIZE, C_BLACK)
        draw = ImageDraw.Draw(img)
        
        # 1. Rotating Outer Ring
        angle_off = i * 18
        draw_hud_ring(draw, cx, cy, 240, 10, C_NEON_DIM, angle_off, angle_off+90)
        draw_hud_ring(draw, cx, cy, 240, 10, C_NEON_DIM, angle_off+180, angle_off+270)
        
        # 2. Pulsing Inner Circle (Breathing)
        pulse = (math.sin(i * 0.5) + 1) * 0.5 # 0 to 1
        r_inner = 100 + (pulse * 20)
        draw.ellipse([cx-r_inner, cy-r_inner, cx+r_inner, cy+r_inner], outline=C_NEON, width=8)
        
        # 3. Center Target Dot
        draw.ellipse([cx-10, cy-10, cx+10, cy+10], fill=C_NEON)
        
        # 4. Scanning Line
        y_scan = 100 + (i * 15) % 312
        draw.line([100, y_scan, 412, y_scan], fill=(0, 255, 255, 128), width=2)
        
        frames.append(img)
    
    save_frames("focus_police", frames)

# --- 2. Distraction (Replaced with "WARNING HUD") ---
def gen_distraction_hud():
    frames = []
    
    for i in range(10):
        img = Image.new('RGB', SRC_SIZE, C_BLACK)
        draw = ImageDraw.Draw(img)
        
        # Flashing Border
        if i % 2 == 0:
            border_c = C_WARN
            draw.rectangle([10, 10, 502, 502], outline=C_WARN, width=20)
        else:
            border_c = C_WARN_DIM
            draw.rectangle([10, 10, 502, 502], outline=C_WARN_DIM, width=10)
        
        # Triangle Warning
        draw.polygon([(256, 100), (456, 400), (56, 400)], outline=C_WARN, width=15)
        
        # Exclamation Mark
        draw.rectangle([240, 180, 272, 300], fill=C_WARN)
        draw.rectangle([240, 330, 272, 360], fill=C_WARN)
        
        frames.append(img)
        
    save_frames("distraction", frames)

# --- 3. Selfie (Sci-Fi Shutter) ---
def gen_selfie_hud():
    frames = []
    cx, cy = 256, 256
    
    # Lock phases
    for i in range(10):
        img = Image.new('RGB', SRC_SIZE, C_BLACK)
        draw = ImageDraw.Draw(img)
        
        # 4 Brackets closing in
        offset = 200 - (i * 15)
        # TL
        draw.line([(cx-offset, cy-offset), (cx-offset+50, cy-offset)], fill=C_WHITE, width=10)
        draw.line([(cx-offset, cy-offset), (cx-offset, cy-offset+50)], fill=C_WHITE, width=10)
        # TR
        draw.line([(cx+offset, cy-offset), (cx+offset-50, cy-offset)], fill=C_WHITE, width=10)
        draw.line([(cx+offset, cy-offset), (cx+offset, cy-offset+50)], fill=C_WHITE, width=10)
        # BL
        draw.line([(cx-offset, cy+offset), (cx-offset+50, cy+offset)], fill=C_WHITE, width=10)
        draw.line([(cx-offset, cy+offset), (cx-offset, cy+offset-50)], fill=C_WHITE, width=10)
        # BR
        draw.line([(cx+offset, cy+offset), (cx+offset-50, cy+offset)], fill=C_WHITE, width=10)
        draw.line([(cx+offset, cy+offset), (cx+offset, cy+offset-50)], fill=C_WHITE, width=10)
        
        frames.append(img)

    # Flash
    white = Image.new('RGB', SRC_SIZE, C_WHITE)
    frames.append(white)
    frames.append(white)
    
    save_frames("selfie_cam", frames)

if __name__ == "__main__":
    gen_focus_hud()
    gen_distraction_hud()
    gen_selfie_hud()
    print("Done (HUD Style).")
