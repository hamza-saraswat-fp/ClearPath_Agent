"""ClearPath relevance scoring for Gong call transcripts — V3.

Speaker-aware, sentence-based scoring.
Counts CUSTOMER SENTENCES containing workflow language, not raw keyword hits.
A customer giving 20 substantive sentences about their process is gold;
a customer saying "okay" 20 times while the rep demos features is noise.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field

from ..models.gong_schemas import (
    GongCallMetadata,
    GongTranscript,
    TranscriptSentence,
    KeywordMatch,
    ScoredCall,
)

logger = logging.getLogger(__name__)

# Minimum words for a customer sentence to count as "substantive"
# Filters out "okay", "yeah", "that makes sense", "completed"
MIN_SENTENCE_WORDS = 8


@dataclass
class ScoringWeights:
    """Configurable weights for each scoring signal."""

    customer_workflow: float = 0.45   # ownership + process language
    customer_actions: float = 0.20    # actionable detail from customer
    flow_structure: float = 0.15      # customer-described statuses/steps
    clearpath_depth: float = 0.10     # ClearPath feature discussion (any speaker)
    call_properties: float = 0.10     # title, duration, speaker balance


@dataclass
class KeywordConfig:
    """All keyword lists used for scoring, grouped by category."""

    # Gate keywords
    gate_product: list[str] = field(default_factory=lambda: [
        "clearpath", "clear path", "status action flow",
        "action button", "action buttons",
        "focus view", "focus views",
        "status instruction", "status instructions",
    ])
    gate_combo_all: list[list[str]] = field(default_factory=lambda: [
        ["status", "workflow"],
    ])

    # Customer ownership — THE strongest signal. Customer declaring
    # their process: "our guys", "we need", "I want them to"
    # IMPORTANT: Keep these specific to workflow/process context.
    # Generic phrases like "we have", "we do", "i want to" match
    # non-workflow sentences ("we have QuickBooks", "we do accounting")
    # and cause false positives.
    customer_ownership: list[str] = field(default_factory=lambda: [
        "our process", "our workflow", "how we do it",
        "what we currently do", "our flow", "the way we handle",
        "our techs", "our dispatchers", "our team",
        "we typically", "we usually", "we always",
        "our customers", "our office",
        "i want them to", "i need them to", "they need to",
        "we need them to", "we want them to",
        "we need", "we want", "our guys",
    ])

    # Process language — sequential descriptions
    process_language: list[str] = field(default_factory=lambda: [
        "first we", "then we", "next step", "after that",
        "once the", "when the job", "before they",
        "the next thing", "from there", "at that point",
        "step one", "step two", "step three",
        "when they", "after they", "once they",
    ])

    # Role-based descriptions — customer describing who does what
    # Avoid generic phrases like "someone's going to", "they're going to"
    role_descriptions: list[str] = field(default_factory=lambda: [
        "the tech goes", "the tech will", "the technician",
        "dispatcher assigns", "dispatcher sends", "dispatcher will",
        "office staff", "office manager", "the office",
        "the customer gets", "the customer receives",
        "the manager", "service agent",
        "the tech needs to", "the tech has to",
        "our admin", "our dispatcher",
    ])

    # Actionable detail — ClearPath-mappable actions
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

    # Status/stage terms
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

    # Sequential connectors
    sequential_connectors: list[str] = field(default_factory=lambda: [
        "first", "then", "next", "after", "finally",
        "second", "third", "fourth", "fifth",
        "once that", "from there", "at that point",
        "the next step", "following that",
    ])

    # ClearPath features
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


class GongScorerV3:
    """Scores Gong calls for ClearPath pipeline testing relevance.

    Scoring is based on counting CUSTOMER SENTENCES (not keyword hits).
    A sentence counts only if it's from an external speaker and is 8+ words
    (filtering out "okay", "yeah", etc.)
    """

    IDEAL_MIN_MINUTES: float = 15.0
    IDEAL_MAX_MINUTES: float = 60.0
    ABSOLUTE_MIN_MINUTES: float = 5.0
    ABSOLUTE_MAX_MINUTES: float = 120.0

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
        """Build set of speaker_ids belonging to external (customer) participants."""
        transcript_speaker_ids = {
            s.speaker_id for s in transcript.sentences if s.speaker_id
        }
        external_user_ids = {
            p.user_id for p in metadata.external_participants if p.user_id
        }

        # Direct match
        external_speaker_ids = transcript_speaker_ids & external_user_ids

        # Inference: if no direct matches, infer from internal IDs
        if not external_speaker_ids and len(transcript_speaker_ids) >= 2:
            internal_user_ids = {
                p.user_id for p in metadata.internal_participants if p.user_id
            }
            internal_speaker_ids = transcript_speaker_ids & internal_user_ids
            if internal_speaker_ids:
                external_speaker_ids = transcript_speaker_ids - internal_speaker_ids

        return external_speaker_ids

    def _count_customer_sentences(
        self,
        ext_sentences: list[TranscriptSentence],
        keywords: list[str],
        category: str,
    ) -> tuple[int, list[KeywordMatch]]:
        """Count external speaker sentences (8+ words) containing any keyword.

        Returns (sentence_count, keyword_matches_for_display).
        """
        sentence_count = 0
        kw_hits: dict[str, int] = {}
        kw_samples: dict[str, list[str]] = {}

        for s in ext_sentences:
            if len(s.text.split()) < MIN_SENTENCE_WORDS:
                continue
            text_lower = s.text.lower()
            matched = False
            for kw in keywords:
                if kw.lower() in text_lower:
                    matched = True
                    kw_hits[kw] = kw_hits.get(kw, 0) + 1
                    if kw not in kw_samples:
                        kw_samples[kw] = []
                    if len(kw_samples[kw]) < 2:
                        kw_samples[kw].append(s.text[:150])
            if matched:
                sentence_count += 1

        matches = []
        for kw, count in kw_hits.items():
            matches.append(KeywordMatch(
                keyword=kw,
                count=count,
                category=category,
                sample_sentences=kw_samples.get(kw, []),
            ))

        return sentence_count, matches

    def _count_keywords(
        self,
        text_lower: str,
        keywords: list[str],
        category: str,
    ) -> tuple[int, list[KeywordMatch]]:
        """Count keyword occurrences in text (for gate and clearpath_depth)."""
        total_hits = 0
        matches: list[KeywordMatch] = []
        for kw in keywords:
            count = text_lower.count(kw.lower())
            if count > 0:
                capped = min(count, 5)
                total_hits += capped
                matches.append(KeywordMatch(keyword=kw, count=capped, category=category))
        return total_hits, matches

    def score_call(
        self,
        metadata: GongCallMetadata,
        transcript: GongTranscript | None,
    ) -> ScoredCall:
        """Score a single call for ClearPath relevance."""
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
            full_text_lower = transcript.full_text.lower()
            transcript_word_count = len(full_text_lower.split())

            # Build speaker map
            external_ids = self._build_external_ids(metadata, transcript)

            # External speaker ratio
            if transcript.sentences and external_ids:
                ext_count = sum(
                    1 for s in transcript.sentences if s.speaker_id in external_ids
                )
                external_ratio = ext_count / len(transcript.sentences)

            ext_sentences, _ = transcript.sentences_by_speaker(external_ids) if external_ids else ([], [])

            # --- Gate (uses full text, all speakers) ---
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

            # --- Scoring: count customer SENTENCES, not keyword hits ---

            # Collect per-category matches for display
            ownership_sents, ownership_matches = self._count_customer_sentences(
                ext_sentences, self.keywords.customer_ownership, "customer_ownership",
            )
            process_sents, process_matches = self._count_customer_sentences(
                ext_sentences, self.keywords.process_language, "process_language",
            )
            role_sents, role_matches = self._count_customer_sentences(
                ext_sentences, self.keywords.role_descriptions, "role_descriptions",
            )
            action_sents, action_matches = self._count_customer_sentences(
                ext_sentences, self.keywords.actionable, "actionable_detail",
            )
            status_sents, status_matches = self._count_customer_sentences(
                ext_sentences, self.keywords.status_terms, "status_terms",
            )
            connector_sents, connector_matches = self._count_customer_sentences(
                ext_sentences, self.keywords.sequential_connectors, "sequential_connectors",
            )
            all_keyword_matches.extend(
                ownership_matches + process_matches + role_matches
                + action_matches + status_matches + connector_matches
            )

            # Signal 1: Customer workflow (0.45)
            # Score by per-sentence richness: a sentence combining ownership
            # with actions ("I want them to take photos") is a real workflow
            # declaration. A sentence with just ownership ("we need to discuss")
            # is weak. This separates real workflow descriptions from admin talk.
            rich_sents = 0      # 2+ categories, including ownership/process
            moderate_sents = 0  # 1 category that's ownership or process
            ownership_kws = [kw.lower() for kw in self.keywords.customer_ownership]
            process_kws = [kw.lower() for kw in self.keywords.process_language]
            action_kws = [kw.lower() for kw in self.keywords.actionable]
            status_kws = [kw.lower() for kw in self.keywords.status_terms]
            role_kws = [kw.lower() for kw in self.keywords.role_descriptions]

            for s in ext_sentences:
                if len(s.text.split()) < MIN_SENTENCE_WORDS:
                    continue
                tl = s.text.lower()
                has_own = any(kw in tl for kw in ownership_kws)
                has_proc = any(kw in tl for kw in process_kws)
                has_act = any(kw in tl for kw in action_kws)
                has_stat = any(kw in tl for kw in status_kws)
                has_role = any(kw in tl for kw in role_kws)

                cats = sum([has_own, has_proc, has_act, has_stat, has_role])
                if cats >= 2 and (has_own or has_proc):
                    rich_sents += 1
                elif has_own or has_proc:
                    moderate_sents += 1

            # Rich sentences worth 4x, moderate worth 1x
            # Scale: 24 points = 1.0 (e.g. 6 rich sentences = full score)
            workflow_raw = rich_sents * 4.0 + moderate_sents * 1.0
            workflow_score = min(1.0, workflow_raw / 24.0)
            breakdown["customer_workflow"] = workflow_score

            # Signal 2: Customer actions (0.20)
            distinct_actions = sum(1 for m in action_matches if m.count > 0)
            action_score = min(1.0, (action_sents + distinct_actions * 1.5) / 12.0)
            breakdown["customer_actions"] = action_score

            # Signal 3: Flow structure (0.15) — customer-described statuses
            distinct_statuses = sum(1 for m in status_matches if m.count > 0)
            flow_steps = distinct_statuses
            flow_score = min(1.0, (distinct_statuses * 2.0 + min(connector_sents, 5)) / 10.0)
            breakdown["flow_structure"] = flow_score

            # Signal 4: ClearPath depth (0.10) — all speakers OK
            depth_hits, depth_matches = self._count_keywords(
                full_text_lower, self.keywords.clearpath_features, "clearpath_depth",
            )
            all_keyword_matches.extend(depth_matches)
            distinct_features = sum(1 for m in depth_matches if m.count > 0)
            depth_score = min(1.0, (depth_hits + distinct_features * 2) / 15.0)
            breakdown["clearpath_depth"] = depth_score

            # Customer keyword ratio for display
            total_cust = ownership_sents + process_sents + role_sents + action_sents + status_sents
            all_wf_kws = (
                self.keywords.customer_ownership + self.keywords.process_language
                + self.keywords.role_descriptions + self.keywords.actionable
                + self.keywords.status_terms
            )
            all_sents_with_kw = 0
            for s in transcript.sentences:
                if len(s.text.split()) < MIN_SENTENCE_WORDS:
                    continue
                text_lower = s.text.lower()
                if any(kw.lower() in text_lower for kw in all_wf_kws):
                    all_sents_with_kw += 1
            customer_kw_ratio = total_cust / all_sents_with_kw if all_sents_with_kw > 0 else 0.0

            total_keyword_hits = sum(m.count for m in all_keyword_matches)

            # Relevant snippets from customer sentences
            all_kws = (
                self.keywords.customer_ownership + self.keywords.process_language
                + self.keywords.actionable + self.keywords.clearpath_features
            )
            for sent in ext_sentences:
                if len(sent.text.split()) < MIN_SENTENCE_WORDS:
                    continue
                text_lower = sent.text.lower()
                if any(kw.lower() in text_lower for kw in all_kws):
                    snippet = sent.text[:200]
                    if snippet not in relevant_snippets:
                        relevant_snippets.append(snippet)
                    if len(relevant_snippets) >= 5:
                        break

        # Signal 5: Call properties (0.10)
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
            speaker_score = 0.3

        properties_score = (title_score * 0.4 + duration_score * 0.3 + speaker_score * 0.3)
        breakdown["call_properties"] = properties_score

        # --- Weighted total ---
        total = sum(
            breakdown.get(signal, 0) * weight
            for signal, weight in [
                ("customer_workflow", self.weights.customer_workflow),
                ("customer_actions", self.weights.customer_actions),
                ("flow_structure", self.weights.flow_structure),
                ("clearpath_depth", self.weights.clearpath_depth),
                ("call_properties", self.weights.call_properties),
            ]
        )

        return ScoredCall(
            metadata=metadata,
            total_score=round(total, 4),
            passed_gate=passed_gate,
            score_breakdown={k: round(v, 4) for k, v in breakdown.items()},
            keyword_matches=[m for m in all_keyword_matches if m.count > 0],
            total_keyword_hits=total_keyword_hits,
            relevant_snippets=relevant_snippets,
            has_transcript=transcript is not None,
            transcript_word_count=transcript_word_count,
            flow_steps_detected=flow_steps,
            external_speaker_ratio=round(external_ratio, 3),
            customer_keyword_ratio=round(customer_kw_ratio, 3),
        )

    def _score_title(self, title: str | None) -> float:
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
        return 1.0 - (minutes - self.IDEAL_MAX_MINUTES) / (
            self.ABSOLUTE_MAX_MINUTES - self.IDEAL_MAX_MINUTES
        ) * 0.8
