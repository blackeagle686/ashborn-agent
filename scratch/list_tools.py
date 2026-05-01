import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from ashborn.agent import get_ashborn_agent

async def list_tools():
    agent = await get_ashborn_agent()
    print("Registered tools:")
    for name, tool in agent.tools.get_all_tools().items():
        print(f"  - {name}")

if __name__ == "__main__":
    asyncio.run(list_tools())
