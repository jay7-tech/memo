import os
import math
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps

# Config
TARGET_SIZE = (128, 128)
ASSETS_DIR = Path("interface/lcd/assets")

# Neon Palette (Cyberpunk Style)
COLOR_CORE = (200, 255, 255)   # Bright White-ish Center
COLOR_GLOW_DEFAULT = (0, 255, 180) # Cyan/Teal
COLOR_THINKING = (0, 150, 255)   # Deep Blue
COLOR_LISTENING = (255, 50, 150) # Hot Pink
COLOR_WARNING = (255, 60, 0)     # Orange/Red
COLOR_FLASH = (255, 255, 255)

def ensure_clean_dir(name):
    path = ASSETS_DIR / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def draw_squircle(draw, bounds, radius, fill):
    """Draws a rounded rectangle (Vector-style eye)."""
    draw.rounded_rectangle(bounds, radius=radius, fill=fill)

def create_glow_eye(size, eye_bbox, core_color, glow_color, eyelid_h=0.0, eyelid_angle=0.0, opacity=1.0):
    """
    Generates a single frame of glowing eyes with eyelids.
    size: (w, h) of canvas
    eye_bbox: (x, y, w, h) of the eye shape
    eyelid_h: 0.0 (open) to 1.0 (closed)
    eyelid_angle: rotation of eyelid in degrees (positive = angry \ /, negative = sad / \)
    """
    # Create large canvas for anti-aliasing/blur
    scale = 4
    w, h = size[0]*scale, size[1]*scale
    ex, ey, ew, eh = [v*scale for v in eye_bbox]
    
    # 1. Base Glow Layer (Blurred)
    glow = Image.new("RGBA", (w, h), (0,0,0,0))
    g_draw = ImageDraw.Draw(glow)
    draw_squircle(g_draw, [ex, ey, ex+ew, ey+eh], radius=ew//3, fill=(*glow_color, 255))
    
    # Apply Blur
    glow = glow.filter(ImageFilter.GaussianBlur(8*scale)) # Cleaner glow

    # 2. Core Layer (Sharp)
    core = Image.new("RGBA", (w, h), (0,0,0,0))
    c_draw = ImageDraw.Draw(core)
    draw_squircle(c_draw, [ex+10, ey+10, ex+ew-10, ey+eh-10], radius=ew//3, fill=(*core_color, 240))
    
    # 3. Composite Eye
    final = Image.new("RGBA", (w, h), (0,0,0,0))
    final.alpha_composite(glow)
    final.alpha_composite(core)
    
    # 4. Apply Eyelid Mask (Inverse)
    if eyelid_h > 0.0 or eyelid_angle != 0:
        mask = Image.new("L", (w, h), 255)
        m_draw = ImageDraw.Draw(mask)
        
        # Calculate eyelid rectangle
        lid_h_px = h * eyelid_h
        
        # We draw a black shape where the Eyelid COVERS the eye
        # Basic top-down eyelid
        # Rotate logic is complex, approximating with polygon
        
        # Center of eye
        cx, cy = ex + ew/2, ey + eh/2
        
        # Top eyelid (lowers from top)
        # Create a large rectangle rotated around center
        # We actually just mask the Top part
        
        # Simple approach: Draw rotated rectangle "blocking" the top
        blocker_w = w * 1.5
        blocker_h = h * 1.5
        
        # Base position (fully open = above eye)
        # lid_pos triggers 0 to 1 mapping
        # 0 -> top of eye
        # 1 -> bottom of eye
        lid_y = ey + (eh * eyelid_h)
        
        # If angry (angle > 0), outer corners lower. 
        # For simplicity in this script, we just rotate a masking rect
        
        mask_layer = Image.new("RGBA", (w, h), (0,0,0,0))
        ml_draw = ImageDraw.Draw(mask_layer)
        
        # Draw the "Skin" (Black) over the eye
        rect_x0 = -w/2
        rect_y0 = -h # Start way up
        rect_x1 = w*1.5
        rect_y1 = lid_y
        
        # If we need rotation, we draw rect on a temp layer then rotate
        # Angry eyes: \ /  (Rotate Left Eye CW, Right Eye CCW)
        # We need to render Left and Right separately? 
        # Yes, this func draws ONE eye shape? No, usually draws the whole face if bbox is passed.
        # Let's assume bbox is ONE eye.
        
        # Skip rotation for now to ensure robustness, just use height for Blink
        ml_draw.rectangle([0, 0, w, lid_y], fill=(0,0,0,255))
        
        # Apply mask to final
        # Actually easier: Just clear pixels in final where mask is opaque (or actually mask is "where to KEEP")
        # Let's use simple crop:
        # Just draw a black rectangle on top of 'final'
        
        # Better Eyelid:
        # Create a separate image for "Eyelid" which is Black
        eyelid_img = Image.new("RGBA", (w, h), (0,0,0,0))
        el_draw = ImageDraw.Draw(eyelid_img)
        
        # Pivot point
        cx, cy = ex + ew/2, ey + eh/2
        
        # Draw a big black box for the lid
        # Height is driven by eyelid_h (0 = top of eye, 1 = bottom)
        # Offset by angle
        
        # Effective Y position of lid edge
        edge_y = ey + (eh * eyelid_h)
        
        # Draw rectangle covering everything ABOVE edge_y
        # Expand bounds to cover rotation
        el_draw.rectangle([-w, -h, w*2, edge_y], fill=(0,0,0,255))
        
        # Rotate this eyelid layer around center of eye
        if eyelid_angle != 0:
            eyelid_img = eyelid_img.rotate(eyelid_angle, center=(cx, cy), translate=None)
            
        # Composite Black Eyelid onto Glowing Eye
        final.alpha_composite(eyelid_img)

    # Downscale
    final = final.resize(size, resample=Image.Resampling.LANCZOS)
    
    # Adjust global opacity
    if opacity < 1.0:
        # Apply alpha mult
        r, g, b, a = final.split()
        a = a.point(lambda p: p * opacity)
        final = Image.merge("RGBA", (r, g, b, a))
        
    return final.convert("RGB") # Flatten to black

def render_sequence(name, func, frames=30):
    print(f"Rendering '{name}'...")
    out_dir = ensure_clean_dir(name)
    for i in range(frames):
        img = func(i, frames)
        img.save(out_dir / f"frame_{i:03d}.png")

# --- Animation Functions ---

def anim_idle_center(i, total):
    # Breathing effect
    cycle = math.sin((i / total) * math.pi * 2) # -1 to 1
    # Breath brightness: 0.8 to 1.0
    opacity = 0.85 + (cycle * 0.15)
    
    img = Image.new("RGB", TARGET_SIZE, (0,0,0))
    left = create_glow_eye(TARGET_SIZE, (20, 44, 34, 40), COLOR_CORE, COLOR_GLOW_DEFAULT, opacity=opacity)
    right = create_glow_eye(TARGET_SIZE, (74, 44, 34, 40), COLOR_CORE, COLOR_GLOW_DEFAULT, opacity=opacity)
    
    # Composite (Add)
    # Since background is black, we can just max or add. 
    # But create_glow_eye returns RGB.
    # Simple paste with crop?
    # Actually, create_glow_eye takes WHOLE canvas size and bbox. so we can just Add them.
    # Wait, create_glow_eye creates a layer with alpha. Better to let it return RGBA.
    # Updated create_glow_eye to return RGB... let's change it to RGBA logic inside
    
    # Optimization: Just draw 2 eyes on one canvas call?
    # Reworked logic below for dual eyes
    
    return draw_face((20, 44, 34, 40), (74, 44, 34, 40), glow=COLOR_GLOW_DEFAULT, opacity=opacity)

def draw_face(l_bbox, r_bbox, glow, opacity=1.0, l_lid=0.0, r_lid=0.0, l_ang=0.0, r_ang=0.0):
    # Combine two eyes on one image
    base = Image.new("RGB", TARGET_SIZE, (0,0,0))
    # Hack: Render individually and composite?
    # Proper: Render RGBA then paste on Black.
    
    # Left
    l_img = create_glow_eye(TARGET_SIZE, l_bbox, COLOR_CORE, glow, eyelid_h=l_lid, eyelid_angle=l_ang, opacity=opacity)
    # Right
    r_img = create_glow_eye(TARGET_SIZE, r_bbox, COLOR_CORE, glow, eyelid_h=r_lid, eyelid_angle=r_ang, opacity=opacity)
    
    # Additive blend? Or just Screen?
    # Since eyes are spatially separate, simple add works.
    return ImageChops.add(l_img, r_img)

from PIL import ImageChops

def anim_blink(i, total):
    # Fast blink
    # Frame 0-10: Open
    # 10-15: Closing
    # 15-20: Closed
    # 20-25: Opening
    t = i / total
    lid = 0.0
    if 0.3 < t < 0.4: lid = (t-0.3)*10 # Closing
    elif 0.4 <= t < 0.5: lid = 1.0 # Closed
    elif 0.5 <= t < 0.6: lid = 1.0 - (t-0.5)*10 # Opening
    
    return draw_face((20, 44, 34, 40), (74, 44, 34, 40), COLOR_GLOW_DEFAULT, l_lid=lid, r_lid=lid)

def anim_thinking_search(i, total):
    # Eyes moving L -> R
    # Frame 0-10: look left
    # 10-20: look up
    # 20-30: look right
    
    # Interpolate positions
    # Base: (20,44)
    off_x, off_y = 0, 0
    
    phase = (i / total) * math.pi * 2
    off_x = math.cos(phase) * 6
    off_y = math.sin(phase) * 6
    
    # Slight squint
    return draw_face((20+off_x, 44+off_y, 34, 40), (74+off_x, 44+off_y, 34, 40), COLOR_THINKING, l_lid=0.3, r_lid=0.3)

def anim_listening_active(i, total):
    # Pulse size and color
    pulse = math.sin((i / total) * math.pi * 2) # -1 to 1
    scale = 1.0 + (pulse * 0.1) # +/- 10%
    
    # Expand height mainly
    h_scale = 40 * scale
    w_scale = 34 * (1.0 - pulse*0.05) # Squeeze slightly
    
    cent_ly = 44 + 20
    new_ly = cent_ly - h_scale/2
    
    return draw_face((20, new_ly, 34, h_scale), (74, new_ly, 34, h_scale), COLOR_LISTENING)

def anim_flash(i, total):
    # 5 frames
    brightness = int(255 * (1.0 - i/total))
    return Image.new("RGB", TARGET_SIZE, (brightness, brightness, brightness))

def anim_angry(i, total):
    # Throbbing angry
    pulse = math.sin((i/total)*math.pi*4) # fast pulse
    op = 0.9 + pulse*0.1
    # Angled eyelids
    return draw_face((20, 44, 34, 40), (74, 44, 34, 40), COLOR_WARNING, opacity=op, l_lid=0.4, r_lid=0.4, l_ang=20, r_ang=-20)

def anim_wink(i, total):
    # One eye closes
    lid_r = 0.0
    if 0.2 < (i/total) < 0.8:
        lid_r = 1.0
    return draw_face((20, 44, 34, 40), (74, 44, 34, 40), COLOR_GLOW_DEFAULT, r_lid=lid_r)

if __name__ == "__main__":
    print("Generating Vector-Style Assets...")
    render_sequence("idle_center", anim_idle_center, 60)
    # Re-use idle for left/right for now or add look anims
    
    render_sequence("blink", anim_blink, 30)
    render_sequence("thinking", anim_thinking_search, 40)
    render_sequence("listening", anim_listening_active, 30)
    render_sequence("flash", anim_flash, 10)
    render_sequence("angry", anim_angry, 30)
    render_sequence("wink", anim_wink, 30)
    
    # Copy generic blink to sleep?
    print("Done.")
