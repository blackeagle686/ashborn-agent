import os
from phoenix.tools import tool

@tool(name="project_generator", description="Generates a complex, nested project structure. Input: 'base_path' (str), 'structure' (dict where keys are filenames and values are contents. Nested dicts create subdirectories). Use this for manifesting full architectural visions. IMPORTANT: You MUST provide complete, functional code in the content values. DO NOT use placeholders like '# code here' or 'pass'.")
def project_generator_tool(base_path: str, structure: dict) -> str:
    """
    Recursively generates a project structure from a dictionary manifest.
    """
    try:
        _create_structure(base_path, structure)
        return f"Successfully manifested architectural structure at ./{base_path}"
    except Exception as e:
        return f"Error manifesting structure: {str(e)}"

def _create_structure(base_path: str, structure: dict):
    os.makedirs(base_path, exist_ok=True)
    for name, content in structure.items():
        path = os.path.join(base_path, name)
        if isinstance(content, dict):
            _create_structure(path, content)
        else:
            # Ensure parent directory exists for keys that contain paths (e.g. "api/main.py")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding='utf-8') as f:
                f.write(str(content))

@tool(name="terminal", description="Executes a bash command. SECURITY: This tool is restricted. Dangerous commands (rm -rf /, sudo, etc.) and system paths (/etc, /root, etc.) are FORBIDDEN.")
def terminal_tool(command: str) -> str:
    """
    Executes a shell command with security guards.
    """
    import subprocess
    
    # ── Security Layer: Forbidden Patterns ──
    FORBIDDEN = [
        "sudo", "rm -rf /", "rm -rf *", "rm -rf .", "mv /", "cp /",
        "chown", "chmod", "dd if=", ":(){ :|:& };:", "/etc", "/root",
        "/var", "/bin", "/sbin", "/usr/bin", "/usr/sbin"
    ]
    
    cmd_lower = command.lower()
    for pattern in FORBIDDEN:
        if pattern in cmd_lower:
            return f"Security Error: Command contains forbidden pattern '{pattern}'."

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        return output if output else "Command executed successfully (no output)."
    except Exception as e:
        return f"Error executing command: {str(e)}"

