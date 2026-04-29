import os
from phoenix.agent import Agent
from phoenix.tools import Tool
# We will use the proper imports when the installation is done, 
# for now I'll stub out the agent initialization.
from tools.project_generator import project_generator_tool

# Instantiate Ashborn Agent
# Depending on how phx-ashborn is structured, this might look like:
# We know it has Analyzer, Thinker, Engineering toolsets.
# The user wants it to be an expert in generating production ready code.

def get_ashborn_agent():
    # Setup agent with Phoenix framework
    agent = Agent(
        name="Ashborn",
        role="Senior Developer & Project Architect",
        goal="Generate production-ready project structures, setup environments, and configure boilerplate effectively.",
        backstory="A battle-hardened software architect with deep knowledge in modern best practices, microservices, and high-performance design patterns.",
        tools=[project_generator_tool],
        verbose=True
    )
    return agent
