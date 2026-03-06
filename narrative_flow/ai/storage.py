"""Storage layer for narrative briefings."""

import sqlite3
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging
import aiosqlite

logger = logging.getLogger(__name__)


class BriefingStorage:
    """Store and retrieve narrative briefings in SQLite."""

    def __init__(self, db_path: str = "narrative_flow/data/briefings.db"):
        """Initialize briefing storage.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Create database tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            # Main briefings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS briefings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    executive_summary TEXT,
                    markdown_content TEXT,
                    json_content TEXT,
                    emerging_narratives TEXT,
                    overheated_narratives TEXT,
                    key_catalysts TEXT,
                    divergences TEXT,
                    market_regime TEXT,
                    recommendations TEXT,
                    changes_from_previous TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Narrative history table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS narrative_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    narrative TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    stage TEXT,
                    momentum REAL,
                    sentiment REAL,
                    mention_count INTEGER,
                    on_chain_activity REAL,
                    price_change REAL,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Catalyst events table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS catalyst_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    event_type TEXT,
                    event_description TEXT,
                    affected_narratives TEXT,
                    affected_tokens TEXT,
                    impact_score REAL,
                    confidence REAL,
                    source TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Market regime snapshots
            await db.execute("""
                CREATE TABLE IF NOT EXISTS regime_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    narrative TEXT NOT NULL,
                    current_stage TEXT,
                    stage_confidence REAL,
                    time_in_stage INTEGER,
                    next_likely_stage TEXT,
                    transition_probability REAL,
                    risk_level TEXT,
                    opportunity_score REAL,
                    recommendation TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            await db.execute("CREATE INDEX IF NOT EXISTS idx_briefings_timestamp ON briefings(timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_narrative_history_narrative ON narrative_history(narrative)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_catalyst_events_timestamp ON catalyst_events(timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_regime_snapshots_narrative ON regime_snapshots(narrative)")

            await db.commit()
            logger.info("Database initialized successfully")

    async def save_briefing(
        self,
        briefing: Dict[str, Any]
    ) -> int:
        """Save a narrative briefing to database.

        Args:
            briefing: Complete briefing data

        Returns:
            Briefing ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO briefings (
                    timestamp,
                    executive_summary,
                    markdown_content,
                    json_content,
                    emerging_narratives,
                    overheated_narratives,
                    key_catalysts,
                    divergences,
                    market_regime,
                    recommendations,
                    changes_from_previous,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                briefing.get("timestamp", datetime.utcnow()),
                briefing.get("executive_summary", ""),
                briefing.get("markdown_output", ""),
                json.dumps(briefing.get("json_output", {})),
                json.dumps(briefing.get("emerging_narratives", [])),
                json.dumps(briefing.get("overheated_narratives", [])),
                json.dumps(briefing.get("key_catalysts", [])),
                json.dumps(briefing.get("divergences", [])),
                json.dumps(briefing.get("market_regime", {})),
                json.dumps(briefing.get("recommendations", [])),
                json.dumps(briefing.get("changes_from_previous", {})),
                json.dumps(briefing.get("metadata", {}))
            ))
            await db.commit()

            briefing_id = cursor.lastrowid
            logger.info(f"Saved briefing {briefing_id}")
            return briefing_id

    async def get_latest_briefing(self) -> Optional[Dict[str, Any]]:
        """Get the most recent briefing.

        Returns:
            Latest briefing or None
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM briefings
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            row = await cursor.fetchone()

            if row:
                return self._row_to_briefing(row)
            return None

    async def get_briefing_history(
        self,
        limit: int = 10,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get briefing history.

        Args:
            limit: Maximum number of briefings to return
            offset: Number of briefings to skip
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of briefings
        """
        query = "SELECT * FROM briefings WHERE 1=1"
        params = []

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            return [self._row_to_briefing(row) for row in rows]

    async def save_narrative_snapshot(
        self,
        narrative: str,
        metrics: Dict[str, Any]
    ):
        """Save narrative metrics snapshot.

        Args:
            narrative: Narrative name
            metrics: Current metrics
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO narrative_history (
                    narrative,
                    timestamp,
                    stage,
                    momentum,
                    sentiment,
                    mention_count,
                    on_chain_activity,
                    price_change,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                narrative,
                datetime.utcnow(),
                metrics.get("stage", ""),
                metrics.get("momentum", 0),
                metrics.get("sentiment", 0),
                metrics.get("mention_count", 0),
                metrics.get("on_chain_activity", 0),
                metrics.get("price_change", 0),
                json.dumps(metrics.get("metadata", {}))
            ))
            await db.commit()

    async def get_narrative_history(
        self,
        narrative: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get historical data for a narrative.

        Args:
            narrative: Narrative name
            hours: Hours of history to retrieve

        Returns:
            List of historical snapshots
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM narrative_history
                WHERE narrative = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (narrative, since))
            rows = await cursor.fetchall()

            history = []
            for row in rows:
                history.append({
                    "narrative": row["narrative"],
                    "timestamp": row["timestamp"],
                    "stage": row["stage"],
                    "momentum": row["momentum"],
                    "sentiment": row["sentiment"],
                    "mention_count": row["mention_count"],
                    "on_chain_activity": row["on_chain_activity"],
                    "price_change": row["price_change"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                })
            return history

    async def save_catalyst(
        self,
        catalyst: Dict[str, Any]
    ):
        """Save catalyst event to database.

        Args:
            catalyst: Catalyst data
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO catalyst_events (
                    timestamp,
                    event_type,
                    event_description,
                    affected_narratives,
                    affected_tokens,
                    impact_score,
                    confidence,
                    source,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                catalyst.get("timestamp", datetime.utcnow()),
                catalyst.get("event_type", ""),
                catalyst.get("event_description", ""),
                json.dumps(catalyst.get("affected_narratives", [])),
                json.dumps(catalyst.get("affected_tokens", [])),
                catalyst.get("impact_score", 0),
                catalyst.get("confidence", 0),
                catalyst.get("source", ""),
                json.dumps(catalyst.get("metadata", {}))
            ))
            await db.commit()

    async def get_recent_catalysts(
        self,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get recent catalyst events.

        Args:
            hours: Hours of history

        Returns:
            List of catalyst events
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM catalyst_events
                WHERE timestamp >= ?
                ORDER BY impact_score DESC, timestamp DESC
            """, (since,))
            rows = await cursor.fetchall()

            catalysts = []
            for row in rows:
                catalysts.append({
                    "timestamp": row["timestamp"],
                    "event_type": row["event_type"],
                    "event_description": row["event_description"],
                    "affected_narratives": json.loads(row["affected_narratives"]),
                    "affected_tokens": json.loads(row["affected_tokens"]),
                    "impact_score": row["impact_score"],
                    "confidence": row["confidence"],
                    "source": row["source"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                })
            return catalysts

    async def save_regime_snapshot(
        self,
        regime_analysis: Dict[str, Any]
    ):
        """Save market regime snapshot.

        Args:
            regime_analysis: Regime analysis data
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO regime_snapshots (
                    timestamp,
                    narrative,
                    current_stage,
                    stage_confidence,
                    time_in_stage,
                    next_likely_stage,
                    transition_probability,
                    risk_level,
                    opportunity_score,
                    recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow(),
                regime_analysis.get("narrative", ""),
                regime_analysis.get("current_stage", ""),
                regime_analysis.get("stage_confidence", 0),
                regime_analysis.get("time_in_stage", 0),
                regime_analysis.get("next_likely_stage", ""),
                regime_analysis.get("transition_probability", 0),
                regime_analysis.get("risk_level", ""),
                regime_analysis.get("opportunity_score", 0),
                regime_analysis.get("recommendation", "")
            ))
            await db.commit()

    async def get_regime_history(
        self,
        narrative: str,
        hours: int = 168  # 1 week default
    ) -> List[Dict[str, Any]]:
        """Get regime history for a narrative.

        Args:
            narrative: Narrative name
            hours: Hours of history

        Returns:
            List of regime snapshots
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM regime_snapshots
                WHERE narrative = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (narrative, since))
            rows = await cursor.fetchall()

            return [dict(row) for row in rows]

    async def cleanup_old_data(
        self,
        days_to_keep: int = 30
    ):
        """Clean up old data from database.

        Args:
            days_to_keep: Number of days of data to retain
        """
        cutoff = datetime.utcnow() - timedelta(days=days_to_keep)

        async with aiosqlite.connect(self.db_path) as db:
            # Clean each table
            tables = ["briefings", "narrative_history", "catalyst_events", "regime_snapshots"]
            for table in tables:
                await db.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff,))

            await db.commit()
            logger.info(f"Cleaned up data older than {days_to_keep} days")

    def _row_to_briefing(self, row) -> Dict[str, Any]:
        """Convert database row to briefing dict."""
        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "executive_summary": row["executive_summary"],
            "markdown_output": row["markdown_content"],
            "json_output": json.loads(row["json_content"]) if row["json_content"] else {},
            "emerging_narratives": json.loads(row["emerging_narratives"]) if row["emerging_narratives"] else [],
            "overheated_narratives": json.loads(row["overheated_narratives"]) if row["overheated_narratives"] else [],
            "key_catalysts": json.loads(row["key_catalysts"]) if row["key_catalysts"] else [],
            "divergences": json.loads(row["divergences"]) if row["divergences"] else [],
            "market_regime": json.loads(row["market_regime"]) if row["market_regime"] else {},
            "recommendations": json.loads(row["recommendations"]) if row["recommendations"] else [],
            "changes_from_previous": json.loads(row["changes_from_previous"]) if row["changes_from_previous"] else {},
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "created_at": row["created_at"]
        }

    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Statistics about stored data
        """
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}

            # Count briefings
            cursor = await db.execute("SELECT COUNT(*) FROM briefings")
            stats["total_briefings"] = (await cursor.fetchone())[0]

            # Count narratives tracked
            cursor = await db.execute("SELECT COUNT(DISTINCT narrative) FROM narrative_history")
            stats["narratives_tracked"] = (await cursor.fetchone())[0]

            # Count catalyst events
            cursor = await db.execute("SELECT COUNT(*) FROM catalyst_events")
            stats["catalyst_events"] = (await cursor.fetchone())[0]

            # Get date range
            cursor = await db.execute("SELECT MIN(timestamp), MAX(timestamp) FROM briefings")
            row = await cursor.fetchone()
            if row[0]:
                stats["oldest_briefing"] = row[0]
                stats["newest_briefing"] = row[1]

            return stats