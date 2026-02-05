"""Embedding Generator Service.

Creates rich text representations and generates embeddings for
actions, widgets, and status patterns.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .pattern_extractor import FrequencyStats

logger = logging.getLogger(__name__)


# ============================================================================
# Embedding Models
# ============================================================================


class ActionEmbedding(BaseModel):
    """Embedding data for an action."""

    id: str = Field(..., description="Action ID")
    name: str = Field(..., description="Action name")
    rich_text: str = Field(..., description="Rich text representation")
    embedding: list[float] = Field(default_factory=list, description="Embedding vector")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    frequency: int = Field(default=0, description="Usage frequency")
    cooccurrences: list[str] = Field(
        default_factory=list, description="Common co-occurring widgets"
    )


class WidgetEmbedding(BaseModel):
    """Embedding data for a widget."""

    id: str = Field(..., description="Widget ID")
    name: str = Field(..., description="Widget name")
    rich_text: str = Field(..., description="Rich text representation")
    embedding: list[float] = Field(default_factory=list, description="Embedding vector")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    frequency: int = Field(default=0, description="Usage frequency")
    cooccurrences: list[str] = Field(
        default_factory=list, description="Common co-occurring actions"
    )


class StatusPatternEmbedding(BaseModel):
    """Embedding data for a status pattern."""

    id: str = Field(..., description="Pattern ID")
    name: str = Field(..., description="Pattern name")
    rich_text: str = Field(..., description="Rich text representation")
    embedding: list[float] = Field(default_factory=list, description="Embedding vector")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    frequency: int = Field(default=0, description="Usage frequency")


# ============================================================================
# Embedding Cache
# ============================================================================


@dataclass
class EmbeddingCache:
    """Simple file-based cache for embeddings."""

    cache_dir: Path
    _cache: dict = field(default_factory=dict)

    def __post_init__(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_cache()

    def _load_cache(self):
        """Load cache from disk."""
        cache_file = self.cache_dir / "embedding_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    self._cache = json.load(f)
                logger.debug(f"Loaded {len(self._cache)} cached embeddings")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self._cache = {}

    def _save_cache(self):
        """Save cache to disk."""
        cache_file = self.cache_dir / "embedding_cache.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(self._cache, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _get_key(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.md5(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[list[float]]:
        """Get cached embedding for text."""
        key = self._get_key(text)
        return self._cache.get(key)

    def set(self, text: str, embedding: list[float]):
        """Cache an embedding."""
        key = self._get_key(text)
        self._cache[key] = embedding
        # Save periodically (every 100 entries)
        if len(self._cache) % 100 == 0:
            self._save_cache()

    def save(self):
        """Force save cache to disk."""
        self._save_cache()


# ============================================================================
# Embedding Generator
# ============================================================================


class EmbeddingGenerator:
    """Service for generating embeddings with rich text context."""

    DEFAULT_MODEL = "text-embedding-3-small"
    DEFAULT_DIMENSION = 1536
    BATCH_SIZE = 100
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        dimension: int = DEFAULT_DIMENSION,
        cache_dir: Optional[Path] = None,
    ):
        """Initialize the embedding generator.

        Args:
            api_key: OpenAI API key (or will use OPENAI_API_KEY env var)
            model: Embedding model to use
            dimension: Embedding dimension
            cache_dir: Directory for caching embeddings
        """
        self.api_key = api_key
        self.model = model
        self.dimension = dimension
        self._client = None

        # Setup cache
        if cache_dir:
            self.cache = EmbeddingCache(cache_dir)
        else:
            self.cache = None

    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "openai package required. Install with: pip install openai"
                )
        return self._client

    def generate_action_embedding(
        self,
        action: dict,
        patterns: Optional[FrequencyStats] = None,
    ) -> ActionEmbedding:
        """Create embedding for an action.

        Args:
            action: Action data dict
            patterns: Optional frequency stats for enrichment

        Returns:
            ActionEmbedding with rich text and vector
        """
        action_id = action.get("id", "")
        action_name = action.get("name", "")

        # Build rich text
        rich_text = self._create_action_rich_text(action, patterns)

        # Get or generate embedding
        embedding = self._get_embedding(rich_text)

        # Build metadata
        frequency = 0
        cooccurrences = []
        if patterns:
            frequency = patterns.get_action_frequency(action_name)
            # Get top co-occurring widgets
            cooccurrences = self._get_top_cooccurring_widgets(action_name, patterns, n=5)

        return ActionEmbedding(
            id=action_id,
            name=action_name,
            rich_text=rich_text,
            embedding=embedding,
            metadata={
                "description": action.get("description", ""),
                "requires_template": action.get("requires_template", False),
                "template_type": action.get("template_type"),
                "use_cases": action.get("use_cases", []),
            },
            frequency=frequency,
            cooccurrences=cooccurrences,
        )

    def generate_widget_embedding(
        self,
        widget: dict,
        patterns: Optional[FrequencyStats] = None,
    ) -> WidgetEmbedding:
        """Create embedding for a widget.

        Args:
            widget: Widget data dict
            patterns: Optional frequency stats for enrichment

        Returns:
            WidgetEmbedding with rich text and vector
        """
        widget_id = widget.get("id", "")
        widget_name = widget.get("name", "")

        # Build rich text
        rich_text = self._create_widget_rich_text(widget, patterns)

        # Get or generate embedding
        embedding = self._get_embedding(rich_text)

        # Build metadata
        frequency = 0
        cooccurrences = []
        if patterns:
            frequency = patterns.get_widget_frequency(widget_name)
            # Get top co-occurring actions
            cooccurrences = self._get_top_cooccurring_actions(widget_name, patterns, n=5)

        return WidgetEmbedding(
            id=widget_id,
            name=widget_name,
            rich_text=rich_text,
            embedding=embedding,
            metadata={
                "description": widget.get("description", ""),
                "category": widget.get("category", ""),
                "typical_position": widget.get("typical_position", ""),
                "use_cases": widget.get("use_cases", []),
            },
            frequency=frequency,
            cooccurrences=cooccurrences,
        )

    def generate_status_pattern_embedding(
        self,
        pattern: dict,
        flows: Optional[list] = None,
    ) -> StatusPatternEmbedding:
        """Create embedding for a status pattern.

        Args:
            pattern: Status pattern data dict
            flows: Optional status flow data for enrichment

        Returns:
            StatusPatternEmbedding with rich text and vector
        """
        pattern_id = pattern.get("id", "")
        pattern_name = pattern.get("name", "")

        # Build rich text
        rich_text = self._create_status_pattern_rich_text(pattern, flows)

        # Get or generate embedding
        embedding = self._get_embedding(rich_text)

        # Calculate frequency from flows
        frequency = 0
        if flows:
            for flow in flows:
                # Check if any typical status name appears in the flow
                typical_names = pattern.get("typical_status_names", [])
                for name in typical_names:
                    if name.lower() in [s.lower() for s in flow.sequence]:
                        frequency += flow.count

        return StatusPatternEmbedding(
            id=pattern_id,
            name=pattern_name,
            rich_text=rich_text,
            embedding=embedding,
            metadata={
                "description": pattern.get("description", ""),
                "typical_status_names": pattern.get("typical_status_names", []),
                "typical_actions": pattern.get("typical_actions", []),
                "typical_widgets": pattern.get("typical_widgets", []),
            },
            frequency=frequency,
        )

    def _create_action_rich_text(
        self,
        action: dict,
        patterns: Optional[FrequencyStats] = None,
    ) -> str:
        """Generate descriptive rich text for an action.

        Args:
            action: Action data dict
            patterns: Optional frequency stats

        Returns:
            Rich text string for embedding
        """
        parts = []

        # Name and description
        name = action.get("name", "")
        parts.append(f"Action: {name}")

        description = action.get("description", "")
        if description:
            parts.append(f"Description: {description}")

        # Use cases
        use_cases = action.get("use_cases", [])
        if use_cases:
            parts.append(f"Use cases: {', '.join(use_cases)}")

        # Common phrases (important for semantic matching)
        phrases = action.get("common_phrases", [])
        if phrases:
            parts.append(f"Common phrases: {', '.join(phrases)}")

        # Template info
        if action.get("requires_template"):
            template_type = action.get("template_type", "template")
            parts.append(f"Requires {template_type}")

        # Production usage context
        if patterns:
            freq = patterns.get_action_frequency(name)
            if freq > 0:
                parts.append(f"Used in {freq} workflow configurations")

            # Add co-occurrence context
            top_widgets = self._get_top_cooccurring_widgets(name, patterns, n=3)
            if top_widgets:
                parts.append(f"Often paired with widgets: {', '.join(top_widgets)}")

        return ". ".join(parts)

    def _create_widget_rich_text(
        self,
        widget: dict,
        patterns: Optional[FrequencyStats] = None,
    ) -> str:
        """Generate descriptive rich text for a widget.

        Args:
            widget: Widget data dict
            patterns: Optional frequency stats

        Returns:
            Rich text string for embedding
        """
        parts = []

        # Name and description
        name = widget.get("name", "")
        parts.append(f"Widget: {name}")

        description = widget.get("description", "")
        if description:
            parts.append(f"Description: {description}")

        # Category and position
        category = widget.get("category", "")
        if category:
            parts.append(f"Category: {category}")

        position = widget.get("typical_position", "")
        if position:
            parts.append(f"Typically displayed at: {position}")

        # Use cases
        use_cases = widget.get("use_cases", [])
        if use_cases:
            parts.append(f"Use cases: {', '.join(use_cases)}")

        # Common phrases
        phrases = widget.get("common_phrases", [])
        if phrases:
            parts.append(f"Common phrases: {', '.join(phrases)}")

        # Always recommended
        if widget.get("recommended_always"):
            parts.append("Recommended for all statuses")

        # Production usage context
        if patterns:
            freq = patterns.get_widget_frequency(name)
            total = patterns.total_workflows
            if freq > 0 and total > 0:
                pct = (freq / total) * 100
                parts.append(f"Appears in {pct:.0f}% of workflows")

            # Add co-occurrence context
            top_actions = self._get_top_cooccurring_actions(name, patterns, n=3)
            if top_actions:
                parts.append(f"Typically shown with actions: {', '.join(top_actions)}")

        return ". ".join(parts)

    def _create_status_pattern_rich_text(
        self,
        pattern: dict,
        flows: Optional[list] = None,
    ) -> str:
        """Generate descriptive rich text for a status pattern.

        Args:
            pattern: Status pattern data dict
            flows: Optional status flow data

        Returns:
            Rich text string for embedding
        """
        parts = []

        # Name and description
        name = pattern.get("name", "")
        parts.append(f"Status Pattern: {name}")

        description = pattern.get("description", "")
        if description:
            parts.append(f"Description: {description}")

        # Typical status names
        typical_names = pattern.get("typical_status_names", [])
        if typical_names:
            parts.append(f"Typical status names: {', '.join(typical_names)}")

        # Typical actions
        typical_actions = pattern.get("typical_actions", [])
        if typical_actions:
            # Extract just the action names from IDs
            action_names = [a.split(":")[-1].replace("_", " ").title() for a in typical_actions]
            parts.append(f"Typical actions: {', '.join(action_names)}")

        # Typical widgets
        typical_widgets = pattern.get("typical_widgets", [])
        if typical_widgets:
            widget_names = [w.split(":")[-1].replace("_", " ").title() for w in typical_widgets]
            parts.append(f"Typical widgets: {', '.join(widget_names)}")

        # Instructions
        instructions = pattern.get("typical_instructions", "")
        if instructions:
            parts.append(f"Typical instructions: {instructions}")

        # Add flow context
        if flows:
            # Find flows that include this pattern's typical names
            matching_flows = 0
            for flow in flows:
                for typical_name in typical_names:
                    if any(typical_name.lower() in s.lower() for s in flow.sequence):
                        matching_flows += flow.count
                        break
            if matching_flows > 0:
                parts.append(f"Found in {matching_flows} workflow configurations")

        return ". ".join(parts)

    def _get_embedding(self, text: str) -> list[float]:
        """Get embedding from cache or API.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Check cache
        if self.cache:
            cached = self.cache.get(text)
            if cached:
                return cached

        # Generate embedding
        embedding = self._call_embedding_api(text)

        # Cache result
        if self.cache and embedding:
            self.cache.set(text, embedding)

        return embedding

    def _call_embedding_api(self, text: str) -> list[float]:
        """Call the embedding API with retry logic.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        import time

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text,
                    dimensions=self.dimension,
                )
                return response.data[0].embedding
            except Exception as e:
                logger.warning(f"Embedding API attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"Failed to generate embedding after {self.MAX_RETRIES} attempts")
                    return []

        return []

    def _get_top_cooccurring_widgets(
        self,
        action_name: str,
        patterns: FrequencyStats,
        n: int = 5,
    ) -> list[str]:
        """Get top widgets that co-occur with an action.

        Args:
            action_name: Action name
            patterns: Frequency stats
            n: Number of top widgets to return

        Returns:
            List of widget names
        """
        widget_counts = []
        for (action, widget), count in patterns.action_widget_pairs.items():
            if action == action_name:
                widget_counts.append((widget, count))

        widget_counts.sort(key=lambda x: -x[1])
        return [w for w, _ in widget_counts[:n]]

    def _get_top_cooccurring_actions(
        self,
        widget_name: str,
        patterns: FrequencyStats,
        n: int = 5,
    ) -> list[str]:
        """Get top actions that co-occur with a widget.

        Args:
            widget_name: Widget name
            patterns: Frequency stats
            n: Number of top actions to return

        Returns:
            List of action names
        """
        action_counts = []
        for (action, widget), count in patterns.action_widget_pairs.items():
            if widget == widget_name:
                action_counts.append((action, count))

        action_counts.sort(key=lambda x: -x[1])
        return [a for a, _ in action_counts[:n]]

    async def generate_batch_embeddings(
        self,
        texts: list[str],
        batch_size: int = BATCH_SIZE,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for API calls

        Returns:
            List of embedding vectors
        """
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            logger.info(f"Processing embedding batch {i // batch_size + 1}")

            batch_embeddings = []
            for text in batch:
                embedding = self._get_embedding(text)
                batch_embeddings.append(embedding)

            embeddings.extend(batch_embeddings)

            # Small delay between batches
            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)

        return embeddings

    def generate_all_embeddings(
        self,
        actions: list[dict],
        widgets: list[dict],
        status_patterns: list[dict],
        patterns: Optional[FrequencyStats] = None,
        flows: Optional[list] = None,
    ) -> dict:
        """Generate embeddings for all entity types.

        Args:
            actions: List of action dicts
            widgets: List of widget dicts
            status_patterns: List of status pattern dicts
            patterns: Optional frequency stats
            flows: Optional status flow data

        Returns:
            Dict with action_embeddings, widget_embeddings, status_pattern_embeddings
        """
        logger.info(
            f"Generating embeddings for {len(actions)} actions, "
            f"{len(widgets)} widgets, {len(status_patterns)} patterns"
        )

        action_embeddings = []
        for action in actions:
            try:
                emb = self.generate_action_embedding(action, patterns)
                action_embeddings.append(emb)
            except Exception as e:
                logger.error(f"Failed to generate embedding for action {action.get('id')}: {e}")

        widget_embeddings = []
        for widget in widgets:
            try:
                emb = self.generate_widget_embedding(widget, patterns)
                widget_embeddings.append(emb)
            except Exception as e:
                logger.error(f"Failed to generate embedding for widget {widget.get('id')}: {e}")

        pattern_embeddings = []
        for pattern in status_patterns:
            try:
                emb = self.generate_status_pattern_embedding(pattern, flows)
                pattern_embeddings.append(emb)
            except Exception as e:
                logger.error(f"Failed to generate embedding for pattern {pattern.get('id')}: {e}")

        # Save cache
        if self.cache:
            self.cache.save()

        logger.info(
            f"Generated {len(action_embeddings)} action, "
            f"{len(widget_embeddings)} widget, "
            f"{len(pattern_embeddings)} pattern embeddings"
        )

        return {
            "action_embeddings": action_embeddings,
            "widget_embeddings": widget_embeddings,
            "status_pattern_embeddings": pattern_embeddings,
        }
