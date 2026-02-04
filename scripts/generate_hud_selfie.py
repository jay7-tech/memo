
import os
import math
from PIL import Image, ImageDraw, ImageFont

# Config
ASSET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "interface", "lcd", "assets", "selfie_cam"))
SIZE = (128, 128)
BG = (0, 0, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
WHITE = (255, 255, 255)
RED = (255, 50, 50)

# Eye Config
EYE_W = 30
EYE_H = 40
EYE_GAP = 20
CX = 64
CY = 64

def draw_hud_brackets(draw, progress):
    # progress 0.0 to 1.0 (Slide in)
    margin = 10 + (20 * (1.0 - progress))
    w = 20
    t = 2
    
    # TL
    draw.line([(margin, margin), (margin+w, margin)], fill=CYAN, width=t)
    draw.line([(margin, margin), (margin, margin+w)], fill=CYAN, width=t)
    
    # TR
    draw.line([(128-margin, margin), (128-margin-w, margin)], fill=CYAN, width=t)
    draw.line([(128-margin, margin), (128-margin, margin+w)], fill=CYAN, width=t)
    
    # BL
    draw.line([(margin, 128-margin), (margin+w, 128-margin)], fill=CYAN, width=t)
    draw.line([(margin, 128-margin), (margin, 128-margin-w)], fill=CYAN, width=t)
    
    # BR
    draw.line([(128-margin, 128-margin), (128-margin-w, 128-margin)], fill=CYAN, width=t)
    draw.line([(128-margin, 128-margin), (128-margin, 128-margin-w)], fill=CYAN, width=t)

def draw_eyes(draw, number=None, color=CYAN):
    # Left Eye
    lx = CX - EYE_GAP - EYE_W//2
    ly = CY - EYE_H//2
    draw.rounded_rectangle([lx, ly, lx+EYE_W, ly+EYE_H], radius=10, outline=color, width=3)
    
    # Right Eye
    rx = CX + EYE_GAP - EYE_W//2
    ry = CY - EYE_H//2
    draw.rounded_rectangle([rx, ry, rx+EYE_W, ry+EYE_H], radius=10, outline=color, width=3)
    
    # Number
    if number:
        # Draw number in center (or in eyes? Let's do Center for readability)
        # Font hack: Draw pixelated number
        # 3
        draw.text((CX-5, CY-10), str(number), fill=WHITE, font_size=25)

def generate():
    if not os.path.exists(ASSET_DIR):
        os.makedirs(ASSET_DIR) # Overwrites existing folder effectively
        
    print(f"Generating HUD Selfie in {ASSET_DIR}...")
    frames = []
    
    # 1. Lock On (Frames 0-10)
    for i in range(10):
        img = Image.new('RGB', SIZE, BG)
        draw = ImageDraw.Draw(img)
        progress = i / 9.0
        draw_hud_brackets(draw, progress)
        draw_eyes(draw, color=CYAN)
        
        if i > 5:
             draw.text((35, 100), "LOCKED", fill=CYAN, font_size=10)
             
        frames.append(img)
        
    # 2. Count 3 (Frames 10-20)
    for i in range(10):
        img = Image.new('RGB', SIZE, BG)
        draw = ImageDraw.Draw(img)
        draw_hud_brackets(draw, 1.0)
        draw_eyes(draw, number="3", color=CYAN)
        draw.text((35, 100), "REC...", fill=RED, font_size=10)
        frames.append(img)

    # 3. Count 2 (Frames 20-30)
    for i in range(10):
        img = Image.new('RGB', SIZE, BG)
        draw = ImageDraw.Draw(img)
        draw_hud_brackets(draw, 1.0)
        draw_eyes(draw, number="2", color=CYAN)
        draw.text((35, 100), "REC...", fill=RED, font_size=10)
        frames.append(img)

    # 4. Count 1 (Frames 30-40)
    for i in range(10):
        img = Image.new('RGB', SIZE, BG)
        draw = ImageDraw.Draw(img)
        draw_hud_brackets(draw, 1.0)
        draw_eyes(draw, number="1", color=MAGENTA) # Warning color
        draw.text((35, 100), "CLR...", fill=MAGENTA, font_size=10)
        frames.append(img)
        
    # 5. Flash (Frames 40-42) purely white
    for i in range(3):
        img = Image.new('RGB', SIZE, WHITE)
        frames.append(img)
        
    # 6. Fade Out (Frames 43-45)
    for i in range(3):
        alpha = int(255 * (1.0 - (i/3.0)))
        img = Image.new('RGB', SIZE, (alpha, alpha, alpha))
        frames.append(img)

    # Save
    for idx, frame in enumerate(frames):
        path = os.path.join(ASSET_DIR, f"frame_{idx+1:03d}.png")
        frame.save(path)
        print(f"Saved {path}")

if __name__ == "__main__":
    generate()
