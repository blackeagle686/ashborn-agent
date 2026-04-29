import typer
import asyncio
import os
from dotenv import load_dotenv

# Set log level to suppress telemetry info logs by default in the CLI
os.environ["LOG_LEVEL"] = "WARNING"

# Silence HuggingFace specific warnings and progress bars
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.rule import Rule
from rich.text import Text
from rich.theme import Theme
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.live import Live

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
    # Show an attractive progress bar during initialization
    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[bold #ff8c00]{task.description}[/bold #ff8c00]"),
        BarColumn(bar_width=40, complete_style="#ff8c00", finished_style="bold green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=True
    ) as progress:
        startup_task = progress.add_task("Awakening Ashborn Agent...", total=100)
        
        def on_startup(p, m):
            progress.update(startup_task, completed=p*100, description=f"{m}...")
            
        agent = await get_ashborn_agent(on_startup_progress=on_startup)
    
    console.print()
    console.print(Panel(
        Text.assemble(
            ("\n  🐦‍🔥 ", "bold #ff8c00"),
            ("ASHBORN AGENT CLI", "bold #ff8c00 underline"),
            ("\n  ", ""),
            ("Powered by Phoenix AI Framework", "italic dim white"),
            ("\n\n  ", ""),
            ("Ready to manifest your vision into production-ready code.", "white"),
            ("\n  ", ""),
            ("Type ", "dim white"),
            ("exit", "bold cyan"),
            (" or ", "dim white"),
            ("quit", "bold cyan"),
            (" to leave. Let's build something amazing!", "dim white")
        ),
        border_style="#ff8c00",
        padding=(1, 4),
        title="[bold white]WELCOME[/bold white]",
        title_align="left"
    ))
    console.print(Rule(style="#ff8c00"))
    
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
            full_response = ""
            # Get the generator but don't start it yet
            gen = agent.run_stream(user_input, mode="auto")
            
            # Phase 1: Status reporting (using console.status for a clean, transient look)
            with console.status("[assistant]Ashborn is focusing...[/assistant]", spinner="bouncingBar") as status:
                async for event in gen:
                    if event["type"] == "status":
                        status.update(f"[assistant]🐦‍🔥 {event['content']}[/assistant]")
                    elif event["type"] == "chunk":
                        # First chunk of content arrived!
                        full_response = event["content"]
                        break
            
            # Phase 2: Content streaming (using Live for real-time Markdown rendering)
            if full_response:
                console.print(Text("Ashborn", style="assistant"))
                with Live(Markdown(full_response), console=console, refresh_per_second=12) as live:
                    async for event in gen:
                        if event["type"] == "chunk":
                            full_response += event["content"]
                            live.update(Markdown(full_response))
            
            console.print()
            console.print(Rule(style="dim"))
            
        except Exception as e:
            console.print(f"\n[error]Error:[/error] {str(e)}\n")
            console.print(Rule(style="dim"))

async def _generate_task(project_name: str, project_type: str):
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]{task.description}[/bold green]"),
            BarColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"Initializing for {project_name}...", total=100)
            
            def on_startup(p, m):
                progress.update(task, completed=p*100, description=f"{m}...")
                
            agent = await get_ashborn_agent(on_startup_progress=on_startup)
            
        console.print(f"\n[success]🚀 Generating {project_type} project: {project_name}...[/success]\n")
        prompt = f"Please generate a production-ready project named {project_name} of type {project_type}."
        
        full_response = ""
        gen = agent.run_stream(prompt, mode="plan")
        
        with console.status(f"[assistant]Ashborn is scaffolding {project_name}...[/assistant]", spinner="bouncingBar") as status:
            async for event in gen:
                if event["type"] == "status":
                    status.update(f"[assistant]🐦‍🔥 {event['content']}[/assistant]")
                elif event["type"] == "chunk":
                    full_response = event["content"]
                    break
                    
        if full_response:
            console.print(Text("Ashborn Output", style="assistant"))
            with Live(Panel(Markdown(full_response), title="[assistant]Ashborn Output[/assistant]", border_style="green"), console=console, refresh_per_second=12) as live:
                async for event in gen:
                    if event["type"] == "chunk":
                        full_response += event["content"]
                        live.update(Panel(Markdown(full_response), title="[assistant]Ashborn Output[/assistant]", border_style="green"))
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
