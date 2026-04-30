import os

def replace_in_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

replace_in_file('ashborn/cli/chat_screen.py', [
    ('border: tall #982598;', 'border: round #982598;')
])

replace_in_file('ashborn/cli/setup_wizard.py', [
    ('border: tall #982598;', 'border: round #982598;'),
    ('border: tall #ff4444;', 'border: round #ff4444;')
])
print("Borders rounded.")
