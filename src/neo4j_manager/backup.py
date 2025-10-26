"""Backup and restore utilities for Neo4j."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path
from .connection import Neo4jConnection

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages Neo4j backup and restore operations."""

    def __init__(self, connection: Neo4jConnection, backup_dir: str = "./backup"):
        """
        Initialize backup manager.

        Args:
            connection: Neo4j connection instance
            backup_dir: Directory to store backups
        """
        self.connection = connection
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup_filename(self, prefix: str = "neo4j_backup") -> str:
        """
        Generate timestamped backup filename.

        Args:
            prefix: Filename prefix

        Returns:
            Backup filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.graphml"

    def export_to_graphml(self, filename: Optional[str] = None, include_types: bool = True) -> str:
        """
        Export database to GraphML format using APOC.

        Args:
            filename: Output filename (auto-generated if None)
            include_types: Include type information in export

        Returns:
            Path to exported file

        Raises:
            Exception: If APOC is not available or export fails
        """
        if filename is None:
            filename = self.create_backup_filename()

        # Remove .graphml extension if present (APOC adds it)
        filename_base = filename.replace(".graphml", "")

        query = f"""
        CALL apoc.export.graphml.all('{filename_base}.graphml', {{
            useTypes: {str(include_types).lower()},
            readLabels: true,
            storeNodeIds: false
        }})
        YIELD file, nodes, relationships, time
        RETURN file, nodes, relationships, time
        """

        try:
            result = self.connection.execute_query(query)
            if result:
                logger.info(
                    f"Exported {result[0]['nodes']} nodes and "
                    f"{result[0]['relationships']} relationships in "
                    f"{result[0]['time']}ms"
                )
            return str(self.backup_dir / f"{filename_base}.graphml")
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise

    def import_from_graphml(self, filepath: str, clear_database: bool = False) -> Dict[str, int]:
        """
        Import database from GraphML format using APOC.

        Args:
            filepath: Path to GraphML file
            clear_database: Whether to clear database before import

        Returns:
            Dictionary with import statistics

        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: If import fails
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Backup file not found: {filepath}")

        # Clear database if requested
        if clear_database:
            logger.warning("Clearing database before import")
            self.connection.clear_database()

        # Get filename for APOC (needs to be in import directory)
        filename = os.path.basename(filepath)

        query = f"""
        CALL apoc.import.graphml('file:///{filename}', {{
            readLabels: true,
            storeNodeIds: false,
            defaultRelationshipType: 'RELATED',
            batchSize: 1000,
            useTypes: false
        }})
        YIELD nodes, relationships, time
        RETURN nodes, relationships, time
        """

        try:
            result = self.connection.execute_query(query)
            if result:
                stats = {
                    "nodes": result[0]["nodes"],
                    "relationships": result[0]["relationships"],
                    "time_ms": result[0]["time"],
                }
                logger.info(
                    f"Imported {stats['nodes']} nodes and "
                    f"{stats['relationships']} relationships in "
                    f"{stats['time_ms']}ms"
                )
                return stats
            return {"nodes": 0, "relationships": 0, "time_ms": 0}
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise

    def list_backups(self) -> list[Path]:
        """
        List all backup files in backup directory.

        Returns:
            List of backup file paths
        """
        return sorted(self.backup_dir.glob("*.graphml*"), key=lambda p: p.stat().st_mtime)

    def get_latest_backup(self) -> Optional[Path]:
        """
        Get the most recent backup file.

        Returns:
            Path to latest backup or None if no backups exist
        """
        backups = self.list_backups()
        return backups[-1] if backups else None
