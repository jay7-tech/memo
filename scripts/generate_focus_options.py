
import os
import math
import shutil
import random
from PIL import Image, ImageDraw, ImageFont

# Config
# Config
TARGET_SIZE = (128, 128)
CANVAS_SIZE = (512, 512) 
# Use relative path compatible with both Windows and Pi
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "interface", "lcd", "assets"))

# Palette
BG_COLOR = (10, 10, 15)
COLOR_RED = (255, 40, 40)
COLOR_WHITE = (255, 255, 255)
COLOR_CYAN = (0, 255, 255)

def ensure_clean_dir(name):
    path = os.path.join(ASSETS_DIR, name)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    return path

def render_frame(func, idx, total):
    img = Image.new('RGB', CANVAS_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)
    func(draw, idx, total)
    img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    return img

def draw_vector_eye(draw, cx, cy, w, h, fill):
    # Standard Squircle Eye
    radius = min(w, h) * 0.4
    draw.rounded_rectangle([cx-w/2, cy-h/2, cx+w/2, cy+h/2], radius=radius, fill=fill)

def draw_no_phone_symbol(draw, cx, cy, scale):
    # Phone
    pw, ph = 100*scale, 160*scale
    draw.rounded_rectangle([cx-pw/2, cy-ph/2, cx+pw/2, cy+ph/2], radius=15*scale, outline=COLOR_WHITE, width=10)
    # Screen
    draw.rounded_rectangle([cx-pw/2+10, cy-ph/2+15, cx+pw/2-10, cy+ph/2-15], radius=5*scale, fill=COLOR_WHITE)
    
    # Red Circle
    r = 110 * scale
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=COLOR_RED, width=20)
    # Slash
    lx = r * 0.707
    draw.line([cx-lx, cy-lx, cx+lx, cy+lx], fill=COLOR_RED, width=20)


# --- OPTION A: CLEAN ICON (Eyes vanish) ---
def anim_opt_a(draw, i, total):
    # 0-5: Eyes shrink/vanish
    # 5-25: Icon Pulse
    # 25-30: Eyes return
    
    if i < 5:
        # Vanish
        s = 1.0 - (i/5.0)
        w, h = 180*s, 240*s
        draw_vector_eye(draw, 140, 256, w, h, COLOR_CYAN)
        draw_vector_eye(draw, 372, 256, w, h, COLOR_CYAN)
    elif i > 25:
        # Return
        s = (i-25)/5.0
        w, h = 180*s, 240*s
        draw_vector_eye(draw, 140, 256, w, h, COLOR_CYAN)
        draw_vector_eye(draw, 372, 256, w, h, COLOR_CYAN)
    else:
        # Icon
        pulse = math.sin(i * 0.5) * 0.1
        draw_no_phone_symbol(draw, 256, 256, 1.0 + pulse)

# --- OPTION B: SPLIT (Eyes move aside) ---
def anim_opt_b(draw, i, total):
    # Eyes slide to edges
    # Icon in center
    
    # Static layout for loop smoothness
    # Left Eye pushed left
    lx = 80
    rx = 512 - 80
    w, h = 120, 200 # Narrower eyes
    
    # Shake eyes (Angry)
    shake = random.randint(-2, 2)
    
    draw_vector_eye(draw, lx+shake, 256, w, h, COLOR_RED)
    draw_vector_eye(draw, rx+shake, 256, w, h, COLOR_RED)
    
    # Icon Center
    pulse = math.sin(i * 0.5) * 0.05
    draw_no_phone_symbol(draw, 256, 256, 0.8 + pulse)

# --- OPTION C: GLITCH TEXT (Cyber) ---
def anim_opt_c(draw, i, total):
    # Eyes are Red X
    # Text overlay "NO PHONE"
    
    # Draw X Eyes
    w, h = 180, 240
    shake = random.randint(-5, 5)
    
    # Eye 1 X
    cx, cy = 140+shake, 256
    lx = 100
    draw.line([cx-lx, cy-lx, cx+lx, cy+lx], fill=COLOR_RED, width=20)
    draw.line([cx+lx, cy-lx, cx-lx, cy+lx], fill=COLOR_RED, width=20)
    
    # Eye 2 X
    cx, cy = 372+shake, 256
    draw.line([cx-lx, cy-lx, cx+lx, cy+lx], fill=COLOR_RED, width=20)
    draw.line([cx+lx, cy-lx, cx-lx, cy+lx], fill=COLOR_RED, width=20)
    
    # Text Overlay ?
    # Just huge red X's might be stylish enough.
    # User asked for "No mobile symbol".
    # Let's draw a small phone icon being destroyed?
    
    # Let's stick to X eyes + Glitch blocks
    if i % 3 == 0:
        draw.rectangle([0, random.randint(0, 500), 512, random.randint(0, 500)], fill=COLOR_WHITE)


def generate():
    print("Generating Options...")
    
    # Option A
    d = ensure_clean_dir("focus_warning_opt_a")
    for i in range(30):
        render_frame(anim_opt_a, i, 30).save(os.path.join(d, f"frame_{i:03d}.png"))

    # Option B
    d = ensure_clean_dir("focus_warning_opt_b")
    for i in range(30):
        render_frame(anim_opt_b, i, 30).save(os.path.join(d, f"frame_{i:03d}.png"))
        
    print("Options Generated.")
    
    # Default to Option A (Cleanest)
    target = os.path.join(ASSETS_DIR, "focus_warning")
    if os.path.exists(target): shutil.rmtree(target)
    shutil.copytree(os.path.join(ASSETS_DIR, "focus_warning_opt_a"), target)
    print("Applied Option A as default.")

if __name__ == "__main__":
    generate()
