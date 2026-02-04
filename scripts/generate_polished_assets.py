
import os
import math
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops

# Config
TARGET_SIZE = (128, 128)
ASSETS_DIR = r"c:\Users\JAYADEEP GOWDA K B\Desktop\MEMO\interface\lcd\assets"

# Palette (Consistent with Original)
COLOR_CORE = (220, 255, 255)   # Bright Center
COLOR_IDLE = (0, 255, 180)     # Cyan
COLOR_FOCUS = (0, 150, 255)    # Deep Blue
COLOR_WARN = (255, 50, 0)      # Orange/Red
COLOR_BG = (0, 0, 0)

def ensure_clean_dir(name):
    path = os.path.join(ASSETS_DIR, name)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    return path

def draw_squircle(draw, bounds, radius, fill):
    draw.rounded_rectangle(bounds, radius=radius, fill=fill)

def create_glow_eye(size, eye_bbox, core_color, glow_color, opacity=1.0, eyelid_h=0.0):
    # Supersampling factor
    scale = 4
    w, h = size[0]*scale, size[1]*scale
    ex, ey, ew, eh = [v*scale for v in eye_bbox]
    
    # 1. Glow Layer (Blurred)
    glow = Image.new("RGBA", (w, h), (0,0,0,0))
    g_draw = ImageDraw.Draw(glow)
    draw_squircle(g_draw, [ex, ey, ex+ew, ey+eh], radius=ew//3, fill=(*glow_color, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(12*scale)) # Soft glow
    
    # 2. Outer Rim (Semi-Sharp)
    rim = Image.new("RGBA", (w, h), (0,0,0,0))
    r_draw = ImageDraw.Draw(rim)
    # Slightly larger than core
    draw_squircle(r_draw, [ex-2*scale, ey-2*scale, ex+ew+2*scale, ey+eh+2*scale], radius=ew//3, fill=(*glow_color, 150))
    rim = rim.filter(ImageFilter.GaussianBlur(4*scale))

    # 3. Core Layer (Sharp White-ish)
    core = Image.new("RGBA", (w, h), (0,0,0,0))
    c_draw = ImageDraw.Draw(core)
    # Inset slightly
    draw_squircle(c_draw, [ex+4*scale, ey+4*scale, ex+ew-4*scale, ey+eh-4*scale], radius=ew//3, fill=(*core_color, 255))
    
    # Composite
    final = Image.new("RGBA", (w, h), (0,0,0,0))
    final.alpha_composite(glow)
    final.alpha_composite(rim)
    final.alpha_composite(core)
    
    # Eyelid Mask logic
    if eyelid_h > 0:
        # Create mask
        mask = Image.new("RGBA", (w, h), (0,0,0,0))
        m_draw = ImageDraw.Draw(mask)
        
        # Black rect covering top part
        lid_y = ey + (eh * eyelid_h)
        # Draw from top (-h) to lid_y
        m_draw.rectangle([-w, -h, w*2, lid_y], fill=(0,0,0,255))
        
        # We want to ERASE the eye where the lid is.
        # But here 'final' has transparent background.
        # If we composite black on it, it becomes black. 
        # Since we output RGB on black eventually, this works.
        final.alpha_composite(mask)
        
    # Resize
    final = final.resize(size, resample=Image.Resampling.LANCZOS)
    
    # Global Opacity
    if opacity < 1.0:
        r, g, b, a = final.split()
        a = a.point(lambda p: p * opacity)
        final = Image.merge("RGBA", (r, g, b, a))
        
    return final.convert("RGB")

def render_sequence(name, func, frames=30):
    print(f"Rendering {name}...")
    out_dir = ensure_clean_dir(name)
    for i in range(frames):
        img = func(i, frames)
        img.save(os.path.join(out_dir, f"frame_{i:03d}.png"))

# --- Animations ---

def anim_idle_breathing(i, total):
    # Smooth Sine Breathing
    pulse = math.sin((i / total) * math.pi * 2) 
    
    # Scale: +/- 5%
    scale = 1.0 + (pulse * 0.05)
    
    # Opacity: Pulse brightness too
    op = 0.9 + (pulse * 0.1)
    
    # Bob: +/- 2px
    bob_y = pulse * 2.0
    
    # Base Box: (20, 44, 34, 40)
    w = 34 * scale
    h = 40 * scale
    
    # Center points (original centers)
    lx_c = 20 + 17
    ly_c = 44 + 20 + bob_y
    rx_c = 74 + 17
    ry_c = 44 + 20 + bob_y
    
    # Calc new bbox
    l_box = (lx_c - w/2, ly_c - h/2, w, h)
    r_box = (rx_c - w/2, ry_c - h/2, w, h)
    
    # Draw
    l_img = create_glow_eye(TARGET_SIZE, l_box, COLOR_CORE, COLOR_IDLE, opacity=op)
    r_img = create_glow_eye(TARGET_SIZE, r_box, COLOR_CORE, COLOR_IDLE, opacity=op)
    
    return ImageChops.add(l_img, r_img)

def anim_focus_scan(i, total):
    # Searching Look (Left <-> Right) + Pulsing Blue
    
    # Movement: Slow Pan
    # Sine wave for X offset
    scan_x = math.sin((i / total) * math.pi * 2) * 10
    
    # Scale Pulse (Faster "Processing" throb)
    pulse = math.sin((i / total) * math.pi * 4) # 2 pulses per loop
    scale = 1.0 + (pulse * 0.03)
    
    w = 34 * scale
    h = 40 * scale # Squint slightly relative to idle? No, wide open for scanning
    
    base_y = 44
    
    l_box = (20 + scan_x, base_y, w, h)
    r_box = (74 + scan_x, base_y, w, h)
    
    # Color: FOCUS BLUE
    l_img = create_glow_eye(TARGET_SIZE, l_box, COLOR_CORE, COLOR_FOCUS)
    r_img = create_glow_eye(TARGET_SIZE, r_box, COLOR_CORE, COLOR_FOCUS)
    
    return ImageChops.add(l_img, r_img)

def anim_focus_warning(i, total):
    # Red/Orange + Angry Squint + Shake
    
    # Shake (Random vibration)
    import random
    shake_x = random.randint(-2, 2) if i % 2 == 0 else 0
    shake_y = random.randint(-1, 1) if i % 2 == 0 else 0
    
    # Throb opacity
    pulse = math.sin((i/total)*math.pi*4)
    op = 0.9 + (pulse * 0.1)
    
    # Squint (Eyelid)
    lid = 0.4 # 40% closed from top
    
    # Same base pos + shake
    l_box = (20 + shake_x, 44 + shake_y, 34, 40)
    r_box = (74 + shake_x, 44 + shake_y, 34, 40)
    
    l_img = create_glow_eye(TARGET_SIZE, l_box, COLOR_CORE, COLOR_WARN, opacity=op, eyelid_h=lid)
    r_img = create_glow_eye(TARGET_SIZE, r_box, COLOR_CORE, COLOR_WARN, opacity=op, eyelid_h=lid)
    
    # Add a "!" symbol?
    # Let's keep it minimalist first. The red angry eyes are usually clear enough.
    # Text "NO" maybe?
    # Let's draw a simple "!" in the center between eyes
    
    combined = ImageChops.add(l_img, r_img)
    
    # Draw '!'
    d = ImageDraw.Draw(combined)
    # Center X = 64
    d.rounded_rectangle([62, 30, 66, 70], radius=2, fill=COLOR_WARN)
    d.rounded_rectangle([62, 75, 66, 79], radius=2, fill=COLOR_WARN)
    
    return combined

if __name__ == "__main__":
    generate_scan = True
    generate_idle = True
    generate_warn = True
    
    render_sequence("idle_center", anim_idle_breathing, 60)
    render_sequence("focus_scan", anim_focus_scan, 60)
    render_sequence("focus_warning", anim_focus_warning, 20) # Faster loop
    
    print("Polished Assets Generated.")
