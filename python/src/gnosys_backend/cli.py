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

    console.print(table)

    console.print("\n[bold]Examples:[/bold]")
    console.print("  gnosys status --verbose")
    console.print('  gnosys store --content "Remember this"')
    console.print("  gnosys get abc123")
    console.print("  gnosys search project --limit 10")

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


def main() -> None:
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
