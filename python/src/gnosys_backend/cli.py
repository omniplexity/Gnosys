"""
Gnosys CLI - Command-line interface for Gnosys memory backend.

Provides commands for interacting with the Gnosys memory system:
- status: Show backend status and statistics
- help: Display help information
- store: Store a new memory
- get: Retrieve a memory by ID
- search: Search memories
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

from gnosys_backend.config import AppConfig, load_config

app = typer.Typer(
    name="gnosys",
    help="Gnosys Memory Backend CLI",
    add_completion=False,
)
console = Console()


class GnosysCLIError(Exception):
    """CLI-specific error."""

    def __init__(
        self,
        message: str,
        code: int = 1,
        suggestions: list[str] | None = None,
    ):
        self.message = message
        self.code = code
        self.suggestions = suggestions or []
        super().__init__(message)


def get_backend_url(config: AppConfig) -> str:
    """Get the backend URL from config."""
    return f"http://{config.host}:{config.port}"


def make_request(
    method: str,
    url: str,
    timeout: float = 10.0,
    **kwargs: Any,
) -> dict[str, Any]:
    """Make HTTP request to backend with error handling."""
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError as e:
        raise GnosysCLIError(
            message=f"Cannot connect to Gnosys backend at {url}",
            code=1001,
            suggestions=[
                "Ensure the backend is running: gnosys-backend",
                "Check the port configuration in config.json",
                "Verify no firewall is blocking the connection",
            ],
        ) from e
    except httpx.TimeoutException as e:
        raise GnosysCLIError(
            message=f"Request timed out after {timeout}s",
            code=1002,
            suggestions=[
                "Increase timeout with --timeout option",
                "Check backend responsiveness",
            ],
        ) from e
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json().get("detail", str(e))
        raise GnosysCLIError(
            message=error_detail,
            code=e.response.status_code,
            suggestions=["Check the API endpoint", "Review request parameters"],
        ) from e
    except json.JSONDecodeError as e:
        raise GnosysCLIError(
            message=f"Invalid JSON response from backend: {e}",
            code=1003,
            suggestions=["Backend may be down or returning errors"],
        ) from e


def format_error(error: Exception) -> str:
    """Format error as structured output."""
    if isinstance(error, GnosysCLIError):
        output = {
            "error": {
                "code": error.code,
                "message": error.message,
            }
        }
        if error.suggestions:
            output["error"]["suggestions"] = error.suggestions
        return json.dumps(output, indent=2)

    # Handle other exceptions
    return json.dumps(
        {
            "error": {
                "code": 1,
                "message": str(error),
            }
        },
        indent=2,
    )


@app.command()
def status(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show verbose status information",
    ),
) -> None:
    """
    Show Gnosys backend status and statistics.

    Returns backend URL, database path, memory count, and uptime.
    """
    try:
        config = load_config()
        backend_url = get_backend_url(config)

        # Get health status
        health_data = make_request("GET", f"{backend_url}/health")

        # Get stats
        stats_data = make_request("GET", f"{backend_url}/stats")

        # Calculate uptime
        start_time = time.time()
        uptime_seconds = (
            start_time - start_time
        )  # Placeholder - would need backend to track this

        if verbose:
            console.print("\n[bold cyan]Gnosys Backend Status[/bold cyan]")
            console.print(f"  Status: {health_data.get('status', 'unknown')}")
            console.print(f"  Version: {health_data.get('version', 'unknown')}")
            console.print(f"  Service: {health_data.get('service', 'unknown')}")
            console.print(f"  Backend URL: {backend_url}")
            console.print(f"  Database: {health_data.get('database', 'unknown')}")

            console.print("\n[bold cyan]Statistics[/bold cyan]")
            console.print(f"  Total memories: {stats_data.get('total_memories', 0)}")

            # Memory breakdown by tier
            tiers = stats_data.get("by_tier", {})
            if tiers:
                console.print("  By tier:")
                for tier_name, count in tiers.items():
                    console.print(f"    {tier_name}: {count}")

            # Memory breakdown by type
            types = stats_data.get("by_type", {})
            if types:
                console.print("  By type:")
                for type_name, count in types.items():
                    console.print(f"    {type_name}: {count}")
        else:
            # Compact output
            output = {
                "status": health_data.get("status"),
                "version": health_data.get("version"),
                "backend_url": backend_url,
                "database": str(Path(health_data.get("database", "")).name),
                "total_memories": stats_data.get("total_memories", 0),
            }
            console.print(json.dumps(output, indent=2))

    except GnosysCLIError as e:
        console.print(format_error(e), style="bold red")
        raise typer.Exit(code=e.code)


@app.command()
def help(
    command: Optional[str] = typer.Argument(
        None,
        help="Show help for specific command",
    ),
) -> None:
    """
    Display help information for Gnosys commands.

    Shows all commands with usage examples.
    """
    if command:
        # Show help for specific command
        if command == "status":
            console.print("[bold]gnosys status[/bold]")
            console.print("  Show backend status and statistics")
            console.print("")
            console.print("  [bold]Options:[/bold]")
            console.print("    -v, --verbose    Show verbose status information")
            console.print("")
            console.print("  [bold]Examples:[/bold]")
            console.print("    gnosys status")
            console.print("    gnosys status --verbose")
            return
        elif command == "help":
            console.print("[bold]gnosys help [command][/bold]")
            console.print("  Display help information")
            return
        elif command == "store":
            console.print("[bold]gnosys store --content <text>[/bold]")
            console.print("  Store a new memory in the backend")
            console.print("")
            console.print("  [bold]Options:[/bold]")
            console.print("    -c, --content    Required. The memory content to store")
            console.print(
                "    -t, --type    Memory type (conversational, procedural, factual)"
            )
            console.print(
                "    -i, --tier    Memory tier (working, episodic, semantic, archive)"
            )
            console.print("    --tags       Comma-separated tags")
            console.print("")
            console.print("  [bold]Examples:[/bold]")
            console.print('    gnosys store --content "Remember to buy milk"')
            console.print('    gnosys store -c "Task completed" -t factual -i semantic')
            return
        elif command == "get":
            console.print("[bold]gnosys get <id>[/bold]")
            console.print("  Retrieve a memory by ID")
            console.print("")
            console.print("  [bold]Arguments:[/bold]")
            console.print("    <id>    Required. The memory ID to retrieve")
            console.print("")
            console.print("  [bold]Examples:[/bold]")
            console.print("    gnosys get abc123")
            return
        elif command == "search":
            console.print("[bold]gnosys search <query>[/bold]")
            console.print("  Search memories by keyword")
            console.print("")
            console.print("  [bold]Arguments:[/bold]")
            console.print("    <query>    Required. Search query")
            console.print("")
            console.print("  [bold]Options:[/bold]")
            console.print("    -l, --limit    Max results (1-100)")
            console.print("    -t, --type    Filter by memory type")
            console.print("    -i, --tier    Filter by tier")
            console.print("")
            console.print("  [bold]Examples:[/bold]")
            console.print("    gnosys search project")
            console.print("    gnosys search deadline -l 5")
            return
        elif command == "stats":
            console.print("[bold]gnosys stats[/bold]")
            console.print("  Show memory statistics by type and tier")
            return
        elif command == "backup":
            console.print(
                "[bold]gnosys backup [--type full|incremental] [--components <list>][/bold]"
            )
            console.print("  Create a backup of Gnosys data")
            console.print("")
            console.print("  [bold]Options:[/bold]")
            console.print("    -t, --type         Backup type (full, incremental)")
            console.print(
                "    -c, --components  Comma-separated components (database,vectors,skills)"
            )
            console.print("")
            console.print("  [bold]Examples:[/bold]")
            console.print("    gnosys backup")
            console.print("    gnosys backup --type full")
            console.print("    gnosys backup -t incremental -c database,vectors")
            return
        elif command == "list-backups":
            console.print("[bold]gnosys list-backups[/bold]")
            console.print("  List all available backups")
            return
        elif command == "restore":
            console.print(
                "[bold]gnosys restore --backup-path <path> --target <dir>[/bold]"
            )
            console.print("  Restore Gnosys from a backup")
            console.print("")
            console.print("  [bold]Options:[/bold]")
            console.print("    -b, --backup-path  Path to backup file")
            console.print("    -t, --target       Target directory for restore")
            console.print("    --overwrite        Overwrite existing files")
            console.print("")
            console.print("  [bold]Examples:[/bold]")
            console.print("    gnosys restore -b ./backup.tar.gz -t ./data")
            return
        elif command == "context":
            console.print("[bold]gnosys context <query> [options][/bold]")
            console.print("  Retrieve context from memory for a query")
            console.print("")
            console.print("  [bold]Arguments:[/bold]")
            console.print("    <query>    Required. Query to retrieve context for")
            console.print("")
            console.print("  [bold]Options:[/bold]")
            console.print(
                "    -m, --max-tokens  Maximum tokens to retrieve (default: 4096)"
            )
            console.print(
                "    -t, --tiers       Comma-separated tiers (working,episodic,semantic,archive)"
            )
            console.print("")
            console.print("  [bold]Examples:[/bold]")
            console.print('    gnosys context "my project details"')
            console.print('    gnosys context "project" -m 2048 -t working,episodic')
            return
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            raise typer.Exit(code=1)

    # Show general help
    console.print("[bold cyan]Gnosys CLI Help[/bold cyan]\n")
    console.print("Usage: gnosys <command> [options]\n")
    console.print("[bold]Commands:[/bold]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    table.add_row("status", "Show backend status and statistics")
    table.add_row("help", "Display help information")
    table.add_row("store", "Store a new memory")
    table.add_row("get", "Retrieve a memory by ID")
    table.add_row("search", "Search memories")
    table.add_row("stats", "Show memory statistics")
    table.add_row("backup", "Create a backup")
    table.add_row("list-backups", "List available backups")
    table.add_row("restore", "Restore from a backup")
    table.add_row("context", "Retrieve context for a query")
    table.add_row("schedule", "Manage scheduled tasks")
    table.add_row("detect-skills", "Detect skills from trajectories")
    table.add_row("skills", "List, view, create, delete skills")

    console.print(table)

    console.print("\n[bold]Examples:[/bold]")
    console.print("  gnosys status --verbose")
    console.print('  gnosys store --content "Remember this"')
    console.print("  gnosys get abc123")
    console.print("  gnosys search project --limit 10")
    console.print("  gnosys stats")
    console.print("  gnosys backup")
    console.print("  gnosys list-backups")
    console.print('  gnosys context "project details" --max-tokens 2048')

    console.print("\n[bold]Get help for a command:[/bold]")
    console.print("  gnosys help <command>")


@app.command()
def store(
    content: str = typer.Option(
        ...,
        "--content",
        "-c",
        help="The memory content to store",
    ),
    memory_type: str = typer.Option(
        "conversational",
        "--type",
        "-t",
        help="Memory type (conversational, procedural, factual)",
    ),
    tier: str = typer.Option(
        "semantic",
        "--tier",
        "-i",
        help="Memory tier (working, episodic, semantic, archive)",
    ),
    tags: str = typer.Option(
        "",
        "--tags",
        help="Comma-separated tags",
    ),
) -> None:
    """
    Store a new memory in the backend.

    Saves the content to the database with specified type and tier.
    """
    try:
        config = load_config()
        backend_url = get_backend_url(config)

        # Prepare request
        payload: dict[str, Any] = {
            "content": content,
            "memory_type": memory_type,
            "tier": tier,
        }
        if tags:
            payload["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

        # Store memory
        result = make_request(
            "POST",
            f"{backend_url}/memories",
            json=payload,
        )

        memory = result.get("memory", {})
        console.print(json.dumps(memory, indent=2, default=str))

    except GnosysCLIError as e:
        console.print(format_error(e), style="bold red")
        raise typer.Exit(code=e.code)


@app.command()
def get(
    memory_id: str = typer.Argument(..., help="The memory ID to retrieve"),
) -> None:
    """
    Retrieve a memory by ID.

    Returns the full memory record including content and metadata.
    """
    try:
        config = load_config()
        backend_url = get_backend_url(config)

        # Get memory
        result = make_request("GET", f"{backend_url}/memories/{memory_id}")

        memory = result.get("memory", {})
        console.print(json.dumps(memory, indent=2, default=str))

    except GnosysCLIError as e:
        console.print(format_error(e), style="bold red")
        raise typer.Exit(code=e.code)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        help="Maximum number of results",
        min=1,
        max=100,
    ),
    memory_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by memory type",
    ),
    tier: Optional[str] = typer.Option(
        None,
        "--tier",
        "-i",
        help="Filter by tier",
    ),
) -> None:
    """
    Search memories by keyword.

    Returns matching memories with relevance scores.
    """
    try:
        config = load_config()
        backend_url = get_backend_url(config)

        # Prepare params
        params: dict[str, Any] = {"q": query, "limit": limit}
        if memory_type:
            params["memory_type"] = memory_type
        if tier:
            params["tier"] = tier

        # Search
        result = make_request("GET", f"{backend_url}/memories/search", params=params)

        results = result.get("results", [])
        console.print(json.dumps(result, indent=2, default=str))

    except GnosysCLIError as e:
        console.print(format_error(e), style="bold red")
        raise typer.Exit(code=e.code)


@app.command()
def stats() -> None:
    """
    Show memory statistics by type and tier.

    Displays counts of memories grouped by type and tier.
    """
    try:
        config = load_config()
        backend_url = get_backend_url(config)

        # Get stats
        stats_data = make_request("GET", f"{backend_url}/stats")

        console.print(json.dumps(stats_data, indent=2, default=str))

    except GnosysCLIError as e:
        console.print(format_error(e), style="bold red")
        raise typer.Exit(code=e.code)


@app.command()
def backup(
    backup_type: str = typer.Option(
        "full",
        "--type",
        "-t",
        help="Backup type: full, incremental",
    ),
    components: str = typer.Option(
        "database,vectors",
        "--components",
        "-c",
        help="Comma-separated components to backup",
    ),
) -> None:
    """
    Create a backup of Gnosys data.

    Backs up database, vectors, and other components.
    """
    try:
        config = load_config()
        backend_url = get_backend_url(config)

        payload = {
            "backup_type": backup_type,
            "components": [c.strip() for c in components.split(",")],
        }

        result = make_request("POST", f"{backend_url}/backup", json=payload)
        console.print(json.dumps(result, indent=2))

    except GnosysCLIError as e:
        console.print(format_error(e), style="bold red")
        raise typer.Exit(code=e.code)


@app.command()
def list_backups() -> None:
    """
    List all available backups.
    """
    try:
        config = load_config()
        backend_url = get_backend_url(config)

        result = make_request("GET", f"{backend_url}/backup")
        console.print(json.dumps(result, indent=2))

    except GnosysCLIError as e:
        console.print(format_error(e), style="bold red")
        raise typer.Exit(code=e.code)


@app.command()
def restore(
    backup_path: str = typer.Option(
        ...,
        "--backup-path",
        "-b",
        help="Path to backup file",
    ),
    target_dir: str = typer.Option(
        ...,
        "--target",
        help="Target directory for restore",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing files",
    ),
) -> None:
    """
    Restore Gnosys from a backup.
    """
    try:
        config = load_config()
        backend_url = get_backend_url(config)

        payload = {
            "backup_path": backup_path,
            "target_dir": target_dir,
            "overwrite": overwrite,
        }

        result = make_request("POST", f"{backend_url}/restore", json=payload)
        console.print(json.dumps(result, indent=2))

    except GnosysCLIError as e:
        console.print(format_error(e), style="bold red")
        raise typer.Exit(code=e.code)


@app.command()
def context(
    query: str = typer.Argument(..., help="Query to retrieve context for"),
    max_tokens: int = typer.Option(
        4096,
        "--max-tokens",
        "-m",
        help="Maximum tokens to retrieve",
    ),
    tiers: str = typer.Option(
        "working,episodic,semantic",
        "--tiers",
        "-t",
        help="Comma-separated tiers to include",
    ),
) -> None:
    """
    Retrieve context from memory for a query.

    Retrieves relevant memories from the specified tiers to use as context.
    """
    try:
        config = load_config()
        backend_url = get_backend_url(config)

        tier_list = [t.strip() for t in tiers.split(",")]
        payload = {
            "query": query,
            "max_tokens": max_tokens,
            "include_tiers": tier_list,
        }

        result = make_request("POST", f"{backend_url}/context/retrieve", json=payload)

        console.print(f"[bold]Query:[/bold] {result.get('query')}")
        console.print(
            f"[bold]Used Tokens:[/bold] {result.get('used_tokens')} / {result.get('token_budget')}"
        )
        console.print(
            f"[bold]Tiers:[/bold] {', '.join(result.get('tiers_included', []))}"
        )
        console.print("")
        console.print("[bold]Context:[/bold]")
        console.print(result.get("assembly_text", ""))

    except GnosysCLIError as e:
        console.print(format_error(e), style="bold red")
        raise typer.Exit(code=e.code)


@app.command()
def schedule(
    action: str = typer.Argument(..., help="Action: list, add, run, delete"),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Task name (for add/delete)"
    ),
    task_type: str = typer.Option("health_check", "--type", "-t", help="Task type"),
    schedule: str = typer.Option(
        "@every 15m", "--schedule", "-s", help="Cron schedule or @every interval"
    ),
    task_id: Optional[str] = typer.Option(
        None, "--id", "-i", help="Task ID (for run/delete)"
    ),
) -> None:
    """
    Manage scheduled tasks.

    List, add, run, or delete scheduled tasks.
    """
    try:
        config = load_config()
        backend_url = get_backend_url(config)

        if action == "list":
            result = make_request("GET", f"{backend_url}/scheduler/tasks")
            tasks = result.get("tasks", [])
            if not tasks:
                console.print("[yellow]No scheduled tasks found.[/yellow]")
                return

            table = Table(show_header=True, header_style="bold")
            table.add_column("Name")
            table.add_column("Type")
            table.add_column("Schedule")
            table.add_column("Enabled")
            table.add_column("Next Run")

            for task in tasks:
                table.add_row(
                    task.get("name", ""),
                    task.get("task_type", ""),
                    task.get("schedule", ""),
                    str(task.get("enabled", False)),
                    str(task.get("next_run_at", "N/A")),
                )
            console.print(table)

        elif action == "add":
            if not name:
                console.print("[red]Error: --name required for add action[/red]")
                raise typer.Exit(code=1)

            payload = {
                "name": name,
                "task_type": task_type,
                "schedule": schedule,
                "enabled": True,
                "description": f"CLI: {task_type} task",
                "action": {"type": task_type},
                "delivery": {"method": "internal"},
            }
            result = make_request(
                "POST", f"{backend_url}/scheduler/tasks", json=payload
            )
            console.print(f"[green]Task '{name}' created successfully.[/green]")
            console.print(json.dumps(result, indent=2))

        elif action == "run":
            if not task_id:
                console.print("[red]Error: --id required for run action[/red]")
                raise typer.Exit(code=1)

            result = make_request(
                "POST", f"{backend_url}/scheduler/tasks/{task_id}/run"
            )
            console.print(f"[green]Task executed: {result.get('executed')}[/green]")
            if result.get("result"):
                console.print(json.dumps(result.get("result"), indent=2))

        elif action == "delete":
            if not task_id and not name:
                console.print(
                    "[red]Error: --id or --name required for delete action[/red]"
                )
                raise typer.Exit(code=1)

            # First get task ID if name provided
            if not task_id:
                list_result = make_request("GET", f"{backend_url}/scheduler/tasks")
                tasks = list_result.get("tasks", [])
                matching = [t for t in tasks if t.get("name") == name]
                if not matching:
                    console.print(f"[red]Task '{name}' not found[/red]")
                    raise typer.Exit(code=1)
                task_id = matching[0].get("id")

            make_request("DELETE", f"{backend_url}/scheduler/tasks/{task_id}")
            console.print(f"[green]Task deleted successfully.[/green]")

        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            raise typer.Exit(code=1)

    except GnosysCLIError as e:
        console.print(format_error(e), style="bold red")
        raise typer.Exit(code=e.code)


@app.command()
def detect_skills(
    trajectory_limit: int = typer.Option(
        100, "--trajectory-limit", "-l", help="Number of trajectories to analyze"
    ),
    min_frequency: int = typer.Option(
        3, "--min-frequency", "-f", help="Minimum pattern frequency"
    ),
) -> None:
    """
    Detect skills from trajectory patterns.

    Analyzes recent task trajectories to extract repeated tool sequences
    that can be saved as reusable skills.
    """
    try:
        config = load_config()
        backend_url = get_backend_url(config)

        payload = {
            "trajectory_limit": trajectory_limit,
            "min_frequency": min_frequency,
        }

        result = make_request("POST", f"{backend_url}/skills/detect", json=payload)

        patterns = result.get("patterns", [])
        if not patterns:
            console.print("[yellow]No skill patterns detected.[/yellow]")
            return

        console.print(f"[bold]Detected {len(patterns)} skill patterns:[/bold]\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Tools")
        table.add_column("Frequency")
        table.add_column("Success Rate")

        for pattern in patterns:
            tools = " -> ".join(pattern.get("tools", []))
            table.add_row(
                tools,
                str(pattern.get("frequency", 0)),
                f"{pattern.get('success_rate', 0) * 100:.1f}%",
            )

        console.print(table)

        console.print("\n[bold]To extract a skill, use:[/bold]")
        console.print(
            "  gnosys skills create --tools '<tool1,tool2,...>' --workflow '<step1,step2,...>'"
        )

    except GnosysCLIError as e:
        console.print(format_error(e), style="bold red")
        raise typer.Exit(code=e.code)


@app.command()
def skills(
    action: str = typer.Argument(..., help="Action: list, view, create, delete"),
    skill_id: Optional[str] = typer.Option(
        None, "--id", "-i", help="Skill ID (for view/delete)"
    ),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Skill name (for create)"
    ),
    tools: Optional[str] = typer.Option(
        None, "--tools", "-t", help="Comma-separated tools (for create)"
    ),
    workflow: Optional[str] = typer.Option(
        None, "--workflow", "-w", help="Comma-separated workflow steps (for create)"
    ),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Skill description (for create)"
    ),
) -> None:
    """
    Manage skills.

    List, view, create, or delete skills.
    """
    try:
        config = load_config()
        backend_url = get_backend_url(config)

        if action == "list":
            result = make_request("GET", f"{backend_url}/skills")
            skills = result.get("skills", [])
            if not skills:
                console.print("[yellow]No skills found.[/yellow]")
                return

            table = Table(show_header=True, header_style="bold")
            table.add_column("Name")
            table.add_column("Version")
            table.add_column("Tools")
            table.add_column("Use Count")
            table.add_column("Success Rate")

            for skill in skills:
                tools_str = ", ".join(skill.get("tools", [])[:3])
                if len(skill.get("tools", [])) > 3:
                    tools_str += "..."
                table.add_row(
                    skill.get("name", ""),
                    skill.get("version", ""),
                    tools_str,
                    str(skill.get("use_count", 0)),
                    f"{skill.get('success_rate', 0) * 100:.1f}%",
                )
            console.print(table)

        elif action == "view":
            if not skill_id:
                console.print("[red]Error: --id required for view action[/red]")
                raise typer.Exit(code=1)

            result = make_request("GET", f"{backend_url}/skills/{skill_id}")
            console.print(json.dumps(result, indent=2))

        elif action == "create":
            if not name:
                console.print("[red]Error: --name required for create action[/red]")
                raise typer.Exit(code=1)
            if not tools:
                console.print("[red]Error: --tools required for create action[/red]")
                raise typer.Exit(code=1)
            if not workflow:
                console.print("[red]Error: --workflow required for create action[/red]")
                raise typer.Exit(code=1)

            payload = {
                "name": name,
                "tools": [t.strip() for t in tools.split(",")],
                "workflow": [w.strip() for w in workflow.split(",")],
                "description": description or f"Skill created via CLI",
            }

            result = make_request("POST", f"{backend_url}/skills", json=payload)
            console.print(f"[green]Skill '{name}' created successfully.[/green]")
            console.print(json.dumps(result, indent=2))

        elif action == "delete":
            if not skill_id:
                console.print("[red]Error: --id required for delete action[/red]")
                raise typer.Exit(code=1)

            make_request("DELETE", f"{backend_url}/skills/{skill_id}")
            console.print(f"[green]Skill deleted successfully.[/green]")

        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            raise typer.Exit(code=1)

    except GnosysCLIError as e:
        console.print(format_error(e), style="bold red")
        raise typer.Exit(code=e.code)


def main() -> None:
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
