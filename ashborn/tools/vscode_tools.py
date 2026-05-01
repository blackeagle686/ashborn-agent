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
    from ashborn.server import vscode_ipc_context
    vscode_call = vscode_ipc_context.get()
    
    if not vscode_call:
        return "ERROR: VS Code communication bridge not available in this environment."

    # Request the search from VS Code
    result = await vscode_call("search", {
        "query": query,
        "is_regex": is_regex,
        "include": include,
        "exclude": exclude
    })
    
    return result
