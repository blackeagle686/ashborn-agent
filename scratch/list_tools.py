import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from ashborn.agent import get_ashborn_agent

async def list_tools():
    agent = await get_ashborn_agent()
    print("Registered tools keys:")
    print(agent.tools.get_all_tools_info().keys())

if __name__ == "__main__":
    asyncio.run(list_tools())
