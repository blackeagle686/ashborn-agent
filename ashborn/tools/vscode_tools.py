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
@tool(
    name="vscode_create_file",
    description=(
        "Creates a new file in the workspace with the specified content. "
        "Input: 'path' (str), 'content' (str). "
        "Returns a success message or an error."
    )
)
async def vscode_create_file_tool(path: str, content: str, **context) -> str:
    """
    Creates a file by calling back into the VS Code extension.
    """
    from ashborn.server import vscode_ipc_context
    vscode_call = vscode_ipc_context.get()
    if not vscode_call:
        return "ERROR: VS Code communication bridge not available."
    return await vscode_call("create_file", {"path": path, "content": content})

@tool(
    name="vscode_edit_file",
    description=(
        "Updates an existing file in the workspace with new content. "
        "The user will be prompted to review a diff before applying. "
        "Input: 'path' (str), 'content' (str). "
        "Returns a success message, 'REJECTED', or an error."
    )
)
async def vscode_edit_file_tool(path: str, content: str, **context) -> str:
    """
    Edits a file by calling back into the VS Code extension (shows diff).
    """
    from ashborn.server import vscode_ipc_context
    vscode_call = vscode_ipc_context.get()
    if not vscode_call:
        return "ERROR: VS Code communication bridge not available."
    return await vscode_call("edit_file", {"path": path, "content": content})

@tool(
    name="vscode_delete_file",
    description=(
        "Deletes a file or directory in the workspace. "
        "The user will be prompted for confirmation. "
        "Input: 'path' (str). "
        "Returns a success message, 'REJECTED', or an error."
    )
)
async def vscode_delete_file_tool(path: str, **context) -> str:
    """
    Deletes a file by calling back into the VS Code extension (requires confirmation).
    """
    from ashborn.server import vscode_ipc_context
    vscode_call = vscode_ipc_context.get()
    if not vscode_call:
        return "ERROR: VS Code communication bridge not available."
    return await vscode_call("delete_file", {"path": path})
 
+@tool(
+    name="vscode_terminal_run",
+    description=(
+        "Executes a bash command in a dedicated VS Code terminal and captures the output. "
+        "Input: 'command' (str). "
+        "Returns the stdout/stderr of the command."
+    )
+)
+async def vscode_terminal_run_tool(command: str, **context) -> str:
+    """
+    Executes a terminal command via the VS Code extension.
+    """
+    from ashborn.server import vscode_ipc_context
+    vscode_call = vscode_ipc_context.get()
+    if not vscode_call:
+        return "ERROR: VS Code communication bridge not available."
+    return await vscode_call("terminal_run", {"command": command})
