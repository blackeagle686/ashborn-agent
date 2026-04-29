import typer
import asyncio
import os
from dotenv import load_dotenv

# Set log level to suppress telemetry info logs by default in the CLI
os.environ["LOG_LEVEL"] = "WARNING"

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.rule import Rule
from rich.text import Text
from rich.theme import Theme

from agent import get_ashborn_agent

# Load environment variables
load_dotenv()

# Define a custom, attractive theme
custom_theme = Theme({
    "user": "bold cyan",
    "assistant": "bold #ff8c00", # Phoenix Orange
    "info": "dim white",
    "error": "bold red",
    "success": "bold green"
})

app = typer.Typer(help="Ashborn Agent CLI - Generate production-ready projects.")
console = Console(theme=custom_theme)

async def _interactive_loop():
    # Show an attractive spinner during initialization
    with console.status("[info]Initializing Ashborn Agent services...[/info]", spinner="point"):
        agent = await get_ashborn_agent()
    
    console.print()
    console.print(Panel(
        "[bold #ff8c00]🐦‍🔥 Ashborn Agent CLI[/bold #ff8c00]\n"
        "[dim]Powered by Phoenix AI Framework[/dim]\n\n"
        "Type [bold cyan]exit[/bold cyan] or [bold cyan]quit[/bold cyan] to leave. Ready to build!",
        border_style="#ff8c00",
        padding=(1, 2)
    ))
    console.print(Rule(style="dim"))
    
    while True:
        console.print()
        user_input = Prompt.ask(Text("You", style="user"))
        
        if user_input.lower() in ['exit', 'quit']:
            console.print("\n[info]Shutting down Ashborn... Goodbye![/info]")
            break
            
        if not user_input.strip():
            continue
            
        console.print()
        
        try:
            # Show a dynamic spinner while the agent thinks and acts
            with console.status("[assistant]Ashborn is analyzing and planning...[/assistant]", spinner="bouncingBar") as status:
                def update_status(message: str):
                    status.update(f"[assistant]Ashborn: {message}[/assistant]")
                
                response = await agent.run(user_input, mode="auto", on_progress=update_status)
            
            # Render response as elegant Markdown (with syntax highlighting)
            md = Markdown(response)
            console.print(Text("Ashborn", style="assistant"))
            console.print(md)
            console.print()
            console.print(Rule(style="dim"))
            
        except Exception as e:
            console.print(f"\n[error]Error:[/error] {str(e)}\n")
            console.print(Rule(style="dim"))

async def _generate_task(project_name: str, project_type: str):
    with console.status("[info]Initializing Ashborn Agent services...[/info]", spinner="point"):
        agent = await get_ashborn_agent()
    
    console.print(f"\n[success]Generating {project_type} project: {project_name}...[/success]\n")
    prompt = f"Please generate a production-ready project named {project_name} of type {project_type}."
    
    try:
        with console.status(f"[assistant]Ashborn is scaffolding {project_name}...[/assistant]", spinner="bouncingBar") as status:
            def update_status(message: str):
                status.update(f"[assistant]Ashborn: {message}[/assistant]")
            response = await agent.run(prompt, mode="plan", on_progress=update_status) 
            
        md = Markdown(response)
        console.print(Panel(md, title="[assistant]Ashborn Output[/assistant]", border_style="green"))
    except Exception as e:
        console.print(f"\n[error]Error:[/error] {str(e)}")

@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        asyncio.run(_interactive_loop())

@app.command()
def interact():
    """
    Start an interactive session with the Ashborn agent.
    """
    asyncio.run(_interactive_loop())

@app.command()
def generate(project_name: str, project_type: str):
    """
    Quickly generate a project without entering interactive mode.
    """
    asyncio.run(_generate_task(project_name, project_type))

if __name__ == "__main__":
    app()
