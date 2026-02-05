
import os
import math
import shutil
import random
from PIL import Image, ImageDraw, ImageFilter

# Config
# Config
TARGET_SIZE = (128, 128)
CANVAS_SIZE = (512, 512) # 4x Supersampling
# Use relative path compatible with both Windows and Pi
params_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "interface", "lcd", "assets"))
ASSETS_DIR = params_path

# Palette (Ultimate Aesthetic)
BG_COLOR = (10, 10, 15)       # Almost Black
COLOR_CYAN = (0, 255, 255)      # Cyber Cyan
COLOR_BLUE = (0, 120, 255)      # Deep Blue
COLOR_RED = (255, 40, 40)       # Alert Red
COLOR_WHITE = (255, 255, 255) 

# Styles
STROKE_WIDTH = 16 

def ensure_clean_dir(name):
    path = os.path.join(ASSETS_DIR, name)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    return path

def draw_eye_shape(draw, cx, cy, w, h, fill, radius):
    draw.rounded_rectangle([cx-w/2, cy-h/2, cx+w/2, cy+h/2], radius=radius, fill=fill)

def draw_vector_eye(draw, cx, cy, w, h, fill, mood='neutral', glow=False):
    radius = min(w, h) * 0.4
    
    # 1. Glow Layer (Optional)
    if glow:
        # We need to draw on a temp buffer to blur
        # But `draw` is directly on the main image.
        # We can simulate glow by drawing a larger, transparent rect? 
        # No, PIL draw doesn't support alpha blending on RGB directly easily without new images.
        # Given this is a frame generator, we can afford to make temp images.
        # But refactoring `render_frame` to pass `img` instead of `draw` is needed.
        # Or simpler: Just draw a bigger darker rect behind?
        # A true blur is better.
        pass # Handle in caller or change architecture.
        # Let's keep smooth vector for now, user said "add a bit glow very little".
        # We can approximate with a semi-transparent stroke if we had alpha.
    
    # Draw logic matches previous
    if mood == 'angry':
        draw.rounded_rectangle([cx-w/2, cy-h/2 + h*0.2, cx+w/2, cy+h/2], radius=radius, fill=fill)
    elif mood == 'scan':
        draw.rounded_rectangle([cx-w/2, cy-h/2, cx+w/2, cy+h/2], radius=radius, fill=fill)
        draw.line([cx-w/2+10, cy, cx+w/2-10, cy], fill=BG_COLOR, width=8)
    else: # Neutral
        draw.rounded_rectangle([cx-w/2, cy-h/2, cx+w/2, cy+h/2], radius=radius, fill=fill)
    
    # Glint
    gw = w * 0.25
    gh = h * 0.15
    gx = cx + w*0.25
    gy = cy - h*0.25
    draw.rounded_rectangle([gx, gy, gx+gw, gy+gh], radius=5, fill=COLOR_WHITE)

def draw_heart(draw, cx, cy, size, fill):
    # Simple Heart Shape
    # 2 circles + triangle
    r = size // 2
    draw.pieslice([cx-size, cy-size, cx, cy], 180, 0, fill=fill)
    draw.pieslice([cx, cy-size, cx+size, cy], 180, 0, fill=fill)
    # Bottom triangle
    # This is rough, let's use polygon for cleaner look
    draw.polygon([
        (cx-size, cy-r),
        (cx+size, cy-r),
        (cx, cy+size)
    ], fill=fill)
    # Circles again to cover top flat part of triangle
    draw.pieslice([cx-size, cy-size, cx, cy], 180, 0, fill=fill)
    draw.pieslice([cx, cy-size, cx+size, cy], 180, 0, fill=fill)

def draw_mute_icon(draw, cx, cy, scale, fill):
    # Mic
    mw, mh = 40*scale, 70*scale
    draw.rounded_rectangle([cx-mw/2, cy-mh/2, cx+mw/2, cy+mh/2], radius=15*scale, fill=None, outline=fill, width=6)
    draw.rectangle([cx-mw/2+4, cy-mh/2+4, cx+mw/2-4, cy+mh/2-4], fill=fill) # Fill mic body
    
    # Stand
    draw.line([cx, cy+mh/2, cx, cy+mh/2+15*scale], fill=fill, width=6)
    draw.line([cx-20*scale, cy+mh/2+15*scale, cx+20*scale, cy+mh/2+15*scale], fill=fill, width=6)
    
    # Slash (Red)
    r = 50 * scale
    draw.line([cx-r, cy-r, cx+r, cy+r], fill=COLOR_RED, width=8)

# --- NEW ANIMATIONS ---

def anim_silence(draw, i, total, layer='core'):
    # Neutral eyes + Mute Icon
    w = 180
    h = 240
    fill = COLOR_CYAN
    if layer == 'glow': fill = (0, 255, 255, 100); w+=20; h+=20;
    else: fill = (0, 255, 255, 255)
    
    # Dimmer eyes
    draw_vector_eye(draw, 140, 256, w, h, fill)
    draw_vector_eye(draw, 372, 256, w, h, fill)
    
    if layer == 'core':
        draw_mute_icon(draw, 256, 256, 1.2, COLOR_WHITE)

def anim_happy(draw, i, total, layer='core'):
    # Bouncing
    bounce = math.abs(math.sin((i/total) * math.pi * 2)) * 20
    y = 256 - bounce
    w = 180
    h = 240
    
    fill = COLOR_CYAN
    if layer == 'glow': fill = (0, 255, 255, 100); w+=20; h+=20;
    else: fill = (0, 255, 255, 255)

    # Happy Eyes = Arc? Or just normal for now
    # Let's draw inverted arch for "smiling eyes" effect -> Actually just squinting bottom
    # Simulating by drawing full eye then covering bottom? No, just draw smaller height
    
    h_happy = h * 0.6
    draw_vector_eye(draw, 140, y, w, h_happy, fill)
    draw_vector_eye(draw, 372, y, w, h_happy, fill)

def anim_love(draw, i, total, layer='core'):
    # Heart Eyes Pulse
    pulse = math.sin((i/total) * math.pi * 2) * 0.1 + 1.0 # 0.9 - 1.1
    size = 70 * pulse
    
    fill = (255, 105, 180) # Hot Pink
    if layer == 'glow': fill = (255, 105, 180, 100); size+=5
    else: fill = (255, 105, 180, 255)

    draw_heart(draw, 140, 256, size, fill)
    draw_heart(draw, 372, 256, size, fill)

def anim_sad(draw, i, total, layer='core'):
    # Looking down
    droop = (i / total) * 10
    y = 256 + 20
    w = 180
    h = 200 # Squinted slightly
    
    fill = COLOR_BLUE # Sad Blue
    if layer == 'glow': fill = (0, 120, 255, 100); w+=20; h+=20;
    else: fill = (0, 120, 255, 255)
    
    draw_vector_eye(draw, 140, y, w, h, fill)
    draw_vector_eye(draw, 372, y, w, h, fill)

def anim_surprised(draw, i, total, layer='core'):
    # Shaking small amplitude
    shake = random.randint(-5, 5)
    w = 200 # Wider
    h = 280 # Taller
    
    fill = COLOR_CYAN
    if layer == 'glow': fill = (0, 255, 255, 100); w+=20; h+=20;
    else: fill = (0, 255, 255, 255)

    draw_vector_eye(draw, 140+shake, 256+shake, w, h, fill)
    draw_vector_eye(draw, 372+shake, 256+shake, w, h, fill)

def anim_confused(draw, i, total, layer='core'):
    # One eye normal, one eye small/raised
    w = 180
    h = 240
    
    fill = COLOR_CYAN
    if layer == 'glow': fill = (0, 255, 255, 100); w+=20; h+=20;
    else: fill = (0, 255, 255, 255)
    
    # Left Normal
    draw_vector_eye(draw, 140, 256, w, h, fill)
    
    # Right Squinted & Raised
    draw_vector_eye(draw, 372, 230, w, h*0.6, fill)

def generate():
    print("Generating Glow-Enhanced Ultimate Assets...")
    
    d = ensure_clean_dir("idle_center")
    for i in range(60):
        img = render_frame_with_glow(anim_idle, i, 60)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    d = ensure_clean_dir("focus_scan")
    for i in range(60):
        img = render_frame_with_glow(anim_scan, i, 60)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    d = ensure_clean_dir("focus_warning")
    for i in range(20):
        img = render_frame_with_glow(anim_warn, i, 20)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    d = ensure_clean_dir("thinking")
    for i in range(30):
        img = render_frame_with_glow(anim_thinking, i, 30)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    d = ensure_clean_dir("listening")
    for i in range(20):
        img = render_frame_with_glow(anim_listening, i, 20)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    d = ensure_clean_dir("blink")
    for i in range(30):
        img = render_frame_with_glow(anim_blink, i, 30)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    d = ensure_clean_dir("wink")
    for i in range(20): # Short
        img = render_frame_with_glow(anim_wink, i, 20)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    # --- NEW ---
    d = ensure_clean_dir("silence")
    for i in range(1): # Static
        img = render_frame_with_glow(anim_silence, i, 1)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    d = ensure_clean_dir("happy")
    for i in range(30):
        img = render_frame_with_glow(anim_happy, i, 30)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))
        
    d = ensure_clean_dir("love")
    for i in range(30):
        img = render_frame_with_glow(anim_love, i, 30)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))

    d = ensure_clean_dir("sad")
    for i in range(30):
        img = render_frame_with_glow(anim_sad, i, 30)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))

    d = ensure_clean_dir("surprised")
    for i in range(20):
        img = render_frame_with_glow(anim_surprised, i, 20)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))

    d = ensure_clean_dir("confused")
    for i in range(1): # Static-ish
        img = render_frame_with_glow(anim_confused, i, 1)
        img.save(os.path.join(d, f"frame_{i:03d}.png"))

    print("Done.")

if __name__ == "__main__":
    generate()

if __name__ == "__main__":
    generate()
