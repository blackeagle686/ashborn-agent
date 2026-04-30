from phoenix.agent import Agent
from phoenix import init_phoenix, startup_phoenix
from .tools.project_generator import project_generator_tool

async def get_ashborn_agent(on_startup_progress=None):
    """
    Initializes the Phoenix framework, starts up services, and returns the Ashborn agent.
    """
    init_phoenix()
    await startup_phoenix(on_progress=on_startup_progress)
    from .cognition import AshbornThinker, AshbornPlanner
    
    # 2. Create the agent with upgraded cognition modules
    agent = Agent(
        thinker=AshbornThinker(),
        planner=AshbornPlanner()
    )
    
    agent.register_tool(project_generator_tool)
    
    return agent
