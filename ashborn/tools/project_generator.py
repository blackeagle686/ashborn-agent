import os
from phoenix.tools import tool

@tool(name="project_generator", description="Generates a complex, nested project structure. Input: 'base_path' (str), 'structure' (dict where keys are filenames and values are contents. Nested dicts create subdirectories). Use this for manifesting full architectural visions.")
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
            with open(path, "w") as f:
                f.write(content)

@tool(name="terminal", description="Executes a bash command in the terminal. Use for installing dependencies, running tests, or managing files.")
def terminal_tool(command: str) -> str:
    """
    Executes a shell command and returns the output.
    """
    import subprocess
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        return output if output else "Command executed successfully (no output)."
    except Exception as e:
        return f"Error executing command: {str(e)}"

