
import os
import math
import shutil
import random
from PIL import Image, ImageDraw

# Config
# Config
TARGET_SIZE = (128, 128)
CANVAS_SIZE = (512, 512) 
# Use relative path compatible with both Windows and Pi
params_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "interface", "lcd", "assets"))
ASSETS_DIR = params_path

# Palette (High Contrast Modern)
BG_COLOR = (10, 10, 15)
COLOR_RED = (255, 50, 60) # Vibrant Red
COLOR_WHITE = (255, 255, 255)
COLOR_CYAN = (0, 255, 240)

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
    # Massive Squircle Eye (Idle Style)
    radius = min(w, h) * 0.4
    draw.rounded_rectangle([cx-w/2, cy-h/2, cx+w/2, cy+h/2], radius=radius, fill=fill)
    
    # Simple glint
    draw.rounded_rectangle([cx+w*0.2, cy-h*0.25, cx+w*0.35, cy-h*0.1], radius=10, fill=COLOR_WHITE)

def draw_clean_phone_symbol(draw, cx, cy, scale):
    # Modern Minimalist Phone
    # Hollow White Outline
    pw = 140 * scale
    ph = 240 * scale
    
    # Body
    draw.rounded_rectangle([cx-pw/2, cy-ph/2, cx+pw/2, cy+ph/2], radius=25*scale, outline=COLOR_WHITE, width=12)
    
    # Notch / Speaker / Button details (Minimal)
    # Home bar
    draw.line([cx-pw*0.3, cy+ph/2-15*scale, cx+pw*0.3, cy+ph/2-15*scale], fill=COLOR_WHITE, width=6)
    
    # Prohibition Symbol (Overlay)
    r = 160 * scale
    
    # Ring
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=COLOR_RED, width=20)
    
    # Slash (45 deg)
    # x = r * cos(45)
    delta = r * 0.707
    draw.line([cx-delta, cy-delta, cx+delta, cy+delta], fill=COLOR_RED, width=20)


def anim_final_option_a(draw, i, total):
    # Sequence:
    # 00-08: Eyes Shrink & Vanish (Pop out)
    # 08-10: Blank
    # 10-25: No Phone Symbol pops in and pulses
    # 25-30: Symbol fades or eyes start return? 
    # Let's keep symbol visible till end of loop to ensure readability if looped.
    
    # Transition
    t_vanish = 8
    t_appear = 10
    
    if i < t_vanish:
        # Vanish (Eased)
        # s starts 1.0, goes to 0.0
        prog = i / float(t_vanish)
        # Ease In Back (anticipation?) No just shrink fast
        s = 1.0 - (prog * prog) # Quadratic ease out
        if s < 0: s = 0
        
        w, h = 180*s, 240*s
        if w > 1:
            draw_vector_eye(draw, 140, 256, w, h, COLOR_CYAN)
            draw_vector_eye(draw, 372, 256, w, h, COLOR_CYAN)
            
    elif i >= t_appear:
        # Symbol Pop In
        anim_len = total - t_appear
        local_i = i - t_appear
        
        # Pop in spring
        # 0 -> 1.1 -> 1.0
        
        pop_dur = 6
        scale = 1.0
        
        if local_i < pop_dur:
            p = local_i / pop_dur
            scale = math.sin(p * math.pi * 0.7) * 1.1 # Overshoot slightly
        else:
            # Gentle pulsing while visible
            pulse_phase = (local_i - pop_dur) * 0.2
            scale = 1.0 + (math.sin(pulse_phase) * 0.03)
            
        draw_clean_phone_symbol(draw, 256, 256, scale)

def generate():
    print("Generating Final Warning (Clean Aesthetic)...")
    
    # Generate directly to focus_warning
    d = ensure_clean_dir("focus_warning")
    
    # 30 Frames @ 60ms = ~1.8s loop
    for i in range(30):
        render_frame(anim_final_option_a, i, 30).save(os.path.join(d, f"frame_{i:03d}.png"))
        
    print("Done. Clean Swap Applied.")

if __name__ == "__main__":
    generate()
