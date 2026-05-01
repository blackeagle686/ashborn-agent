from phoenix.framework.agent import tool

@tool(
    name="vscode_search",
    description=(
        "Searches for a text pattern or regular expression across all files in the current workspace using VS Code's native search engine. "
        "Input: 'query' (str), 'is_regex' (bool, default False), 'include' (str, glob pattern like '**/*.ts'), 'exclude' (str, glob pattern). "
        "Returns a list of matching files and line snippets."
    )
)
async def vscode_search_tool(query: str, is_regex: bool = False, include: str = None, exclude: str = None, **context) -> str:
    """
    Performs a workspace-wide search by calling back into the VS Code extension.
    """
    # 'vscode_call' is injected by the server into the tool's context
    vscode_call = context.get("vscode_call")
    if not vscode_call:
        return "ERROR: VS Code communication bridge not available in this environment."

    # Request the search from VS Code
    # The server will emit a 'vscode_tool' event to the frontend, 
    # and wait for the /tool/result response.
    
    # We need to inform the agent's run_stream that it needs to emit an event.
    # However, since the tool itself is async, it can just wait for the IPC.
    
    # Actually, we need to EMIT the event before we wait!
    # The server's call_vscode_tool doesn't know how to emit to the active stream.
    # We should have the tool emit a status update that the frontend catches.
    
    # Wait, the Phoenix Agent's tool context has access to the observer?
    # No, but we can return a special string that the server catches, or just use the IPC.
    
    # Let's use the tool's context to emit. 
    # Actually, the simplest way: the server's call_vscode_tool will handle it.
    
    # Wait, I need a way for the server's call_vscode_tool to tell the generator to yield.
    # This is tricky with SSE.
    
    # Better: the tool call ID is enough. The server can just yield a special event.
    
    result = await vscode_call("search", {
        "query": query,
        "is_regex": is_regex,
        "include": include,
        "exclude": exclude
    })
    
    return result
