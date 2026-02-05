"""Data Enrichment Pipeline.

Combines seed data with production patterns to create enriched entities
with frequency counts, co-occurrence data, and real-world examples.
"""

import logging
from difflib import SequenceMatcher
from typing import Optional

from .pattern_extractor import FrequencyStats, StatusFlow
from .prod_data_parser import ParsedWorkflow

logger = logging.getLogger(__name__)


class DataEnricher:
    """Service for enriching seed data with production patterns."""

    # Fuzzy match threshold for entity matching
    FUZZY_THRESHOLD = 0.85

    def __init__(self, fuzzy_threshold: float = FUZZY_THRESHOLD):
        """Initialize the enricher.

        Args:
            fuzzy_threshold: Threshold for fuzzy string matching (0-1)
        """
        self.fuzzy_threshold = fuzzy_threshold

    def enrich_actions(
        self,
        seed_actions: list[dict],
        prod_patterns: FrequencyStats,
    ) -> list[dict]:
        """Add frequency counts and co-occurrence data to seed actions.

        Args:
            seed_actions: List of action dicts from seed data
            prod_patterns: Frequency stats from production data

        Returns:
            List of enriched action dicts
        """
        enriched = []

        for action in seed_actions:
            enriched_action = action.copy()
            action_name = action.get("name", "")

            # Find matching production action (exact or fuzzy)
            prod_name = self._find_matching_name(
                action_name, prod_patterns.action_frequencies.keys()
            )

            if prod_name:
                # Add frequency
                enriched_action["production_frequency"] = prod_patterns.action_frequencies[
                    prod_name
                ]
                enriched_action["production_workflows"] = prod_patterns.total_workflows

                # Add top co-occurring widgets
                cooccurrences = []
                for (a, w), count in prod_patterns.action_widget_pairs.items():
                    if a == prod_name or self._fuzzy_match(a, action_name):
                        total = prod_patterns.action_frequencies.get(a, 1)
                        confidence = count / total if total > 0 else 0
                        cooccurrences.append(
                            {"widget": w, "count": count, "confidence": round(confidence, 3)}
                        )

                # Sort by confidence and take top 5
                cooccurrences.sort(key=lambda x: -x["confidence"])
                enriched_action["production_cooccurrences"] = cooccurrences[:5]

                # Add commonly paired actions
                paired_actions = []
                for pair, count in prod_patterns.action_action_pairs.items():
                    if prod_name in pair:
                        other = pair[0] if pair[1] == prod_name else pair[1]
                        paired_actions.append({"action": other, "count": count})

                paired_actions.sort(key=lambda x: -x["count"])
                enriched_action["commonly_paired_actions"] = paired_actions[:5]
            else:
                # No production match found
                enriched_action["production_frequency"] = 0
                enriched_action["production_workflows"] = prod_patterns.total_workflows
                enriched_action["production_cooccurrences"] = []
                enriched_action["commonly_paired_actions"] = []

            enriched.append(enriched_action)

        logger.info(f"Enriched {len(enriched)} actions with production data")
        return enriched

    def enrich_widgets(
        self,
        seed_widgets: list[dict],
        prod_patterns: FrequencyStats,
    ) -> list[dict]:
        """Add usage statistics to seed widgets.

        Args:
            seed_widgets: List of widget dicts from seed data
            prod_patterns: Frequency stats from production data

        Returns:
            List of enriched widget dicts
        """
        enriched = []

        for widget in seed_widgets:
            enriched_widget = widget.copy()
            widget_name = widget.get("name", "")

            # Find matching production widget
            prod_name = self._find_matching_name(
                widget_name, prod_patterns.widget_frequencies.keys()
            )

            if prod_name:
                freq = prod_patterns.widget_frequencies[prod_name]
                total = prod_patterns.total_workflows

                enriched_widget["production_frequency"] = freq
                enriched_widget["production_workflows"] = total
                enriched_widget["usage_percentage"] = (
                    round((freq / total) * 100, 1) if total > 0 else 0
                )

                # Add top co-occurring actions
                cooccurrences = []
                for (a, w), count in prod_patterns.action_widget_pairs.items():
                    if w == prod_name or self._fuzzy_match(w, widget_name):
                        total_widget = prod_patterns.widget_frequencies.get(w, 1)
                        confidence = count / total_widget if total_widget > 0 else 0
                        cooccurrences.append(
                            {"action": a, "count": count, "confidence": round(confidence, 3)}
                        )

                cooccurrences.sort(key=lambda x: -x["confidence"])
                enriched_widget["production_cooccurrences"] = cooccurrences[:5]
            else:
                enriched_widget["production_frequency"] = 0
                enriched_widget["production_workflows"] = prod_patterns.total_workflows
                enriched_widget["usage_percentage"] = 0
                enriched_widget["production_cooccurrences"] = []

            enriched.append(enriched_widget)

        logger.info(f"Enriched {len(enriched)} widgets with production data")
        return enriched

    def enrich_status_patterns(
        self,
        seed_patterns: list[dict],
        prod_flows: list[StatusFlow],
    ) -> list[dict]:
        """Add real-world flow examples to seed patterns.

        Args:
            seed_patterns: List of status pattern dicts from seed data
            prod_flows: Status flows from production data

        Returns:
            List of enriched pattern dicts
        """
        enriched = []

        for pattern in seed_patterns:
            enriched_pattern = pattern.copy()
            typical_names = pattern.get("typical_status_names", [])

            # Find matching flows
            matching_flows = []
            total_count = 0

            for flow in prod_flows:
                # Check if any typical name appears in the flow
                matches = False
                for typical in typical_names:
                    for status in flow.sequence:
                        if self._fuzzy_match(typical, status):
                            matches = True
                            break
                    if matches:
                        break

                if matches:
                    matching_flows.append(
                        {
                            "sequence": flow.sequence,
                            "count": flow.count,
                            "flow_names": flow.flow_names[:3],  # Limit examples
                        }
                    )
                    total_count += flow.count

            # Sort by count and take top examples
            matching_flows.sort(key=lambda x: -x["count"])
            enriched_pattern["real_world_examples"] = matching_flows[:5]
            enriched_pattern["production_frequency"] = total_count
            enriched_pattern["matching_workflow_count"] = len(matching_flows)

            enriched.append(enriched_pattern)

        logger.info(f"Enriched {len(enriched)} status patterns with flow data")
        return enriched

    def discover_new_entities(
        self,
        prod_data: list[ParsedWorkflow],
        seed_data: dict,
    ) -> dict:
        """Find actions/widgets/statuses in production that aren't in seed.

        Args:
            prod_data: List of parsed production workflows
            seed_data: Dict with 'actions', 'widgets', 'status_patterns' lists

        Returns:
            Dict with new_actions, new_widgets, new_statuses lists
        """
        # Build sets of known entities
        known_actions = {
            a.get("name", "").lower() for a in seed_data.get("actions", [])
        }
        known_widgets = {
            w.get("name", "").lower() for w in seed_data.get("widgets", [])
        }

        # Track discovered entities
        discovered_actions: dict[str, dict] = {}
        discovered_widgets: dict[str, dict] = {}
        discovered_statuses: dict[str, dict] = {}

        for workflow in prod_data:
            # Check action buttons
            for button in workflow.action_buttons:
                action_name = button.action_type
                if not self._is_known_entity(action_name, known_actions):
                    key = action_name.lower()
                    if key not in discovered_actions:
                        discovered_actions[key] = {
                            "id": f"action:{key.replace(' ', '_')}",
                            "name": action_name,
                            "description": f"Discovered from production data: {button.label}",
                            "requires_template": False,
                            "template_type": None,
                            "use_cases": [],
                            "common_phrases": [button.label],
                            "needs_review": True,
                            "source_workflows": [workflow.source_file],
                            "occurrence_count": 1,
                        }
                    else:
                        discovered_actions[key]["occurrence_count"] += 1
                        if workflow.source_file not in discovered_actions[key]["source_workflows"]:
                            discovered_actions[key]["source_workflows"].append(
                                workflow.source_file
                            )
                        if button.label not in discovered_actions[key]["common_phrases"]:
                            discovered_actions[key]["common_phrases"].append(button.label)

            # Check focus view widgets
            for fv in workflow.focus_views:
                for widget_name in fv.widgets:
                    if not self._is_known_entity(widget_name, known_widgets):
                        key = widget_name.lower()
                        if key not in discovered_widgets:
                            discovered_widgets[key] = {
                                "id": f"widget:{key.replace(' ', '_').replace('/', '_')}",
                                "name": widget_name,
                                "description": f"Discovered from production data",
                                "category": "unknown",
                                "typical_position": "middle",
                                "recommended_always": False,
                                "use_cases": [],
                                "needs_review": True,
                                "source_workflows": [workflow.source_file],
                                "occurrence_count": 1,
                            }
                        else:
                            discovered_widgets[key]["occurrence_count"] += 1
                            if (
                                workflow.source_file
                                not in discovered_widgets[key]["source_workflows"]
                            ):
                                discovered_widgets[key]["source_workflows"].append(
                                    workflow.source_file
                                )

            # Check statuses
            for status in workflow.statuses:
                status_name = status.name
                key = status_name.lower()
                if key not in discovered_statuses:
                    discovered_statuses[key] = {
                        "name": status_name,
                        "category": status.category.value,
                        "sequence": status.sequence,
                        "source_workflows": [workflow.source_file],
                        "occurrence_count": 1,
                    }
                else:
                    discovered_statuses[key]["occurrence_count"] += 1
                    if (
                        workflow.source_file
                        not in discovered_statuses[key]["source_workflows"]
                    ):
                        discovered_statuses[key]["source_workflows"].append(
                            workflow.source_file
                        )

        result = {
            "new_actions": list(discovered_actions.values()),
            "new_widgets": list(discovered_widgets.values()),
            "new_statuses": list(discovered_statuses.values()),
        }

        logger.info(
            f"Discovered {len(result['new_actions'])} new actions, "
            f"{len(result['new_widgets'])} new widgets, "
            f"{len(result['new_statuses'])} statuses"
        )

        return result

    def merge_discovered_entities(
        self,
        seed_data: dict,
        discovered: dict,
        auto_add_threshold: int = 3,
    ) -> dict:
        """Merge high-confidence discovered entities into seed data.

        Args:
            seed_data: Original seed data dict
            discovered: Dict from discover_new_entities
            auto_add_threshold: Minimum occurrences to auto-add (others flagged for review)

        Returns:
            Updated seed data dict
        """
        merged = {
            "actions": list(seed_data.get("actions", [])),
            "widgets": list(seed_data.get("widgets", [])),
            "status_patterns": list(seed_data.get("status_patterns", [])),
        }

        # Add discovered actions with enough occurrences
        for action in discovered.get("new_actions", []):
            if action["occurrence_count"] >= auto_add_threshold:
                action["auto_added"] = True
                action["needs_review"] = True  # Still flag for review
                merged["actions"].append(action)
                logger.info(
                    f"Auto-added action '{action['name']}' "
                    f"(seen {action['occurrence_count']} times)"
                )

        # Add discovered widgets with enough occurrences
        for widget in discovered.get("new_widgets", []):
            if widget["occurrence_count"] >= auto_add_threshold:
                widget["auto_added"] = True
                widget["needs_review"] = True
                merged["widgets"].append(widget)
                logger.info(
                    f"Auto-added widget '{widget['name']}' "
                    f"(seen {widget['occurrence_count']} times)"
                )

        return merged

    def enrich_phrases_from_production(
        self,
        seed_actions: list[dict],
        prod_data: list[ParsedWorkflow],
    ) -> list[dict]:
        """Merge production button labels into action common_phrases.

        Args:
            seed_actions: List of action dicts
            prod_data: Parsed production workflows

        Returns:
            Actions with enriched common_phrases
        """
        # Build map of action name to button labels
        label_map: dict[str, set[str]] = {}

        for workflow in prod_data:
            for button in workflow.action_buttons:
                action_lower = button.action_type.lower()
                if action_lower not in label_map:
                    label_map[action_lower] = set()
                label_map[action_lower].add(button.label)

        # Enrich actions
        enriched = []
        for action in seed_actions:
            enriched_action = action.copy()
            action_name = action.get("name", "").lower()

            # Find matching labels
            matching_labels = set()
            for prod_name, labels in label_map.items():
                if self._fuzzy_match(action_name, prod_name):
                    matching_labels.update(labels)

            if matching_labels:
                # Merge with existing phrases
                existing = set(action.get("common_phrases", []))
                merged = existing.union(matching_labels)
                enriched_action["common_phrases"] = list(merged)
                enriched_action["phrases_from_production"] = list(
                    matching_labels - existing
                )

            enriched.append(enriched_action)

        logger.info(f"Enriched phrases for {len(enriched)} actions")
        return enriched

    def _find_matching_name(
        self,
        name: str,
        candidates: list[str],
    ) -> Optional[str]:
        """Find a matching name from candidates using exact or fuzzy match.

        Args:
            name: Name to match
            candidates: List of candidate names

        Returns:
            Matching name or None
        """
        name_lower = name.lower()

        # Try exact match first
        for candidate in candidates:
            if candidate.lower() == name_lower:
                return candidate

        # Try fuzzy match
        best_match = None
        best_score = 0

        for candidate in candidates:
            score = SequenceMatcher(None, name_lower, candidate.lower()).ratio()
            if score > best_score and score >= self.fuzzy_threshold:
                best_match = candidate
                best_score = score

        return best_match

    def _is_known_entity(self, name: str, known_set: set[str]) -> bool:
        """Check if entity name is known (exact or fuzzy).

        Args:
            name: Entity name
            known_set: Set of known names (lowercase)

        Returns:
            True if known
        """
        name_lower = name.lower()

        # Exact match
        if name_lower in known_set:
            return True

        # Fuzzy match
        for known in known_set:
            if self._fuzzy_match(name_lower, known):
                return True

        return False

    def _fuzzy_match(self, s1: str, s2: str) -> bool:
        """Check if two strings are a fuzzy match.

        Args:
            s1: First string
            s2: Second string

        Returns:
            True if fuzzy match
        """
        score = SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
        return score >= self.fuzzy_threshold
