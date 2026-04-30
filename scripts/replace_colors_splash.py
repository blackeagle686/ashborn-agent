import os
import re

files_to_update = [
    "ashborn/cli/splash_screen.py"
]

color_map = {
    r"#0d0d0d": "#15173D",
    r"#141414": "#15173D",
    r"#1a1a1a": "#15173D",
    r"#1f1f1f": "#15173D",
    r"#2a2a2a": "#982598",
    r"#3a3a3a": "#982598",
    r"#ff8c00": "#982598",
    r"#ffb347": "#E491C9",
    r"#00d4ff": "#E491C9",
    r"#e0e0e0": "#F1E9E9",
    r"#666666": "#E491C9",
}

for file_path in files_to_update:
    if not os.path.exists(file_path):
        continue
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    for old_color, new_color in color_map.items():
        content = re.sub(old_color, new_color, content, flags=re.IGNORECASE)
        
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Splash screen colors updated successfully.")
