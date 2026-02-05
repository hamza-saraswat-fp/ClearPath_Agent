"""Entity Resolver Service.

Maps extracted phrases from user input to canonical ClearPath
action and widget types using fuzzy matching and vector similarity.
"""

import logging
from difflib import SequenceMatcher
from typing import Optional

from ..models.enums import ActionButtonType, WidgetType
from ..models.intent_schemas import (
    ConfidenceLevel,
    ExtractedPhrase,
    ResolvedEntity,
    ResolutionResult,
)

logger = logging.getLogger(__name__)


# Phrase to ActionButtonType mappings
# Maps common phrases/variations to canonical action types
ACTION_PHRASE_MAPPINGS: dict[str, ActionButtonType] = {
    # Clock in/out variations
    "clock in": ActionButtonType.CLOCK_IN_OUT,
    "clock out": ActionButtonType.CLOCK_IN_OUT,
    "punch in": ActionButtonType.CLOCK_IN_OUT,
    "punch out": ActionButtonType.CLOCK_IN_OUT,
    "start time": ActionButtonType.CLOCK_IN_OUT,
    "stop time": ActionButtonType.CLOCK_IN_OUT,
    "time tracking": ActionButtonType.CLOCK_IN_OUT,
    "track time": ActionButtonType.CLOCK_IN_OUT,
    "log time": ActionButtonType.CLOCK_IN_OUT,
    # Communication variations
    "send text": ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
    "send sms": ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
    "send message": ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
    "text customer": ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
    "notify customer": ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
    "customer communication": ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
    "send email": ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
    "email customer": ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
    "on my way text": ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
    "arrival text": ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
    "eta text": ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
    # Form variations
    "fill form": ActionButtonType.FILL_FORM,
    "complete form": ActionButtonType.FILL_FORM,
    "checklist": ActionButtonType.FILL_FORM,
    "inspection form": ActionButtonType.FILL_FORM,
    "safety form": ActionButtonType.FILL_FORM,
    "complete checklist": ActionButtonType.FILL_FORM,
    "fill out form": ActionButtonType.FILL_FORM,
    "paperwork": ActionButtonType.FILL_FORM,
    # Photo variations
    "take photo": ActionButtonType.TAKE_PHOTO,
    "take picture": ActionButtonType.TAKE_PHOTO,
    "snap photo": ActionButtonType.TAKE_PHOTO,
    "before photo": ActionButtonType.TAKE_PHOTO,
    "after photo": ActionButtonType.TAKE_PHOTO,
    "document with photo": ActionButtonType.TAKE_PHOTO,
    "capture photo": ActionButtonType.TAKE_PHOTO,
    # Signature variations
    "collect signature": ActionButtonType.COLLECT_SIGNATURE,
    "get signature": ActionButtonType.COLLECT_SIGNATURE,
    "customer signature": ActionButtonType.COLLECT_SIGNATURE,
    "sign off": ActionButtonType.COLLECT_SIGNATURE,
    "approval signature": ActionButtonType.COLLECT_SIGNATURE,
    # Payment variations
    "collect payment": ActionButtonType.COLLECT_PAYMENT,
    "take payment": ActionButtonType.COLLECT_PAYMENT,
    "process payment": ActionButtonType.COLLECT_PAYMENT,
    "accept payment": ActionButtonType.COLLECT_PAYMENT,
    "receive payment": ActionButtonType.COLLECT_PAYMENT,
    # Estimate variations
    "create estimate": ActionButtonType.CREATE_ESTIMATE,
    "make estimate": ActionButtonType.CREATE_ESTIMATE,
    "new estimate": ActionButtonType.CREATE_ESTIMATE,
    "create quote": ActionButtonType.CREATE_ESTIMATE,
    "make quote": ActionButtonType.CREATE_ESTIMATE,
    "send estimate": ActionButtonType.SEND_ESTIMATE,
    "email estimate": ActionButtonType.SEND_ESTIMATE,
    "view estimate": ActionButtonType.VIEW_ESTIMATE,
    "review estimate": ActionButtonType.VIEW_ESTIMATE,
    # Invoice variations
    "create invoice": ActionButtonType.CREATE_INVOICE,
    "make invoice": ActionButtonType.CREATE_INVOICE,
    "new invoice": ActionButtonType.CREATE_INVOICE,
    "generate invoice": ActionButtonType.CREATE_INVOICE,
    "send invoice": ActionButtonType.SEND_INVOICE,
    "email invoice": ActionButtonType.SEND_INVOICE,
    "view invoice": ActionButtonType.VIEW_INVOICE,
    "review invoice": ActionButtonType.VIEW_INVOICE,
    # Line item/material variations
    "add line item": ActionButtonType.ADD_LINE_ITEM,
    "add item": ActionButtonType.ADD_LINE_ITEM,
    "add material": ActionButtonType.ADD_MATERIAL,
    "add parts": ActionButtonType.ADD_MATERIAL,
    "record materials": ActionButtonType.ADD_MATERIAL,
    "add labor": ActionButtonType.ADD_LABOR,
    "record labor": ActionButtonType.ADD_LABOR,
    "log labor": ActionButtonType.ADD_LABOR,
    "add expense": ActionButtonType.ADD_EXPENSE,
    "record expense": ActionButtonType.ADD_EXPENSE,
    "add receipt": ActionButtonType.ADD_EXPENSE,
    "enter receipt": ActionButtonType.ADD_EXPENSE,
    # Note variations
    "add note": ActionButtonType.ADD_NOTE,
    "add comment": ActionButtonType.ADD_NOTE,
    "leave note": ActionButtonType.ADD_NOTE,
    "write note": ActionButtonType.ADD_NOTE,
    "job note": ActionButtonType.ADD_NOTE,
    # Attachment variations
    "add attachment": ActionButtonType.ADD_ATTACHMENT,
    "attach file": ActionButtonType.ADD_ATTACHMENT,
    "upload file": ActionButtonType.ADD_ATTACHMENT,
    "add document": ActionButtonType.ADD_ATTACHMENT,
    # History variations
    "view customer history": ActionButtonType.VIEW_CUSTOMER_HISTORY,
    "customer history": ActionButtonType.VIEW_CUSTOMER_HISTORY,
    "view asset history": ActionButtonType.VIEW_ASSET_HISTORY,
    "asset history": ActionButtonType.VIEW_ASSET_HISTORY,
    "equipment history": ActionButtonType.VIEW_ASSET_HISTORY,
    "view job history": ActionButtonType.VIEW_JOB_HISTORY,
    "job history": ActionButtonType.VIEW_JOB_HISTORY,
    # Asset variations
    "update asset": ActionButtonType.UPDATE_ASSET,
    "edit asset": ActionButtonType.UPDATE_ASSET,
    "modify asset": ActionButtonType.UPDATE_ASSET,
    "create asset": ActionButtonType.CREATE_ASSET,
    "add asset": ActionButtonType.CREATE_ASSET,
    "new asset": ActionButtonType.CREATE_ASSET,
    "add equipment": ActionButtonType.CREATE_ASSET,
    # Other actions
    "schedule follow up": ActionButtonType.SCHEDULE_FOLLOW_UP,
    "schedule appointment": ActionButtonType.SCHEDULE_FOLLOW_UP,
    "book follow up": ActionButtonType.SCHEDULE_FOLLOW_UP,
    "request review": ActionButtonType.REQUEST_REVIEW,
    "submit for review": ActionButtonType.REQUEST_REVIEW,
    "mark complete": ActionButtonType.MARK_COMPLETE,
    "complete task": ActionButtonType.MARK_COMPLETE,
    "finish": ActionButtonType.MARK_COMPLETE,
}

# Phrase to WidgetType mappings
WIDGET_PHRASE_MAPPINGS: dict[str, WidgetType] = {
    # Job info variations
    "job title": WidgetType.JOB_TITLE,
    "job name": WidgetType.JOB_TITLE,
    "job status": WidgetType.JOB_STATUS,
    "status": WidgetType.JOB_STATUS,
    "current status": WidgetType.JOB_STATUS,
    "instructions": WidgetType.STATUS_INSTRUCTIONS,
    "status instructions": WidgetType.STATUS_INSTRUCTIONS,
    "job details": WidgetType.JOB_DETAILS,
    "job description": WidgetType.JOB_DESCRIPTION,
    "description": WidgetType.JOB_DESCRIPTION,
    "job notes": WidgetType.JOB_NOTES,
    "notes": WidgetType.JOB_NOTES,
    "job tags": WidgetType.JOB_TAGS,
    "tags": WidgetType.JOB_TAGS,
    "custom fields": WidgetType.JOB_CUSTOM_FIELDS,
    "job custom fields": WidgetType.JOB_CUSTOM_FIELDS,
    # Customer variations
    "customer contact": WidgetType.CUSTOMER_CONTACT,
    "customer info": WidgetType.CUSTOMER_CONTACT,
    "contact info": WidgetType.CUSTOMER_CONTACT,
    "customer phone": WidgetType.CUSTOMER_CONTACT,
    "customer email": WidgetType.CUSTOMER_CONTACT,
    "customer address": WidgetType.CUSTOMER_ADDRESS,
    "address": WidgetType.CUSTOMER_ADDRESS,
    "location": WidgetType.CUSTOMER_ADDRESS,
    "job address": WidgetType.CUSTOMER_ADDRESS,
    "customer notes": WidgetType.CUSTOMER_NOTES,
    # Team/scheduling variations
    "assigned team": WidgetType.ASSIGNED_TEAM,
    "team members": WidgetType.ASSIGNED_TEAM,
    "technicians": WidgetType.ASSIGNED_TEAM,
    "scheduled time": WidgetType.SCHEDULED_TIME,
    "appointment time": WidgetType.SCHEDULED_TIME,
    "schedule": WidgetType.SCHEDULED_TIME,
    # Action buttons
    "action buttons": WidgetType.ACTION_BUTTONS,
    "buttons": WidgetType.ACTION_BUTTONS,
    "actions": WidgetType.ACTION_BUTTONS,
    # Forms/files
    "forms": WidgetType.FORMS,
    "form list": WidgetType.FORMS,
    "completed forms": WidgetType.FORMS,
    "files": WidgetType.FILES_PHOTOS,
    "photos": WidgetType.FILES_PHOTOS,
    "files and photos": WidgetType.FILES_PHOTOS,
    "attachments": WidgetType.FILES_PHOTOS,
    "pictures": WidgetType.FILES_PHOTOS,
    "signatures": WidgetType.SIGNATURES,
    "signature list": WidgetType.SIGNATURES,
    "checklist": WidgetType.CHECKLIST,
    "task list": WidgetType.CHECKLIST,
    # Financial
    "estimates": WidgetType.ESTIMATES,
    "quotes": WidgetType.ESTIMATES,
    "invoices": WidgetType.INVOICES,
    "bills": WidgetType.INVOICES,
    "payments": WidgetType.PAYMENTS,
    "payment history": WidgetType.PAYMENTS,
    "line items": WidgetType.LINE_ITEMS,
    "items": WidgetType.LINE_ITEMS,
    "materials": WidgetType.MATERIALS,
    "parts": WidgetType.MATERIALS,
    "labor": WidgetType.LABOR,
    "labor entries": WidgetType.LABOR,
    "expenses": WidgetType.EXPENSES,
    "receipts": WidgetType.EXPENSES,
    # Time
    "timesheets": WidgetType.TIMESHEETS,
    "time entries": WidgetType.TIMESHEETS,
    "time tracking": WidgetType.TIMESHEETS,
    # Assets
    "assets": WidgetType.ASSETS,
    "equipment": WidgetType.ASSETS,
    "units": WidgetType.ASSETS,
    "asset details": WidgetType.ASSET_DETAILS,
    "equipment details": WidgetType.ASSET_DETAILS,
    # History
    "customer history": WidgetType.CUSTOMER_HISTORY,
    "job history": WidgetType.JOB_HISTORY,
    "related jobs": WidgetType.RELATED_JOBS,
}


class EntityResolver:
    """Resolves extracted phrases to canonical ClearPath entities.

    Uses fuzzy matching and optionally vector similarity search
    to map user phrases to ActionButtonType and WidgetType values.
    """

    def __init__(
        self,
        vector_store=None,
        fuzzy_threshold: float = 0.75,
        high_confidence_threshold: float = 0.85,
        medium_confidence_threshold: float = 0.6,
    ):
        """Initialize the entity resolver.

        Args:
            vector_store: Optional VectorStore for semantic similarity search
            fuzzy_threshold: Minimum similarity for fuzzy matching
            high_confidence_threshold: Threshold for auto-accept (>= this)
            medium_confidence_threshold: Threshold for medium confidence (>= this)
        """
        self.vector_store = vector_store
        self.fuzzy_threshold = fuzzy_threshold
        self.high_confidence_threshold = high_confidence_threshold
        self.medium_confidence_threshold = medium_confidence_threshold

    def resolve_action(
        self,
        phrase: ExtractedPhrase,
    ) -> Optional[ResolvedEntity]:
        """Resolve an action phrase to a canonical ActionButtonType.

        Args:
            phrase: The extracted phrase to resolve

        Returns:
            ResolvedEntity if resolved, None otherwise
        """
        phrase_lower = phrase.phrase.lower().strip()

        # Check for exact match first
        if phrase_lower in ACTION_PHRASE_MAPPINGS:
            action_type = ACTION_PHRASE_MAPPINGS[phrase_lower]
            return ResolvedEntity(
                original_phrase=phrase.phrase,
                resolved_type=action_type.value,
                confidence=1.0,
                was_auto_resolved=True,
                user_override=False,
            )

        # Try fuzzy matching
        best_match, best_score = self._fuzzy_match_action(phrase_lower)
        if best_match and best_score >= self.fuzzy_threshold:
            action_type = ACTION_PHRASE_MAPPINGS[best_match]

            # Use LLM's confidence if provided and higher
            confidence = max(best_score, phrase.confidence)

            return ResolvedEntity(
                original_phrase=phrase.phrase,
                resolved_type=action_type.value,
                confidence=confidence,
                was_auto_resolved=confidence >= self.high_confidence_threshold,
                user_override=False,
            )

        # Try suggested type from LLM
        if phrase.suggested_type:
            try:
                # Check if suggested_type matches an ActionButtonType
                for action in ActionButtonType:
                    if action.value.lower() == phrase.suggested_type.lower():
                        return ResolvedEntity(
                            original_phrase=phrase.phrase,
                            resolved_type=action.value,
                            confidence=phrase.confidence,
                            was_auto_resolved=phrase.confidence >= self.high_confidence_threshold,
                            user_override=False,
                        )
            except Exception:
                pass

        # Try vector similarity if available
        if self.vector_store:
            result = self._vector_search_action(phrase_lower)
            if result:
                return result

        logger.debug(f"Could not resolve action phrase: '{phrase.phrase}'")
        return None

    def resolve_widget(
        self,
        phrase: ExtractedPhrase,
    ) -> Optional[ResolvedEntity]:
        """Resolve a widget phrase to a canonical WidgetType.

        Args:
            phrase: The extracted phrase to resolve

        Returns:
            ResolvedEntity if resolved, None otherwise
        """
        phrase_lower = phrase.phrase.lower().strip()

        # Check for exact match first
        if phrase_lower in WIDGET_PHRASE_MAPPINGS:
            widget_type = WIDGET_PHRASE_MAPPINGS[phrase_lower]
            return ResolvedEntity(
                original_phrase=phrase.phrase,
                resolved_type=widget_type.value,
                confidence=1.0,
                was_auto_resolved=True,
                user_override=False,
            )

        # Try fuzzy matching
        best_match, best_score = self._fuzzy_match_widget(phrase_lower)
        if best_match and best_score >= self.fuzzy_threshold:
            widget_type = WIDGET_PHRASE_MAPPINGS[best_match]

            # Use LLM's confidence if provided and higher
            confidence = max(best_score, phrase.confidence)

            return ResolvedEntity(
                original_phrase=phrase.phrase,
                resolved_type=widget_type.value,
                confidence=confidence,
                was_auto_resolved=confidence >= self.high_confidence_threshold,
                user_override=False,
            )

        # Try suggested type from LLM
        if phrase.suggested_type:
            try:
                for widget in WidgetType:
                    if widget.value.lower() == phrase.suggested_type.lower():
                        return ResolvedEntity(
                            original_phrase=phrase.phrase,
                            resolved_type=widget.value,
                            confidence=phrase.confidence,
                            was_auto_resolved=phrase.confidence >= self.high_confidence_threshold,
                            user_override=False,
                        )
            except Exception:
                pass

        # Try vector similarity if available
        if self.vector_store:
            result = self._vector_search_widget(phrase_lower)
            if result:
                return result

        logger.debug(f"Could not resolve widget phrase: '{phrase.phrase}'")
        return None

    def _fuzzy_match_action(
        self,
        phrase: str,
    ) -> tuple[Optional[str], float]:
        """Find best fuzzy match for an action phrase.

        Args:
            phrase: Lowercased phrase to match

        Returns:
            Tuple of (best matching phrase, similarity score)
        """
        best_match = None
        best_score = 0.0

        for known_phrase in ACTION_PHRASE_MAPPINGS.keys():
            score = SequenceMatcher(None, phrase, known_phrase).ratio()
            if score > best_score:
                best_score = score
                best_match = known_phrase

        return best_match, best_score

    def _fuzzy_match_widget(
        self,
        phrase: str,
    ) -> tuple[Optional[str], float]:
        """Find best fuzzy match for a widget phrase.

        Args:
            phrase: Lowercased phrase to match

        Returns:
            Tuple of (best matching phrase, similarity score)
        """
        best_match = None
        best_score = 0.0

        for known_phrase in WIDGET_PHRASE_MAPPINGS.keys():
            score = SequenceMatcher(None, phrase, known_phrase).ratio()
            if score > best_score:
                best_score = score
                best_match = known_phrase

        return best_match, best_score

    def _vector_search_action(
        self,
        phrase: str,
    ) -> Optional[ResolvedEntity]:
        """Search for action using vector similarity.

        Args:
            phrase: The phrase to search for

        Returns:
            ResolvedEntity if found, None otherwise
        """
        try:
            results = self.vector_store.search_by_name(
                name=phrase,
                entity_type="action",
                limit=1,
            )
            if results:
                result = results[0]
                # Map result name to ActionButtonType
                for action in ActionButtonType:
                    if action.value.lower() == result.name.lower():
                        return ResolvedEntity(
                            original_phrase=phrase,
                            resolved_type=action.value,
                            confidence=result.similarity,
                            was_auto_resolved=result.similarity >= self.high_confidence_threshold,
                            user_override=False,
                        )
        except Exception as e:
            logger.warning(f"Vector search failed for action '{phrase}': {e}")

        return None

    def _vector_search_widget(
        self,
        phrase: str,
    ) -> Optional[ResolvedEntity]:
        """Search for widget using vector similarity.

        Args:
            phrase: The phrase to search for

        Returns:
            ResolvedEntity if found, None otherwise
        """
        try:
            results = self.vector_store.search_by_name(
                name=phrase,
                entity_type="widget",
                limit=1,
            )
            if results:
                result = results[0]
                # Map result name to WidgetType
                for widget in WidgetType:
                    if widget.value.lower() == result.name.lower():
                        return ResolvedEntity(
                            original_phrase=phrase,
                            resolved_type=widget.value,
                            confidence=result.similarity,
                            was_auto_resolved=result.similarity >= self.high_confidence_threshold,
                            user_override=False,
                        )
        except Exception as e:
            logger.warning(f"Vector search failed for widget '{phrase}': {e}")

        return None

    def get_action_candidates(
        self,
        phrase: ExtractedPhrase,
        limit: int = 5,
    ) -> list[tuple[ActionButtonType, float]]:
        """Get candidate actions for an ambiguous phrase.

        Args:
            phrase: The phrase to find candidates for
            limit: Maximum number of candidates

        Returns:
            List of (ActionButtonType, confidence) tuples
        """
        phrase_lower = phrase.phrase.lower().strip()
        candidates = []

        # Get fuzzy matches
        for known_phrase, action_type in ACTION_PHRASE_MAPPINGS.items():
            score = SequenceMatcher(None, phrase_lower, known_phrase).ratio()
            if score >= 0.5:  # Lower threshold for candidates
                candidates.append((action_type, score))

        # Deduplicate and sort by score
        seen = set()
        unique_candidates = []
        for action_type, score in sorted(candidates, key=lambda x: x[1], reverse=True):
            if action_type not in seen:
                seen.add(action_type)
                unique_candidates.append((action_type, score))

        return unique_candidates[:limit]

    def get_widget_candidates(
        self,
        phrase: ExtractedPhrase,
        limit: int = 5,
    ) -> list[tuple[WidgetType, float]]:
        """Get candidate widgets for an ambiguous phrase.

        Args:
            phrase: The phrase to find candidates for
            limit: Maximum number of candidates

        Returns:
            List of (WidgetType, confidence) tuples
        """
        phrase_lower = phrase.phrase.lower().strip()
        candidates = []

        # Get fuzzy matches
        for known_phrase, widget_type in WIDGET_PHRASE_MAPPINGS.items():
            score = SequenceMatcher(None, phrase_lower, known_phrase).ratio()
            if score >= 0.5:  # Lower threshold for candidates
                candidates.append((widget_type, score))

        # Deduplicate and sort by score
        seen = set()
        unique_candidates = []
        for widget_type, score in sorted(candidates, key=lambda x: x[1], reverse=True):
            if widget_type not in seen:
                seen.add(widget_type)
                unique_candidates.append((widget_type, score))

        return unique_candidates[:limit]

    def check_template_requirements(
        self,
        action_type: ActionButtonType,
    ) -> dict[str, bool]:
        """Check if an action requires template_id or form_id.

        Args:
            action_type: The action button type

        Returns:
            Dict with 'requires_template' and 'requires_form' flags
        """
        template_actions = {
            ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
            ActionButtonType.CREATE_ESTIMATE,
            ActionButtonType.CREATE_INVOICE,
            ActionButtonType.SEND_ESTIMATE,
            ActionButtonType.SEND_INVOICE,
        }

        form_actions = {
            ActionButtonType.FILL_FORM,
        }

        return {
            "requires_template": action_type in template_actions,
            "requires_form": action_type in form_actions,
        }

    def resolve_all(
        self,
        action_phrases: list[ExtractedPhrase],
        widget_phrases: list[ExtractedPhrase],
    ) -> ResolutionResult:
        """Resolve all action and widget phrases.

        Args:
            action_phrases: List of action phrases to resolve
            widget_phrases: List of widget phrases to resolve

        Returns:
            ResolutionResult with all resolved and unresolved items
        """
        result = ResolutionResult()

        # Resolve actions
        for phrase in action_phrases:
            resolved = self.resolve_action(phrase)
            if resolved:
                result.resolved_actions[phrase.phrase] = resolved
                if not resolved.was_auto_resolved:
                    result.review_required.append(phrase)
            else:
                result.unresolved_phrases.append(phrase)

        # Resolve widgets
        for phrase in widget_phrases:
            resolved = self.resolve_widget(phrase)
            if resolved:
                result.resolved_widgets[phrase.phrase] = resolved
                if not resolved.was_auto_resolved:
                    result.review_required.append(phrase)
            else:
                result.unresolved_phrases.append(phrase)

        logger.info(
            f"Resolved {len(result.resolved_actions)} actions, "
            f"{len(result.resolved_widgets)} widgets, "
            f"{len(result.unresolved_phrases)} unresolved, "
            f"{len(result.review_required)} need review"
        )

        return result
