
import os
import math
import shutil
import random
from PIL import Image, ImageDraw, ImageOps

# Config
# Config
TARGET_SIZE = (128, 128)
CANVAS_SIZE = (512, 512) # 4x Supersampling
# Use relative path compatible with both Windows and Pi
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "interface", "lcd", "assets"))

# --- SAFETY CHECK ---
import sys
if os.path.exists(ASSETS_DIR):
    print(f"⚠️  WARNING: Asset directory exists at: {ASSETS_DIR}")
    print("Running this script will OVERWRITE your high-quality assets with generated ones.")
    response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
    if response.lower() != 'yes':
        print("Aborted.")
        sys.exit(0)
# --------------------

# Palette (Retro / Pop)
BG_COLOR = (240, 240, 245) # Off-White Background? Or keep Dark?
# User wants "Aesthetic Modern". Usually that implies Dark Mode for screens.
# But the reference image has white background.
# Let's stick to Dark BG for the LCD to blend with bezel, but use Bright Pop Colors.
BG_COLOR = (20, 20, 25) 
STROKE_COLOR = (255, 255, 255) # White strokes on dark BG looks "Neon Retro"
# OR Black strokes on Colored Eyes?
# Let's do: Colored Eyes with THICK BLACK OUTLINE, but since BG is dark, maybe White Outline?
# Review image: Black outlines.
# Let's try: White Eyes, Black Pupils, Thick White Outline for contrast against Dark BG?
# Or changing the eyes to be "Stickers" with White Border.

# Let's go with:
# Eye Fill: White (Idle)
# Pupil: Black
# Outline: Thick White (Outer Glow vibe) or Cyan?
# Let's match the image: Colorful.

COLOR_IDLE_FILL = (255, 255, 255) # White
COLOR_PUPIL = (0, 0, 0)
COLOR_SCAN_FILL = (255, 220, 0)   # Yellow (Lightning)
COLOR_WARN_FILL = (255, 80, 80)   # Red/Pink
COLOR_WARN_X = (40, 0, 0)         # Dark Red X

STROKE_WIDTH = 16

def ensure_clean_dir(name):
    path = os.path.join(ASSETS_DIR, name)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    return path

def draw_oval_eye(draw, cx, cy, w, h, pupil_x_off, pupil_y_off):
    # Retro Oval Eye
    # 1. White Sclera
    draw.ellipse([cx-w/2, cy-h/2, cx+w/2, cy+h/2], fill=COLOR_IDLE_FILL, outline=None)
    
    # 2. Pupil (Large Black Pie-Cut? Or just Oval?)
    # Reference shows standard oval pupils or Pacman.
    # Let's do standard large oval pupil.
    pw, ph = w*0.4, h*0.4
    px = cx + pupil_x_off
    py = cy + pupil_y_off
    draw.ellipse([px-pw/2, py-ph/2, px+pw/2, py+ph/2], fill=COLOR_PUPIL)
    
    # 3. Glint
    gw = pw * 0.3
    draw.ellipse([px+pw/4, py-ph/4, px+pw/4+gw, py-ph/4+gw], fill=(255, 255, 255))

def draw_lightning_eye(draw, cx, cy, scale):
    # Lightning Bolt Shape
    # Points relative to center
    w = 80 * scale
    h = 120 * scale
    
    # Zig-Zag path
    # Top-Right, Mid-Left, Mid-Right, Bottom-Left ...
    # Let's look at reference (Row 2 Col 1): Blocky Lightning
    
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
    # Line 1
    draw.line([cx-l/2, cy-l/2, cx+l/2, cy+l/2], fill=COLOR_WARN_X, width=int(th))
    # Line 2
    draw.line([cx+l/2, cy-l/2, cx-l/2, cy+l/2], fill=COLOR_WARN_X, width=int(th))


def render_frame(func, idx, total):
    img = Image.new('RGB', CANVAS_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)
    func(draw, idx, total)
    img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    return img

# --- Animations ---

def anim_idle(draw, i, total):
    # Breathing + Looking Around
    
    # Breathing Scale
    cycle = math.sin((i / total) * math.pi * 2) 
    scale = 1.0 + (cycle * 0.03)
    
    w = 100 * scale
    h = 140 * scale
    
    # Look Logic
    # 0-30: Look Center
    # 30-40: Look Right
    # 40-50: Look Left
    # 50-60: Center
    
    px, py = 0, 0
    if 30 <= i < 40:
        px = 15
    elif 40 <= i < 50:
        px = -15
        
    y = 256
    
    draw_oval_eye(draw, 180, y, w, h, px, py)
    draw_oval_eye(draw, 332, y, w, h, px, py)

def anim_scan(draw, i, total):
    # Lightning Pulsing
    pulse = math.sin((i/total) * math.pi * 4) # Fast pulse
    scale = 1.0 + (pulse * 0.1)
    
    # Color Cycle? Yellow -> White
    
    draw_lightning_eye(draw, 180, 256, scale)
    draw_lightning_eye(draw, 332, 256, scale)

def anim_warn(draw, i, total):
    # X Eyes shaking
    shake_x = random.randint(-3, 3) 
    shake_y = random.randint(-3, 3)
    
    scale = 1.0 + (math.sin(i*0.5)*0.05)
    
    draw_x_eye(draw, 180+shake_x, 256+shake_y, scale)
    draw_x_eye(draw, 332+shake_x, 256+shake_y, scale)


def generate():
    print("Generating Retro Vector Assets...")
    
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
        
    print("Done.")

if __name__ == "__main__":
    generate()
