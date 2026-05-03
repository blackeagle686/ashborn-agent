from phoenix import Agent, init_phoenix, startup_phoenix
from .tools.project_generator import project_generator_tool
from .tools.file_tools import file_read_lines_tool, file_update_multi_tool

async def get_ashborn_agent(on_startup_progress=None):
    """
    Initializes the Phoenix framework, starts up services, and returns the Ashborn agent.
    """
    init_phoenix()
    await startup_phoenix()
    from .cognition import AshbornThinker, AshbornPlanner, AshbornReflector, AshbornLoop
    
    # Create the agent with the task-file driven loop and upgraded cognition modules
    agent = Agent(
        loop_cls=AshbornLoop,
        component_factories={
            "thinker": lambda **ctx: AshbornThinker(ctx["llm"]),
            "planner": lambda **ctx: AshbornPlanner(ctx["llm"], ctx["tools"]),
            "reflector": lambda **ctx: AshbornReflector(ctx["llm"]),
        }
    )
    
    from .tools.project_generator import project_generator_tool, terminal_tool
    from .tools.vscode_tools import vscode_search_tool, vscode_create_file_tool, vscode_edit_file_tool, vscode_delete_file_tool, vscode_terminal_run_tool
    from .tools.file_tools import file_read_lines_tool, file_update_multi_tool, file_write_tool
    from phoenix.framework.agent.tools import FileReadTool, FileEditTool
    
    agent.register_tool(FileReadTool())
    agent.register_tool(file_write_tool) # Using our reliable custom tool
    agent.register_tool(FileEditTool())
    agent.register_tool(project_generator_tool)
    agent.register_tool(terminal_tool)
    agent.register_tool(vscode_search_tool)
    agent.register_tool(vscode_create_file_tool)
    agent.register_tool(vscode_edit_file_tool)
    agent.register_tool(vscode_delete_file_tool)
    agent.register_tool(vscode_terminal_run_tool)
    agent.register_tool(file_read_lines_tool)   # numbered output for precise edits
    agent.register_tool(file_update_multi_tool) # surgical multi-block editor
    
    return agent
