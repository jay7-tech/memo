
import os
import math
import shutil
import random
from PIL import Image, ImageDraw

# --- CONFIG ---
TARGET_SIZE = (128, 128)
CANVAS_SIZE = (512, 512) # 4x Supersampling for smoothness

# Define Assets Path (Relative to script execution root)
# Assumes running from project root: python3 scripts/fix_assets.py
ASSETS_DIR = os.path.abspath("interface/lcd/assets")

# Check if we are inside scripts folder
if os.getcwd().endswith("scripts"):
    ASSETS_DIR = os.path.abspath("../interface/lcd/assets")

print(f"Target Assets Directory: {ASSETS_DIR}")

# --- PALETTE (RETRO VECTOR) ---
BG_COLOR = (20, 20, 25) 
COLOR_IDLE_FILL = (255, 255, 255) # White
COLOR_PUPIL = (0, 0, 0)
COLOR_SCAN_FILL = (255, 220, 0)   # Yellow (Lightning)
COLOR_WARN_FILL = (255, 80, 80)   # Red/Pink
COLOR_WARN_X = (40, 0, 0)         # Dark Red X

def ensure_clean_dir(name):
    path = os.path.join(ASSETS_DIR, name)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    return path

def draw_oval_eye(draw, cx, cy, w, h, pupil_x_off, pupil_y_off):
    # Retro Oval Eye
    draw.ellipse([cx-w/2, cy-h/2, cx+w/2, cy+h/2], fill=COLOR_IDLE_FILL, outline=None)
    
    # Pupil
    pw, ph = w*0.4, h*0.4
    px = cx + pupil_x_off
    py = cy + pupil_y_off
    draw.ellipse([px-pw/2, py-ph/2, px+pw/2, py+ph/2], fill=COLOR_PUPIL)
    
    # Glint
    gw = pw * 0.3
    draw.ellipse([px+pw/4, py-ph/4, px+pw/4+gw, py-ph/4+gw], fill=(255, 255, 255))

def draw_lightning_eye(draw, cx, cy, scale):
    w = 80 * scale
    h = 120 * scale
    points = [
        (cx + w*0.2, cy - h*0.5), # Top 
        (cx + w*0.5, cy - h*0.5), # Top R
        (cx + w*0.1, cy + h*0.1), # Mid R
        (cx + w*0.4, cy + h*0.1), # Spur R
        (cx - w*0.2, cy + h*0.5), # Bottom Tip
        (cx - w*0.1, cy - h*0.1), # Mid L
        (cx - w*0.4, cy - h*0.1), # Spur L
    ]
    draw.polygon(points, fill=COLOR_SCAN_FILL)

def draw_x_eye(draw, cx, cy, scale):
    # Round Eye Base
    w, h = 100*scale, 100*scale
    draw.ellipse([cx-w/2, cy-h/2, cx+w/2, cy+h/2], fill=COLOR_WARN_FILL)
    
    # Big X
    th = 15 * scale
    l = w * 0.6
    draw.line([cx-l/2, cy-l/2, cx+l/2, cy+l/2], fill=COLOR_WARN_X, width=int(th))
    draw.line([cx+l/2, cy-l/2, cx-l/2, cy+l/2], fill=COLOR_WARN_X, width=int(th))

def render_frame(func, idx, total):
    img = Image.new('RGB', CANVAS_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)
    func(draw, idx, total)
    img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    return img

# --- Animations ---
def anim_idle(draw, i, total):
    cycle = math.sin((i / total) * math.pi * 2) 
    scale = 1.0 + (cycle * 0.03)
    w = 100 * scale
    h = 140 * scale
    px, py = 0, 0
    if 30 <= i < 40: px = 15
    elif 40 <= i < 50: px = -15
    y = 256
    draw_oval_eye(draw, 180, y, w, h, px, py)
    draw_oval_eye(draw, 332, y, w, h, px, py)

def anim_scan(draw, i, total):
    pulse = math.sin((i/total) * math.pi * 4) # Fast pulse
    scale = 1.0 + (pulse * 0.1)
    draw_lightning_eye(draw, 180, 256, scale)
    draw_lightning_eye(draw, 332, 256, scale)

def anim_warn(draw, i, total):
    shake_x = random.randint(-3, 3) 
    shake_y = random.randint(-3, 3)
    scale = 1.0 + (math.sin(i*0.5)*0.05)
    draw_x_eye(draw, 180+shake_x, 256+shake_y, scale)
    draw_x_eye(draw, 332+shake_x, 256+shake_y, scale)

def generate():
    print("Generating Retro Vector Assets (Aesthetic Version)...")
    
    # Idle
    d = ensure_clean_dir("idle_center")
    for i in range(60):
        img = render_frame(anim_idle, i, 60)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    # Scan
    d = ensure_clean_dir("focus_scan")
    for i in range(30):
        img = render_frame(anim_scan, i, 30)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    # Warn
    d = ensure_clean_dir("focus_warning")
    for i in range(20):
        img = render_frame(anim_warn, i, 20)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    print("\n✅ Success! Aesthetic Assets Generated.")

if __name__ == "__main__":
    generate()
