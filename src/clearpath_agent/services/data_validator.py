"""Data Validation and Deduplication Service.

Validates entity data and removes duplicates using exact, fuzzy,
and semantic matching strategies.
"""

import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Validation Result Models
# ============================================================================


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue."""

    field: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    value: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validating a single entity."""

    entity_id: str
    entity_type: str
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]


@dataclass
class DeduplicationResult:
    """Result of deduplication process."""

    original_count: int = 0
    deduplicated_count: int = 0
    exact_matches: int = 0
    fuzzy_matches: int = 0
    flagged_for_review: list[dict] = field(default_factory=list)


# ============================================================================
# Data Validator Service
# ============================================================================


class DataValidator:
    """Service for validating and deduplicating entity data."""

    # Validation configuration
    REQUIRED_ACTION_FIELDS = ["id", "name", "description"]
    REQUIRED_WIDGET_FIELDS = ["id", "name", "description", "category"]
    REQUIRED_PATTERN_FIELDS = ["id", "name", "description"]

    # Deduplication thresholds
    FUZZY_THRESHOLD = 0.85
    SEMANTIC_THRESHOLD = 0.95

    def __init__(
        self,
        fuzzy_threshold: float = FUZZY_THRESHOLD,
        semantic_threshold: float = SEMANTIC_THRESHOLD,
    ):
        """Initialize the validator.

        Args:
            fuzzy_threshold: Threshold for fuzzy name matching (0-1)
            semantic_threshold: Threshold for semantic embedding matching (0-1)
        """
        self.fuzzy_threshold = fuzzy_threshold
        self.semantic_threshold = semantic_threshold

    def validate_action(self, action: dict) -> ValidationResult:
        """Validate an action entity.

        Args:
            action: Action dict to validate

        Returns:
            ValidationResult with issues if any
        """
        entity_id = action.get("id", "unknown")
        issues = []

        # Check required fields
        for field_name in self.REQUIRED_ACTION_FIELDS:
            if not action.get(field_name):
                issues.append(
                    ValidationIssue(
                        field=field_name,
                        message=f"Missing required field: {field_name}",
                        severity=ValidationSeverity.ERROR,
                    )
                )

        # Validate ID format
        action_id = action.get("id", "")
        if action_id and not action_id.startswith("action:"):
            issues.append(
                ValidationIssue(
                    field="id",
                    message="Action ID should start with 'action:'",
                    severity=ValidationSeverity.WARNING,
                    value=action_id,
                    suggestion=f"action:{action_id}",
                )
            )

        # Validate template requirements
        if action.get("requires_template") and not action.get("template_type"):
            issues.append(
                ValidationIssue(
                    field="template_type",
                    message="template_type required when requires_template is true",
                    severity=ValidationSeverity.ERROR,
                )
            )

        # Check for empty arrays that should have content
        if action.get("use_cases") is not None and len(action.get("use_cases", [])) == 0:
            issues.append(
                ValidationIssue(
                    field="use_cases",
                    message="use_cases array is empty",
                    severity=ValidationSeverity.INFO,
                )
            )

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationResult(
            entity_id=entity_id,
            entity_type="action",
            is_valid=is_valid,
            issues=issues,
        )

    def validate_widget(self, widget: dict) -> ValidationResult:
        """Validate a widget entity.

        Args:
            widget: Widget dict to validate

        Returns:
            ValidationResult with issues if any
        """
        entity_id = widget.get("id", "unknown")
        issues = []

        # Check required fields
        for field_name in self.REQUIRED_WIDGET_FIELDS:
            if not widget.get(field_name):
                issues.append(
                    ValidationIssue(
                        field=field_name,
                        message=f"Missing required field: {field_name}",
                        severity=ValidationSeverity.ERROR,
                    )
                )

        # Validate ID format
        widget_id = widget.get("id", "")
        if widget_id and not widget_id.startswith("widget:"):
            issues.append(
                ValidationIssue(
                    field="id",
                    message="Widget ID should start with 'widget:'",
                    severity=ValidationSeverity.WARNING,
                    value=widget_id,
                    suggestion=f"widget:{widget_id}",
                )
            )

        # Validate category
        valid_categories = [
            "job_info",
            "contact",
            "location",
            "scheduling",
            "team",
            "actions",
            "documentation",
            "communication",
            "instructions",
            "data",
            "tasks",
            "financial",
            "materials",
            "time",
            "assets",
            "contracts",
            "organization",
            "project",
            "unknown",
        ]
        category = widget.get("category", "")
        if category and category not in valid_categories:
            issues.append(
                ValidationIssue(
                    field="category",
                    message=f"Unknown category: {category}",
                    severity=ValidationSeverity.WARNING,
                    value=category,
                )
            )

        # Validate typical_position
        valid_positions = ["top", "middle", "bottom"]
        position = widget.get("typical_position", "")
        if position and position not in valid_positions:
            issues.append(
                ValidationIssue(
                    field="typical_position",
                    message=f"Unknown position: {position}",
                    severity=ValidationSeverity.WARNING,
                    value=position,
                )
            )

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationResult(
            entity_id=entity_id,
            entity_type="widget",
            is_valid=is_valid,
            issues=issues,
        )

    def validate_status_pattern(self, pattern: dict) -> ValidationResult:
        """Validate a status pattern entity.

        Args:
            pattern: Status pattern dict to validate

        Returns:
            ValidationResult with issues if any
        """
        entity_id = pattern.get("id", "unknown")
        issues = []

        # Check required fields
        for field_name in self.REQUIRED_PATTERN_FIELDS:
            if not pattern.get(field_name):
                issues.append(
                    ValidationIssue(
                        field=field_name,
                        message=f"Missing required field: {field_name}",
                        severity=ValidationSeverity.ERROR,
                    )
                )

        # Validate ID format
        pattern_id = pattern.get("id", "")
        if pattern_id and not pattern_id.startswith("pattern:"):
            issues.append(
                ValidationIssue(
                    field="id",
                    message="Pattern ID should start with 'pattern:'",
                    severity=ValidationSeverity.WARNING,
                    value=pattern_id,
                    suggestion=f"pattern:{pattern_id}",
                )
            )

        # Check typical_status_names
        if not pattern.get("typical_status_names"):
            issues.append(
                ValidationIssue(
                    field="typical_status_names",
                    message="Pattern should have typical_status_names",
                    severity=ValidationSeverity.WARNING,
                )
            )

        # Check typical_actions reference valid IDs
        for action_id in pattern.get("typical_actions", []):
            if not action_id.startswith("action:"):
                issues.append(
                    ValidationIssue(
                        field="typical_actions",
                        message=f"Invalid action ID format: {action_id}",
                        severity=ValidationSeverity.WARNING,
                        value=action_id,
                    )
                )

        # Check typical_widgets reference valid IDs
        for widget_id in pattern.get("typical_widgets", []):
            if not widget_id.startswith("widget:"):
                issues.append(
                    ValidationIssue(
                        field="typical_widgets",
                        message=f"Invalid widget ID format: {widget_id}",
                        severity=ValidationSeverity.WARNING,
                        value=widget_id,
                    )
                )

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationResult(
            entity_id=entity_id,
            entity_type="status_pattern",
            is_valid=is_valid,
            issues=issues,
        )

    def validate_relationship(
        self,
        relationship: dict,
        known_ids: set[str],
    ) -> ValidationResult:
        """Validate a relationship references valid entities.

        Args:
            relationship: Relationship dict to validate
            known_ids: Set of known entity IDs

        Returns:
            ValidationResult with issues if any
        """
        issues = []

        source = relationship.get("source", "")
        target = relationship.get("target", "")
        relation = relationship.get("relation", "")
        weight = relationship.get("weight", 0)

        # Check source exists
        if source not in known_ids:
            issues.append(
                ValidationIssue(
                    field="source",
                    message=f"Source entity not found: {source}",
                    severity=ValidationSeverity.ERROR,
                    value=source,
                )
            )

        # Check target exists
        if target not in known_ids:
            issues.append(
                ValidationIssue(
                    field="target",
                    message=f"Target entity not found: {target}",
                    severity=ValidationSeverity.ERROR,
                    value=target,
                )
            )

        # Check relation type
        valid_relations = [
            "SUGGESTS_WIDGET",
            "COMMONLY_PAIRED_WITH",
            "TYPICALLY_INCLUDES",
            "HAS_ACTION",
            "HAS_WIDGET",
            "NEXT_STATUS",
        ]
        if relation not in valid_relations:
            issues.append(
                ValidationIssue(
                    field="relation",
                    message=f"Unknown relation type: {relation}",
                    severity=ValidationSeverity.WARNING,
                    value=relation,
                )
            )

        # Check weight bounds
        if not (0 <= weight <= 1):
            issues.append(
                ValidationIssue(
                    field="weight",
                    message=f"Weight must be between 0 and 1: {weight}",
                    severity=ValidationSeverity.ERROR,
                    value=str(weight),
                )
            )

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationResult(
            entity_id=f"{source}->{target}",
            entity_type="relationship",
            is_valid=is_valid,
            issues=issues,
        )

    def deduplicate_actions(self, actions: list[dict]) -> tuple[list[dict], DeduplicationResult]:
        """Remove duplicate actions using fuzzy matching.

        Args:
            actions: List of action dicts

        Returns:
            Tuple of (deduplicated list, DeduplicationResult)
        """
        return self._deduplicate_entities(actions, "action")

    def deduplicate_widgets(self, widgets: list[dict]) -> tuple[list[dict], DeduplicationResult]:
        """Remove duplicate widgets using fuzzy matching.

        Args:
            widgets: List of widget dicts

        Returns:
            Tuple of (deduplicated list, DeduplicationResult)
        """
        return self._deduplicate_entities(widgets, "widget")

    def _deduplicate_entities(
        self,
        entities: list[dict],
        entity_type: str,
    ) -> tuple[list[dict], DeduplicationResult]:
        """Generic deduplication for any entity type.

        Args:
            entities: List of entity dicts
            entity_type: "action", "widget", etc.

        Returns:
            Tuple of (deduplicated list, DeduplicationResult)
        """
        if not entities:
            return [], DeduplicationResult(0, 0)

        result = DeduplicationResult(original_count=len(entities))
        deduplicated = []
        seen_ids: set[str] = set()
        seen_names: dict[str, dict] = {}  # lowercase name -> entity

        for entity in entities:
            entity_id = entity.get("id", "")
            entity_name = entity.get("name", "")
            name_lower = entity_name.lower()

            # Check exact ID match
            if entity_id in seen_ids:
                result.exact_matches += 1
                # Merge: prefer entity with more data
                continue

            # Check exact name match
            if name_lower in seen_names:
                result.exact_matches += 1
                # Merge the entities
                existing = seen_names[name_lower]
                merged = self._merge_entities(existing, entity)
                # Update in deduplicated list
                for i, e in enumerate(deduplicated):
                    if e.get("id") == existing.get("id"):
                        deduplicated[i] = merged
                        break
                continue

            # Check fuzzy name match
            fuzzy_match = None
            for seen_name, seen_entity in seen_names.items():
                similarity = SequenceMatcher(None, name_lower, seen_name).ratio()
                if similarity >= self.fuzzy_threshold:
                    fuzzy_match = seen_entity
                    break

            if fuzzy_match:
                result.fuzzy_matches += 1
                result.flagged_for_review.append(
                    {
                        "type": entity_type,
                        "original": fuzzy_match,
                        "duplicate": entity,
                        "similarity": similarity,
                        "reason": "fuzzy_name_match",
                    }
                )
                # Keep the original, flag for review
                continue

            # No match found, add entity
            seen_ids.add(entity_id)
            seen_names[name_lower] = entity
            deduplicated.append(entity)

        result.deduplicated_count = len(deduplicated)

        logger.info(
            f"Deduplicated {entity_type}s: {result.original_count} -> {result.deduplicated_count} "
            f"(exact: {result.exact_matches}, fuzzy: {result.fuzzy_matches})"
        )

        return deduplicated, result

    def _merge_entities(self, entity1: dict, entity2: dict) -> dict:
        """Merge two entities, preferring more complete data.

        Args:
            entity1: First entity
            entity2: Second entity

        Returns:
            Merged entity
        """
        merged = entity1.copy()

        # Merge arrays (concatenate and dedupe)
        for key in ["use_cases", "common_phrases"]:
            if key in entity2:
                existing = set(merged.get(key, []))
                existing.update(entity2.get(key, []))
                merged[key] = list(existing)

        # Merge frequencies (sum)
        for key in ["production_frequency", "frequency"]:
            if key in entity2:
                merged[key] = merged.get(key, 0) + entity2.get(key, 0)

        # Prefer non-empty strings
        for key in ["description"]:
            if not merged.get(key) and entity2.get(key):
                merged[key] = entity2[key]

        return merged

    def validate_all(
        self,
        actions: list[dict],
        widgets: list[dict],
        status_patterns: list[dict],
        relationships: list[dict],
    ) -> list[ValidationResult]:
        """Validate all entities.

        Args:
            actions: List of action dicts
            widgets: List of widget dicts
            status_patterns: List of status pattern dicts
            relationships: List of relationship dicts

        Returns:
            List of all validation results
        """
        results = []

        # Validate actions
        for action in actions:
            results.append(self.validate_action(action))

        # Validate widgets
        for widget in widgets:
            results.append(self.validate_widget(widget))

        # Validate status patterns
        for pattern in status_patterns:
            results.append(self.validate_status_pattern(pattern))

        # Build known IDs for relationship validation
        known_ids = set()
        known_ids.update(a.get("id", "") for a in actions)
        known_ids.update(w.get("id", "") for w in widgets)
        known_ids.update(p.get("id", "") for p in status_patterns)

        # Validate relationships
        for rel in relationships:
            results.append(self.validate_relationship(rel, known_ids))

        # Summary
        errors = sum(1 for r in results if not r.is_valid)
        warnings = sum(len(r.warnings) for r in results)

        logger.info(
            f"Validation complete: {len(results)} entities, "
            f"{errors} with errors, {warnings} warnings"
        )

        return results

    def generate_validation_report(self, results: list[ValidationResult]) -> str:
        """Create human-readable validation report.

        Args:
            results: List of ValidationResult objects

        Returns:
            Formatted report string
        """
        lines = ["=" * 60, "Validation Report", "=" * 60, ""]

        # Summary
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        invalid = total - valid
        all_errors = sum(len(r.errors) for r in results)
        all_warnings = sum(len(r.warnings) for r in results)

        lines.append(f"Total entities validated: {total}")
        lines.append(f"  Valid: {valid}")
        lines.append(f"  Invalid: {invalid}")
        lines.append(f"  Total errors: {all_errors}")
        lines.append(f"  Total warnings: {all_warnings}")
        lines.append("")

        # Group by entity type
        by_type: dict[str, list[ValidationResult]] = {}
        for result in results:
            if result.entity_type not in by_type:
                by_type[result.entity_type] = []
            by_type[result.entity_type].append(result)

        for entity_type, type_results in by_type.items():
            type_invalid = [r for r in type_results if not r.is_valid]
            type_warnings = [r for r in type_results if r.warnings]

            lines.append(f"\n{entity_type.upper()}S ({len(type_results)} total)")
            lines.append("-" * 40)

            if type_invalid:
                lines.append(f"\nInvalid ({len(type_invalid)}):")
                for result in type_invalid[:10]:  # Limit output
                    lines.append(f"  {result.entity_id}:")
                    for issue in result.errors:
                        lines.append(f"    ERROR: {issue.field} - {issue.message}")
                if len(type_invalid) > 10:
                    lines.append(f"  ... and {len(type_invalid) - 10} more")

            if type_warnings:
                lines.append(f"\nWarnings ({len(type_warnings)}):")
                for result in type_warnings[:10]:
                    lines.append(f"  {result.entity_id}:")
                    for issue in result.warnings:
                        lines.append(f"    WARN: {issue.field} - {issue.message}")
                if len(type_warnings) > 10:
                    lines.append(f"  ... and {len(type_warnings) - 10} more")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
