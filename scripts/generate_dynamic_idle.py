
import os
import math
import random
from PIL import Image, ImageDraw

# Config
ASSET_DIR = r"c:\Users\JAYADEEP GOWDA K B\Desktop\MEMO\interface\lcd\assets\idle_center"
TARGET_SIZE = (128, 128)
CANVAS_SIZE = (512, 512)

# Palette (Cyber Aesthetic)
BG_COLOR = (20, 20, 25)
CYAN = (0, 255, 255)
WHITE = (255, 255, 255)
MINT = (150, 255, 200)

def draw_vector_eye(draw, cx, cy, w, h, color):
    # Base
    draw.rounded_rectangle([cx-w/2, cy-h/2, cx+w/2, cy+h/2], radius=40, fill=color, outline=WHITE, width=8)
    # Highlight (Top Right)
    draw.ellipse([cx+w/3, cy-h/3, cx+w/3+20, cy-h/3+20], fill=WHITE)

def draw_particle(draw, x, y, size, opacity):
    # Diamond shape
    fill = (MINT[0], MINT[1], MINT[2], opacity) # RGBA needed?
    # Simple cross
    l = size
    draw.line([x-l, y, x+l, y], fill=(MINT[0], MINT[1], MINT[2]), width=2)
    draw.line([x, y-l, x, y+l], fill=(MINT[0], MINT[1], MINT[2]), width=2)

def generate():
    if not os.path.exists(ASSET_DIR): os.makedirs(ASSET_DIR)
    print(f"Generating Dynamic Idle in {ASSET_DIR}...")
    
    frames = []
    total_frames = 60 # 1 loop ~3-4 seconds depending on FPS
    
    # Particles state
    particles = []
    for _ in range(5):
        particles.append({
            'x': random.randint(50, 460),
            'y': random.randint(50, 460),
            'speed': random.uniform(0.5, 2.0),
            'phase': random.uniform(0, 6.28)
        })
    
    for i in range(total_frames):
        img = Image.new('RGB', CANVAS_SIZE, BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        # Breathing Logic
        # Sine wave 0 to 1 to 0
        cycle = math.sin((i / total_frames) * 2 * math.pi)
        
        # Scale: 0.95 to 1.05
        # We simulate scale by changing W/H
        scale_factor = 1.0 + (0.05 * cycle)
        
        # Bob: Y position moves up/down slightly
        bob_y = cycle * 10
        
        base_w = 100
        base_h = 140
        
        w = base_w * scale_factor
        h = base_h * (1.0 + (0.02 * cycle)) # Strech slightly more vertically
        
        y = 256 + bob_y
        
        # Draw Eyes
        draw_vector_eye(draw, 180, y, w, h, CYAN)
        draw_vector_eye(draw, 332, y, w, h, CYAN)
        
        # Draw Particles
        for p in particles:
            # Drift Up
            p['y'] -= p['speed']
            if p['y'] < -20: p['y'] = 530
            
            # Opacity flicker
            op = (math.sin(i * 0.1 + p['phase']) + 1) * 0.5 # 0-1
            # Draw
            draw_particle(draw, p['x'], p['y'], 5 + (5*op), int(255*op))
            
        # Draw Small HUD Elements (Static or moving)
        # Underscore bars
        draw.line([150, 400, 210, 400], fill=(50, 50, 50), width=4)
        draw.line([302, 400, 362, 400], fill=(50, 50, 50), width=4)
        
        # Resize
        img_resized = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
        frames.append(img_resized)

    for idx, frame in enumerate(frames):
        # We need seamless loop
        frame.save(os.path.join(ASSET_DIR, f"frame_{idx:03d}.png"))
        
if __name__ == "__main__":
    generate()
