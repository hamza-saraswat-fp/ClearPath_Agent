"""Pattern Extraction Engine.

Analyzes parsed production data to discover usage patterns including
status flows, action-widget co-occurrences, and role preferences.
"""

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional

from .prod_data_parser import ParsedWorkflow

logger = logging.getLogger(__name__)


# ============================================================================
# Pattern Models
# ============================================================================


@dataclass
class StatusFlow:
    """Sequence of statuses with transition counts."""

    sequence: list[str] = field(default_factory=list)
    count: int = 0
    flow_names: list[str] = field(default_factory=list)

    @property
    def as_string(self) -> str:
        """Return flow as arrow-separated string."""
        return " -> ".join(self.sequence)

    def __hash__(self):
        return hash(tuple(self.sequence))


@dataclass
class CooccurrencePattern:
    """Pair of action/widget with co-occurrence statistics."""

    source_type: str  # "action" or "widget"
    source_id: str
    source_name: str
    target_type: str  # "action" or "widget"
    target_id: str
    target_name: str
    count: int = 0
    confidence: float = 0.0
    contexts: list[str] = field(default_factory=list)  # Status names where seen

    def __hash__(self):
        return hash((self.source_id, self.target_id))


@dataclass
class ActionPreferences:
    """Role-specific action/widget usage statistics."""

    action_counts: dict[str, int] = field(default_factory=dict)
    widget_counts: dict[str, int] = field(default_factory=dict)
    total_statuses: int = 0

    @property
    def top_actions(self) -> list[tuple[str, int]]:
        """Get top 10 actions by count."""
        return sorted(self.action_counts.items(), key=lambda x: -x[1])[:10]

    @property
    def top_widgets(self) -> list[tuple[str, int]]:
        """Get top 10 widgets by count."""
        return sorted(self.widget_counts.items(), key=lambda x: -x[1])[:10]


@dataclass
class FrequencyStats:
    """Global frequency counts for all entities."""

    action_frequencies: Counter = field(default_factory=Counter)
    widget_frequencies: Counter = field(default_factory=Counter)
    status_frequencies: Counter = field(default_factory=Counter)
    action_widget_pairs: Counter = field(default_factory=Counter)  # (action, widget) pairs
    action_action_pairs: Counter = field(default_factory=Counter)  # (action, action) pairs
    total_workflows: int = 0

    def get_action_frequency(self, action: str) -> int:
        """Get frequency count for an action."""
        return self.action_frequencies.get(action, 0)

    def get_widget_frequency(self, widget: str) -> int:
        """Get frequency count for a widget."""
        return self.widget_frequencies.get(widget, 0)

    def get_cooccurrence_count(self, action: str, widget: str) -> int:
        """Get co-occurrence count for action-widget pair."""
        return self.action_widget_pairs.get((action, widget), 0)


# ============================================================================
# Pattern Extractor
# ============================================================================


class PatternExtractor:
    """Service for extracting usage patterns from production data."""

    # Thresholds for filtering patterns
    MIN_OCCURRENCES = 2
    MIN_CONFIDENCE = 0.5

    def __init__(
        self,
        min_occurrences: int = MIN_OCCURRENCES,
        min_confidence: float = MIN_CONFIDENCE,
    ):
        """Initialize the pattern extractor.

        Args:
            min_occurrences: Minimum occurrences to include pattern
            min_confidence: Minimum confidence score (0-1)
        """
        self.min_occurrences = min_occurrences
        self.min_confidence = min_confidence

    def extract_status_flows(
        self, workflows: list[ParsedWorkflow]
    ) -> list[StatusFlow]:
        """Identify common status sequences across workflows.

        Args:
            workflows: List of parsed workflows

        Returns:
            List of StatusFlow objects representing common sequences
        """
        flow_counts: dict[tuple, StatusFlow] = {}

        for workflow in workflows:
            if not workflow.statuses:
                continue

            # Sort statuses by sequence
            sorted_statuses = sorted(workflow.statuses, key=lambda s: s.sequence)
            sequence = [s.name for s in sorted_statuses]

            if len(sequence) < 2:
                continue

            seq_tuple = tuple(sequence)
            if seq_tuple not in flow_counts:
                flow_counts[seq_tuple] = StatusFlow(
                    sequence=sequence,
                    count=0,
                    flow_names=[],
                )
            flow_counts[seq_tuple].count += 1
            if workflow.flow_name:
                flow_counts[seq_tuple].flow_names.append(workflow.flow_name)

        # Filter by minimum occurrences
        flows = [f for f in flow_counts.values() if f.count >= self.min_occurrences]

        # Sort by count descending
        flows.sort(key=lambda f: -f.count)

        logger.info(f"Extracted {len(flows)} status flows from {len(workflows)} workflows")
        return flows

    def extract_action_widget_cooccurrence(
        self, workflows: list[ParsedWorkflow]
    ) -> list[CooccurrencePattern]:
        """Find which actions and widgets appear together.

        Args:
            workflows: List of parsed workflows

        Returns:
            List of CooccurrencePattern objects
        """
        # Track action-widget pairs per status
        pair_counts: Counter = Counter()
        action_counts: Counter = Counter()
        pair_contexts: defaultdict = defaultdict(set)

        for workflow in workflows:
            # Group by status
            status_actions: dict[str, set[str]] = defaultdict(set)
            status_widgets: dict[str, set[str]] = defaultdict(set)

            for button in workflow.action_buttons:
                status_actions[button.status_name].add(button.action_type)
                action_counts[button.action_type] += 1

            for fv in workflow.focus_views:
                for widget in fv.widgets:
                    status_widgets[fv.status_name].add(widget)

            # Find co-occurrences within same status
            for status_name in status_actions:
                actions = status_actions[status_name]
                widgets = status_widgets.get(status_name, set())

                for action in actions:
                    for widget in widgets:
                        pair = (action, widget)
                        pair_counts[pair] += 1
                        pair_contexts[pair].add(status_name)

        # Calculate confidence and create patterns
        patterns = []
        for (action, widget), count in pair_counts.items():
            if count < self.min_occurrences:
                continue

            # Confidence = how often widget appears when action is present
            action_total = action_counts[action]
            confidence = count / action_total if action_total > 0 else 0

            if confidence < self.min_confidence:
                continue

            pattern = CooccurrencePattern(
                source_type="action",
                source_id=self._normalize_id(action, "action"),
                source_name=action,
                target_type="widget",
                target_id=self._normalize_id(widget, "widget"),
                target_name=widget,
                count=count,
                confidence=round(confidence, 3),
                contexts=list(pair_contexts[(action, widget)]),
            )
            patterns.append(pattern)

        # Sort by confidence descending
        patterns.sort(key=lambda p: (-p.confidence, -p.count))

        logger.info(
            f"Extracted {len(patterns)} action-widget co-occurrence patterns"
        )
        return patterns

    def extract_action_cooccurrence(
        self, workflows: list[ParsedWorkflow]
    ) -> list[CooccurrencePattern]:
        """Find which actions commonly appear together.

        Args:
            workflows: List of parsed workflows

        Returns:
            List of CooccurrencePattern objects for action pairs
        """
        pair_counts: Counter = Counter()
        action_counts: Counter = Counter()
        pair_contexts: defaultdict = defaultdict(set)

        for workflow in workflows:
            # Group actions by status
            status_actions: dict[str, set[str]] = defaultdict(set)

            for button in workflow.action_buttons:
                status_actions[button.status_name].add(button.action_type)
                action_counts[button.action_type] += 1

            # Find action pairs within same status
            for status_name, actions in status_actions.items():
                action_list = sorted(actions)
                for i, action1 in enumerate(action_list):
                    for action2 in action_list[i + 1 :]:
                        pair = (action1, action2)
                        pair_counts[pair] += 1
                        pair_contexts[pair].add(status_name)

        # Calculate confidence and create patterns
        patterns = []
        for (action1, action2), count in pair_counts.items():
            if count < self.min_occurrences:
                continue

            # Confidence based on smaller action count
            min_count = min(action_counts[action1], action_counts[action2])
            confidence = count / min_count if min_count > 0 else 0

            if confidence < self.min_confidence:
                continue

            pattern = CooccurrencePattern(
                source_type="action",
                source_id=self._normalize_id(action1, "action"),
                source_name=action1,
                target_type="action",
                target_id=self._normalize_id(action2, "action"),
                target_name=action2,
                count=count,
                confidence=round(confidence, 3),
                contexts=list(pair_contexts[(action1, action2)]),
            )
            patterns.append(pattern)

        patterns.sort(key=lambda p: (-p.confidence, -p.count))

        logger.info(f"Extracted {len(patterns)} action-action co-occurrence patterns")
        return patterns

    def extract_role_preferences(
        self, workflows: list[ParsedWorkflow]
    ) -> dict[str, ActionPreferences]:
        """Identify action/widget preferences by user role.

        Args:
            workflows: List of parsed workflows

        Returns:
            Dict mapping role name to ActionPreferences
        """
        role_prefs: dict[str, ActionPreferences] = {}

        for workflow in workflows:
            # Track actions per role
            for button in workflow.action_buttons:
                role = button.user_role.value
                if role not in role_prefs:
                    role_prefs[role] = ActionPreferences()

                prefs = role_prefs[role]
                action = button.action_type
                prefs.action_counts[action] = prefs.action_counts.get(action, 0) + 1

            # Track widgets per role
            for fv in workflow.focus_views:
                role = fv.user_role.value
                if role not in role_prefs:
                    role_prefs[role] = ActionPreferences()

                prefs = role_prefs[role]
                prefs.total_statuses += 1

                for widget in fv.widgets:
                    prefs.widget_counts[widget] = prefs.widget_counts.get(widget, 0) + 1

        logger.info(f"Extracted preferences for {len(role_prefs)} user roles")
        return role_prefs

    def calculate_frequencies(
        self, workflows: list[ParsedWorkflow]
    ) -> FrequencyStats:
        """Count how often each action/widget/status appears.

        Args:
            workflows: List of parsed workflows

        Returns:
            FrequencyStats with global counts
        """
        stats = FrequencyStats(total_workflows=len(workflows))

        for workflow in workflows:
            # Count statuses
            for status in workflow.statuses:
                stats.status_frequencies[status.name] += 1

            # Group by status for pair counting
            status_actions: dict[str, set[str]] = defaultdict(set)
            status_widgets: dict[str, set[str]] = defaultdict(set)

            # Count actions
            for button in workflow.action_buttons:
                stats.action_frequencies[button.action_type] += 1
                status_actions[button.status_name].add(button.action_type)

            # Count widgets
            for fv in workflow.focus_views:
                for widget in fv.widgets:
                    stats.widget_frequencies[widget] += 1
                    status_widgets[fv.status_name].add(widget)

            # Count pairs within same status
            for status_name in status_actions:
                actions = list(status_actions[status_name])
                widgets = list(status_widgets.get(status_name, []))

                # Action-widget pairs
                for action in actions:
                    for widget in widgets:
                        stats.action_widget_pairs[(action, widget)] += 1

                # Action-action pairs
                for i, a1 in enumerate(actions):
                    for a2 in actions[i + 1 :]:
                        pair = tuple(sorted([a1, a2]))
                        stats.action_action_pairs[pair] += 1

        logger.info(
            f"Calculated frequencies: "
            f"{len(stats.action_frequencies)} actions, "
            f"{len(stats.widget_frequencies)} widgets, "
            f"{len(stats.status_frequencies)} statuses"
        )
        return stats

    def extract_all_patterns(
        self, workflows: list[ParsedWorkflow]
    ) -> dict:
        """Extract all pattern types at once.

        Args:
            workflows: List of parsed workflows

        Returns:
            Dict containing all extracted patterns
        """
        logger.info(f"Extracting all patterns from {len(workflows)} workflows")

        return {
            "status_flows": self.extract_status_flows(workflows),
            "action_widget_cooccurrence": self.extract_action_widget_cooccurrence(
                workflows
            ),
            "action_cooccurrence": self.extract_action_cooccurrence(workflows),
            "role_preferences": self.extract_role_preferences(workflows),
            "frequencies": self.calculate_frequencies(workflows),
        }

    def _normalize_id(self, name: str, entity_type: str) -> str:
        """Normalize a name to an ID format.

        Args:
            name: Entity name
            entity_type: "action", "widget", or "status"

        Returns:
            Normalized ID string
        """
        # Convert to lowercase, replace spaces with underscores
        normalized = name.lower().strip()
        normalized = normalized.replace(" ", "_")
        normalized = normalized.replace("/", "_")
        normalized = "".join(c for c in normalized if c.isalnum() or c == "_")
        return f"{entity_type}:{normalized}"

    def get_top_patterns(
        self,
        patterns: list[CooccurrencePattern],
        n: int = 10,
    ) -> list[CooccurrencePattern]:
        """Get top N patterns by confidence.

        Args:
            patterns: List of patterns
            n: Number of top patterns to return

        Returns:
            Top N patterns
        """
        return sorted(patterns, key=lambda p: (-p.confidence, -p.count))[:n]

    def summarize_patterns(self, patterns: dict) -> str:
        """Generate a text summary of extracted patterns.

        Args:
            patterns: Dict from extract_all_patterns

        Returns:
            Human-readable summary string
        """
        lines = ["=" * 50, "Pattern Extraction Summary", "=" * 50, ""]

        # Status flows
        flows = patterns.get("status_flows", [])
        lines.append(f"Status Flows: {len(flows)} unique sequences")
        for flow in flows[:5]:
            lines.append(f"  - {flow.as_string} (count: {flow.count})")
        if len(flows) > 5:
            lines.append(f"  ... and {len(flows) - 5} more")
        lines.append("")

        # Action-widget co-occurrence
        aw_patterns = patterns.get("action_widget_cooccurrence", [])
        lines.append(f"Action-Widget Pairs: {len(aw_patterns)} patterns")
        for p in aw_patterns[:5]:
            lines.append(
                f"  - {p.source_name} + {p.target_name}: "
                f"{p.confidence:.0%} confidence ({p.count} occurrences)"
            )
        if len(aw_patterns) > 5:
            lines.append(f"  ... and {len(aw_patterns) - 5} more")
        lines.append("")

        # Action-action co-occurrence
        aa_patterns = patterns.get("action_cooccurrence", [])
        lines.append(f"Action-Action Pairs: {len(aa_patterns)} patterns")
        for p in aa_patterns[:5]:
            lines.append(
                f"  - {p.source_name} + {p.target_name}: "
                f"{p.confidence:.0%} confidence ({p.count} occurrences)"
            )
        if len(aa_patterns) > 5:
            lines.append(f"  ... and {len(aa_patterns) - 5} more")
        lines.append("")

        # Frequencies
        freqs = patterns.get("frequencies")
        if freqs:
            lines.append(f"Frequencies (from {freqs.total_workflows} workflows):")
            lines.append(f"  - Actions: {len(freqs.action_frequencies)} unique")
            lines.append(f"  - Widgets: {len(freqs.widget_frequencies)} unique")
            lines.append(f"  - Statuses: {len(freqs.status_frequencies)} unique")

            # Top actions
            top_actions = freqs.action_frequencies.most_common(5)
            lines.append("  Top actions:")
            for action, count in top_actions:
                lines.append(f"    - {action}: {count}")

            # Top widgets
            top_widgets = freqs.widget_frequencies.most_common(5)
            lines.append("  Top widgets:")
            for widget, count in top_widgets:
                lines.append(f"    - {widget}: {count}")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)
