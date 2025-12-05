# src/routine_workflow/help_renderer.py

"""Rich-powered --help renderer."""

import argparse
from typing import Dict, Set

from .constants import STEP_NAMES, PRIMARY_ALIASES

def render_rich_help(console, parser: argparse.ArgumentParser) -> None:
    """Render a friendly --help using rich panels and tables.

    This mirrors the argparse data but prints it with richer formatting.
    """
    from rich.text import Text
    from rich.table import Table
    from rich.panel import Panel
    from rich.markdown import Markdown

    # Usage (bold yellow box)
    usage = parser.format_usage()
    console.print(Panel(Text(usage, style="bold yellow"), title="Usage", border_style="yellow"))

    # Description
    description = parser.description
    if description:
        console.print(f"[bold magenta]Description:[/bold magenta] {description}")

    # Options Table (green flags, dim defaults)
    options_table = Table(title="[bold magenta]Options[/bold magenta]", show_header=True, header_style="bold cyan")
    options_table.add_column("Flag", style="green", no_wrap=True)
    options_table.add_column("Description", style="white")

    for action in parser._actions:
        if getattr(action, 'dest', None) == 'help':  # skip built-in help action
            continue
        # Build a succinct flag string (shorts + longs)
        flag_str = ' '.join(action.option_strings) if action.option_strings else action.dest.upper()
        desc = action.help or ''
        if (action.default is not argparse.SUPPRESS) and (action.default is not None) and (not isinstance(action.default, bool)):
            # Show non-boolean defaults inline (booleans are obvious from presence/absence)
            default = f" [dim](default: {action.default})[/dim]"
            desc += default
        options_table.add_row(flag_str, desc)

    console.print(options_table)

    # --- UPDATED Steps Table (now shows aliases) ---
    steps_table = Table(title="[bold magenta]Available Workflow Steps[/bold magenta]", show_header=True, header_style="bold cyan")
    steps_table.add_column("Alias (Name)", style="cyan", no_wrap=True)
    steps_table.add_column("Step ID", style="dim", no_wrap=True)
    steps_table.add_column("Description", style="white")

    step_descriptions = {
        "step1": "Delete old dumps (prune artifacts)",
        "step2": "Reformat code (ruff, autoimport, etc.)",
        "step2.5": "Run pytest suite",
        "step3": "Clean caches (rm temps)",
        "step3.5": "Security scan (bandit, safety)",
        "step4": "Backup project (tar/zip)",
        "step5": "Generate dumps (create-dump tool)",
        "step6": "Commit hygiene snapshot to git",
        "step6.5": "Dependency vulnerability audit (pip-audit)",
    }

    for step_id in sorted(STEP_NAMES):
        alias = PRIMARY_ALIASES.get(step_id, "N/A")
        desc = step_descriptions.get(step_id, "Custom/undefined step")
        steps_table.add_row(alias, step_id, desc)

    console.print(steps_table)
    # --- End UPDATED Steps Table ---

    # Examples Panel (render the parser epilog as Markdown code blocks)
    epilog_lines = [line.rstrip() for line in (parser.epilog or "").splitlines() if line.strip()]
    examples_content = "# Usage Examples\n"
    for line in epilog_lines:
        if line.startswith('#') or line.lower().startswith('examples:'):
            continue
        # --- FIXED: Use line.strip() to handle leading whitespace ---
        if line.strip().startswith('routine-workflow'):
            examples_content += f"- ```bash\n{line.strip()}\n```\n"
        else:
            examples_content += f"{line}\n"

    examples_panel = Panel(
        Markdown(examples_content),
        title="[bold green]Quick Starts[/bold green]",
        border_style="green",
        expand=False,
    )
    console.print(examples_panel)
