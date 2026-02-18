"""Gong API client with pagination, rate limiting, and caching."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from ..models.gong_schemas import (
    GongCallMetadata,
    GongParticipant,
    GongTranscript,
    TranscriptSentence,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.gong.io/v2"

# FieldPulse Implementation Team — used as the default primaryUserIds filter
# so we only pull calls from reps who run ClearPath onboarding/setup.
IMPLEMENTATION_TEAM: dict[str, str] = {
    "Addi Tsirulnik": "162550164159092294",
    "Andrea Garcia": "6991071075265750379",
    "Carson Taylor": "8014438823641208328",
    "Cody Spicer": "5864989316930958045",
    "Emily Wilkinson": "4038301358055378460",
    "Evelyn Flores": "7484112991976154658",
    "Fatima Garcia": "2300262866372969296",
    "Isabella Luna": "4106250285327505389",
    "Joshua Fritz": "1831298001804466518",
    "Judith Smith": "950008143974210124",
    "Juliana Estrada-Arias": "1251652670340154997",
    "Keaton Crume": "2833440606475709528",
    "Luis Estrada": "5959296687071622232",
    "Mariano Balladares": "6666168456452231186",
    "Matt Callahan": "4734792332388889628",
    "Noor Barghouti": "4370725868718233566",
    "Shivani Patel": "6368800477830228178",
    "Sinai Gonzalez": "138947330637201874",
    "Spencer Croston": "2026181299498578160",
}

DEFAULT_USER_IDS = list(IMPLEMENTATION_TEAM.values())


class GongClient:
    """Client for Gong REST API v2.

    All operations are read-only. Handles pagination, rate limiting,
    and local JSON file caching to avoid redundant API calls.
    """

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        cache_dir: Optional[Path] = None,
        requests_per_second: float = 0.25,
    ):
        self._auth = (access_key, secret_key)
        self._client = httpx.Client(
            base_url=BASE_URL,
            auth=self._auth,
            timeout=60.0,
            headers={"Content-Type": "application/json"},
        )
        self._cache_dir = cache_dir or Path(".gong_cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._min_interval = 1.0 / requests_per_second
        self._last_request_time = 0.0

    def _rate_limit(self) -> None:
        """Sleep if needed to respect rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _cache_key(self, endpoint: str, params: dict) -> str:
        """Generate a deterministic cache key."""
        raw = f"{endpoint}:{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _read_cache(self, key: str) -> Optional[dict]:
        """Read from JSON file cache."""
        path = self._cache_dir / f"{key}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def _write_cache(self, key: str, data: dict) -> None:
        """Write to JSON file cache."""
        path = self._cache_dir / f"{key}.json"
        with open(path, "w") as f:
            json.dump(data, f, default=str)

    def list_calls(
        self,
        from_date: datetime,
        to_date: datetime,
        primary_user_ids: Optional[list[str]] = None,
        use_cache: bool = True,
    ) -> list[GongCallMetadata]:
        """List calls filtered by date range and user IDs.

        Uses POST /calls/extensive with primaryUserIds to restrict results
        to implementation team calls only. This dramatically reduces volume
        compared to GET /calls which returns ALL calls.
        """
        user_ids = primary_user_ids or DEFAULT_USER_IDS

        cache_params = {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "users": sorted(user_ids),
        }
        cache_key = self._cache_key("list_calls_v2", cache_params)

        if use_cache:
            cached = self._read_cache(cache_key)
            if cached:
                logger.info("Using cached call list (%d calls)", len(cached["calls"]))
                return [GongCallMetadata(**c) for c in cached["calls"]]

        all_calls: list[GongCallMetadata] = []
        cursor: Optional[str] = None

        while True:
            self._rate_limit()
            body: dict = {
                "filter": {
                    "fromDateTime": from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "toDateTime": to_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "primaryUserIds": user_ids,
                },
                "contentSelector": {
                    "exposedFields": {
                        "parties": True,
                    }
                },
            }
            if cursor:
                body["cursor"] = cursor

            logger.debug("POST /calls/extensive (users=%d)", len(user_ids))
            response = self._client.post("/calls/extensive", json=body)
            response.raise_for_status()
            data = response.json()

            for call in data.get("calls", []):
                meta = call.get("metaData", {})
                parties = call.get("parties", [])
                parsed = self._parse_call_metadata(meta, parties=parties)
                all_calls.append(parsed)

            cursor = data.get("records", {}).get("cursor")
            current_total = data.get("records", {}).get("totalRecords")
            if not cursor:
                break

            logger.info(
                "Fetched %d calls so far (total: %s), paginating...",
                len(all_calls),
                current_total or "unknown",
            )

        self._write_cache(cache_key, {
            "calls": [c.model_dump(mode="json") for c in all_calls]
        })
        logger.info("Fetched %d total calls from Gong", len(all_calls))
        return all_calls

    def get_call_details(
        self,
        call_ids: list[str],
        use_cache: bool = True,
    ) -> list[GongCallMetadata]:
        """Get detailed metadata for specific calls by ID.

        Uses POST /calls/extensive with callIds filter.
        Used by detail/export commands when you already have call IDs.
        """
        all_details: list[GongCallMetadata] = []
        batch_size = 100

        for i in range(0, len(call_ids), batch_size):
            batch = call_ids[i : i + batch_size]
            cache_key = self._cache_key("details", {"ids": sorted(batch)})

            if use_cache:
                cached = self._read_cache(cache_key)
                if cached:
                    all_details.extend(
                        [GongCallMetadata(**c) for c in cached["calls"]]
                    )
                    continue

            self._rate_limit()
            body = {
                "filter": {"callIds": batch},
                "contentSelector": {
                    "exposedFields": {"parties": True}
                },
            }
            response = self._client.post("/calls/extensive", json=body)
            response.raise_for_status()
            data = response.json()

            batch_calls: list[GongCallMetadata] = []
            for call in data.get("calls", []):
                meta = call.get("metaData", {})
                parties = call.get("parties", [])
                parsed = self._parse_call_metadata(meta, parties=parties)
                batch_calls.append(parsed)

            self._write_cache(
                cache_key,
                {"calls": [c.model_dump(mode="json") for c in batch_calls]},
            )
            all_details.extend(batch_calls)

        return all_details

    def get_transcripts(
        self,
        call_ids: list[str],
        use_cache: bool = True,
    ) -> list[GongTranscript]:
        """Get transcripts for specific calls.

        Uses POST /calls/transcript in batches of 50.
        """
        all_transcripts: list[GongTranscript] = []
        batch_size = 50

        for i in range(0, len(call_ids), batch_size):
            batch = call_ids[i : i + batch_size]
            cache_key = self._cache_key("transcripts", {"ids": sorted(batch)})

            if use_cache:
                cached = self._read_cache(cache_key)
                if cached:
                    all_transcripts.extend(
                        [GongTranscript(**t) for t in cached["transcripts"]]
                    )
                    continue

            self._rate_limit()
            body: dict = {"filter": {"callIds": batch}}
            cursor: Optional[str] = None

            batch_transcripts: list[GongTranscript] = []
            while True:
                if cursor:
                    body["cursor"] = cursor

                logger.debug("POST /calls/transcript batch=%d", len(batch))
                response = self._client.post("/calls/transcript", json=body)
                response.raise_for_status()
                data = response.json()

                for call_transcript in data.get("callTranscripts", []):
                    # Gong transcript structure: each entry in "transcript"
                    # is a speaker turn containing a nested "sentences" array.
                    all_sentences: list[TranscriptSentence] = []
                    for turn in call_transcript.get("transcript", []):
                        speaker_id = turn.get("speakerId")
                        topic = turn.get("topic")
                        for s in turn.get("sentences", []):
                            all_sentences.append(
                                TranscriptSentence(
                                    speaker_id=speaker_id,
                                    topic=topic,
                                    text=s.get("text", ""),
                                    start_time=s.get("start"),
                                    end_time=s.get("end"),
                                )
                            )
                    transcript = GongTranscript(
                        call_id=call_transcript.get("callId", ""),
                        sentences=all_sentences,
                    )
                    batch_transcripts.append(transcript)

                cursor = data.get("records", {}).get("cursor")
                if not cursor:
                    break

            self._write_cache(
                cache_key,
                {"transcripts": [t.model_dump(mode="json") for t in batch_transcripts]},
            )
            all_transcripts.extend(batch_transcripts)
            logger.info(
                "Fetched transcripts for %d/%d calls",
                len(all_transcripts),
                len(call_ids),
            )

        return all_transcripts

    def _parse_call_metadata(
        self,
        raw: dict,
        parties: Optional[list[dict]] = None,
    ) -> GongCallMetadata:
        """Parse raw Gong API call data into GongCallMetadata."""
        participants: list[GongParticipant] = []
        party_list = parties or raw.get("parties", raw.get("participants", []))
        for p in party_list:
            participants.append(
                GongParticipant(
                    name=p.get("name", p.get("displayName", "")),
                    email=p.get("emailAddress", p.get("email")),
                    title=p.get("title"),
                    user_id=p.get("userId", p.get("speakerId")),
                    affiliation=p.get("affiliation"),
                )
            )

        return GongCallMetadata(
            call_id=raw.get("id", raw.get("callId", "")),
            title=raw.get("title"),
            started=raw.get("started"),
            duration_seconds=raw.get("duration"),
            direction=raw.get("direction"),
            participants=participants,
            url=raw.get("url"),
            workspace_id=raw.get("workspaceId"),
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
