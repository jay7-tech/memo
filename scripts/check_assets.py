
import os
import sys
from pathlib import Path

def check_assets():
    print("=== ASSET DIAGNOSTIC ===")
    
    # 1. Check Manager Path Logic
    # Mimic manager.py path resolution
    base_path = Path("interface/lcd/manager.py").resolve()
    if not base_path.exists():
        # Maybe running from scripts/
        base_path = Path("../interface/lcd/manager.py").resolve()
        
    print(f"Manager File Concept: {base_path}")
    expected_assets = base_path.parent / "assets"
    print(f"Expected Assets Dir:  {expected_assets}")
    
    if not expected_assets.exists():
        print("❌ ASSETS DIRECTORY MISSING AT EXPECTED LOCATION!")
        
        # Check if it exists elsewhere
        possible = list(Path(".").glob("**/interface/lcd/assets"))
        if possible:
            print(f"Found it here instead: {possible[0]}")
            print("Action: You need to move it to the expected location.")
        return

    print("✅ Assets Directory Exists.")
    
    # 2. List Content
    print("\n--- Listing Folders ---")
    subdirs = [d for d in expected_assets.iterdir() if d.is_dir()]
    found_keys = []
    for d in subdirs:
        # Check for images
        imgs = list(d.glob("*.png")) + list(d.glob("*.jpg"))
        status = f"✅ ({len(imgs)} imgs)" if imgs else "⚠️ (Empty)"
        print(f"  📂 {d.name:<20} {status}")
        found_keys.append(d.name)
        
    print("\n--- Logic Check ---")
    required = ["focus_warning", "focus_scan", "idle_center"]
    aliases = {
        "focus_warning": ["distraction", "warn", "angry"]
    }
    
    for req in required:
        if req in found_keys:
            print(f"  ✅ '{req}' found directly.")
        else:
            # Check aliases
            found_alias = False
            for a in aliases.get(req, []):
                if a in found_keys:
                    print(f"  ✅ '{req}' missing, but alias '{a}' found (will work).")
                    found_alias = True
                    break
            if not found_alias:
                 print(f"  ❌ '{req}' MISSING! (And no aliases found)")
                 
    print("\n=== PERMISSIONS ===")
    try:
        test_file = list(expected_assets.rglob("*.png"))[0]
        with open(test_file, 'rb') as f:
            print("  ✅ Can read asset files.")
    except IndexError:
        print("  ⚠️ No files to test read.")
    except PermissionError:
        print("  ❌ PERMISSION DENIED! Run: sudo chown -R pi:pi interface/lcd/assets")
        
if __name__ == "__main__":
    current = Path.cwd()
    print(f"Running from: {current}")
    check_assets()
