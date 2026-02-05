"""CLI Ingestion Tool.

Command-line interface for running the knowledge base ingestion pipeline.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Setup console for rich output
console = Console()

# Module imports (done inside functions to avoid import errors during CLI setup)


def setup_logging(log_level: str, log_file: Optional[Path] = None):
    """Configure logging for the ingestion pipeline."""
    from ..utils.logging_config import setup_ingestion_logging

    setup_ingestion_logging(level=log_level, log_file=log_file)


def load_seed_data(seed_dir: Path) -> dict:
    """Load seed data from JSON files."""
    seed_data = {}

    files = {
        "actions": "actions.json",
        "widgets": "widgets.json",
        "status_patterns": "status_patterns.json",
        "relationships": "relationships.json",
    }

    for key, filename in files.items():
        filepath = seed_dir / filename
        if filepath.exists():
            with open(filepath) as f:
                data = json.load(f)
                # Handle both wrapped and unwrapped formats
                if key in data:
                    seed_data[key] = data[key]
                else:
                    seed_data[key] = data
        else:
            console.print(f"[yellow]Warning: {filepath} not found[/yellow]")
            seed_data[key] = []

    return seed_data


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load ingestion configuration."""
    default_config = {
        "seed_data": {
            "actions_file": "seed/actions.json",
            "widgets_file": "seed/widgets.json",
            "status_patterns_file": "seed/status_patterns.json",
            "relationships_file": "seed/relationships.json",
        },
        "production_data": {
            "directory": "Clearpath_Prod_Data/",
            "file_patterns": ["*.xlsx", "*.xls"],
            "skip_files": ["~$*.xlsx"],
        },
        "embedding": {
            "model": "text-embedding-3-small",
            "dimension": 1536,
            "batch_size": 100,
            "max_retries": 3,
        },
        "vector_store": {
            "table_prefix": "clearpath_",
            "batch_size": 500,
        },
        "graph_store": {
            "batch_size": 500,
            "merge_strategy": "weighted_average",
            "min_relationship_weight": 0.3,
        },
        "validation": {
            "fuzzy_match_threshold": 0.85,
            "semantic_match_threshold": 0.95,
            "min_frequency": 1,
            "auto_add_threshold": 3,
        },
        "patterns": {
            "min_occurrences": 2,
            "min_confidence": 0.5,
            "max_patterns_per_category": 100,
        },
    }

    if config_path and config_path.exists():
        try:
            import yaml

            with open(config_path) as f:
                loaded = yaml.safe_load(f)
                # Deep merge with defaults
                for key in default_config:
                    if key in loaded:
                        if isinstance(default_config[key], dict):
                            default_config[key].update(loaded[key])
                        else:
                            default_config[key] = loaded[key]
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load config: {e}[/yellow]")

    return default_config


@click.group()
def cli():
    """ClearPath Knowledge Base Ingestion CLI."""
    pass


@cli.command()
@click.option(
    "--seed-dir",
    type=click.Path(exists=True, path_type=Path),
    default="seed/",
    help="Directory containing seed data JSON files",
)
@click.option(
    "--prod-dir",
    type=click.Path(exists=True, path_type=Path),
    default="Clearpath_Prod_Data/",
    help="Directory containing production Excel files",
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to ingestion config YAML file",
)
@click.option(
    "--skip-vector",
    is_flag=True,
    default=False,
    help="Skip vector store ingestion",
)
@click.option(
    "--skip-graph",
    is_flag=True,
    default=False,
    help="Skip graph store ingestion",
)
@click.option(
    "--skip-embeddings",
    is_flag=True,
    default=False,
    help="Skip embedding generation (useful for testing)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Parse and validate without writing to databases",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default="reports/",
    help="Directory for output reports",
)
def ingest(
    seed_dir: Path,
    prod_dir: Path,
    config: Optional[Path],
    skip_vector: bool,
    skip_graph: bool,
    skip_embeddings: bool,
    dry_run: bool,
    log_level: str,
    output_dir: Path,
):
    """Ingest seed and production data into vector and graph stores.

    This command orchestrates the full ingestion pipeline:
    1. Load seed data from JSON files
    2. Parse production Excel files
    3. Extract patterns from production data
    4. Enrich seed data with production patterns
    5. Validate and deduplicate all entities
    6. Generate embeddings for all entities
    7. Upsert to Supabase vector store
    8. Upsert to Neo4j graph store
    9. Generate ingestion report
    """
    # Setup logging
    log_file = output_dir / "ingestion.log" if output_dir else None
    setup_logging(log_level, log_file)

    logger = logging.getLogger(__name__)
    logger.info("Starting ingestion pipeline")

    # Load configuration
    cfg = load_config(config)

    console.print("\n[bold blue]ClearPath Knowledge Base Ingestion[/bold blue]\n")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No data will be written to databases[/yellow]\n")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Statistics tracking
    stats = {
        "start_time": datetime.now(),
        "seed_actions": 0,
        "seed_widgets": 0,
        "seed_patterns": 0,
        "seed_relationships": 0,
        "prod_files_parsed": 0,
        "prod_statuses": 0,
        "prod_actions": 0,
        "prod_widgets": 0,
        "patterns_extracted": 0,
        "validation_errors": 0,
        "validation_warnings": 0,
        "embeddings_generated": 0,
        "vector_records_upserted": 0,
        "graph_nodes_created": 0,
        "graph_relationships_created": 0,
    }

    try:
        # ================================================================
        # Step 1: Load seed data
        # ================================================================
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading seed data...", total=None)

            seed_data = load_seed_data(seed_dir)

            stats["seed_actions"] = len(seed_data.get("actions", []))
            stats["seed_widgets"] = len(seed_data.get("widgets", []))
            stats["seed_patterns"] = len(seed_data.get("status_patterns", []))
            stats["seed_relationships"] = len(seed_data.get("relationships", []))

            progress.update(task, completed=True)

        console.print(
            f"  Loaded: {stats['seed_actions']} actions, "
            f"{stats['seed_widgets']} widgets, "
            f"{stats['seed_patterns']} patterns, "
            f"{stats['seed_relationships']} relationships"
        )

        # ================================================================
        # Step 2: Parse production Excel files
        # ================================================================
        from ..services.prod_data_parser import ProductionDataParser

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Parsing production Excel files...", total=None)

            parser = ProductionDataParser()
            workflows = parser.parse_directory(prod_dir)

            stats["prod_files_parsed"] = len(workflows)
            stats["prod_statuses"] = sum(w.status_count for w in workflows)
            stats["prod_actions"] = sum(w.action_count for w in workflows)
            stats["prod_widgets"] = sum(w.widget_count for w in workflows)

            progress.update(task, completed=True)

        console.print(
            f"  Parsed: {stats['prod_files_parsed']} files, "
            f"{stats['prod_statuses']} statuses, "
            f"{stats['prod_actions']} action buttons"
        )

        # ================================================================
        # Step 3: Extract patterns from production data
        # ================================================================
        from ..services.pattern_extractor import PatternExtractor

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Extracting patterns...", total=None)

            extractor = PatternExtractor(
                min_occurrences=cfg["patterns"]["min_occurrences"],
                min_confidence=cfg["patterns"]["min_confidence"],
            )
            patterns = extractor.extract_all_patterns(workflows)

            stats["patterns_extracted"] = (
                len(patterns.get("status_flows", []))
                + len(patterns.get("action_widget_cooccurrence", []))
                + len(patterns.get("action_cooccurrence", []))
            )

            progress.update(task, completed=True)

        console.print(f"  Extracted: {stats['patterns_extracted']} patterns")

        # ================================================================
        # Step 4: Enrich seed data with production patterns
        # ================================================================
        from ..services.data_enricher import DataEnricher

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Enriching seed data...", total=None)

            enricher = DataEnricher(
                fuzzy_threshold=cfg["validation"]["fuzzy_match_threshold"]
            )

            frequencies = patterns.get("frequencies")
            flows = patterns.get("status_flows", [])

            enriched_actions = enricher.enrich_actions(
                seed_data.get("actions", []), frequencies
            )
            enriched_widgets = enricher.enrich_widgets(
                seed_data.get("widgets", []), frequencies
            )
            enriched_patterns = enricher.enrich_status_patterns(
                seed_data.get("status_patterns", []), flows
            )

            # Discover new entities
            discovered = enricher.discover_new_entities(workflows, seed_data)

            # Merge discovered entities into enriched lists
            # Filter by auto_add_threshold to only include frequently-occurring entities
            auto_add_threshold = cfg["validation"].get("auto_add_threshold", 3)
            added_actions = 0
            added_widgets = 0

            for action in discovered.get("new_actions", []):
                if action.get("occurrence_count", 0) >= auto_add_threshold:
                    enriched_actions.append(action)
                    added_actions += 1

            for widget in discovered.get("new_widgets", []):
                if widget.get("occurrence_count", 0) >= auto_add_threshold:
                    enriched_widgets.append(widget)
                    added_widgets += 1

            progress.update(task, completed=True)

        console.print(
            f"  Discovered: {len(discovered.get('new_actions', []))} new actions, "
            f"{len(discovered.get('new_widgets', []))} new widgets "
            f"(added {added_actions} actions, {added_widgets} widgets with >= {auto_add_threshold} occurrences)"
        )

        # ================================================================
        # Step 5: Validate and deduplicate
        # ================================================================
        from ..services.data_validator import DataValidator

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Validating and deduplicating...", total=None)

            validator = DataValidator(
                fuzzy_threshold=cfg["validation"]["fuzzy_match_threshold"],
                semantic_threshold=cfg["validation"]["semantic_match_threshold"],
            )

            # Deduplicate
            deduped_actions, action_dedup = validator.deduplicate_actions(enriched_actions)
            deduped_widgets, widget_dedup = validator.deduplicate_widgets(enriched_widgets)

            # Validate
            validation_results = validator.validate_all(
                deduped_actions,
                deduped_widgets,
                enriched_patterns,
                seed_data.get("relationships", []),
            )

            stats["validation_errors"] = sum(
                1 for r in validation_results if not r.is_valid
            )
            stats["validation_warnings"] = sum(
                len(r.warnings) for r in validation_results
            )

            progress.update(task, completed=True)

        console.print(
            f"  Validation: {stats['validation_errors']} errors, "
            f"{stats['validation_warnings']} warnings"
        )

        # Save validation report
        report = validator.generate_validation_report(validation_results)
        report_path = output_dir / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, "w") as f:
            f.write(report)

        # ================================================================
        # Step 6: Generate embeddings (unless skipped)
        # ================================================================
        embeddings_data = None
        if not skip_embeddings:
            from ..services.embedding_generator import EmbeddingGenerator

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Generating embeddings...", total=None)

                cache_dir = output_dir / ".embedding_cache"
                generator = EmbeddingGenerator(
                    model=cfg["embedding"]["model"],
                    dimension=cfg["embedding"]["dimension"],
                    cache_dir=cache_dir,
                )

                embeddings_data = generator.generate_all_embeddings(
                    deduped_actions,
                    deduped_widgets,
                    enriched_patterns,
                    patterns=frequencies,
                    flows=flows,
                )

                stats["embeddings_generated"] = (
                    len(embeddings_data.get("action_embeddings", []))
                    + len(embeddings_data.get("widget_embeddings", []))
                    + len(embeddings_data.get("status_pattern_embeddings", []))
                )

                progress.update(task, completed=True)

            console.print(f"  Generated: {stats['embeddings_generated']} embeddings")
        else:
            console.print("  [yellow]Skipping embedding generation[/yellow]")

        # ================================================================
        # Step 7: Upsert to vector store (unless skipped or dry run)
        # ================================================================
        if not skip_vector and not dry_run and embeddings_data:
            import os

            from ..services.vector_store import VectorStore

            supabase_url = os.environ.get("SUPABASE_URL")
            supabase_key = os.environ.get("SUPABASE_KEY")

            if supabase_url and supabase_key:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Upserting to vector store...", total=None)

                    vector_store = VectorStore(
                        supabase_url=supabase_url,
                        supabase_key=supabase_key,
                        table_prefix=cfg["vector_store"]["table_prefix"],
                    )

                    actions_upserted = vector_store.upsert_action_embeddings(
                        embeddings_data.get("action_embeddings", [])
                    )
                    widgets_upserted = vector_store.upsert_widget_embeddings(
                        embeddings_data.get("widget_embeddings", [])
                    )
                    patterns_upserted = vector_store.upsert_status_pattern_embeddings(
                        embeddings_data.get("status_pattern_embeddings", [])
                    )

                    stats["vector_records_upserted"] = (
                        actions_upserted + widgets_upserted + patterns_upserted
                    )

                    progress.update(task, completed=True)

                console.print(f"  Upserted: {stats['vector_records_upserted']} records")
            else:
                console.print(
                    "  [yellow]Skipping vector store - SUPABASE_URL/KEY not set[/yellow]"
                )
        elif skip_vector:
            console.print("  [yellow]Skipping vector store (--skip-vector)[/yellow]")
        elif dry_run:
            console.print("  [yellow]Skipping vector store (dry run)[/yellow]")

        # ================================================================
        # Step 8: Upsert to graph store (unless skipped or dry run)
        # ================================================================
        if not skip_graph and not dry_run:
            import os

            from ..services.graph_store import GraphStore

            neo4j_uri = os.environ.get("NEO4J_URI")
            neo4j_user = os.environ.get("NEO4J_USERNAME", "neo4j")
            neo4j_password = os.environ.get("NEO4J_PASSWORD")

            if neo4j_uri and neo4j_password:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Upserting to graph store...", total=None)

                    graph_store = GraphStore(
                        uri=neo4j_uri,
                        user=neo4j_user,
                        password=neo4j_password,
                    )

                    # Initialize schema
                    graph_store.initialize_schema()

                    # Create nodes
                    action_nodes = graph_store.create_action_nodes(deduped_actions)
                    widget_nodes = graph_store.create_widget_nodes(deduped_widgets)
                    pattern_nodes = graph_store.create_status_pattern_nodes(enriched_patterns)

                    # Create status nodes from production data
                    status_dict = {}  # Aggregate unique statuses with frequency
                    for workflow in workflows:
                        for status in workflow.statuses:
                            key = status.name.lower()
                            if key not in status_dict:
                                status_dict[key] = {
                                    "name": status.name,
                                    "category": status.category.value if hasattr(status.category, "value") else str(status.category),
                                    "frequency": 0,
                                }
                            status_dict[key]["frequency"] += 1
                    status_nodes = graph_store.create_status_nodes(list(status_dict.values()))

                    stats["graph_nodes_created"] = action_nodes + widget_nodes + pattern_nodes + status_nodes

                    # Create NEXT_STATUS edges from status flows
                    flow_edges = graph_store.create_status_flow_edges(flows)

                    # Create HAS_ACTION edges from production action buttons
                    action_edges = graph_store.create_status_action_edges(workflows)

                    # Create HAS_WIDGET edges from production focus views
                    widget_edges = graph_store.create_status_widget_edges(workflows)

                    # Create relationships from seed data
                    seed_rels = graph_store.create_relationships(
                        seed_data.get("relationships", [])
                    )

                    # Create relationships from status patterns
                    pattern_rels = graph_store.create_status_pattern_relationships(
                        enriched_patterns
                    )

                    # Merge production patterns
                    prod_rels = graph_store.merge_production_patterns(
                        patterns.get("action_widget_cooccurrence", [])
                        + patterns.get("action_cooccurrence", []),
                        merge_strategy=cfg["graph_store"]["merge_strategy"],
                    )

                    stats["graph_relationships_created"] = seed_rels + pattern_rels + prod_rels + flow_edges + action_edges + widget_edges

                    graph_store.close()

                    progress.update(task, completed=True)

                console.print(
                    f"  Created: {stats['graph_nodes_created']} nodes, "
                    f"{stats['graph_relationships_created']} relationships"
                )
            else:
                console.print(
                    "  [yellow]Skipping graph store - NEO4J_URI/PASSWORD not set[/yellow]"
                )
        elif skip_graph:
            console.print("  [yellow]Skipping graph store (--skip-graph)[/yellow]")
        elif dry_run:
            console.print("  [yellow]Skipping graph store (dry run)[/yellow]")

        # ================================================================
        # Step 9: Generate final report
        # ================================================================
        from ..services.report_generator import ReportGenerator

        stats["end_time"] = datetime.now()
        stats["duration"] = str(stats["end_time"] - stats["start_time"])

        report_gen = ReportGenerator()
        final_report = report_gen.generate_summary_report(stats)

        # Save reports
        report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Text report
        report_path = output_dir / f"ingestion_{report_timestamp}.md"
        with open(report_path, "w") as f:
            f.write(final_report)

        # JSON stats
        stats_path = output_dir / f"ingestion_{report_timestamp}.json"
        # Convert datetime objects for JSON
        json_stats = {
            k: str(v) if isinstance(v, datetime) else v for k, v in stats.items()
        }
        with open(stats_path, "w") as f:
            json.dump(json_stats, f, indent=2)

        # Print summary table
        console.print("\n")
        _print_summary_table(stats)

        console.print(f"\n[green]Reports saved to: {output_dir}[/green]")
        console.print("[bold green]Ingestion complete![/bold green]\n")

    except Exception as e:
        logger.exception("Ingestion failed")
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        sys.exit(1)


def _print_summary_table(stats: dict):
    """Print a summary table of ingestion statistics."""
    table = Table(title="Ingestion Summary")

    table.add_column("Category", style="cyan")
    table.add_column("Metric", style="white")
    table.add_column("Value", style="green", justify="right")

    # Seed data
    table.add_row("Seed Data", "Actions", str(stats.get("seed_actions", 0)))
    table.add_row("", "Widgets", str(stats.get("seed_widgets", 0)))
    table.add_row("", "Status Patterns", str(stats.get("seed_patterns", 0)))
    table.add_row("", "Relationships", str(stats.get("seed_relationships", 0)))

    # Production data
    table.add_row("Production", "Files Parsed", str(stats.get("prod_files_parsed", 0)))
    table.add_row("", "Statuses", str(stats.get("prod_statuses", 0)))
    table.add_row("", "Action Buttons", str(stats.get("prod_actions", 0)))

    # Processing
    table.add_row("Processing", "Patterns Extracted", str(stats.get("patterns_extracted", 0)))
    table.add_row("", "Embeddings Generated", str(stats.get("embeddings_generated", 0)))

    # Validation
    table.add_row("Validation", "Errors", str(stats.get("validation_errors", 0)))
    table.add_row("", "Warnings", str(stats.get("validation_warnings", 0)))

    # Output
    table.add_row("Output", "Vector Records", str(stats.get("vector_records_upserted", 0)))
    table.add_row("", "Graph Nodes", str(stats.get("graph_nodes_created", 0)))
    table.add_row("", "Graph Relationships", str(stats.get("graph_relationships_created", 0)))

    # Duration
    table.add_row("", "Duration", str(stats.get("duration", "N/A")))

    console.print(table)


@cli.command()
@click.option(
    "--seed-dir",
    type=click.Path(exists=True, path_type=Path),
    default="seed/",
    help="Directory containing seed data JSON files",
)
def validate(seed_dir: Path):
    """Validate seed data without running full ingestion."""
    from ..services.data_validator import DataValidator

    console.print("\n[bold blue]Validating Seed Data[/bold blue]\n")

    seed_data = load_seed_data(seed_dir)

    validator = DataValidator()
    results = validator.validate_all(
        seed_data.get("actions", []),
        seed_data.get("widgets", []),
        seed_data.get("status_patterns", []),
        seed_data.get("relationships", []),
    )

    report = validator.generate_validation_report(results)
    console.print(report)


@cli.command()
@click.option(
    "--prod-dir",
    type=click.Path(exists=True, path_type=Path),
    default="Clearpath_Prod_Data/",
    help="Directory containing production Excel files",
)
def analyze(prod_dir: Path):
    """Analyze production data and show patterns."""
    from ..services.pattern_extractor import PatternExtractor
    from ..services.prod_data_parser import ProductionDataParser

    console.print("\n[bold blue]Analyzing Production Data[/bold blue]\n")

    parser = ProductionDataParser()
    workflows = parser.parse_directory(prod_dir)

    console.print(f"Parsed {len(workflows)} workflow files\n")

    extractor = PatternExtractor()
    patterns = extractor.extract_all_patterns(workflows)

    summary = extractor.summarize_patterns(patterns)
    console.print(summary)


@cli.command()
def schema():
    """Generate SQL schema for Supabase vector store."""
    from ..services.vector_store import VectorStore

    console.print("\n[bold blue]Supabase Vector Store Schema[/bold blue]\n")

    vs = VectorStore(
        supabase_url="placeholder",
        supabase_key="placeholder",
    )

    statements = vs._get_schema_sql()
    for stmt in statements:
        console.print(stmt)
        console.print()

    console.print("\n[bold]Search Functions:[/bold]\n")
    console.print(vs.get_search_function_sql())


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
