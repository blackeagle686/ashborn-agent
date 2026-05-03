import asyncio
import os
from dotenv import load_dotenv

# Load API keys from .env
load_dotenv()

from ashborn.agent import get_ashborn_agent

async def main():
    print("========================================")
    print("🚀 Initializing Ashborn Agent Test")
    print("========================================\n")
    
    agent = await get_ashborn_agent()
    
    prompt = "Create a new python package called 'math_utils'. It must contain an __init__.py, a calc.py with a factorial function, and a test_calc.py that asserts factorial(5) == 120. Please generate them together in one pass."
    
    print(f"[USER PROMPT]: {prompt}\n")
    print("⏳ Running agent in FULL PLAN MODE...\n")
    
    try:
        # Agent.run_stream abstracts away the session & memory and uses AshbornLoop.run_stream internally.
        async for chunk in agent.run_stream(prompt, mode="plan"):
            ctype = chunk.get("type")
            role = chunk.get("role", "SYSTEM").upper()
            content = chunk.get("content", "")
            
            if ctype == "status":
                print(f"\n[{role} STATUS] => {content}")
            elif ctype == "chunk":
                # Print streaming text immediately
                print(content, end="", flush=True)
            elif ctype == "thought":
                print(f"\n[{role} THOUGHT] => {content}")
            else:
                print(f"\n[EVENT: {ctype}] => {content}")
                
    except Exception as e:
        print(f"\n[ERROR] => {e}")
        import traceback
        traceback.print_exc()
        
    print("\n\n========================================")
    print("✅ Test Complete!")
    print("========================================")

if __name__ == "__main__":
    asyncio.run(main())
