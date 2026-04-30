import os
import sys
import asyncio

# Add the project root to sys.path
sys.path.append(os.getcwd())

from ashborn.tools.project_generator import project_generator_tool

def test_project_generator():
    base_path = "test_project"
    structure = {
        "main.py": "print('hello')",
        "subdir": {
            "module.py": "x = 1",
            "nested": {
                "file.txt": "content"
            }
        },
        "api/routes.py": "from fastapi import APIRouter"
    }
    
    # The tool is wrapped in @tool, so we need to call .func or use it as a tool
    # Wait, the decorator returns an instance of FunctionTool which has an .execute method
    
    # Let's try calling the function directly first (via .func)
    from ashborn.tools.project_generator import project_generator_tool
    # Since it's a FunctionTool instance
    print(f"Tool name: {project_generator_tool.name}")
    
    # We need to run it in an event loop if it was async, but it's sync.
    # However, the BaseTool.execute is async.
    
    async def run_test():
        result = await project_generator_tool.execute(base_path=base_path, structure=structure)
        print(f"Success: {result.success}")
        print(f"Output: {result.output}")
        print(f"Error: {result.error}")
        
        # Verify files
        expected_files = [
            "test_project/main.py",
            "test_project/subdir/module.py",
            "test_project/subdir/nested/file.txt",
            "test_project/api/routes.py"
        ]
        for f in expected_files:
            if os.path.exists(f):
                print(f"Found: {f}")
            else:
                print(f"MISSING: {f}")

    asyncio.run(run_test())

if __name__ == "__main__":
    test_project_generator()
