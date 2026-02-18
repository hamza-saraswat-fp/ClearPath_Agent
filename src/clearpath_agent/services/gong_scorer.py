"""ClearPath relevance scoring for Gong call transcripts.

Uses a gated, speaker-aware approach:
1. ClearPath Gate — call must mention ClearPath/action buttons/focus views
2. Speaker-aware weighted scoring — keywords from CUSTOMER speakers are
   weighted heavily; rep-spoken keywords are discounted or ignored.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field

from ..models.gong_schemas import (
    GongCallMetadata,
    GongTranscript,
    KeywordMatch,
    ScoredCall,
)

logger = logging.getLogger(__name__)

# Maximum times a single keyword counts toward a score.
# Prevents "and then" x55 from inflating scores.
MAX_KEYWORD_HITS = 5


@dataclass
class ScoringWeights:
    """Configurable weights for each scoring signal."""

    customer_workflow: float = 0.40
    customer_actions: float = 0.25
    flow_structure: float = 0.15
    clearpath_depth: float = 0.10
    customer_engagement: float = 0.10


@dataclass
class KeywordConfig:
    """All keyword lists used for scoring, grouped by category."""

    # Gate keywords — a call needs to match at least one gate group:
    #   Group A (product terms): any one of these, OR
    #   Group B (workflow setup combo): "status" + "workflow" both present
    gate_product: list[str] = field(default_factory=lambda: [
        "clearpath", "clear path", "status action flow",
        "action button", "action buttons",
        "focus view", "focus views",
        "status instruction", "status instructions",
    ])
    gate_combo_all: list[list[str]] = field(default_factory=lambda: [
        ["status", "workflow"],
    ])

    # Workflow description — customer describing their actual process
    # NOTE: "and then" removed — it's conversational filler, not a workflow signal.
    process_language: list[str] = field(default_factory=lambda: [
        "first we", "then we", "next step", "after that",
        "once the", "when the job", "before they",
        "the next thing", "from there", "at that point",
        "step one", "step two", "step three",
    ])

    customer_ownership: list[str] = field(default_factory=lambda: [
        "our process", "our workflow", "how we do it",
        "what we currently do", "our flow", "the way we handle",
        "our techs", "our dispatchers", "our team",
        "we typically", "we usually", "we always",
        "our customers", "our office",
        "i want them to", "i need them to", "they need to",
        "we need", "we want", "our guys",
    ])

    role_descriptions: list[str] = field(default_factory=lambda: [
        "the tech goes", "the tech will", "the technician",
        "dispatcher assigns", "dispatcher sends", "dispatcher will",
        "office staff", "office manager", "the office",
        "the customer gets", "the customer receives",
        "the manager", "service agent",
    ])

    # Actionable detail — specific ClearPath-mappable actions
    actionable: list[str] = field(default_factory=lambda: [
        "send a text", "send text", "send notification", "send sms",
        "fill out form", "fill form", "complete form",
        "collect payment", "take payment", "process payment",
        "take photos", "take a photo", "take picture",
        "get signature", "collect signature", "capture signature",
        "create estimate", "send estimate",
        "create invoice", "send invoice",
        "clock in", "clock out", "time tracking",
        "schedule follow up", "follow-up", "reschedule",
        "request review", "leave review",
        "add note", "add notes", "leave a note",
        "checklist", "check list",
        "add attachment", "upload",
    ])

    # Status/stage terms for flow structure detection
    status_terms: list[str] = field(default_factory=lambda: [
        "new job", "job created", "unassigned",
        "assigned", "dispatched", "dispatch",
        "en route", "on the way", "heading to", "driving to",
        "on site", "arrived", "at the job", "at the location",
        "in progress", "working on", "started",
        "on hold", "paused", "waiting for",
        "completed", "done", "finished", "wrapped up",
        "cancelled", "canceled",
        "pending", "scheduled", "confirmed",
        "follow up", "warranty",
    ])

    # Sequential connectors for flow structure detection
    sequential_connectors: list[str] = field(default_factory=lambda: [
        "first", "then", "next", "after", "finally",
        "second", "third", "fourth", "fifth",
        "once that", "from there", "at that point",
        "the next step", "following that",
    ])

    # ClearPath depth — discussing specific features
    clearpath_features: list[str] = field(default_factory=lambda: [
        "action button", "action buttons", "action menu",
        "focus view", "focus views",
        "status instruction", "status instructions",
        "custom status", "custom statuses",
        "status workflow", "workflow name",
        "import file", "import template", "excel import",
        "widget", "widgets",
        "change status", "status change",
        "restrict status", "lock status",
    ])


class GongScorer:
    """Scores Gong calls for ClearPath pipeline testing relevance.

    Speaker-aware: keywords from external (customer) speakers are weighted
    heavily for workflow/actionable signals. Rep-spoken keywords only count
    for clearpath_depth (feature discussion is naturally rep-led).
    """

    # Duration scoring constants
    IDEAL_MIN_MINUTES: float = 15.0
    IDEAL_MAX_MINUTES: float = 60.0
    ABSOLUTE_MIN_MINUTES: float = 5.0
    ABSOLUTE_MAX_MINUTES: float = 120.0

    # Title patterns
    TITLE_PATTERNS: list[str] = [
        r"clearpath", r"clear\s*path",
        r"status\s*(action)?\s*flow",
        r"workflow", r"onboarding",
        r"implementation", r"configuration",
        r"setup\s*call", r"training",
    ]

    def __init__(
        self,
        weights: ScoringWeights | None = None,
        keywords: KeywordConfig | None = None,
    ):
        self.weights = weights or ScoringWeights()
        self.keywords = keywords or KeywordConfig()

    def _build_external_ids(
        self,
        metadata: GongCallMetadata,
        transcript: GongTranscript,
    ) -> set[str]:
        """Build the set of speaker_ids belonging to external (customer) participants.

        Strategy: match participant user_ids against speaker_ids found in the
        transcript. External participants whose user_id appears as a speaker_id
        are identified. All other (unmapped) speaker_ids are treated as internal.
        """
        # Collect all speaker_ids actually present in the transcript
        transcript_speaker_ids = {
            s.speaker_id for s in transcript.sentences if s.speaker_id
        }

        # External participant user_ids
        external_user_ids = {
            p.user_id for p in metadata.external_participants if p.user_id
        }

        # Direct matches: external user_id == transcript speaker_id
        external_speaker_ids = transcript_speaker_ids & external_user_ids

        # If no direct matches, try inference: if we know the internal user_ids,
        # any remaining speaker_ids must be external.
        if not external_speaker_ids and len(transcript_speaker_ids) >= 2:
            internal_user_ids = {
                p.user_id for p in metadata.internal_participants if p.user_id
            }
            internal_speaker_ids = transcript_speaker_ids & internal_user_ids
            if internal_speaker_ids:
                external_speaker_ids = transcript_speaker_ids - internal_speaker_ids

        return external_speaker_ids

    def score_call(
        self,
        metadata: GongCallMetadata,
        transcript: GongTranscript | None,
    ) -> ScoredCall:
        """Score a single call for ClearPath relevance.

        Step 1: Check ClearPath gate (must mention ClearPath terms).
        Step 2: Speaker-aware weighted scoring on calls that pass the gate.
        """
        breakdown: dict[str, float] = {}
        all_keyword_matches: list[KeywordMatch] = []
        relevant_snippets: list[str] = []
        total_keyword_hits = 0
        transcript_word_count = 0
        external_ratio = 0.0
        customer_kw_ratio = 0.0
        flow_steps = 0
        passed_gate = False

        if transcript:
            full_text = transcript.full_text
            full_text_lower = full_text.lower()
            transcript_word_count = len(full_text.split())

            # --- Build speaker map ---
            external_ids = self._build_external_ids(metadata, transcript)

            # Compute external speaker ratio
            if transcript.sentences and external_ids:
                ext_count = sum(
                    1 for s in transcript.sentences if s.speaker_id in external_ids
                )
                external_ratio = ext_count / len(transcript.sentences)

            # Get speaker-split text
            ext_text_lower = transcript.external_text(external_ids).lower() if external_ids else ""
            ext_sentences, _ = transcript.sentences_by_speaker(external_ids) if external_ids else ([], [])

            # --- Step 1: Gate ---
            product_hits, product_matches = self._count_keywords(
                full_text_lower, self.keywords.gate_product, "gate"
            )
            all_keyword_matches.extend(product_matches)

            if product_hits > 0:
                passed_gate = True
            else:
                for combo in self.keywords.gate_combo_all:
                    if all(kw.lower() in full_text_lower for kw in combo):
                        passed_gate = True
                        break

            if not passed_gate and metadata.title:
                if "workflow" in metadata.title.lower():
                    passed_gate = True

            if not passed_gate:
                return ScoredCall(
                    metadata=metadata,
                    total_score=0.0,
                    passed_gate=False,
                    score_breakdown={"gate": 0.0},
                    keyword_matches=product_matches,
                    total_keyword_hits=0,
                    has_transcript=True,
                    transcript_word_count=transcript_word_count,
                )

            # --- Step 2: Speaker-aware weighted scoring ---

            # Track total customer vs all keyword hits for engagement ratio
            total_customer_kw = 0
            total_all_kw = 0

            # Signal 1: Customer workflow (0.40) — EXTERNAL speakers only
            process_hits, process_matches = self._count_keywords(
                ext_text_lower, self.keywords.process_language, "process_language",
            )
            ownership_hits, ownership_matches = self._count_keywords(
                ext_text_lower, self.keywords.customer_ownership, "customer_ownership",
            )
            role_hits, role_matches = self._count_keywords(
                ext_text_lower, self.keywords.role_descriptions, "role_descriptions",
            )
            all_keyword_matches.extend(process_matches + ownership_matches + role_matches)

            cust_workflow_raw = process_hits * 2.0 + ownership_hits * 3.0 + role_hits * 1.5
            workflow_score = min(1.0, cust_workflow_raw / 15.0)
            breakdown["customer_workflow"] = workflow_score

            cust_wf_hits = process_hits + ownership_hits + role_hits
            total_customer_kw += cust_wf_hits
            # Count same keywords from ALL speakers for engagement ratio
            all_process, _ = self._count_keywords(
                full_text_lower, self.keywords.process_language, "_all",
            )
            all_ownership, _ = self._count_keywords(
                full_text_lower, self.keywords.customer_ownership, "_all",
            )
            all_role, _ = self._count_keywords(
                full_text_lower, self.keywords.role_descriptions, "_all",
            )
            total_all_kw += all_process + all_ownership + all_role

            # Signal 2: Customer actions (0.25) — EXTERNAL speakers only
            action_hits, action_matches = self._count_keywords(
                ext_text_lower, self.keywords.actionable, "actionable_detail",
            )
            all_keyword_matches.extend(action_matches)
            distinct_actions = sum(1 for m in action_matches if m.count > 0)
            action_score = min(1.0, (action_hits + distinct_actions * 2) / 15.0)
            breakdown["customer_actions"] = action_score

            total_customer_kw += action_hits
            all_action, _ = self._count_keywords(
                full_text_lower, self.keywords.actionable, "_all",
            )
            total_all_kw += all_action

            # Signal 3: Flow structure (0.15) — EXTERNAL speakers only
            status_hits, status_matches = self._count_keywords(
                ext_text_lower, self.keywords.status_terms, "status_terms",
            )
            connector_hits, connector_matches = self._count_keywords(
                ext_text_lower, self.keywords.sequential_connectors, "sequential_connectors",
            )
            all_keyword_matches.extend(status_matches + connector_matches)

            distinct_statuses = sum(1 for m in status_matches if m.count > 0)
            flow_steps = distinct_statuses
            structure_raw = distinct_statuses * 2.5 + min(connector_hits, 8) * 0.5
            flow_score = min(1.0, structure_raw / 15.0)
            breakdown["flow_structure"] = flow_score

            total_customer_kw += status_hits + connector_hits
            all_status, _ = self._count_keywords(
                full_text_lower, self.keywords.status_terms, "_all",
            )
            all_connector, _ = self._count_keywords(
                full_text_lower, self.keywords.sequential_connectors, "_all",
            )
            total_all_kw += all_status + all_connector

            # Signal 4: ClearPath depth (0.10) — ALL speakers (features are rep-led)
            depth_hits, depth_matches = self._count_keywords(
                full_text_lower, self.keywords.clearpath_features, "clearpath_depth",
            )
            all_keyword_matches.extend(depth_matches)
            distinct_features = sum(1 for m in depth_matches if m.count > 0)
            depth_score = min(1.0, (depth_hits + distinct_features * 2) / 15.0)
            breakdown["clearpath_depth"] = depth_score

            # Signal 5: Customer engagement (0.10)
            # What % of all workflow keywords come from the customer?
            if total_all_kw > 0:
                customer_kw_ratio = total_customer_kw / total_all_kw
            else:
                customer_kw_ratio = 0.0

            if customer_kw_ratio >= 0.35:
                engagement_score = 1.0
            elif customer_kw_ratio >= 0.15:
                engagement_score = (customer_kw_ratio - 0.15) / 0.20
            else:
                engagement_score = 0.0
            breakdown["customer_engagement"] = engagement_score

            # Compute total keyword hits (from matches that have hits)
            total_keyword_hits = sum(m.count for m in all_keyword_matches if m.category != "_all")

            # Build relevant snippets from EXTERNAL speaker sentences
            all_kws = (
                self.keywords.process_language
                + self.keywords.customer_ownership
                + self.keywords.actionable
                + self.keywords.clearpath_features
            )
            # Prefer snippets from external speakers
            if ext_sentences:
                for sent in ext_sentences:
                    text_lower = sent.text.lower()
                    if any(kw.lower() in text_lower for kw in all_kws):
                        snippet = sent.text[:200]
                        if snippet not in relevant_snippets:
                            relevant_snippets.append(snippet)
                        if len(relevant_snippets) >= 5:
                            break

            # Fall back to all speakers if not enough external snippets
            if len(relevant_snippets) < 3:
                matching_sentences = transcript.sentences_containing(all_kws)
                for sent in matching_sentences[:8]:
                    snippet = sent.text[:200]
                    if snippet not in relevant_snippets:
                        relevant_snippets.append(snippet)
                    if len(relevant_snippets) >= 5:
                        break

        # Signal: Call properties — works even without transcript
        title_score = self._score_title(metadata.title)
        duration_score = self._score_duration(metadata.duration_minutes)

        if external_ratio > 0:
            if 0.20 <= external_ratio <= 0.60:
                speaker_score = 1.0
            elif external_ratio < 0.20:
                speaker_score = external_ratio / 0.20
            else:
                speaker_score = max(0.0, 1.0 - (external_ratio - 0.60) / 0.40)
        else:
            speaker_score = 0.3  # neutral when unknown

        properties_score = (title_score * 0.4 + duration_score * 0.3 + speaker_score * 0.3)
        # call_properties is folded into the other signals' weights;
        # we store it for display but it doesn't have its own weight in the total.
        breakdown["call_properties"] = properties_score

        # --- Weighted total ---
        total = sum(
            breakdown.get(signal, 0) * weight
            for signal, weight in [
                ("customer_workflow", self.weights.customer_workflow),
                ("customer_actions", self.weights.customer_actions),
                ("flow_structure", self.weights.flow_structure),
                ("clearpath_depth", self.weights.clearpath_depth),
                ("customer_engagement", self.weights.customer_engagement),
            ]
        )

        return ScoredCall(
            metadata=metadata,
            total_score=round(total, 4),
            passed_gate=passed_gate,
            score_breakdown={k: round(v, 4) for k, v in breakdown.items()},
            keyword_matches=[m for m in all_keyword_matches if m.count > 0 and m.category != "_all"],
            total_keyword_hits=total_keyword_hits,
            relevant_snippets=relevant_snippets,
            has_transcript=transcript is not None,
            transcript_word_count=transcript_word_count,
            flow_steps_detected=flow_steps,
            external_speaker_ratio=round(external_ratio, 3),
            customer_keyword_ratio=round(customer_kw_ratio, 3),
        )

    def _count_keywords(
        self,
        text_lower: str,
        keywords: list[str],
        category: str,
    ) -> tuple[int, list[KeywordMatch]]:
        """Count keyword occurrences in text, capping each at MAX_KEYWORD_HITS."""
        total_hits = 0
        matches: list[KeywordMatch] = []

        for kw in keywords:
            raw_count = text_lower.count(kw.lower())
            count = min(raw_count, MAX_KEYWORD_HITS)
            if count > 0:
                total_hits += count
                matches.append(KeywordMatch(
                    keyword=kw,
                    count=count,
                    category=category,
                ))

        return total_hits, matches

    def _score_title(self, title: str | None) -> float:
        """Score the call title against known ClearPath patterns."""
        if not title:
            return 0.0
        title_lower = title.lower()
        matches = sum(1 for p in self.TITLE_PATTERNS if re.search(p, title_lower))
        if matches >= 2:
            return 1.0
        elif matches == 1:
            return 0.6
        return 0.0

    def _score_duration(self, minutes: float) -> float:
        """Score call duration. Sweet spot: 15-60 minutes."""
        if minutes < self.ABSOLUTE_MIN_MINUTES:
            return 0.0
        if minutes > self.ABSOLUTE_MAX_MINUTES:
            return 0.2
        if self.IDEAL_MIN_MINUTES <= minutes <= self.IDEAL_MAX_MINUTES:
            return 1.0
        if minutes < self.IDEAL_MIN_MINUTES:
            return (minutes - self.ABSOLUTE_MIN_MINUTES) / (
                self.IDEAL_MIN_MINUTES - self.ABSOLUTE_MIN_MINUTES
            )
        # Between IDEAL_MAX and ABSOLUTE_MAX
        return 1.0 - (minutes - self.IDEAL_MAX_MINUTES) / (
            self.ABSOLUTE_MAX_MINUTES - self.IDEAL_MAX_MINUTES
        ) * 0.8
