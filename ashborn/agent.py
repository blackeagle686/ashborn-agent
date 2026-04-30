from phoenix.agent import Agent
from phoenix import init_phoenix, startup_phoenix
from .tools.project_generator import project_generator_tool

async def get_ashborn_agent(on_startup_progress=None):
    """
    Initializes the Phoenix framework, starts up services, and returns the Ashborn agent.
    """
    init_phoenix()
    await startup_phoenix()
    from .cognition import AshbornThinker, AshbornPlanner, AshbornReflector
    
    # 2. Create the agent with upgraded cognition modules
    agent = Agent(
        component_factories={
            "thinker": lambda **ctx: AshbornThinker(ctx["llm"]),
            "planner": lambda **ctx: AshbornPlanner(ctx["llm"], ctx["tools"]),
            "reflector": lambda **ctx: AshbornReflector(ctx["llm"]),
        }
    )
    
    from phoenix.tools.io import FileReadTool, FileWriteTool, FileEditTool
    
    agent.register_tool(FileReadTool())
    agent.register_tool(FileWriteTool())
    agent.register_tool(FileEditTool())
    agent.register_tool(project_generator_tool)
    
    return agent
