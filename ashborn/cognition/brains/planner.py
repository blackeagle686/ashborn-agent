from phoenix.framework.agent.cognition.planner.planner import Planner

class AshbornPlanner(Planner):
    """
    Ashborn Planner utilizing the updated Phoenix AI planner -> actor -> reflector architecture.
    Inherits stateful task tracking and precise tool action selection natively.
    """
    
    def __init__(self, llm, tools, task_store=None, profile=None):
        super().__init__(llm, tools, task_store=task_store, profile=profile)
