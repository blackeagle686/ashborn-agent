# This tool helps scaffold production-ready project structures.
import os
import subprocess
from phoenix.tools import Tool

def generate_project(project_name: str, project_type: str) -> str:
    """
    Generates a production-ready project structure based on the project type.
    Supported types: 'python_microservice', 'cli'
    """
    try:
        os.makedirs(project_name, exist_ok=True)
        
        if project_type == 'python_microservice':
            _create_file(os.path.join(project_name, "main.py"), "# Entrypoint for microservice\nprint('Microservice running')")
            _create_file(os.path.join(project_name, "requirements.txt"), "fastapi\nuvicorn\npydantic")
            _create_file(os.path.join(project_name, "Dockerfile"), "FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD [\"python\", \"main.py\"]")
            return f"Successfully generated {project_type} at ./{project_name}"
            
        elif project_type == 'cli':
            _create_file(os.path.join(project_name, "main.py"), "import typer\n\napp = typer.Typer()\n\n@app.command()\ndef hello(name: str):\n    print(f'Hello {name}')\n\nif __name__ == '__main__':\n    app()")
            _create_file(os.path.join(project_name, "requirements.txt"), "typer\nrich")
            return f"Successfully generated {project_type} at ./{project_name}"
            
        else:
            return f"Error: Unsupported project type '{project_type}'. Supported: 'python_microservice', 'cli'"
            
    except Exception as e:
        return f"Error generating project: {str(e)}"

def _create_file(path: str, content: str):
    with open(path, "w") as f:
        f.write(content)

project_generator_tool = Tool(
    name="project_generator",
    description="Generates boilerplate code for a production-ready project. Provide the 'project_name' and 'project_type'.",
    func=generate_project
)
