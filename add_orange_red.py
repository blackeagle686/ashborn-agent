import os
import re

files = [
    "ashborn/cli/chat_screen.py",
    "ashborn/cli/setup_wizard.py",
    "ashborn/cli/splash_screen.py"
]

for file_path in files:
    if not os.path.exists(file_path):
        continue
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # In chat_screen.py, let's make the logo orange
    if "chat_screen.py" in file_path:
        content = content.replace("color: #982598;\n        text-style: bold;\n        width: auto;\n    }", 
                                  "color: #FF6B00;\n        text-style: bold;\n        width: auto;\n    }") # header logo
        
        # User message color
        content = content.replace("[bold #E491C9]┌─ You[/]", "[bold #FF3333]┌─ You[/]")
        content = content.replace("[bold #E491C9]│[/]", "[bold #FF3333]│[/]")
        content = content.replace("[bold #E491C9]└", "[bold #FF3333]└")
        
        # Ashborn message header orange
        content = content.replace("[bold #982598]┌─ 🐦‍🔥 Ashborn[/]", "[bold #FF6B00]┌─ 🐦‍🔥 Ashborn[/]")
        content = content.replace("[bold #982598]│[/]", "[bold #FF6B00]│[/]")
        content = content.replace("[bold #982598]└", "[bold #FF6B00]└")
        
        # Input prefix >
        content = content.replace("id=\"input-prefix\" {\n        color: #982598;", "id=\"input-prefix\" {\n        color: #FF6B00;")

    # In setup_wizard.py
    if "setup_wizard.py" in file_path:
        # Button save background
        content = content.replace("background: #982598;\n        color: #15173D;", "background: #FF6B00;\n        color: #15173D;")
        content = content.replace("background: #E491C9;\n    }", "background: #FF3333;\n    }") # hover
        
        # Logo
        content = content.replace("#logo {\n        text-align: center;\n        color: #982598;", "#logo {\n        text-align: center;\n        color: #FF6B00;")

    # In splash_screen.py
    if "splash_screen.py" in file_path:
        # splash logo
        content = content.replace("#splash-logo {\n        text-align: center;\n        color: #982598;", "#splash-logo {\n        text-align: center;\n        color: #FF6B00;")
        content = content.replace("Text(logo, style=\"bold #982598\")", "Text(logo, style=\"bold #FF6B00\")")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Added orange and red successfully.")
