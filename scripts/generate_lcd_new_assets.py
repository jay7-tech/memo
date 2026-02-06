import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# High Resolution Source -> Downscale for AA (Super Sampling)
SRC_SIZE = (512, 512)
OUT_SIZE = (128, 128)
ASSETS_DIR = "interface/lcd/assets"

# --- SAFETY CHECK ---
import sys
# Ensure absolute path for safety check just in case
abs_asset_path = os.path.abspath(ASSETS_DIR)
if os.path.exists(abs_asset_path):
    print(f"⚠️  WARNING: Asset directory exists at: {abs_asset_path}")
    print("Running this script will OVERWRITE your high-quality assets with generated ones.")
    response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
    if response.lower() != 'yes':
        print("Aborted.")
        sys.exit(0)
# --------------------

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

# --- COLORS (Cyberpunk / Vector Theme) ---
C_BG_BLUE = (10, 20, 40)
C_BG_RED = (40, 10, 10)
C_CYAN = (0, 255, 255)
C_RED = (255, 50, 50)
C_WHITE = (255, 255, 255)
C_BLACK = (0, 0, 0)
C_GREY = (50, 50, 50)

# --- 1. Focus Mode (Police/Serious) ---
def gen_focus_police():
    frames = []
    # Vector Style: Thick strokes, clean shapes
    
    for i in range(12): 
        # Create High-Res Canvas
        img = Image.new('RGB', SRC_SIZE, C_BG_BLUE if i < 6 else C_BG_RED)
        draw = ImageDraw.Draw(img)
        
        # Draw Border (Siren Light)
        border_color = C_CYAN if i < 6 else C_RED
        w = 20
        draw.rectangle([0, 0, SRC_SIZE[0], SRC_SIZE[1]], outline=border_color, width=30)
        
        # Eyes: Rectangular Shutter Shades style
        eye_w, eye_h = 140, 60
        left_eye = [80, 200, 80+eye_w, 200+eye_h]
        right_eye = [292, 200, 292+eye_w, 200+eye_h]
        
        # Draw Eyes
        draw.rounded_rectangle(left_eye, radius=20, fill=border_color)
        draw.rounded_rectangle(right_eye, radius=20, fill=border_color)
        
        # Pupil Slit (Robocop style)
        draw.rectangle([100, 225, 200, 235], fill=C_BLACK)
        draw.rectangle([312, 225, 412, 235], fill=C_BLACK)
        
        # Badge Star
        cx, cy = 256, 120
        r = 30
        draw.polygon([
            (cx, cy-r), (cx+r*0.3, cy-r*0.3), (cx+r, cy), 
            (cx+r*0.3, cy+r*0.3), (cx, cy+r), (cx-r*0.3, cy+r*0.3), 
            (cx-r, cy), (cx-r*0.3, cy-r*0.3)
        ], fill=(255, 215, 0)) # Gold star
        
        frames.append(img)
    
    save_frames("focus_police", frames)

# --- 2. Distraction (No Phone) ---
def gen_distraction():
    frames = []
    
    for i in range(10):
        img = Image.new('RGB', SRC_SIZE, (20, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Angry Eyes (Vector Triangles)
        # Left Eye
        draw.polygon([(100, 200), (220, 200), (160, 280)], fill=C_RED)
        # Right Eye
        draw.polygon([(292, 200), (412, 200), (352, 280)], fill=C_RED)
        
        # Angry Eyebrows
        draw.line([(80, 180), (240, 240)], fill=C_RED, width=25)
        draw.line([(432, 180), (272, 240)], fill=C_RED, width=25)
        
        # Flashing NO symbol
        if i % 2 == 0:
            # Circle
            draw.ellipse([100, 300, 412, 450], outline=C_RED, width=20)
            # Slash
            draw.line([(150, 320), (362, 430)], fill=C_RED, width=20)
            
            # Text "NO PHONE"
            # (Simplifying: Just the symbol is cleaner)
            
        frames.append(img)
        
    save_frames("distraction", frames)

# --- 3. Selfie (Vector Camera) ---
def gen_selfie_cam():
    frames = []
    
    # 1. Aperture Animation
    for step in range(0, 10):
        img = Image.new('RGB', SRC_SIZE, C_BLACK)
        draw = ImageDraw.Draw(img)
        
        cx, cy = 256, 256
        max_r = 200
        current_r = max_r * (1 - (step/10))
        
        # Lens Ring
        draw.ellipse([cx-210, cy-210, cx+210, cy+210], outline=C_WHITE, width=10)
        draw.ellipse([cx-230, cy-230, cx+230, cy+230], outline=C_GREY, width=5)
        
        # Iris (Closing)
        if current_r > 0:
            draw.ellipse([cx-current_r, cy-current_r, cx+current_r, cy+current_r], fill=C_WHITE)
            
        frames.append(img)
        
    # 2. BRIGHT FLASH
    white = Image.new('RGB', SRC_SIZE, C_WHITE)
    frames.append(white)
    frames.append(white)
    frames.append(white)
    
    # 3. Fade
    grey = Image.new('RGB', SRC_SIZE, (100, 100, 100))
    frames.append(grey)
    
    save_frames("selfie_cam", frames)

if __name__ == "__main__":
    gen_focus_police()
    gen_distraction()
    gen_selfie_cam()
    print("Done (High Quality).")
