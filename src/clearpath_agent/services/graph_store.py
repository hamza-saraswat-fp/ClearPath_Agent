"""Neo4j Graph Store Service.

Builds and manages the knowledge graph in Neo4j for relationship-based queries.
"""

import logging
from typing import Optional

from .pattern_extractor import CooccurrencePattern, StatusFlow

logger = logging.getLogger(__name__)


# ============================================================================
# Neo4j Graph Store Service
# ============================================================================


class GraphStore:
    """Service for managing the knowledge graph in Neo4j."""

    BATCH_SIZE = 500

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
    ):
        """Initialize the graph store.

        Args:
            uri: Neo4j connection URI (e.g., bolt://localhost:7687)
            user: Neo4j username
            password: Neo4j password
            database: Database name
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self._driver = None

    @property
    def driver(self):
        """Lazy-load Neo4j driver."""
        if self._driver is None:
            try:
                from neo4j import GraphDatabase

                self._driver = GraphDatabase.driver(
                    self.uri, auth=(self.user, self.password)
                )
            except ImportError:
                raise ImportError(
                    "neo4j package required. Install with: pip install neo4j"
                )
        return self._driver

    def close(self):
        """Close the driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def initialize_schema(self):
        """Create constraints and indexes in Neo4j."""
        with self.driver.session(database=self.database) as session:
            # Create constraints for unique IDs
            constraints = [
                "CREATE CONSTRAINT action_id IF NOT EXISTS FOR (a:Action) REQUIRE a.id IS UNIQUE",
                "CREATE CONSTRAINT widget_id IF NOT EXISTS FOR (w:Widget) REQUIRE w.id IS UNIQUE",
                "CREATE CONSTRAINT status_id IF NOT EXISTS FOR (s:Status) REQUIRE s.id IS UNIQUE",
                "CREATE CONSTRAINT status_pattern_id IF NOT EXISTS FOR (p:StatusPattern) REQUIRE p.id IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.debug(f"Created constraint: {constraint}")
                except Exception as e:
                    logger.warning(f"Constraint may already exist: {e}")

            # Create indexes for name searches
            indexes = [
                "CREATE INDEX action_name IF NOT EXISTS FOR (a:Action) ON (a.name)",
                "CREATE INDEX widget_name IF NOT EXISTS FOR (w:Widget) ON (w.name)",
                "CREATE INDEX status_name IF NOT EXISTS FOR (s:Status) ON (s.name)",
                "CREATE INDEX status_pattern_name IF NOT EXISTS FOR (p:StatusPattern) ON (p.name)",
            ]

            for index in indexes:
                try:
                    session.run(index)
                    logger.debug(f"Created index: {index}")
                except Exception as e:
                    logger.warning(f"Index may already exist: {e}")

        logger.info("Neo4j schema initialized")

    def create_action_nodes(self, actions: list[dict]) -> int:
        """Create Action nodes in the graph.

        Args:
            actions: List of action dicts from seed data

        Returns:
            Number of nodes created/updated
        """
        if not actions:
            return 0

        with self.driver.session(database=self.database) as session:
            count = 0
            for action in actions:
                try:
                    session.run(
                        """
                        MERGE (a:Action {id: $id})
                        SET a.name = $name,
                            a.description = $description,
                            a.requires_template = $requires_template,
                            a.template_type = $template_type,
                            a.frequency = $frequency
                        """,
                        id=action.get("id", ""),
                        name=action.get("name", ""),
                        description=action.get("description", ""),
                        requires_template=action.get("requires_template", False),
                        template_type=action.get("template_type"),
                        frequency=action.get("frequency", 0),
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to create action node: {e}")

            logger.info(f"Created/updated {count} Action nodes")
            return count

    def create_widget_nodes(self, widgets: list[dict]) -> int:
        """Create Widget nodes in the graph.

        Args:
            widgets: List of widget dicts from seed data

        Returns:
            Number of nodes created/updated
        """
        if not widgets:
            return 0

        with self.driver.session(database=self.database) as session:
            count = 0
            for widget in widgets:
                try:
                    session.run(
                        """
                        MERGE (w:Widget {id: $id})
                        SET w.name = $name,
                            w.description = $description,
                            w.category = $category,
                            w.typical_position = $typical_position,
                            w.recommended_always = $recommended_always,
                            w.frequency = $frequency
                        """,
                        id=widget.get("id", ""),
                        name=widget.get("name", ""),
                        description=widget.get("description", ""),
                        category=widget.get("category", ""),
                        typical_position=widget.get("typical_position", ""),
                        recommended_always=widget.get("recommended_always", False),
                        frequency=widget.get("frequency", 0),
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to create widget node: {e}")

            logger.info(f"Created/updated {count} Widget nodes")
            return count

    def create_status_nodes(self, statuses: list[dict]) -> int:
        """Create Status nodes in the graph.

        Args:
            statuses: List of status dicts

        Returns:
            Number of nodes created/updated
        """
        if not statuses:
            return 0

        with self.driver.session(database=self.database) as session:
            count = 0
            for status in statuses:
                try:
                    status_id = f"status:{status.get('name', '').lower().replace(' ', '_')}"
                    session.run(
                        """
                        MERGE (s:Status {id: $id})
                        SET s.name = $name,
                            s.category = $category,
                            s.frequency = $frequency
                        """,
                        id=status_id,
                        name=status.get("name", ""),
                        category=status.get("category", ""),
                        frequency=status.get("frequency", 0),
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to create status node: {e}")

            logger.info(f"Created/updated {count} Status nodes")
            return count

    def create_status_pattern_nodes(self, patterns: list[dict]) -> int:
        """Create StatusPattern nodes in the graph.

        Args:
            patterns: List of status pattern dicts from seed data

        Returns:
            Number of nodes created/updated
        """
        if not patterns:
            return 0

        with self.driver.session(database=self.database) as session:
            count = 0
            for pattern in patterns:
                try:
                    session.run(
                        """
                        MERGE (p:StatusPattern {id: $id})
                        SET p.name = $name,
                            p.description = $description,
                            p.typical_status_names = $typical_status_names,
                            p.frequency = $frequency
                        """,
                        id=pattern.get("id", ""),
                        name=pattern.get("name", ""),
                        description=pattern.get("description", ""),
                        typical_status_names=pattern.get("typical_status_names", []),
                        frequency=pattern.get("frequency", 0),
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to create status pattern node: {e}")

            logger.info(f"Created/updated {count} StatusPattern nodes")
            return count

    def create_status_flow_edges(self, flows: list[StatusFlow]) -> int:
        """Create NEXT_STATUS relationships from status flows.

        For each flow sequence [A, B, C], creates edges:
          (A)-[:NEXT_STATUS {count: N}]->(B)
          (B)-[:NEXT_STATUS {count: N}]->(C)

        Args:
            flows: List of StatusFlow objects from pattern extraction

        Returns:
            Number of relationships created/updated
        """
        if not flows:
            return 0

        with self.driver.session(database=self.database) as session:
            count = 0
            for flow in flows:
                if len(flow.sequence) < 2:
                    continue

                # Create edges between consecutive statuses
                for i in range(len(flow.sequence) - 1):
                    from_status = flow.sequence[i]
                    to_status = flow.sequence[i + 1]

                    # Generate status IDs matching create_status_nodes() format
                    from_id = f"status:{from_status.lower().replace(' ', '_')}"
                    to_id = f"status:{to_status.lower().replace(' ', '_')}"

                    try:
                        session.run(
                            """
                            MATCH (s1:Status {id: $from_id})
                            MATCH (s2:Status {id: $to_id})
                            MERGE (s1)-[r:NEXT_STATUS]->(s2)
                            SET r.count = COALESCE(r.count, 0) + $count,
                                r.flow_names = COALESCE(r.flow_names, []) + $flow_names
                            """,
                            from_id=from_id,
                            to_id=to_id,
                            count=flow.count,
                            flow_names=flow.flow_names,
                        )
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to create NEXT_STATUS edge {from_status} -> {to_status}: {e}")

            logger.info(f"Created/updated {count} NEXT_STATUS relationships")
            return count

    def create_status_action_edges(self, workflows: list) -> int:
        """Create HAS_ACTION relationships from production workflows.

        For each action button in production data, creates:
          (Status)-[:HAS_ACTION {role, order, count}]->(Action)

        Args:
            workflows: List of ParsedWorkflow objects

        Returns:
            Number of relationships created/updated
        """
        if not workflows:
            return 0

        # Aggregate action buttons by (status_name, action_type, role)
        edge_data: dict[tuple, dict] = {}
        for workflow in workflows:
            for button in workflow.action_buttons:
                status_id = f"status:{button.status_name.lower().replace(' ', '_')}"
                action_id = f"action:{button.action_type.lower().replace(' ', '_')}"
                role = button.user_role.value if hasattr(button.user_role, "value") else str(button.user_role)

                key = (status_id, action_id, role)
                if key not in edge_data:
                    edge_data[key] = {
                        "status_id": status_id,
                        "action_id": action_id,
                        "role": role,
                        "order": button.order,
                        "count": 0,
                    }
                edge_data[key]["count"] += 1

        with self.driver.session(database=self.database) as session:
            count = 0
            for edge in edge_data.values():
                try:
                    session.run(
                        """
                        MATCH (s:Status {id: $status_id})
                        MATCH (a:Action {id: $action_id})
                        MERGE (s)-[r:HAS_ACTION {role: $role}]->(a)
                        SET r.order = $order,
                            r.count = COALESCE(r.count, 0) + $count
                        """,
                        status_id=edge["status_id"],
                        action_id=edge["action_id"],
                        role=edge["role"],
                        order=edge["order"],
                        count=edge["count"],
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to create HAS_ACTION edge: {e}")

            logger.info(f"Created/updated {count} HAS_ACTION relationships")
            return count

    def create_status_widget_edges(self, workflows: list) -> int:
        """Create HAS_WIDGET relationships from production workflows.

        For each focus view in production data, creates:
          (Status)-[:HAS_WIDGET {role, order, count}]->(Widget)

        Args:
            workflows: List of ParsedWorkflow objects

        Returns:
            Number of relationships created/updated
        """
        if not workflows:
            return 0

        # Aggregate focus views by (status_name, widget, role)
        edge_data: dict[tuple, dict] = {}
        for workflow in workflows:
            for fv in workflow.focus_views:
                status_id = f"status:{fv.status_name.lower().replace(' ', '_')}"
                role = fv.user_role.value if hasattr(fv.user_role, "value") else str(fv.user_role)

                for idx, widget_name in enumerate(fv.widgets):
                    widget_id = f"widget:{widget_name.lower().replace(' ', '_')}"

                    key = (status_id, widget_id, role)
                    if key not in edge_data:
                        edge_data[key] = {
                            "status_id": status_id,
                            "widget_id": widget_id,
                            "role": role,
                            "order": idx,
                            "count": 0,
                        }
                    edge_data[key]["count"] += 1

        with self.driver.session(database=self.database) as session:
            count = 0
            for edge in edge_data.values():
                try:
                    session.run(
                        """
                        MATCH (s:Status {id: $status_id})
                        MATCH (w:Widget {id: $widget_id})
                        MERGE (s)-[r:HAS_WIDGET {role: $role}]->(w)
                        SET r.order = $order,
                            r.count = COALESCE(r.count, 0) + $count
                        """,
                        status_id=edge["status_id"],
                        widget_id=edge["widget_id"],
                        role=edge["role"],
                        order=edge["order"],
                        count=edge["count"],
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to create HAS_WIDGET edge: {e}")

            logger.info(f"Created/updated {count} HAS_WIDGET relationships")
            return count

    def create_relationships(
        self,
        relationships: list[dict],
        patterns: Optional[list[CooccurrencePattern]] = None,
    ) -> int:
        """Create relationships (edges) in the graph.

        Args:
            relationships: List of relationship dicts from seed data
            patterns: Optional production co-occurrence patterns

        Returns:
            Number of relationships created/updated
        """
        if not relationships:
            return 0

        with self.driver.session(database=self.database) as session:
            count = 0
            for rel in relationships:
                try:
                    source = rel.get("source", "")
                    target = rel.get("target", "")
                    relation = rel.get("relation", "RELATED_TO")
                    weight = rel.get("weight", 0.5)
                    reason = rel.get("reason", "")

                    # Determine source and target node types
                    source_type = self._get_node_type(source)
                    target_type = self._get_node_type(target)

                    if not source_type or not target_type:
                        continue

                    # Build dynamic Cypher query
                    query = f"""
                        MATCH (s:{source_type} {{id: $source}})
                        MATCH (t:{target_type} {{id: $target}})
                        MERGE (s)-[r:{relation}]->(t)
                        SET r.weight = $weight,
                            r.reason = $reason,
                            r.count = COALESCE(r.count, 0) + 1
                    """

                    session.run(
                        query,
                        source=source,
                        target=target,
                        weight=weight,
                        reason=reason,
                    )
                    count += 1

                except Exception as e:
                    logger.error(f"Failed to create relationship: {e}")

            logger.info(f"Created/updated {count} relationships")
            return count

    def merge_production_patterns(
        self,
        patterns: list[CooccurrencePattern],
        merge_strategy: str = "weighted_average",
    ) -> int:
        """Add or update edges from production data patterns.

        Args:
            patterns: List of CooccurrencePattern from production data
            merge_strategy: "weighted_average", "production_only", or "max"

        Returns:
            Number of relationships updated
        """
        if not patterns:
            return 0

        with self.driver.session(database=self.database) as session:
            count = 0
            for pattern in patterns:
                try:
                    source_type = self._get_node_type_from_entity(pattern.source_type)
                    target_type = self._get_node_type_from_entity(pattern.target_type)

                    if not source_type or not target_type:
                        continue

                    # Determine relationship type
                    if pattern.source_type == "action" and pattern.target_type == "widget":
                        rel_type = "SUGGESTS_WIDGET"
                    elif pattern.source_type == "action" and pattern.target_type == "action":
                        rel_type = "COMMONLY_PAIRED_WITH"
                    else:
                        rel_type = "RELATED_TO"

                    # Build merge query based on strategy
                    if merge_strategy == "production_only":
                        weight_expr = "$prod_weight"
                    elif merge_strategy == "max":
                        weight_expr = "CASE WHEN r.weight > $prod_weight THEN r.weight ELSE $prod_weight END"
                    else:  # weighted_average
                        weight_expr = "(COALESCE(r.weight, 0) + $prod_weight) / 2"

                    query = f"""
                        MATCH (s:{source_type} {{id: $source}})
                        MATCH (t:{target_type} {{id: $target}})
                        MERGE (s)-[r:{rel_type}]->(t)
                        SET r.weight = {weight_expr},
                            r.count = COALESCE(r.count, 0) + $count,
                            r.confidence = $confidence,
                            r.production_derived = true
                    """

                    session.run(
                        query,
                        source=pattern.source_id,
                        target=pattern.target_id,
                        prod_weight=pattern.confidence,
                        count=pattern.count,
                        confidence=pattern.confidence,
                    )
                    count += 1

                except Exception as e:
                    logger.error(f"Failed to merge production pattern: {e}")

            logger.info(f"Merged {count} production patterns")
            return count

    def create_status_pattern_relationships(self, patterns: list[dict]) -> int:
        """Create TYPICALLY_INCLUDES relationships from status patterns.

        Args:
            patterns: List of status pattern dicts with typical_actions and typical_widgets

        Returns:
            Number of relationships created
        """
        if not patterns:
            return 0

        with self.driver.session(database=self.database) as session:
            count = 0
            for pattern in patterns:
                pattern_id = pattern.get("id", "")

                # Create relationships to typical actions
                for action_id in pattern.get("typical_actions", []):
                    try:
                        session.run(
                            """
                            MATCH (p:StatusPattern {id: $pattern_id})
                            MATCH (a:Action {id: $action_id})
                            MERGE (p)-[r:TYPICALLY_INCLUDES]->(a)
                            SET r.weight = 0.8
                            """,
                            pattern_id=pattern_id,
                            action_id=action_id,
                        )
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to link pattern to action: {e}")

                # Create relationships to typical widgets
                for widget_id in pattern.get("typical_widgets", []):
                    try:
                        session.run(
                            """
                            MATCH (p:StatusPattern {id: $pattern_id})
                            MATCH (w:Widget {id: $widget_id})
                            MERGE (p)-[r:TYPICALLY_INCLUDES]->(w)
                            SET r.weight = 0.8
                            """,
                            pattern_id=pattern_id,
                            widget_id=widget_id,
                        )
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to link pattern to widget: {e}")

            logger.info(f"Created {count} status pattern relationships")
            return count

    def query_suggested_widgets(
        self,
        action_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Query widgets suggested by an action.

        Args:
            action_id: Action ID
            limit: Maximum results

        Returns:
            List of widget dicts with weights
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                """
                MATCH (a:Action {id: $action_id})-[r:SUGGESTS_WIDGET]->(w:Widget)
                RETURN w.id AS id, w.name AS name, w.description AS description,
                       r.weight AS weight, r.count AS count
                ORDER BY r.weight DESC
                LIMIT $limit
                """,
                action_id=action_id,
                limit=limit,
            )
            return [dict(record) for record in result]

    def query_commonly_paired_actions(
        self,
        action_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Query actions commonly paired with given action.

        Args:
            action_id: Action ID
            limit: Maximum results

        Returns:
            List of action dicts with weights
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                """
                MATCH (a:Action {id: $action_id})-[r:COMMONLY_PAIRED_WITH]-(other:Action)
                RETURN other.id AS id, other.name AS name, other.description AS description,
                       r.weight AS weight, r.count AS count
                ORDER BY r.weight DESC
                LIMIT $limit
                """,
                action_id=action_id,
                limit=limit,
            )
            return [dict(record) for record in result]

    def query_pattern_entities(
        self,
        pattern_id: str,
    ) -> dict:
        """Query all entities typically included in a status pattern.

        Args:
            pattern_id: Status pattern ID

        Returns:
            Dict with actions and widgets lists
        """
        with self.driver.session(database=self.database) as session:
            # Get actions
            actions_result = session.run(
                """
                MATCH (p:StatusPattern {id: $pattern_id})-[r:TYPICALLY_INCLUDES]->(a:Action)
                RETURN a.id AS id, a.name AS name, r.weight AS weight
                ORDER BY r.weight DESC
                """,
                pattern_id=pattern_id,
            )

            # Get widgets
            widgets_result = session.run(
                """
                MATCH (p:StatusPattern {id: $pattern_id})-[r:TYPICALLY_INCLUDES]->(w:Widget)
                RETURN w.id AS id, w.name AS name, r.weight AS weight
                ORDER BY r.weight DESC
                """,
                pattern_id=pattern_id,
            )

            return {
                "actions": [dict(r) for r in actions_result],
                "widgets": [dict(r) for r in widgets_result],
            }

    def get_graph_stats(self) -> dict:
        """Get statistics about the graph.

        Returns:
            Dict with node and relationship counts
        """
        with self.driver.session(database=self.database) as session:
            stats = {}

            # Node counts
            for label in ["Action", "Widget", "Status", "StatusPattern"]:
                result = session.run(f"MATCH (n:{label}) RETURN count(n) AS count")
                stats[f"{label.lower()}_nodes"] = result.single()["count"]

            # Relationship counts
            result = session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count")
            for record in result:
                stats[f"rel_{record['type'].lower()}"] = record["count"]

            return stats

    def clear_all(self):
        """Clear all nodes and relationships from the graph."""
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("Cleared all nodes and relationships from graph")

    def _get_node_type(self, entity_id: str) -> Optional[str]:
        """Determine Neo4j node type from entity ID prefix.

        Args:
            entity_id: Entity ID (e.g., "action:clock_in")

        Returns:
            Neo4j label or None
        """
        if entity_id.startswith("action:"):
            return "Action"
        elif entity_id.startswith("widget:"):
            return "Widget"
        elif entity_id.startswith("status:"):
            return "Status"
        elif entity_id.startswith("pattern:"):
            return "StatusPattern"
        return None

    def _get_node_type_from_entity(self, entity_type: str) -> Optional[str]:
        """Convert entity type string to Neo4j label.

        Args:
            entity_type: "action", "widget", etc.

        Returns:
            Neo4j label or None
        """
        mapping = {
            "action": "Action",
            "widget": "Widget",
            "status": "Status",
            "status_pattern": "StatusPattern",
            "pattern": "StatusPattern",
        }
        return mapping.get(entity_type.lower())
