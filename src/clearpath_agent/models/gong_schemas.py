"""Pydantic models for Gong API data and call relevance scoring."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GongParticipant(BaseModel):
    """A participant in a Gong call."""

    name: str = ""
    email: Optional[str] = None
    title: Optional[str] = None
    user_id: Optional[str] = None
    affiliation: Optional[str] = None  # "internal" or "external"


class GongCallMetadata(BaseModel):
    """Metadata for a single Gong call."""

    call_id: str
    title: Optional[str] = None
    started: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    direction: Optional[str] = None  # "Inbound", "Outbound", "Conference"
    participants: list[GongParticipant] = Field(default_factory=list)
    url: Optional[str] = None
    workspace_id: Optional[str] = None

    @property
    def duration_minutes(self) -> float:
        return (self.duration_seconds or 0) / 60.0

    @property
    def external_participants(self) -> list[GongParticipant]:
        return [p for p in self.participants if (p.affiliation or "").lower() == "external"]

    @property
    def internal_participants(self) -> list[GongParticipant]:
        return [p for p in self.participants if (p.affiliation or "").lower() == "internal"]


class TranscriptSentence(BaseModel):
    """A single sentence/utterance from a call transcript."""

    speaker_id: Optional[str] = None
    speaker_name: Optional[str] = None
    topic: Optional[str] = None
    start_time: Optional[float] = None  # milliseconds from call start
    end_time: Optional[float] = None
    text: str = ""


class GongTranscript(BaseModel):
    """Full transcript for a Gong call."""

    call_id: str
    sentences: list[TranscriptSentence] = Field(default_factory=list)

    @property
    def full_text(self) -> str:
        return " ".join(s.text for s in self.sentences)

    def sentences_containing(self, keywords: list[str]) -> list[TranscriptSentence]:
        """Return sentences containing any of the given keywords (case-insensitive)."""
        results = []
        for sentence in self.sentences:
            text_lower = sentence.text.lower()
            if any(kw.lower() in text_lower for kw in keywords):
                results.append(sentence)
        return results

    def external_text(self, external_ids: set) -> str:
        """Return concatenated text from external (customer) speakers only."""
        return " ".join(
            s.text for s in self.sentences if s.speaker_id in external_ids
        )

    def internal_text(self, external_ids: set) -> str:
        """Return concatenated text from non-external (rep) speakers."""
        return " ".join(
            s.text for s in self.sentences if s.speaker_id not in external_ids
        )

    def sentences_by_speaker(
        self, external_ids: set
    ) -> tuple[list, list]:
        """Split sentences into (external, internal) lists."""
        ext, internal = [], []
        for s in self.sentences:
            if s.speaker_id in external_ids:
                ext.append(s)
            else:
                internal.append(s)
        return ext, internal


class KeywordMatch(BaseModel):
    """A keyword match found in a transcript."""

    keyword: str
    count: int
    category: str = ""  # e.g. "gate", "workflow", "actionable", "clearpath_depth"
    sample_sentences: list[str] = Field(default_factory=list)


class ScoredCall(BaseModel):
    """A Gong call with its ClearPath relevance score."""

    metadata: GongCallMetadata
    total_score: float = 0.0
    passed_gate: bool = False
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    keyword_matches: list[KeywordMatch] = Field(default_factory=list)
    total_keyword_hits: int = 0
    relevant_snippets: list[str] = Field(default_factory=list)
    has_transcript: bool = False
    transcript_word_count: int = 0
    flow_steps_detected: int = 0
    external_speaker_ratio: float = 0.0
    customer_keyword_ratio: float = 0.0
