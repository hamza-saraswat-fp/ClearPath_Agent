"""CLI Build Tool.

Command-line interface for running the ConfigBuilder pipeline to transform
Structured Intent JSON into ClearPath configurations.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

# Setup console for rich output
console = Console()


def setup_logging(log_level: str, log_file: Optional[Path] = None):
    """Configure logging for the build pipeline."""
    from ..utils.logging_config import setup_ingestion_logging

    setup_ingestion_logging(level=log_level, log_file=log_file)


@click.group()
def cli():
    """ClearPath Configuration Builder CLI."""
    pass


@cli.command()
@click.option(
    "--intent-file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to JSON file containing Structured Intent",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Path for output JSON file (default: stdout)",
)
@click.option(
    "--excel-output",
    type=click.Path(path_type=Path),
    default=None,
    help="Path for Excel template output (JSON format)",
)
@click.option(
    "--review",
    is_flag=True,
    default=False,
    help="Show configuration for review before export",
)
@click.option(
    "--validate-only",
    is_flag=True,
    default=False,
    help="Run validation without generating output",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Treat warnings as errors",
)
@click.option(
    "--no-defaults",
    is_flag=True,
    default=False,
    help="Skip applying default widgets and toggles",
)
@click.option(
    "--no-best-practices",
    is_flag=True,
    default=False,
    help="Skip enforcing best practices",
)
@click.option(
    "--use-knowledge-base",
    is_flag=True,
    default=False,
    help="Use knowledge base for entity resolution (requires env vars)",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="WARNING",
    help="Logging level",
)
def build(
    intent_file: Path,
    output: Optional[Path],
    excel_output: Optional[Path],
    review: bool,
    validate_only: bool,
    strict: bool,
    no_defaults: bool,
    no_best_practices: bool,
    use_knowledge_base: bool,
    log_level: str,
):
    """Build a ClearPath configuration from Structured Intent JSON.

    This command transforms a Structured Intent JSON file (from LLM extraction)
    into a complete StatusActionFlow configuration ready for Excel export.

    Example usage:

        clearpath-build build --intent-file intent.json --output config.json

        clearpath-build build --intent-file intent.json --review

        clearpath-build build --intent-file intent.json --validate-only
    """
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    console.print("\n[bold blue]ClearPath Configuration Builder[/bold blue]\n")

    try:
        # Load intent from file
        with open(intent_file) as f:
            intent_data = json.load(f)

        logger.info(f"Loaded intent from {intent_file}")

        # Import models and services
        from ..models.intent_schemas import StructuredIntent
        from ..services.builder_pipeline import BuilderPipeline, create_pipeline
        from ..services.config_editor import ConfigEditor

        # Parse intent
        try:
            intent = StructuredIntent(**intent_data)
            console.print(f"[green]Loaded workflow:[/green] {intent.workflow_name}")
            console.print(f"  Steps: {len(intent.steps)}")
            console.print(f"  Total actions: {sum(len(s.action_phrases) for s in intent.steps)}")
            console.print(f"  Total widgets: {sum(len(s.information_needs) for s in intent.steps)}")
            console.print()
        except Exception as e:
            console.print(f"[bold red]Error parsing intent: {e}[/bold red]")
            sys.exit(1)

        # Create pipeline
        if use_knowledge_base:
            import os

            pipeline = create_pipeline(
                supabase_url=os.environ.get("SUPABASE_URL"),
                supabase_key=os.environ.get("SUPABASE_KEY"),
                neo4j_uri=os.environ.get("NEO4J_URI"),
                neo4j_user=os.environ.get("NEO4J_USERNAME", "neo4j"),
                neo4j_password=os.environ.get("NEO4J_PASSWORD"),
            )
        else:
            pipeline = BuilderPipeline(strict_validation=strict)

        # Execute build
        result = pipeline.execute(
            intent=intent,
            apply_defaults=not no_defaults,
            apply_best_practices=not no_best_practices,
        )

        # Show validation results
        _print_validation_results(result)

        # Handle validate-only mode
        if validate_only:
            if result.is_valid:
                console.print("[bold green]Validation passed![/bold green]")
                sys.exit(0)
            else:
                console.print("[bold red]Validation failed![/bold red]")
                sys.exit(1)

        # Check if build succeeded
        if not result.success:
            console.print(f"[bold red]Build failed: {result.error_message}[/bold red]")
            sys.exit(1)

        # Show review if requested
        if review:
            editor = ConfigEditor()
            _show_review(result, editor)

        # Show applied defaults
        if result.applied_defaults:
            console.print("\n[cyan]Applied Defaults:[/cyan]")
            for default in result.applied_defaults[:10]:
                console.print(f"  - {default}")
            if len(result.applied_defaults) > 10:
                console.print(f"  ... and {len(result.applied_defaults) - 10} more")

        # Show items needing review
        if result.low_confidence_items:
            console.print("\n[yellow]Items Needing Review (low confidence):[/yellow]")
            for item in result.low_confidence_items[:5]:
                console.print(
                    f"  - {item.get('phrase', 'Unknown')}: "
                    f"{item.get('suggested_type', 'Unknown')} "
                    f"(confidence: {item.get('confidence', 0):.2f})"
                )

        if result.template_required_items:
            console.print("\n[yellow]Template Required Items:[/yellow]")
            for item in result.template_required_items[:5]:
                console.print(
                    f"  - {item.get('action_type', 'Unknown')}: "
                    f"requires template configuration"
                )

        # Output configuration
        if output:
            config_dict = result.config.model_dump(mode="json")
            with open(output, "w") as f:
                json.dump(config_dict, f, indent=2)
            console.print(f"\n[green]Configuration saved to:[/green] {output}")
        else:
            # Print to stdout if no output file specified
            config_dict = result.config.model_dump(mode="json")
            console.print("\n[bold]Generated Configuration:[/bold]")
            syntax = Syntax(
                json.dumps(config_dict, indent=2),
                "json",
                theme="monokai",
                line_numbers=True,
            )
            console.print(syntax)

        # Output Excel template
        if excel_output and result.excel_template:
            excel_dict = result.excel_template.model_dump(mode="json")
            with open(excel_output, "w") as f:
                json.dump(excel_dict, f, indent=2)
            console.print(f"[green]Excel template saved to:[/green] {excel_output}")

        # Print summary
        _print_build_summary(result)

        console.print("\n[bold green]Build complete![/bold green]\n")

    except Exception as e:
        logger.exception("Build failed")
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@cli.command()
@click.option(
    "--template",
    type=click.Choice(["service_call", "installation", "inspection", "emergency"]),
    required=True,
    help="Template to use",
)
@click.option(
    "--name",
    type=str,
    default=None,
    help="Custom workflow name",
)
@click.option(
    "--job-types",
    type=str,
    default=None,
    help="Comma-separated job types",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Path for output JSON file",
)
def from_template(
    template: str,
    name: Optional[str],
    job_types: Optional[str],
    output: Optional[Path],
):
    """Generate a configuration from a pre-built template.

    Available templates:
    - service_call: Standard service call workflow
    - installation: Equipment installation workflow
    - inspection: Inspection/assessment workflow
    - emergency: Emergency service workflow

    Example:

        clearpath-build from-template --template service_call --output config.json
    """
    console.print("\n[bold blue]Building from Template[/bold blue]\n")

    try:
        from ..data.default_templates import get_template
        from ..services.builder_pipeline import BuilderPipeline

        # Get template
        config = get_template(template)
        if not config:
            console.print(f"[bold red]Template not found: {template}[/bold red]")
            sys.exit(1)

        console.print(f"[green]Using template:[/green] {template}")

        # Apply customizations
        if name:
            config = config.model_copy(update={"name": name})
            console.print(f"  Custom name: {name}")

        if job_types:
            types_list = [t.strip() for t in job_types.split(",")]
            config = config.model_copy(update={"job_types": types_list})
            console.print(f"  Job types: {types_list}")

        # Validate
        pipeline = BuilderPipeline()
        validation_result = pipeline.validator.validate_config(config)

        if not validation_result.is_valid:
            console.print("\n[yellow]Validation warnings:[/yellow]")
            for issue in validation_result.issues:
                console.print(f"  - {issue}")

        # Output
        if output:
            config_dict = config.model_dump(mode="json")
            with open(output, "w") as f:
                json.dump(config_dict, f, indent=2)
            console.print(f"\n[green]Configuration saved to:[/green] {output}")
        else:
            config_dict = config.model_dump(mode="json")
            console.print("\n[bold]Generated Configuration:[/bold]")
            syntax = Syntax(
                json.dumps(config_dict, indent=2),
                "json",
                theme="monokai",
                line_numbers=True,
            )
            console.print(syntax)

        # Summary
        console.print(f"\n[cyan]Summary:[/cyan]")
        console.print(f"  Statuses: {len(config.statuses)}")
        total_buttons = sum(len(s.action_buttons) for s in config.statuses)
        console.print(f"  Action Buttons: {total_buttons}")
        total_widgets = sum(len(s.widgets) for s in config.statuses)
        console.print(f"  Widgets: {total_widgets}")

        console.print("\n[bold green]Template build complete![/bold green]\n")

    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@cli.command()
def list_templates():
    """List available workflow templates."""
    from ..data.default_templates import list_templates as get_templates

    console.print("\n[bold blue]Available Templates[/bold blue]\n")

    templates = get_templates()

    table = Table()
    table.add_column("Template", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Statuses", style="green", justify="right")
    table.add_column("Job Types", style="yellow")

    for info in templates:
        table.add_row(
            info.get("name", ""),
            info.get("description", ""),
            str(info.get("status_count", 0)),
            ", ".join(info.get("job_types", [])),
        )

    console.print(table)
    console.print()


@cli.command()
@click.option(
    "--config-file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to configuration JSON file",
)
def validate(config_file: Path):
    """Validate a configuration file.

    Example:

        clearpath-build validate --config-file config.json
    """
    console.print("\n[bold blue]Validating Configuration[/bold blue]\n")

    try:
        with open(config_file) as f:
            config_data = json.load(f)

        from ..models.entities import StatusActionFlow
        from ..services.config_validator import ConfigValidator

        # Parse config
        try:
            config = StatusActionFlow(**config_data)
        except Exception as e:
            console.print(f"[bold red]Invalid configuration format: {e}[/bold red]")
            sys.exit(1)

        # Validate
        validator = ConfigValidator()
        result = validator.validate_config(config, check_best_practices=True)

        # Show results
        if result.is_valid:
            console.print("[bold green]Configuration is valid![/bold green]\n")
        else:
            console.print("[bold red]Configuration has validation errors![/bold red]\n")

        if result.issues:
            table = Table(title="Validation Results")
            table.add_column("Severity", style="cyan")
            table.add_column("Code", style="yellow")
            table.add_column("Message", style="white")

            for issue in result.issues:
                severity_style = {
                    "error": "red",
                    "warning": "yellow",
                    "info": "blue",
                }.get(issue.severity.value, "white")

                table.add_row(
                    f"[{severity_style}]{issue.severity.value}[/{severity_style}]",
                    issue.code,
                    issue.message,
                )

            console.print(table)

        console.print(f"\n  Errors: {result.error_count}")
        console.print(f"  Warnings: {result.warning_count}")
        console.print(f"  Info: {result.info_count}")

        if not result.is_valid:
            sys.exit(1)

    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@cli.command()
@click.option(
    "--config-file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to configuration JSON file",
)
def preview(config_file: Path):
    """Preview a configuration in human-readable format.

    Example:

        clearpath-build preview --config-file config.json
    """
    console.print("\n[bold blue]Configuration Preview[/bold blue]\n")

    try:
        with open(config_file) as f:
            config_data = json.load(f)

        from ..models.entities import StatusActionFlow
        from ..services.config_editor import ConfigEditor

        config = StatusActionFlow(**config_data)
        editor = ConfigEditor()

        summary = editor.get_review_summary(config)
        console.print(summary)

    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        sys.exit(1)


def _print_validation_results(result):
    """Print validation results in a table."""
    if not result.validation_result:
        return

    vr = result.validation_result

    if vr.issues:
        table = Table(title="Validation Results")
        table.add_column("Severity", style="cyan", width=10)
        table.add_column("Code", style="yellow", width=25)
        table.add_column("Message", style="white")

        for issue in vr.issues[:15]:  # Limit to first 15
            severity_style = {
                "error": "red",
                "warning": "yellow",
                "info": "blue",
            }.get(issue.severity.value, "white")

            table.add_row(
                f"[{severity_style}]{issue.severity.value}[/{severity_style}]",
                issue.code,
                issue.message[:60] + "..." if len(issue.message) > 60 else issue.message,
            )

        if len(vr.issues) > 15:
            table.add_row("...", "...", f"and {len(vr.issues) - 15} more issues")

        console.print(table)
        console.print()


def _show_review(result, editor):
    """Show configuration review."""
    if not result.config:
        return

    console.print("\n[bold cyan]Configuration Review[/bold cyan]")
    console.print("=" * 60)

    summary = editor.get_review_summary(result.config)
    console.print(summary)

    console.print("=" * 60)


def _print_build_summary(result):
    """Print build summary table."""
    if not result.config:
        return

    summary = result.get_summary()

    table = Table(title="Build Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")

    table.add_row("Statuses", str(summary.get("status_count", 0)))
    table.add_row("Action Buttons", str(summary.get("action_button_count", 0)))
    table.add_row("Validation Errors", str(summary.get("validation_errors", 0)))
    table.add_row("Validation Warnings", str(summary.get("validation_warnings", 0)))
    table.add_row("Low Confidence Items", str(summary.get("low_confidence_items", 0)))
    table.add_row("Template Required", str(summary.get("template_required_items", 0)))
    table.add_row("Defaults Applied", str(summary.get("defaults_applied", 0)))

    console.print(table)


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
