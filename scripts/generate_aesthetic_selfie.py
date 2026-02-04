
import os
import math
import random
from PIL import Image, ImageDraw, ImageFont

# Config
ASSET_DIR = r"c:\Users\JAYADEEP GOWDA K B\Desktop\MEMO\interface\lcd\assets\selfie_cam"
TARGET_SIZE = (128, 128)
CANVAS_SIZE = (512, 512) # 4x Supersampling for Vector Look

# Palette (Sticker / Pop Art)
BG_COLOR = (30, 30, 35) # Dark Grey Background (makes colors pop)
CAM_BODY = (255, 255, 255) # White
CAM_ACCENT = (255, 100, 150) # Hot Pink
LENS_OUTER = (50, 50, 50) # Dark Grey
LENS_INNER = (0, 200, 255) # Cyan
STROKE = (20, 20, 20) # Almost Black Outline
STROKE_WIDTH = 12

def draw_rounded_rect(draw, box, radius, fill, outline, width):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def draw_camera_character(draw, cx, cy, scale=1.0, rotation=0, open_shutter=True):
    # Apply Scale
    w = 260 * scale
    h = 180 * scale
    
    # Rotation (Simple implementation: Skip true rotation for complex shapes in PIL unless wrapping entire image)
    # We will simulate rotation by offsetting elements slightly or just bouncing
    
    # Body
    x1 = cx - w/2
    y1 = cy - h/2
    x2 = cx + w/2
    y2 = cy + h/2
    
    # Flash Unit (Top Bump)
    fw = 80 * scale
    fh = 40 * scale
    fx1 = cx - fw/2
    fy1 = y1 - fh/2
    draw_rounded_rect(draw, [fx1, fy1, fx1+fw, y1+fh], radius=20, fill=CAM_ACCENT, outline=STROKE, width=STROKE_WIDTH)
    
    # Main Body
    draw_rounded_rect(draw, [x1, y1, x2, y2], radius=40, fill=CAM_BODY, outline=STROKE, width=STROKE_WIDTH)
    
    # Lens (Big Central Eye)
    lens_r = 75 * scale
    draw.ellipse([cx-lens_r, cy-lens_r, cx+lens_r, cy+lens_r], fill=LENS_OUTER, outline=STROKE, width=STROKE_WIDTH)
    
    # Shutter / Iris
    iris_r = 55 * scale
    draw.ellipse([cx-iris_r, cy-iris_r, cx+iris_r, cy+iris_r], fill=LENS_INNER)
    
    # Glint (Shiny Vector Look)
    glint_r = 15 * scale
    gx = cx + 25 * scale
    gy = cy - 25 * scale
    draw.ellipse([gx-glint_r, gy-glint_r, gx+glint_r, gy+glint_r], fill=(255, 255, 255))
    
    # Cheek / Smile (It's a "Character")
    # Left Cheek
    draw.ellipse([x1+20*scale, y2-50*scale, x1+60*scale, y2-20*scale], fill=(255, 200, 200))
    # Right Cheek
    draw.ellipse([x2-60*scale, y2-50*scale, x2-20*scale, y2-20*scale], fill=(255, 200, 200))

def draw_number_bubble(draw, num, scale):
    # Draw a speech bubble with the number
    cx, cy = 400, 150 # Top Right
    r = 60 * scale
    if r <= 0: return
    
    # Bubble
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255, 255, 0), outline=STROKE, width=STROKE_WIDTH)
    
    # Text (mockup with lines for thick vector look)
    # Drawing '3', '2', '1' with lines
    tc = STROKE
    tw = 15
    
    if num == 3:
        # Two arcs
        draw.arc([cx-30, cy-40, cx+30, cy], -90, 90, fill=tc, width=tw)
        draw.arc([cx-30, cy, cx+30, cy+40], -90, 90, fill=tc, width=tw)
    elif num == 2:
        draw.line([cx-30, cy-30, cx+30, cy-30, cx+30, cy, cx-30, cy+40, cx+30, cy+40], fill=tc, width=tw, joint='curve')
    elif num == 1:
        draw.line([cx, cy-40, cx, cy+40], fill=tc, width=tw)

def generate():
    if not os.path.exists(ASSET_DIR):
        os.makedirs(ASSET_DIR)
        
    print(f"Generating High-Res Vector Selfie in {ASSET_DIR}...")
    frames = []
    
    total_frames = 50 # 3 seconds @ ~60ms
    
    for i in range(total_frames):
        # 1. Create High Res Canvas
        img = Image.new('RGB', CANVAS_SIZE, BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        # 2. Animation Logic
        # Phase 1: Bounce In (0-10)
        scale = 1.0
        cy = 256
        if i < 10:
            prog = i / 10.0
            # Overshoot ease
            cy = 256 + (256 * (1-prog))
        
        # Phase 2: Bobbing/Breathing (10-50)
        bob = math.sin((i-10) * 0.5) * 20
        
        # Draw Camera
        draw_camera_character(draw, 256, cy + bob, scale=1.0)
        
        # Phase 3: Countdown Bubbles
        # 10-20: '3'
        # 20-30: '2'
        # 30-40: '1'
        num = None
        zoom = 0.0
        
        if 10 <= i < 22:
            num = 3
            prog = (i-10)/5.0
            zoom = min(1.0, prog)
        elif 22 <= i < 34:
            num = 2
            prog = (i-22)/5.0
            zoom = min(1.0, prog)
        elif 34 <= i < 46:
            num = 1
            prog = (i-34)/5.0
            zoom = min(1.0, prog)
            
        if num:
             draw_number_bubble(draw, num, zoom)
        
        # Phase 4: Flash (46-50)
        if i >= 46:
             # Starburst white
             intensity = min(255, int((i-46)*100))
             overlay = Image.new('RGB', CANVAS_SIZE, (255, 255, 255))
             mask = Image.new('L', CANVAS_SIZE, intensity)
             img = Image.composite(overlay, img, mask)

        # 3. Downscale for Anti-Aliasing
        img_resized = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
        frames.append(img_resized)

    # Save
    for idx, frame in enumerate(frames):
        path = os.path.join(ASSET_DIR, f"frame_{idx+1:03d}.png")
        frame.save(path)
        print(f"Saved {path}")

if __name__ == "__main__":
    generate()
