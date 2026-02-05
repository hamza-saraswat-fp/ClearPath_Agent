"""Ingestion Report Generator.

Generates human-readable reports for ingestion pipeline results.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .data_validator import ValidationResult
from .pattern_extractor import CooccurrencePattern, StatusFlow

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Service for generating ingestion reports."""

    def generate_summary_report(self, stats: dict) -> str:
        """Generate overall statistics report in Markdown format.

        Args:
            stats: Dictionary of ingestion statistics

        Returns:
            Markdown-formatted report string
        """
        lines = [
            "# ClearPath Knowledge Base Ingestion Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Duration
        if "duration" in stats:
            lines.append(f"**Duration:** {stats['duration']}")
            lines.append("")

        # Seed Data Section
        lines.extend(
            [
                "## Seed Data",
                "",
                "| Entity Type | Count |",
                "|-------------|-------|",
                f"| Actions | {stats.get('seed_actions', 0)} |",
                f"| Widgets | {stats.get('seed_widgets', 0)} |",
                f"| Status Patterns | {stats.get('seed_patterns', 0)} |",
                f"| Relationships | {stats.get('seed_relationships', 0)} |",
                "",
            ]
        )

        # Production Data Section
        lines.extend(
            [
                "## Production Data",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Files Parsed | {stats.get('prod_files_parsed', 0)} |",
                f"| Statuses Found | {stats.get('prod_statuses', 0)} |",
                f"| Action Buttons | {stats.get('prod_actions', 0)} |",
                f"| Unique Widgets | {stats.get('prod_widgets', 0)} |",
                "",
            ]
        )

        # Pattern Extraction Section
        lines.extend(
            [
                "## Pattern Extraction",
                "",
                f"- **Total Patterns Discovered:** {stats.get('patterns_extracted', 0)}",
                "",
            ]
        )

        # Validation Section
        lines.extend(
            [
                "## Validation Results",
                "",
                f"- **Errors:** {stats.get('validation_errors', 0)}",
                f"- **Warnings:** {stats.get('validation_warnings', 0)}",
                "",
            ]
        )

        # Embedding Section
        if stats.get("embeddings_generated", 0) > 0:
            lines.extend(
                [
                    "## Embeddings",
                    "",
                    f"- **Total Generated:** {stats.get('embeddings_generated', 0)}",
                    "",
                ]
            )

        # Database Operations Section
        lines.extend(
            [
                "## Database Operations",
                "",
                "### Vector Store (Supabase)",
                "",
                f"- **Records Upserted:** {stats.get('vector_records_upserted', 0)}",
                "",
                "### Graph Store (Neo4j)",
                "",
                f"- **Nodes Created:** {stats.get('graph_nodes_created', 0)}",
                f"- **Relationships Created:** {stats.get('graph_relationships_created', 0)}",
                "",
            ]
        )

        return "\n".join(lines)

    def generate_validation_report(self, results: list[ValidationResult]) -> str:
        """Generate detailed validation report.

        Args:
            results: List of ValidationResult objects

        Returns:
            Markdown-formatted report string
        """
        lines = [
            "# Validation Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Summary
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        invalid = total - valid
        all_errors = sum(len(r.errors) for r in results)
        all_warnings = sum(len(r.warnings) for r in results)

        lines.extend(
            [
                "## Summary",
                "",
                f"- **Total Entities:** {total}",
                f"- **Valid:** {valid}",
                f"- **Invalid:** {invalid}",
                f"- **Total Errors:** {all_errors}",
                f"- **Total Warnings:** {all_warnings}",
                "",
            ]
        )

        # Group by entity type
        by_type: dict[str, list[ValidationResult]] = {}
        for result in results:
            if result.entity_type not in by_type:
                by_type[result.entity_type] = []
            by_type[result.entity_type].append(result)

        for entity_type, type_results in by_type.items():
            lines.append(f"## {entity_type.title()}s")
            lines.append("")

            invalid_results = [r for r in type_results if not r.is_valid]
            warning_results = [r for r in type_results if r.is_valid and r.warnings]

            if not invalid_results and not warning_results:
                lines.append("All entities valid.")
                lines.append("")
                continue

            if invalid_results:
                lines.append("### Errors")
                lines.append("")
                for result in invalid_results[:20]:
                    lines.append(f"**{result.entity_id}**")
                    for issue in result.errors:
                        lines.append(f"- `{issue.field}`: {issue.message}")
                        if issue.suggestion:
                            lines.append(f"  - Suggestion: `{issue.suggestion}`")
                    lines.append("")
                if len(invalid_results) > 20:
                    lines.append(f"*... and {len(invalid_results) - 20} more*")
                    lines.append("")

            if warning_results:
                lines.append("### Warnings")
                lines.append("")
                for result in warning_results[:20]:
                    lines.append(f"**{result.entity_id}**")
                    for issue in result.warnings:
                        lines.append(f"- `{issue.field}`: {issue.message}")
                    lines.append("")
                if len(warning_results) > 20:
                    lines.append(f"*... and {len(warning_results) - 20} more*")
                    lines.append("")

        return "\n".join(lines)

    def generate_enrichment_report(
        self,
        enriched: dict,
        original: dict,
    ) -> str:
        """Generate report of what was added/changed during enrichment.

        Args:
            enriched: Enriched data dict
            original: Original seed data dict

        Returns:
            Markdown-formatted report string
        """
        lines = [
            "# Enrichment Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Actions enrichment
        lines.append("## Actions Enriched")
        lines.append("")

        enriched_actions = enriched.get("actions", [])
        original_ids = {a.get("id") for a in original.get("actions", [])}

        new_actions = [a for a in enriched_actions if a.get("id") not in original_ids]
        if new_actions:
            lines.append(f"### New Actions Discovered ({len(new_actions)})")
            lines.append("")
            for action in new_actions[:10]:
                lines.append(f"- **{action.get('name')}** (ID: `{action.get('id')}`)")
                if action.get("needs_review"):
                    lines.append("  - ⚠️ Needs review")
            if len(new_actions) > 10:
                lines.append(f"  *... and {len(new_actions) - 10} more*")
            lines.append("")

        # Frequency enrichment
        freq_enriched = [
            a
            for a in enriched_actions
            if a.get("production_frequency", 0) > 0 and a.get("id") in original_ids
        ]
        if freq_enriched:
            lines.append(f"### Actions with Production Data ({len(freq_enriched)})")
            lines.append("")
            lines.append("| Action | Frequency | Top Co-occurrences |")
            lines.append("|--------|-----------|-------------------|")
            for action in sorted(
                freq_enriched, key=lambda a: -a.get("production_frequency", 0)
            )[:15]:
                coocs = action.get("production_cooccurrences", [])[:3]
                cooc_str = ", ".join(c.get("widget", "") for c in coocs) if coocs else "-"
                lines.append(
                    f"| {action.get('name')} | {action.get('production_frequency', 0)} | {cooc_str} |"
                )
            lines.append("")

        # Widgets enrichment
        lines.append("## Widgets Enriched")
        lines.append("")

        enriched_widgets = enriched.get("widgets", [])
        original_widget_ids = {w.get("id") for w in original.get("widgets", [])}

        new_widgets = [
            w for w in enriched_widgets if w.get("id") not in original_widget_ids
        ]
        if new_widgets:
            lines.append(f"### New Widgets Discovered ({len(new_widgets)})")
            lines.append("")
            for widget in new_widgets[:10]:
                lines.append(f"- **{widget.get('name')}** (ID: `{widget.get('id')}`)")
            if len(new_widgets) > 10:
                lines.append(f"  *... and {len(new_widgets) - 10} more*")
            lines.append("")

        return "\n".join(lines)

    def generate_pattern_report(
        self,
        patterns: list[CooccurrencePattern],
        flows: Optional[list[StatusFlow]] = None,
    ) -> str:
        """Generate report of discovered patterns.

        Args:
            patterns: List of co-occurrence patterns
            flows: Optional list of status flows

        Returns:
            Markdown-formatted report string
        """
        lines = [
            "# Pattern Discovery Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Status flows
        if flows:
            lines.append("## Status Flows")
            lines.append("")
            lines.append("Common workflow sequences discovered from production data:")
            lines.append("")

            for i, flow in enumerate(flows[:10], 1):
                flow_str = " → ".join(flow.sequence)
                lines.append(f"{i}. **{flow_str}**")
                lines.append(f"   - Occurrences: {flow.count}")
                if flow.flow_names:
                    lines.append(f"   - Examples: {', '.join(flow.flow_names[:3])}")
            lines.append("")

        # Action-Widget patterns
        aw_patterns = [p for p in patterns if p.target_type == "widget"]
        if aw_patterns:
            lines.append("## Action-Widget Co-occurrences")
            lines.append("")
            lines.append("Actions that frequently appear with specific widgets:")
            lines.append("")
            lines.append("| Action | Widget | Confidence | Count |")
            lines.append("|--------|--------|------------|-------|")

            for p in sorted(aw_patterns, key=lambda x: -x.confidence)[:20]:
                lines.append(
                    f"| {p.source_name} | {p.target_name} | {p.confidence:.0%} | {p.count} |"
                )
            lines.append("")

        # Action-Action patterns
        aa_patterns = [p for p in patterns if p.target_type == "action"]
        if aa_patterns:
            lines.append("## Action-Action Co-occurrences")
            lines.append("")
            lines.append("Actions that frequently appear together:")
            lines.append("")
            lines.append("| Action 1 | Action 2 | Confidence | Count |")
            lines.append("|----------|----------|------------|-------|")

            for p in sorted(aa_patterns, key=lambda x: -x.confidence)[:20]:
                lines.append(
                    f"| {p.source_name} | {p.target_name} | {p.confidence:.0%} | {p.count} |"
                )
            lines.append("")

        return "\n".join(lines)

    def save_report(
        self,
        content: str,
        output_dir: Path,
        name: str,
        format: str = "md",
    ) -> Path:
        """Save a report to file.

        Args:
            content: Report content
            output_dir: Output directory
            name: Report name (without extension)
            format: Output format ("md" or "txt")

        Returns:
            Path to saved report
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.{format}"
        filepath = output_dir / filename

        with open(filepath, "w") as f:
            f.write(content)

        logger.info(f"Report saved to: {filepath}")
        return filepath

    def save_json_stats(
        self,
        stats: dict,
        output_dir: Path,
        name: str = "ingestion_stats",
    ) -> Path:
        """Save statistics as JSON for programmatic access.

        Args:
            stats: Statistics dictionary
            output_dir: Output directory
            name: File name (without extension)

        Returns:
            Path to saved JSON file
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.json"
        filepath = output_dir / filename

        # Convert datetime objects to strings
        serializable_stats = {}
        for key, value in stats.items():
            if isinstance(value, datetime):
                serializable_stats[key] = value.isoformat()
            else:
                serializable_stats[key] = value

        with open(filepath, "w") as f:
            json.dump(serializable_stats, f, indent=2)

        logger.info(f"Stats saved to: {filepath}")
        return filepath

    def generate_console_summary(self, stats: dict) -> str:
        """Generate a brief console-friendly summary.

        Args:
            stats: Statistics dictionary

        Returns:
            Formatted summary string
        """
        lines = [
            "",
            "=" * 50,
            "INGESTION COMPLETE",
            "=" * 50,
            "",
            f"Seed Data:     {stats.get('seed_actions', 0)} actions, "
            f"{stats.get('seed_widgets', 0)} widgets, "
            f"{stats.get('seed_patterns', 0)} patterns",
            f"Production:    {stats.get('prod_files_parsed', 0)} files, "
            f"{stats.get('prod_statuses', 0)} statuses",
            f"Patterns:      {stats.get('patterns_extracted', 0)} discovered",
            f"Embeddings:    {stats.get('embeddings_generated', 0)} generated",
            f"Vector Store:  {stats.get('vector_records_upserted', 0)} records",
            f"Graph Store:   {stats.get('graph_nodes_created', 0)} nodes, "
            f"{stats.get('graph_relationships_created', 0)} relationships",
            f"Validation:    {stats.get('validation_errors', 0)} errors, "
            f"{stats.get('validation_warnings', 0)} warnings",
            "",
            f"Duration: {stats.get('duration', 'N/A')}",
            "=" * 50,
        ]
        return "\n".join(lines)
