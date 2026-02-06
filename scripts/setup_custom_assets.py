
import os
import json
import curses
import shutil
from pathlib import Path

# Config Path
CONFIG_PATH = Path("config.json").resolve()
HOME_DIR = Path.home()

def load_config():
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)

def find_asset_candidates(root_dir, depth=2):
    """
    Search for folders that look like they contain MEMO assets.
    Criteria: Contains subfolders like 'focus_warning', 'idle_center', etc.
    """
    candidates = []
    print(f"Scanning {root_dir} for asset folders (depth={depth})...")
    
    # Required heuristic
    markers = ["focus_warning", "idle_center", "focus_scan"]
    
    for root, dirs, files in os.walk(root_dir):
        # Limit depth
        current_depth = len(Path(root).relative_to(root_dir).parts)
        if current_depth > depth:
            # Don't recurse deeper
            dirs[:] = [] 
            continue
            
        # Check current dir
        score = 0
        lc_dirs = [d.lower() for d in dirs]
        for m in markers:
            if m in lc_dirs:
                score += 1
                
        if score >= 1: # Partial match is enough to suggest
             candidates.append(Path(root).resolve())
             
    return candidates

def main(stdscr):
    # Setup Curses
    curses.curs_set(0)
    stdscr.clear()
    
    # 1. Scan
    stdscr.addstr(0, 0, "MEMO // ASSET SETUP WIZARD", curses.A_BOLD)
    stdscr.addstr(2, 0, "Scanning your Home folder for asset collections...")
    stdscr.refresh()
    
    candidates = find_asset_candidates(HOME_DIR, depth=3)
    
    # Add current internal assets as an option
    internal_assets = Path("interface/lcd/assets").resolve()
    candidates.insert(0, internal_assets)
    
    selected_idx = 0
    
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "MEMO // ASSET SETUP WIZARD", curses.A_BOLD)
        stdscr.addstr(1, 0, "Select the folder containing your TRUE assets:")
        stdscr.addstr(2, 0, "Use UP/DOWN to select, ENTER to confirm, Q to quit.")
        
        for i, path in enumerate(candidates):
            style = curses.A_REVERSE if i == selected_idx else curses.A_NORMAL
            label = str(path)
            if path == internal_assets:
                label += " (Default / Internal)"
            stdscr.addstr(4 + i, 2, f" {label} ", style)
            
        key = stdscr.getch()
        
        if key == curses.KEY_UP and selected_idx > 0:
            selected_idx -= 1
        elif key == curses.KEY_DOWN and selected_idx < len(candidates) - 1:
            selected_idx += 1
        elif key == ord('q'):
            return
        elif key == 10: # Enter
            choice = candidates[selected_idx]
            break
            
    # Apply
    stdscr.clear()
    stdscr.addstr(0, 0, f"Selected: {choice}")
    stdscr.addstr(2, 0, "Updating config.json...")
    
    path_str = str(choice)
    # If default, set to null
    if choice == internal_assets:
        path_str = None
        
    cfg = load_config()
    if 'system' not in cfg: cfg['system'] = {}
    cfg['system']['assets_path'] = path_str
    
    save_config(cfg)
    
    stdscr.addstr(4, 0, "✅ Success! Configuration updated.")
    stdscr.addstr(6, 0, "Please restart MEMO now.")
    stdscr.addstr(8, 0, "Press any key to exit.")
    stdscr.getch()

if __name__ == "__main__":
    # Fallback if curses fails (headless)
    try:
        curses.wrapper(main)
    except Exception as e:
        print("Interactive mode failed. Running text mode.")
        # Simple text fallback
        candidates = find_asset_candidates(HOME_DIR, depth=3)
        print("\nFound Asset Folders:")
        for i, c in enumerate(candidates):
            print(f"[{i}] {c}")
        
        sel = input("Enter number (or 'q'): ")
        if sel.isdigit() and int(sel) < len(candidates):
            path = candidates[int(sel)]
            cfg = load_config()
            if 'system' not in cfg: cfg['system'] = {}
            cfg['system']['assets_path'] = str(path)
            save_config(cfg)
            print(f"✅ Set assets path to: {path}")

