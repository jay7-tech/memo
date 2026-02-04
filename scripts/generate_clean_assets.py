
import os
import math
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

# Config
# Config
TARGET_SIZE = (128, 128)
CANVAS_SIZE = (512, 512) # 4x Supersampling for Crisp Look
# Use relative path compatible with both Windows and Pi
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "interface", "lcd", "assets"))

# Palette (Clean Vector Aesthetic)
BG_COLOR = (20, 20, 25)       # Matte Dark
COLOR_EYE_FILL = (0, 255, 240)    # Cyan
COLOR_EYE_OUTLINE = (255, 255, 255) # White Stroke
COLOR_WARN_FILL = (255, 50, 80)   # Coral Red
COLOR_WARN_OUTLINE = (255, 200, 200) # Pale Pink
COLOR_FOCUS_FILL = (50, 150, 255) # Dodger Blue
WHITE = (255, 255, 255)

STROKE_WIDTH = 12

def ensure_clean_dir(name):
    path = os.path.join(ASSETS_DIR, name)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    return path

def draw_vector_eye(draw, cx, cy, w, h, fill, outline, mood='neutral'):
    # Base Shape
    # Mood mods
    
    if mood == 'angry':
        # Angry Eye: Flat top angle
        # Draw polygon or masked rect
        # Simply: Draw rect, clip top corners
        # Easier: Draw path
        
        # Points:
        # TL (inward/down), TR (outward/up) ? No angry is \ /
        # TL (low), TR (high)? No, angry is \ / so inner corners low, outer high.
        # Wait, usually angry is flat top slanted down inward.
        
        # Let's draw a rounded rect then overlay a "eyelid" triangle of BG color?
        # Better: Draw generic pill, then draw a thick "eyebrow" line blocking top.
        
        draw.rounded_rectangle([cx-w/2, cy-h/2, cx+w/2, cy+h/2], radius=40, fill=fill, outline=outline, width=STROKE_WIDTH)
        
        # Eyelid Slash
        # Draw a polygon in BG color to "cut" the eye
        # Left eye or Right eye? 
        # Assume this func draws ONE eye. Caller handles L/R distinction?
        # Actually this func is generic.
        # Let's assume standard pill for now.
        pass
    else:
        # Standard Pill
        draw.rounded_rectangle([cx-w/2, cy-h/2, cx+w/2, cy+h/2], radius=40, fill=fill, outline=outline, width=STROKE_WIDTH)
    
    # Shine / Specular
    shine_size = w * 0.25
    draw.ellipse([cx+w/4, cy-h/4, cx+w/4+shine_size, cy-h/4+shine_size], fill=(255,255,255))
    
def render_frame(func, idx, total, name_prefix):
    img = Image.new('RGB', CANVAS_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)
    func(draw, idx, total)
    img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    return img

# --- Animation Logic ---

def draw_idle(draw, i, total):
    # Breathing
    cycle = math.sin((i / total) * math.pi * 2) 
    
    # Scale: 1.0 to 1.1 (Big Clean Eyes)
    scale = 1.0 + (cycle * 0.05)
    
    # Bob: +/- 5px
    bob = cycle * 10
    
    w = 110 * scale
    h = 160 * scale
    
    y = 256 + bob
    
    # Left
    draw_vector_eye(draw, 180, y, w, h, COLOR_EYE_FILL, COLOR_EYE_OUTLINE)
    # Right
    draw_vector_eye(draw, 332, y, w, h, COLOR_EYE_FILL, COLOR_EYE_OUTLINE)

def draw_focus_scan(draw, i, total):
    # Looking Left <-> Right INTENTLY
    # Pos
    pan = math.sin((i/total)*math.pi*2) * 40
    
    # Eyes Squint a bit (Focus)
    w = 110
    h = 130 
    
    y = 256
    
    # Draw Eyes
    draw_vector_eye(draw, 180 + pan, y, w, h, COLOR_FOCUS_FILL, COLOR_EYE_OUTLINE)
    draw_vector_eye(draw, 332 + pan, y, w, h, COLOR_FOCUS_FILL, COLOR_EYE_OUTLINE)
    
    # HUD: Magnifying Glass Icon sweeping? or Brackets?
    # Simple Brackets
    margin = 50
    length = 60
    # TL
    draw.line([margin, margin, margin+length, margin], fill=COLOR_FOCUS_FILL, width=10)
    draw.line([margin, margin, margin, margin+length], fill=COLOR_FOCUS_FILL, width=10)
    # BR
    draw.line([512-margin, 512-margin, 512-margin-length, 512-margin], fill=COLOR_FOCUS_FILL, width=10)
    draw.line([512-margin, 512-margin, 512-margin, 512-margin-length], fill=COLOR_FOCUS_FILL, width=10)

def draw_focus_warn(draw, i, total):
    # Vibrating Angry Eyes
    import random
    shake = 0
    if i % 2 == 0: shake = random.randint(-5, 5)
    
    # Angry shape (manually drawing angry path)
    
    # Eyes
    y = 256 + shake
    lx = 180 + shake
    rx = 332 + shake
    w, h = 110, 140
    
    # Colors
    fill = COLOR_WARN_FILL
    outline = COLOR_WARN_OUTLINE
    
    # Left Eye (Angry Slice)
    # Base
    draw.rounded_rectangle([lx-w/2, y-h/2, lx+w/2, y+h/2], radius=40, fill=fill, outline=outline, width=STROKE_WIDTH)
    # Black Slash
    draw.polygon([(lx-w/2-20, y-h/2-20), (lx+w, y), (lx+w+20, y-h/2-50)], fill=BG_COLOR) # Slice top right
    
    # Right Eye
    draw.rounded_rectangle([rx-w/2, y-h/2, rx+w/2, y+h/2], radius=40, fill=fill, outline=outline, width=STROKE_WIDTH)
    
    # Icon: No Phone
    # Circle
    cx, cy = 256, 256
    r = 200
    # draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=COLOR_WARN_OUTLINE, width=10)
    
    # Floating "!"
    # Beat
    scale = 1.0 + (math.sin(i * 0.5) * 0.1)
    
    # draw !
    # Rect
    bw = 20 * scale
    bh = 100 * scale
    draw.rounded_rectangle([cx-bw/2, cy-bh, cx+bw/2, cy+bh/2], radius=10, fill=WHITE)
    draw.ellipse([cx-bw, cy+bh/2+10, cx+bw, cy+bh/2+10+bw*2], fill=WHITE)


def generate():
    print("Generating Clean Vector Assets...")
    
    # Idle
    d = ensure_clean_dir("idle_center")
    for i in range(60):
        img = render_frame(draw_idle, i, 60, "idle")
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    # Focus Scan
    d = ensure_clean_dir("focus_scan")
    for i in range(60):
        img = render_frame(draw_focus_scan, i, 60, "scan")
        img.save(os.path.join(d, f"frame_{i:03d}.png"))

    # Focus Warn
    d = ensure_clean_dir("focus_warning")
    for i in range(20):
        img = render_frame(draw_focus_warn, i, 20, "warn")
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    print("Done.")

if __name__ == "__main__":
    generate()
