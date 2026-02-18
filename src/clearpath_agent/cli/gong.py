"""CLI tool for pulling and scoring Gong call transcripts for ClearPath testing.

Usage:
    clearpath-gong search --from-date 2024-06-01 --to-date 2025-02-01 --top 10
    clearpath-gong detail <call_id> --show-transcript
    clearpath-gong export --call-ids abc,def --output-dir gong_transcripts/
    clearpath-gong clear-cache
"""

import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

console = Console()
logger = logging.getLogger(__name__)


def _get_client(
    access_key: Optional[str],
    secret_key: Optional[str],
    cache_dir: Path,
):
    """Create a GongClient, resolving credentials from args or env."""
    from dotenv import load_dotenv

    load_dotenv()

    ak = access_key or os.environ.get("GONG_ACCESS_KEY")
    sk = secret_key or os.environ.get("GONG_SECRET_KEY")

    if not ak or not sk:
        console.print(
            "[red]Error: Gong API credentials required.[/red]\n"
            "Set GONG_ACCESS_KEY and GONG_SECRET_KEY in .env, "
            "or pass --access-key and --secret-key."
        )
        sys.exit(1)

    from ..services.gong_client import GongClient

    return GongClient(access_key=ak, secret_key=sk, cache_dir=cache_dir)


@click.group()
@click.option("--log-level", default="WARNING", help="Log level (DEBUG/INFO/WARNING/ERROR)")
def main(log_level: str):
    """ClearPath Gong Transcript Finder — pull and score Gong calls for pipeline testing."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.WARNING),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


@main.command()
@click.option("--from-date", required=True, type=str, help="Start date (YYYY-MM-DD)")
@click.option("--to-date", required=True, type=str, help="End date (YYYY-MM-DD)")
@click.option("--top", default=25, help="Show top N results (default: 25)")
@click.option("--min-score", default=0.0, type=float, help="Minimum score filter (default: 0.0)")
@click.option("--title-filter", default=None, help="Only process calls whose title contains this")
@click.option("--min-duration", default=0, type=int, help="Min duration in minutes")
@click.option("--max-duration", default=0, type=int, help="Max duration in minutes (0=no limit)")
@click.option("--skip-transcripts", is_flag=True, help="Score on metadata only (fast mode)")
@click.option("--output-json", default=None, type=str, help="Save results to JSON file")
@click.option("--access-key", default=None, help="Gong access key (or set GONG_ACCESS_KEY)")
@click.option("--secret-key", default=None, help="Gong secret key (or set GONG_SECRET_KEY)")
@click.option("--cache-dir", default=".gong_cache", type=str, help="Cache directory")
@click.option("--no-cache", is_flag=True, help="Bypass cache, re-fetch from API")
@click.option("--scorer-version", default="v3", type=click.Choice(["v2", "v3"]), help="Scorer version (default: v3)")
def search(
    from_date: str,
    to_date: str,
    top: int,
    min_score: float,
    title_filter: Optional[str],
    min_duration: int,
    max_duration: int,
    skip_transcripts: bool,
    output_json: Optional[str],
    access_key: Optional[str],
    secret_key: Optional[str],
    cache_dir: str,
    no_cache: bool,
    scorer_version: str,
):
    """Search and score Gong calls for ClearPath relevance."""
    if scorer_version == "v3":
        from ..services.gong_scorer_v3 import GongScorerV3 as GongScorer
    else:
        from ..services.gong_scorer import GongScorer

    # Parse dates
    try:
        dt_from = datetime.strptime(from_date, "%Y-%m-%d")
        dt_to = datetime.strptime(to_date, "%Y-%m-%d")
    except ValueError:
        console.print("[red]Error: Dates must be in YYYY-MM-DD format[/red]")
        sys.exit(1)

    client = _get_client(access_key, secret_key, Path(cache_dir))
    scorer = GongScorer()
    use_cache = not no_cache

    try:
        # Phase 1: Fetch call list
        with console.status("[bold blue]Fetching call list from Gong..."):
            calls = client.list_calls(dt_from, dt_to, use_cache=use_cache)

        console.print(f"Found [bold]{len(calls)}[/bold] calls in date range")

        # Pre-filter by title and duration
        filtered = calls
        if title_filter:
            title_lower = title_filter.lower()
            filtered = [
                c for c in filtered
                if c.title and title_lower in c.title.lower()
            ]
            console.print(
                f"  After title filter '{title_filter}': [bold]{len(filtered)}[/bold] calls"
            )

        if min_duration > 0:
            filtered = [c for c in filtered if c.duration_minutes >= min_duration]
        if max_duration > 0:
            filtered = [c for c in filtered if c.duration_minutes <= max_duration]
        if min_duration > 0 or max_duration > 0:
            console.print(
                f"  After duration filter: [bold]{len(filtered)}[/bold] calls"
            )

        if not filtered:
            console.print("[yellow]No calls match the filters.[/yellow]")
            return

        # Phase 2: Fetch transcripts (unless skipped)
        transcripts_by_id = {}
        if not skip_transcripts:
            call_ids = [c.call_id for c in filtered]
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "Fetching transcripts...", total=len(call_ids)
                )
                # Fetch in batches, updating progress
                batch_size = 50
                for i in range(0, len(call_ids), batch_size):
                    batch = call_ids[i : i + batch_size]
                    batch_transcripts = client.get_transcripts(
                        batch, use_cache=use_cache
                    )
                    for t in batch_transcripts:
                        transcripts_by_id[t.call_id] = t
                    progress.advance(task, advance=len(batch))

        # Phase 3: Score calls
        scored = []
        for call in filtered:
            transcript = transcripts_by_id.get(call.call_id)
            result = scorer.score_call(call, transcript)
            scored.append(result)

        # Filter by min_score, sort by score descending
        scored = [s for s in scored if s.total_score >= min_score]
        scored.sort(key=lambda s: s.total_score, reverse=True)

        # Stats
        passed_gate = sum(1 for s in scored if s.passed_gate)
        console.print(
            f"\n[bold]Results:[/bold] {passed_gate} calls passed ClearPath gate, "
            f"{len(scored)} scored >= {min_score}"
        )

        # Display top N
        display = scored[:top]
        if not display:
            console.print("[yellow]No calls scored above the minimum threshold.[/yellow]")
            return

        table = Table(
            title=f"Top {len(display)} ClearPath-Relevant Calls",
            show_lines=True,
            title_style="bold cyan",
            expand=False,
            padding=(0, 1),
        )
        table.add_column("#", style="dim", justify="right", no_wrap=True)
        table.add_column("Score", style="bold", justify="right", no_wrap=True)
        table.add_column("Cust%", justify="right", no_wrap=True)
        table.add_column("Title", max_width=40, overflow="ellipsis")
        table.add_column("Date", no_wrap=True)
        table.add_column("Dur", justify="right", no_wrap=True)
        table.add_column("Hits", justify="right", no_wrap=True)
        table.add_column("Flow", justify="right", no_wrap=True)

        for i, sc in enumerate(display, 1):
            # Color-code score
            score_val = sc.total_score
            if score_val >= 0.6:
                score_style = "bold green"
            elif score_val >= 0.3:
                score_style = "bold yellow"
            else:
                score_style = "dim"

            # Color-code customer keyword ratio
            ckr = sc.customer_keyword_ratio
            if ckr >= 0.35:
                ckr_style = "bold green"
            elif ckr >= 0.15:
                ckr_style = "yellow"
            else:
                ckr_style = "dim red"

            date_str = (
                sc.metadata.started.strftime("%Y-%m-%d")
                if sc.metadata.started
                else "N/A"
            )
            dur_str = f"{sc.metadata.duration_minutes:.0f}m"

            table.add_row(
                str(i),
                f"[{score_style}]{score_val:.3f}[/{score_style}]",
                f"[{ckr_style}]{ckr:.0%}[/{ckr_style}]",
                escape(sc.metadata.title or "Untitled"),
                date_str,
                dur_str,
                str(sc.total_keyword_hits),
                str(sc.flow_steps_detected),
            )

        console.print(table)

        # Print call IDs for easy copy-paste
        console.print("\n[dim]Call IDs (for use with detail/export):[/dim]")
        for sc in display[:10]:
            console.print(f"  [cyan]{sc.metadata.call_id}[/cyan]  {escape(sc.metadata.title or '')}")

        # Save to JSON
        if output_json:
            output_data = {
                "search_params": {
                    "from_date": from_date,
                    "to_date": to_date,
                    "title_filter": title_filter,
                    "min_duration": min_duration,
                    "max_duration": max_duration,
                    "min_score": min_score,
                },
                "total_calls_scanned": len(calls),
                "calls_passing_gate": passed_gate,
                "results": [s.model_dump(mode="json") for s in scored],
            }
            with open(output_json, "w") as f:
                json.dump(output_data, f, indent=2, default=str)
            console.print(f"\nResults saved to [bold]{output_json}[/bold]")

    finally:
        client.close()


@main.command()
@click.argument("call_id")
@click.option("--show-transcript", is_flag=True, help="Print the full transcript")
@click.option("--highlight-keywords", is_flag=True, help="Highlight keywords in transcript")
@click.option("--access-key", default=None, help="Gong access key")
@click.option("--secret-key", default=None, help="Gong secret key")
@click.option("--cache-dir", default=".gong_cache", type=str)
@click.option("--scorer-version", default="v3", type=click.Choice(["v2", "v3"]), help="Scorer version (default: v3)")
def detail(
    call_id: str,
    show_transcript: bool,
    highlight_keywords: bool,
    access_key: Optional[str],
    secret_key: Optional[str],
    cache_dir: str,
    scorer_version: str,
):
    """Show detailed scoring breakdown for a specific call."""
    if scorer_version == "v3":
        from ..services.gong_scorer_v3 import GongScorerV3 as GongScorer
    else:
        from ..services.gong_scorer import GongScorer

    client = _get_client(access_key, secret_key, Path(cache_dir))
    scorer = GongScorer()

    try:
        # Fetch call details and transcript
        with console.status("[bold blue]Fetching call details..."):
            details = client.get_call_details([call_id])
            transcripts = client.get_transcripts([call_id])

        if not details:
            console.print(f"[red]Call {call_id} not found[/red]")
            return

        metadata = details[0]
        transcript = transcripts[0] if transcripts else None

        # Score it
        scored = scorer.score_call(metadata, transcript)

        # Display metadata panel
        participants_str = ", ".join(
            f"{p.name} ({p.affiliation or 'unknown'})" for p in metadata.participants
        )
        meta_text = (
            f"[bold]Title:[/bold] {escape(metadata.title or 'Untitled')}\n"
            f"[bold]Date:[/bold] {metadata.started.strftime('%Y-%m-%d %H:%M') if metadata.started else 'N/A'}\n"
            f"[bold]Duration:[/bold] {metadata.duration_minutes:.0f} min\n"
            f"[bold]Direction:[/bold] {metadata.direction or 'N/A'}\n"
            f"[bold]Participants:[/bold] {escape(participants_str)}\n"
            f"[bold]Gong URL:[/bold] {metadata.url or 'N/A'}\n"
            f"[bold]Call ID:[/bold] {call_id}"
        )
        console.print(Panel(meta_text, title="Call Metadata", border_style="blue"))

        # Score breakdown table
        score_table = Table(title="Score Breakdown", show_lines=True)
        score_table.add_column("Signal", width=25)
        score_table.add_column("Score", width=8, justify="right")
        score_table.add_column("Weight", width=8, justify="right")
        score_table.add_column("Contribution", width=12, justify="right")

        weights = {
            "customer_workflow": 0.40,
            "customer_actions": 0.25,
            "flow_structure": 0.15,
            "clearpath_depth": 0.10,
            "customer_engagement": 0.10,
        }
        total_contribution = 0.0
        for signal, weight in weights.items():
            score = scored.score_breakdown.get(signal, 0.0)
            contrib = score * weight
            total_contribution += contrib
            score_table.add_row(
                signal, f"{score:.3f}", f"{weight:.2f}", f"{contrib:.4f}"
            )
        # Show call_properties as info-only (not weighted)
        props = scored.score_breakdown.get("call_properties", 0.0)
        score_table.add_row("call_properties", f"{props:.3f}", "[dim]info[/dim]", "[dim]—[/dim]")
        score_table.add_row(
            "[bold]TOTAL[/bold]", "", "", f"[bold]{total_contribution:.4f}[/bold]"
        )
        console.print(score_table)

        # Gate status
        if scored.passed_gate:
            console.print("[green]ClearPath gate: PASSED[/green]")
        else:
            console.print("[red]ClearPath gate: FAILED (no ClearPath keywords found)[/red]")

        # Keyword matches table
        if scored.keyword_matches:
            kw_table = Table(
                title=f"Keyword Matches ({scored.total_keyword_hits} total)",
                show_lines=True,
            )
            kw_table.add_column("Category", width=20)
            kw_table.add_column("Keyword", width=25)
            kw_table.add_column("Count", width=6, justify="right")
            kw_table.add_column("Sample", width=60, no_wrap=True)

            # Sort by count descending
            sorted_matches = sorted(
                scored.keyword_matches, key=lambda m: m.count, reverse=True
            )
            for m in sorted_matches[:30]:
                sample = escape(m.sample_sentences[0][:60]) if m.sample_sentences else ""
                kw_table.add_row(m.category, m.keyword, str(m.count), sample + "...")
            console.print(kw_table)

        # Extra stats
        console.print(
            f"\n[dim]Transcript words: {scored.transcript_word_count} | "
            f"Flow steps detected: {scored.flow_steps_detected} | "
            f"External speaker ratio: {scored.external_speaker_ratio:.1%} | "
            f"Customer keyword ratio: {scored.customer_keyword_ratio:.1%}[/dim]"
        )

        # Relevant snippets
        if scored.relevant_snippets:
            console.print("\n[bold]Most Relevant Snippets:[/bold]")
            for i, snippet in enumerate(scored.relevant_snippets, 1):
                console.print(f"  {i}. [italic]{escape(snippet)}[/italic]")

        # Full transcript
        if show_transcript and transcript:
            console.print("\n")
            console.print(
                Panel("[bold]Full Transcript[/bold]", border_style="green")
            )

            all_keywords = (
                scorer.keywords.gate_product
                + scorer.keywords.process_language
                + scorer.keywords.customer_ownership
                + scorer.keywords.actionable
                + scorer.keywords.clearpath_features
            )

            for sentence in transcript.sentences:
                speaker = sentence.speaker_id or "?"
                text = sentence.text

                if highlight_keywords:
                    rich_text = Text(text)
                    text_lower = text.lower()
                    for kw in all_keywords:
                        start = 0
                        kw_lower = kw.lower()
                        while True:
                            idx = text_lower.find(kw_lower, start)
                            if idx == -1:
                                break
                            rich_text.stylize(
                                "bold yellow", idx, idx + len(kw)
                            )
                            start = idx + 1
                    console.print(f"  [dim]Speaker {speaker}:[/dim] ", end="")
                    console.print(rich_text)
                else:
                    console.print(f"  [dim]Speaker {speaker}:[/dim] {escape(text)}")

    finally:
        client.close()


@main.command()
@click.option("--call-ids", default=None, help="Comma-separated call IDs")
@click.option("--from-json", default=None, help="Load from search results JSON file")
@click.option("--top", default=10, help="When using --from-json, export top N calls")
@click.option("--output-dir", default="gong_transcripts", help="Output directory")
@click.option("--format", "fmt", default="txt", type=click.Choice(["txt", "json"]))
@click.option("--access-key", default=None, help="Gong access key")
@click.option("--secret-key", default=None, help="Gong secret key")
@click.option("--cache-dir", default=".gong_cache", type=str)
def export(
    call_ids: Optional[str],
    from_json: Optional[str],
    top: int,
    output_dir: str,
    fmt: str,
    access_key: Optional[str],
    secret_key: Optional[str],
    cache_dir: str,
):
    """Export transcripts for selected calls to files."""
    # Resolve call IDs
    ids_to_export: list[str] = []

    if from_json:
        with open(from_json) as f:
            data = json.load(f)
        results = data.get("results", [])
        # Already sorted by score in the search output
        for r in results[:top]:
            meta = r.get("metadata", {})
            cid = meta.get("call_id", "")
            if cid:
                ids_to_export.append(cid)
        console.print(
            f"Loaded [bold]{len(ids_to_export)}[/bold] call IDs from {from_json}"
        )
    elif call_ids:
        ids_to_export = [cid.strip() for cid in call_ids.split(",") if cid.strip()]
    else:
        console.print("[red]Error: Provide --call-ids or --from-json[/red]")
        sys.exit(1)

    if not ids_to_export:
        console.print("[yellow]No call IDs to export.[/yellow]")
        return

    client = _get_client(access_key, secret_key, Path(cache_dir))
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    try:
        # Fetch details for filenames
        with console.status("[bold blue]Fetching call details..."):
            details = client.get_call_details(ids_to_export)
        details_by_id = {d.call_id: d for d in details}

        # Fetch transcripts
        with console.status("[bold blue]Fetching transcripts..."):
            transcripts = client.get_transcripts(ids_to_export)

        exported = 0
        for transcript in transcripts:
            meta = details_by_id.get(transcript.call_id)
            title_slug = "untitled"
            if meta and meta.title:
                title_slug = (
                    meta.title.lower()
                    .replace(" ", "_")
                    .replace("/", "-")[:50]
                )
                # Remove non-alphanumeric chars except _ and -
                title_slug = "".join(
                    c for c in title_slug if c.isalnum() or c in "_-"
                )

            date_str = ""
            if meta and meta.started:
                date_str = meta.started.strftime("%Y%m%d") + "_"

            filename = f"{date_str}{title_slug}_{transcript.call_id[:8]}.{fmt}"
            filepath = out_path / filename

            if fmt == "json":
                with open(filepath, "w") as f:
                    json.dump(transcript.model_dump(mode="json"), f, indent=2, default=str)
            else:
                # Text format with speaker labels
                lines = []
                if meta:
                    lines.append(f"Title: {meta.title or 'Untitled'}")
                    lines.append(
                        f"Date: {meta.started.strftime('%Y-%m-%d %H:%M') if meta.started else 'N/A'}"
                    )
                    lines.append(f"Duration: {meta.duration_minutes:.0f} min")
                    participants = ", ".join(
                        f"{p.name} ({p.affiliation or '?'})"
                        for p in meta.participants
                    )
                    lines.append(f"Participants: {participants}")
                    lines.append(f"Call ID: {transcript.call_id}")
                    lines.append("")
                    lines.append("=" * 80)
                    lines.append("")

                for sentence in transcript.sentences:
                    speaker = sentence.speaker_name or sentence.speaker_id or "Unknown"
                    lines.append(f"[{speaker}]: {sentence.text}")

                with open(filepath, "w") as f:
                    f.write("\n".join(lines))

            exported += 1
            console.print(f"  Exported: [cyan]{filepath}[/cyan]")

        console.print(
            f"\n[bold green]Exported {exported} transcripts to {output_dir}/[/bold green]"
        )

    finally:
        client.close()


@main.command("clear-cache")
@click.option("--cache-dir", default=".gong_cache", type=str)
def clear_cache(cache_dir: str):
    """Remove the Gong API cache directory."""
    cache_path = Path(cache_dir)
    if cache_path.exists():
        shutil.rmtree(cache_path)
        console.print(f"[green]Cleared cache at {cache_path}[/green]")
    else:
        console.print(f"[yellow]No cache directory found at {cache_path}[/yellow]")
