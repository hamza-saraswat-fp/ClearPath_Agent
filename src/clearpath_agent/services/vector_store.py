"""Supabase Vector Store Service.

Handles upserting embeddings into Supabase pgvector for similarity search.
"""

import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .embedding_generator import (
    ActionEmbedding,
    StatusPatternEmbedding,
    WidgetEmbedding,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Search Result Model
# ============================================================================


class SearchResult(BaseModel):
    """Result from vector similarity search."""

    id: str = Field(..., description="Entity ID")
    name: str = Field(..., description="Entity name")
    entity_type: str = Field(..., description="Type: action, widget, or status_pattern")
    similarity: float = Field(..., description="Cosine similarity score")
    metadata: dict = Field(default_factory=dict, description="Entity metadata")
    rich_text: str = Field(default="", description="Rich text representation")


# ============================================================================
# Vector Store Service
# ============================================================================


class VectorStore:
    """Service for managing embeddings in Supabase pgvector."""

    TABLE_PREFIX = "clearpath_"
    BATCH_SIZE = 500

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        table_prefix: str = TABLE_PREFIX,
    ):
        """Initialize the vector store.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
            table_prefix: Prefix for table names
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.table_prefix = table_prefix
        self._client = None

    @property
    def client(self):
        """Lazy-load Supabase client."""
        if self._client is None:
            try:
                from supabase import create_client

                self._client = create_client(self.supabase_url, self.supabase_key)
            except ImportError:
                raise ImportError(
                    "supabase package required. Install with: pip install supabase"
                )
        return self._client

    @property
    def actions_table(self) -> str:
        """Actions table name."""
        return f"{self.table_prefix}actions"

    @property
    def widgets_table(self) -> str:
        """Widgets table name."""
        return f"{self.table_prefix}widgets"

    @property
    def status_patterns_table(self) -> str:
        """Status patterns table name."""
        return f"{self.table_prefix}status_patterns"

    def initialize_schema(self):
        """Create tables and indexes if they don't exist.

        Note: This should be run via Supabase SQL editor or migrations.
        This method provides the SQL for reference.
        """
        sql_statements = self._get_schema_sql()
        logger.info("Schema SQL generated. Run these in Supabase SQL editor:")
        for stmt in sql_statements:
            logger.info(stmt)
        return sql_statements

    def _get_schema_sql(self) -> list[str]:
        """Get SQL statements to create the schema."""
        statements = []

        # Enable pgvector extension
        statements.append("CREATE EXTENSION IF NOT EXISTS vector;")

        # Actions table
        statements.append(f"""
CREATE TABLE IF NOT EXISTS {self.actions_table} (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    rich_text TEXT,
    embedding vector(1536),
    metadata JSONB DEFAULT '{{}}',
    frequency INT DEFAULT 0,
    cooccurrences TEXT[] DEFAULT '{{}}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
""")

        # Widgets table
        statements.append(f"""
CREATE TABLE IF NOT EXISTS {self.widgets_table} (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    rich_text TEXT,
    embedding vector(1536),
    metadata JSONB DEFAULT '{{}}',
    frequency INT DEFAULT 0,
    cooccurrences TEXT[] DEFAULT '{{}}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
""")

        # Status patterns table
        statements.append(f"""
CREATE TABLE IF NOT EXISTS {self.status_patterns_table} (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    rich_text TEXT,
    embedding vector(1536),
    metadata JSONB DEFAULT '{{}}',
    frequency INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
""")

        # Indexes for vector similarity search
        statements.append(f"""
CREATE INDEX IF NOT EXISTS {self.actions_table}_embedding_idx
ON {self.actions_table} USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
""")

        statements.append(f"""
CREATE INDEX IF NOT EXISTS {self.widgets_table}_embedding_idx
ON {self.widgets_table} USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
""")

        statements.append(f"""
CREATE INDEX IF NOT EXISTS {self.status_patterns_table}_embedding_idx
ON {self.status_patterns_table} USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
""")

        # Name indexes for text search
        statements.append(f"""
CREATE INDEX IF NOT EXISTS {self.actions_table}_name_idx
ON {self.actions_table} (name);
""")

        statements.append(f"""
CREATE INDEX IF NOT EXISTS {self.widgets_table}_name_idx
ON {self.widgets_table} (name);
""")

        statements.append(f"""
CREATE INDEX IF NOT EXISTS {self.status_patterns_table}_name_idx
ON {self.status_patterns_table} (name);
""")

        return statements

    def upsert_action_embeddings(
        self,
        embeddings: list[ActionEmbedding],
        batch_size: int = BATCH_SIZE,
    ) -> int:
        """Insert or update action embeddings.

        Args:
            embeddings: List of ActionEmbedding objects
            batch_size: Batch size for upserts

        Returns:
            Number of records upserted
        """
        if not embeddings:
            return 0

        upserted = 0
        for i in range(0, len(embeddings), batch_size):
            batch = embeddings[i : i + batch_size]

            records = []
            for emb in batch:
                record = {
                    "id": emb.id,
                    "name": emb.name,
                    "description": emb.metadata.get("description", ""),
                    "rich_text": emb.rich_text,
                    "embedding": emb.embedding,
                    "metadata": emb.metadata,  # Pass dict directly for JSONB column
                    "frequency": emb.frequency,
                    "cooccurrences": emb.cooccurrences,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                records.append(record)

            try:
                result = (
                    self.client.table(self.actions_table)
                    .upsert(records, on_conflict="id")
                    .execute()
                )
                upserted += len(batch)
                logger.info(f"Upserted {upserted}/{len(embeddings)} actions")
            except Exception as e:
                logger.error(f"Failed to upsert action batch: {e}")

        return upserted

    def upsert_widget_embeddings(
        self,
        embeddings: list[WidgetEmbedding],
        batch_size: int = BATCH_SIZE,
    ) -> int:
        """Insert or update widget embeddings.

        Args:
            embeddings: List of WidgetEmbedding objects
            batch_size: Batch size for upserts

        Returns:
            Number of records upserted
        """
        if not embeddings:
            return 0

        upserted = 0
        for i in range(0, len(embeddings), batch_size):
            batch = embeddings[i : i + batch_size]

            records = []
            for emb in batch:
                record = {
                    "id": emb.id,
                    "name": emb.name,
                    "description": emb.metadata.get("description", ""),
                    "rich_text": emb.rich_text,
                    "embedding": emb.embedding,
                    "metadata": emb.metadata,  # Pass dict directly for JSONB column
                    "frequency": emb.frequency,
                    "cooccurrences": emb.cooccurrences,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                records.append(record)

            try:
                result = (
                    self.client.table(self.widgets_table)
                    .upsert(records, on_conflict="id")
                    .execute()
                )
                upserted += len(batch)
                logger.info(f"Upserted {upserted}/{len(embeddings)} widgets")
            except Exception as e:
                logger.error(f"Failed to upsert widget batch: {e}")

        return upserted

    def upsert_status_pattern_embeddings(
        self,
        embeddings: list[StatusPatternEmbedding],
        batch_size: int = BATCH_SIZE,
    ) -> int:
        """Insert or update status pattern embeddings.

        Args:
            embeddings: List of StatusPatternEmbedding objects
            batch_size: Batch size for upserts

        Returns:
            Number of records upserted
        """
        if not embeddings:
            return 0

        upserted = 0
        for i in range(0, len(embeddings), batch_size):
            batch = embeddings[i : i + batch_size]

            records = []
            for emb in batch:
                record = {
                    "id": emb.id,
                    "name": emb.name,
                    "description": emb.metadata.get("description", ""),
                    "rich_text": emb.rich_text,
                    "embedding": emb.embedding,
                    "metadata": emb.metadata,  # Pass dict directly for JSONB column
                    "frequency": emb.frequency,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                records.append(record)

            try:
                result = (
                    self.client.table(self.status_patterns_table)
                    .upsert(records, on_conflict="id")
                    .execute()
                )
                upserted += len(batch)
                logger.info(f"Upserted {upserted}/{len(embeddings)} status patterns")
            except Exception as e:
                logger.error(f"Failed to upsert status pattern batch: {e}")

        return upserted

    def search_similar(
        self,
        query_embedding: list[float],
        entity_type: str,
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> list[SearchResult]:
        """Search for similar entities using vector similarity.

        Args:
            query_embedding: Query embedding vector
            entity_type: "action", "widget", or "status_pattern"
            limit: Maximum results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of SearchResult objects
        """
        table_map = {
            "action": self.actions_table,
            "widget": self.widgets_table,
            "status_pattern": self.status_patterns_table,
        }

        table = table_map.get(entity_type)
        if not table:
            raise ValueError(f"Invalid entity_type: {entity_type}")

        # Use Supabase RPC for vector similarity search
        # Note: This requires a custom function in Supabase
        try:
            # Format embedding as string for Supabase
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            # Call the search RPC function
            result = self.client.rpc(
                f"search_{entity_type}s",
                {
                    "query_embedding": embedding_str,
                    "match_threshold": min_similarity,
                    "match_count": limit,
                },
            ).execute()

            results = []
            for row in result.data:
                results.append(
                    SearchResult(
                        id=row["id"],
                        name=row["name"],
                        entity_type=entity_type,
                        similarity=row.get("similarity", 0),
                        metadata=row.get("metadata") or {},  # Supabase returns JSONB as dict
                        rich_text=row.get("rich_text", ""),
                    )
                )

            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def search_by_name(
        self,
        name: str,
        entity_type: str,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search for entities by name (text search).

        Args:
            name: Name to search for
            entity_type: "action", "widget", or "status_pattern"
            limit: Maximum results to return

        Returns:
            List of SearchResult objects
        """
        table_map = {
            "action": self.actions_table,
            "widget": self.widgets_table,
            "status_pattern": self.status_patterns_table,
        }

        table = table_map.get(entity_type)
        if not table:
            raise ValueError(f"Invalid entity_type: {entity_type}")

        try:
            result = (
                self.client.table(table)
                .select("*")
                .ilike("name", f"%{name}%")
                .limit(limit)
                .execute()
            )

            results = []
            for row in result.data:
                results.append(
                    SearchResult(
                        id=row["id"],
                        name=row["name"],
                        entity_type=entity_type,
                        similarity=1.0,  # Exact match
                        metadata=row.get("metadata") or {},  # Supabase returns JSONB as dict
                        rich_text=row.get("rich_text", ""),
                    )
                )

            return results

        except Exception as e:
            logger.error(f"Name search failed: {e}")
            return []

    def get_by_id(
        self,
        entity_id: str,
        entity_type: str,
    ) -> Optional[dict]:
        """Get an entity by its ID.

        Args:
            entity_id: Entity ID
            entity_type: "action", "widget", or "status_pattern"

        Returns:
            Entity dict or None
        """
        table_map = {
            "action": self.actions_table,
            "widget": self.widgets_table,
            "status_pattern": self.status_patterns_table,
        }

        table = table_map.get(entity_type)
        if not table:
            raise ValueError(f"Invalid entity_type: {entity_type}")

        try:
            result = (
                self.client.table(table)
                .select("*")
                .eq("id", entity_id)
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            return None

    def get_all(
        self,
        entity_type: str,
        limit: int = 1000,
    ) -> list[dict]:
        """Get all entities of a type.

        Args:
            entity_type: "action", "widget", or "status_pattern"
            limit: Maximum results

        Returns:
            List of entity dicts
        """
        table_map = {
            "action": self.actions_table,
            "widget": self.widgets_table,
            "status_pattern": self.status_patterns_table,
        }

        table = table_map.get(entity_type)
        if not table:
            raise ValueError(f"Invalid entity_type: {entity_type}")

        try:
            result = self.client.table(table).select("*").limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get all {entity_type}s: {e}")
            return []

    def delete_all(self, entity_type: str) -> bool:
        """Delete all entities of a type.

        Args:
            entity_type: "action", "widget", or "status_pattern"

        Returns:
            True if successful
        """
        table_map = {
            "action": self.actions_table,
            "widget": self.widgets_table,
            "status_pattern": self.status_patterns_table,
        }

        table = table_map.get(entity_type)
        if not table:
            raise ValueError(f"Invalid entity_type: {entity_type}")

        try:
            # Delete all rows (use neq to match all)
            self.client.table(table).delete().neq("id", "").execute()
            logger.info(f"Deleted all records from {table}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete all from {table}: {e}")
            return False

    def get_stats(self) -> dict:
        """Get statistics about stored embeddings.

        Returns:
            Dict with counts per entity type
        """
        stats = {}

        for entity_type, table in [
            ("actions", self.actions_table),
            ("widgets", self.widgets_table),
            ("status_patterns", self.status_patterns_table),
        ]:
            try:
                result = (
                    self.client.table(table)
                    .select("id", count="exact")
                    .execute()
                )
                stats[entity_type] = result.count or 0
            except Exception as e:
                logger.error(f"Failed to get count for {table}: {e}")
                stats[entity_type] = 0

        return stats

    def get_search_function_sql(self) -> str:
        """Get SQL for creating the vector search function.

        This function should be created in Supabase SQL editor.
        """
        return """
-- Search function for actions
CREATE OR REPLACE FUNCTION search_actions(
    query_embedding vector(1536),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id text,
    name text,
    description text,
    rich_text text,
    metadata jsonb,
    frequency int,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id,
        a.name,
        a.description,
        a.rich_text,
        a.metadata,
        a.frequency,
        1 - (a.embedding <=> query_embedding) AS similarity
    FROM clearpath_actions a
    WHERE 1 - (a.embedding <=> query_embedding) > match_threshold
    ORDER BY a.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Search function for widgets
CREATE OR REPLACE FUNCTION search_widgets(
    query_embedding vector(1536),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id text,
    name text,
    description text,
    rich_text text,
    metadata jsonb,
    frequency int,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        w.id,
        w.name,
        w.description,
        w.rich_text,
        w.metadata,
        w.frequency,
        1 - (w.embedding <=> query_embedding) AS similarity
    FROM clearpath_widgets w
    WHERE 1 - (w.embedding <=> query_embedding) > match_threshold
    ORDER BY w.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Search function for status patterns
CREATE OR REPLACE FUNCTION search_status_patterns(
    query_embedding vector(1536),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id text,
    name text,
    description text,
    rich_text text,
    metadata jsonb,
    frequency int,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.id,
        s.name,
        s.description,
        s.rich_text,
        s.metadata,
        s.frequency,
        1 - (s.embedding <=> query_embedding) AS similarity
    FROM clearpath_status_patterns s
    WHERE 1 - (s.embedding <=> query_embedding) > match_threshold
    ORDER BY s.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""
