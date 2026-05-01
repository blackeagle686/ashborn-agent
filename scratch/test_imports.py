import sys
import os

# Add venv site-packages to path just in case
venv_site_packages = os.path.join(os.getcwd(), "venv/lib/python3.12/site-packages")
if venv_site_packages not in sys.path:
    sys.path.insert(0, venv_site_packages)

print("--- Testing Imports ---")

try:
    from phoenix import Agent, init_phoenix, startup_phoenix
    print("✓ phoenix (Agent, init_phoenix, startup_phoenix)")
except ImportError as e:
    print(f"✗ phoenix: {e}")

try:
    from phoenix.framework.agent.cognition import Thinker, Planner, Reflector
    print("✓ phoenix.framework.agent.cognition (Thinker, Planner, Reflector)")
except ImportError as e:
    print(f"✗ phoenix.framework.agent.cognition: {e}")

try:
    from phoenix.framework.agent.core.loop import AgentLoop
    print("✓ phoenix.framework.agent.core.loop (AgentLoop)")
except ImportError as e:
    print(f"✗ phoenix.framework.agent.core.loop: {e}")

try:
    from phoenix.framework.agent.tools import FileReadTool, FileWriteTool, FileEditTool
    print("✓ phoenix.framework.agent.tools (FileReadTool, FileWriteTool, FileEditTool)")
except ImportError as e:
    print(f"✗ phoenix.framework.agent.tools: {e}")

try:
    from phoenix.framework.agent import tool
    print("✓ phoenix.framework.agent (tool)")
except ImportError as e:
    print(f"✗ phoenix.framework.agent: {e}")

print("--- Done ---")
