
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

def render_frame_with_glow(func, idx, total):
    # Setup RGBA for Glow
    img = Image.new('RGBA', CANVAS_SIZE, (10, 10, 15, 255))
    
    # 1. Glow Layer
    glow_layer = Image.new('RGBA', CANVAS_SIZE, (0,0,0,0))
    g_draw = ImageDraw.Draw(glow_layer)
    func(g_draw, idx, total, layer='glow')
    
    # Blur Glow
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(20))
    
    # 2. Core Layer
    core_layer = Image.new('RGBA', CANVAS_SIZE, (0,0,0,0))
    c_draw = ImageDraw.Draw(core_layer)
    func(c_draw, idx, total, layer='core')
    
    # Composite
    img = Image.alpha_composite(img, glow_layer)
    img = Image.alpha_composite(img, core_layer)
    
    # Resize
    img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    return img.convert('RGB')

# --- Animation Functions adapted for Layers ---

def anim_idle(draw, i, total, layer='core'):
    # Breathing scale
    cycle = math.sin((i / total) * math.pi * 2) 
    scale = 1.0 + (cycle * 0.02)
    
    w = 180 * scale
    h = 240 * scale 
    y = 256
    
    fill = COLOR_CYAN
    if layer == 'glow':
        fill = (0, 255, 255, 100) # Semi-transp/Darker Cyan for glow
        # Draw slightly larger for glow?
        w += 20
        h += 20
    else:
        fill = (0, 255, 255, 255)
        
    draw_vector_eye(draw, 140, y, w, h, fill, mood='neutral')
    draw_vector_eye(draw, 372, y, w, h, fill, mood='neutral')

def anim_scan(draw, i, total, layer='core'):
    pan = math.sin((i/total)*math.pi*2) * 30
    w = 180
    h = 200
    y = 256
    
    fill = COLOR_BLUE
    if layer == 'glow':
        fill = (0, 120, 255, 100)
        w += 20
        h += 20
    else:
        fill = (0, 120, 255, 255)

    draw_vector_eye(draw, 140+pan, y, w, h, fill, mood='scan')
    draw_vector_eye(draw, 372+pan, y, w, h, fill, mood='scan')
    
    # HUD (Only on core)
    if layer == 'core':
        m = 20
        l = 40
        draw.line([m, m, m+l, m], fill=(0, 120, 255, 255), width=8) 
        draw.line([m, m, m, m+l], fill=(0, 120, 255, 255), width=8)
        draw.line([512-m, 512-m, 512-m-l, 512-m], fill=(0, 120, 255, 255), width=8)
        draw.line([512-m, 512-m, 512-m, 512-m-l], fill=(0, 120, 255, 255), width=8)

def draw_no_phone_icon(draw, cx, cy, scale, fill):
    # Phone Body
    pw, ph = 60*scale, 100*scale
    draw.rounded_rectangle([cx-pw/2, cy-ph/2, cx+pw/2, cy+ph/2], radius=10*scale, fill=None, outline=fill, width=8)
    # Screen (Solid)
    draw.rounded_rectangle([cx-pw/2+8, cy-ph/2+8, cx+pw/2-8, cy+ph/2-8], radius=5*scale, fill=fill)
    
    # Prohibit
    r = 70 * scale
    # Circle
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=COLOR_RED, width=10)
    # Slash
    # 45 deg line
    lx = r * 0.707
    draw.line([cx-lx, cy-lx, cx+lx, cy+lx], fill=COLOR_RED, width=10)

def anim_warn(draw, i, total, layer='core'):
    shake = random.randint(-2, 2) if i%2==0 else 0
    w = 180
    h = 220
    y = 256 + shake
    
    # Eyes (Bg) - Angry Red
    fill = COLOR_RED
    if layer == 'glow':
        fill = (255, 40, 40, 80) # Dimmers for glow
        w += 20
        h += 20
    else:
        fill = (255, 40, 40, 255)
        
    draw_vector_eye(draw, 140+shake, y, w, h, fill, mood='angry')
    draw_vector_eye(draw, 372+shake, y, w, h, fill, mood='angry')
    
    # Overlay Icon
    if layer == 'core':
        pulse = (math.sin(i*0.5)+1)*0.5 # 0-1
        scale = 1.0 + pulse * 0.1
        
        # Draw No Phone
        # White Phone, Red Slash
        draw_no_phone_icon(draw, 256, 256, scale, COLOR_WHITE)

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
        
    print("Done.")

if __name__ == "__main__":
    generate()
