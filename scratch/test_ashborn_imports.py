import sys
import os

# Add venv site-packages to path
venv_site_packages = os.path.join(os.getcwd(), "venv/lib/python3.12/site-packages")
if venv_site_packages not in sys.path:
    sys.path.insert(0, venv_site_packages)

# Add current directory to path for ashborn imports
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

print("--- Testing Ashborn Module Imports ---")

try:
    from ashborn.agent import get_ashborn_agent
    print("✓ ashborn.agent (get_ashborn_agent)")
except Exception as e:
    print(f"✗ ashborn.agent: {e}")
    import traceback
    traceback.print_exc()

try:
    from ashborn.cognition import AshbornThinker, AshbornLoop
    print("✓ ashborn.cognition (AshbornThinker, AshbornLoop)")
except Exception as e:
    print(f"✗ ashborn.cognition: {e}")
    import traceback
    traceback.print_exc()

try:
    from ashborn.tools.project_generator import project_generator_tool
    print("✓ ashborn.tools.project_generator (project_generator_tool)")
except Exception as e:
    print(f"✗ ashborn.tools.project_generator: {e}")
    import traceback
    traceback.print_exc()

print("--- Done ---")
