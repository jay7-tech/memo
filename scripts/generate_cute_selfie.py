
import os
import math
from PIL import Image, ImageDraw, ImageFont

# Config
ASSET_DIR = r"c:\Users\JAYADEEP GOWDA K B\Desktop\MEMO\interface\lcd\assets\selfie_cam"
SIZE = (128, 128)
BG_COLOR = (0, 0, 0)
LINE_COLOR = (255, 255, 255)
ACCENT_COLOR = (0, 255, 255) # Cyan
ACCENT_2 = (255, 105, 180) # Hot Pink
LINE_WIDTH = 4

def draw_camera_icon(draw, cx, cy, scale, open_shutter=True):
    # Camera Body
    w = 80 * scale
    h = 60 * scale
    x1 = cx - w/2
    y1 = cy - h/2
    x2 = cx + w/2
    y2 = cy + h/2
    
    # Body
    draw.rounded_rectangle([x1, y1, x2, y2], radius=10*scale, outline=LINE_COLOR, width=LINE_WIDTH)
    
    # Top bump (Flash housing usually)
    bw = 30 * scale
    bh = 10 * scale
    draw.line([x1+10*scale, y1, x1+10*scale+bw, y1], fill=LINE_COLOR, width=LINE_WIDTH) # Top line?
    # Better: small rect on top
    draw.rounded_rectangle([cx-15*scale, y1-10*scale, cx+15*scale, y1], radius=3*scale, outline=LINE_COLOR, width=LINE_WIDTH)
    
    # Lens (Circle)
    lens_r = 25 * scale
    draw.ellipse([cx-lens_r, cy-lens_r, cx+lens_r, cy+lens_r], outline=LINE_COLOR, width=LINE_WIDTH)
    
    # Inner Lens (Accent)
    if open_shutter:
        inner_r = 15 * scale
        draw.ellipse([cx-inner_r, cy-inner_r, cx+inner_r, cy+inner_r], outline=ACCENT_COLOR, width=LINE_WIDTH-1)
        
        # Glint
        draw.ellipse([cx+5*scale, cy-10*scale, cx+10*scale, cy-5*scale], fill=(255,255,255))

def draw_emoji_face(draw, cx, cy, scale):
    # Cute Face: (>_<) OR (^ _ ^)
    
    # Eyes
    eye_r = 15 * scale
    # Left Eye (Arc)
    draw.arc([cx-25*scale-10, cy-10-10, cx-25*scale+10, cy-10+10], 180, 0, fill=LINE_COLOR, width=3) 
    # Right Eye (Arc)
    draw.arc([cx+25*scale-10, cy-10-10, cx+25*scale+10, cy-10+10], 180, 0, fill=LINE_COLOR, width=3)
    
    # Cheeks
    draw.ellipse([cx-35*scale, cy+5*scale, cx-25*scale, cy+15*scale], fill=ACCENT_2)
    draw.ellipse([cx+25*scale, cy+5*scale, cx+35*scale, cy+15*scale], fill=ACCENT_2)
    
    # Mouth (Smile)
    draw.arc([cx-10*scale, cy-5*scale, cx+10*scale, cy+10*scale], 0, 180, fill=LINE_COLOR, width=3)

def generate():
    if not os.path.exists(ASSET_DIR):
        os.makedirs(ASSET_DIR)
        
    print(f"Generating Selfie Animation in {ASSET_DIR}...")
    
    frames = []
    
    # Phase 1: Pop In (Frames 0-5)
    for i in range(6):
        img = Image.new('RGB', SIZE, BG_COLOR)
        draw = ImageDraw.Draw(img)
        progress = i / 5.0
        scale = 0.5 + (0.5 * (math.sin(progress * math.pi / 2))) # Ease out
        draw_camera_icon(draw, 64, 64, scale)
        frames.append(img)
        
    # Phase 2: Say Cheese / Smile (Frames 6-12)
    for i in range(6):
        img = Image.new('RGB', SIZE, BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        # Camera morphs to face? Or Face is overlapping lens?
        # Let's just draw the camera but with the lens 'smiling'
        draw_camera_icon(draw, 64, 64, 1.0, open_shutter=False)
        
        # Override Lens center with Smile
        # draw.rectangle([40,40, 90,90], fill=BG_COLOR) # Clear lens area
        draw_emoji_face(draw, 64, 64, 1.0)
        
        # Text "CHEESE!"
        if i % 2 == 0:
            draw.text((35, 100), "SMILE!", fill=ACCENT_COLOR, font_size=15)
            
        frames.append(img)
        
    # Phase 3: Flash Buildup (Frames 12-14)
    for i in range(3):
        img = Image.new('RGB', SIZE, BG_COLOR)
        draw = ImageDraw.Draw(img)
        scale = 1.0 + (i * 0.1)
        draw_camera_icon(draw, 64, 64, scale)
        
        # Overlay white alpha
        alpha = int(i * 80)
        overlay = Image.new('RGBA', SIZE, (255, 255, 255, alpha))
        img.paste(overlay, (0,0), overlay)
        frames.append(img)
        
    # Phase 4: FLASH (Frames 15-17)
    for i in range(3):
        img = Image.new('RGB', SIZE, (255, 255, 255)) # PURE WHITE
        frames.append(img)
        
    # Save
    for idx, frame in enumerate(frames):
        path = os.path.join(ASSET_DIR, f"frame_{idx+1:03d}.png")
        frame.save(path)
        print(f"Saved {path}")

if __name__ == "__main__":
    generate()
