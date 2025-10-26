"""Unit tests for BackupManager class."""

from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import pytest
from src.neo4j_manager.backup import BackupManager
from src.neo4j_manager.connection import Neo4jConnection


class TestBackupManagerInit:
    """Test BackupManager initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        mock_conn = Mock(spec=Neo4jConnection)
        manager = BackupManager(mock_conn)

        assert manager.connection == mock_conn
        assert manager.backup_dir == Path("./backup")
        assert manager.backup_dir.exists()

    def test_init_with_custom_backup_dir(self):
        """Test initialization with custom backup directory."""
        mock_conn = Mock(spec=Neo4jConnection)
        manager = BackupManager(mock_conn, backup_dir="./custom_backup")

        assert manager.connection == mock_conn
        assert manager.backup_dir == Path("./custom_backup")


class TestBackupFilenameGeneration:
    """Test backup filename generation."""

    @patch("src.neo4j_manager.backup.datetime")
    def test_create_backup_filename_default_prefix(self, mock_datetime):
        """Test backup filename generation with default prefix."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_datetime.now.return_value.strftime.return_value = "20251026_143000"

        manager = BackupManager(mock_conn)
        filename = manager.create_backup_filename()

        assert filename == "neo4j_backup_20251026_143000.graphml"
        mock_datetime.now.return_value.strftime.assert_called_once_with("%Y%m%d_%H%M%S")

    @patch("src.neo4j_manager.backup.datetime")
    def test_create_backup_filename_custom_prefix(self, mock_datetime):
        """Test backup filename generation with custom prefix."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_datetime.now.return_value.strftime.return_value = "20251026_143000"

        manager = BackupManager(mock_conn)
        filename = manager.create_backup_filename(prefix="test_backup")

        assert filename == "test_backup_20251026_143000.graphml"


class TestExportToGraphML:
    """Test GraphML export functionality."""

    def test_export_to_graphml_success(self):
        """Test successful GraphML export."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.execute_query.return_value = [
            {"file": "backup.graphml", "nodes": 100, "relationships": 50, "time": 1500}
        ]

        manager = BackupManager(mock_conn, backup_dir="./test_backups")
        result = manager.export_to_graphml(filename="test_backup.graphml")

        assert result == str(manager.backup_dir / "test_backup.graphml")
        mock_conn.execute_query.assert_called_once()

        # Verify the query contains expected APOC call
        call_args = mock_conn.execute_query.call_args[0][0]
        assert "apoc.export.graphml.all" in call_args
        assert "test_backup.graphml" in call_args

    def test_export_to_graphml_auto_filename(self):
        """Test export with auto-generated filename."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.execute_query.return_value = [
            {"file": "backup.graphml", "nodes": 50, "relationships": 25, "time": 1000}
        ]

        manager = BackupManager(mock_conn, backup_dir="./test_backups")
        result = manager.export_to_graphml()

        assert result.endswith(".graphml")
        assert "neo4j_backup_" in result

    def test_export_to_graphml_with_types(self):
        """Test export with type information enabled."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.execute_query.return_value = [
            {"file": "backup.graphml", "nodes": 10, "relationships": 5, "time": 500}
        ]

        manager = BackupManager(mock_conn)
        manager.export_to_graphml(include_types=True)

        call_args = mock_conn.execute_query.call_args[0][0]
        assert "useTypes: true" in call_args

    def test_export_to_graphml_without_types(self):
        """Test export with type information disabled."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.execute_query.return_value = [
            {"file": "backup.graphml", "nodes": 10, "relationships": 5, "time": 500}
        ]

        manager = BackupManager(mock_conn)
        manager.export_to_graphml(include_types=False)

        call_args = mock_conn.execute_query.call_args[0][0]
        assert "useTypes: false" in call_args

    def test_export_to_graphml_failure(self):
        """Test export failure handling."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.execute_query.side_effect = Exception("APOC not available")

        manager = BackupManager(mock_conn)

        with pytest.raises(Exception) as exc_info:
            manager.export_to_graphml()

        assert "APOC not available" in str(exc_info.value)


class TestImportFromGraphML:
    """Test GraphML import functionality."""

    @patch("src.neo4j_manager.backup.os.path.exists")
    def test_import_from_graphml_success(self, mock_exists):
        """Test successful GraphML import."""
        mock_exists.return_value = True
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.execute_query.return_value = [{"nodes": 100, "relationships": 50, "time": 2000}]

        manager = BackupManager(mock_conn)
        result = manager.import_from_graphml("/fake/path/backup.graphml")

        assert result["nodes"] == 100
        assert result["relationships"] == 50
        assert result["time_ms"] == 2000
        mock_conn.clear_database.assert_not_called()

    @patch("src.neo4j_manager.backup.os.path.exists")
    def test_import_from_graphml_with_clear(self, mock_exists):
        """Test import with database clearing."""
        mock_exists.return_value = True
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.execute_query.return_value = [{"nodes": 50, "relationships": 25, "time": 1000}]

        manager = BackupManager(mock_conn)
        result = manager.import_from_graphml("/fake/path/backup.graphml", clear_database=True)

        mock_conn.clear_database.assert_called_once()
        assert result["nodes"] == 50

    @patch("src.neo4j_manager.backup.os.path.exists")
    def test_import_from_graphml_file_not_found(self, mock_exists):
        """Test import with non-existent file."""
        mock_exists.return_value = False
        mock_conn = Mock(spec=Neo4jConnection)

        manager = BackupManager(mock_conn)

        with pytest.raises(FileNotFoundError):
            manager.import_from_graphml("/fake/path/nonexistent.graphml")

    @patch("src.neo4j_manager.backup.os.path.exists")
    def test_import_from_graphml_failure(self, mock_exists):
        """Test import failure handling."""
        mock_exists.return_value = True
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.execute_query.side_effect = Exception("Import failed")

        manager = BackupManager(mock_conn)

        with pytest.raises(Exception) as exc_info:
            manager.import_from_graphml("/fake/path/backup.graphml")

        assert "Import failed" in str(exc_info.value)

    @patch("src.neo4j_manager.backup.os.path.exists")
    def test_import_from_graphml_no_results(self, mock_exists):
        """Test import when query returns no results."""
        mock_exists.return_value = True
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.execute_query.return_value = []

        manager = BackupManager(mock_conn)
        result = manager.import_from_graphml("/fake/path/backup.graphml")

        assert result == {"nodes": 0, "relationships": 0, "time_ms": 0}


class TestListBackups:
    """Test backup listing functionality."""

    def test_list_backups_empty_directory(self):
        """Test listing backups in empty directory."""
        mock_conn = Mock(spec=Neo4jConnection)
        manager = BackupManager(mock_conn, backup_dir="./empty_test_backups")
        manager.backup_dir.mkdir(exist_ok=True)

        backups = manager.list_backups()

        assert backups == []

    @patch("pathlib.Path.glob")
    def test_list_backups_with_files(self, mock_glob):
        """Test listing backups with existing files."""
        mock_conn = Mock(spec=Neo4jConnection)
        manager = BackupManager(mock_conn)

        # Mock some backup files with stat info
        mock_file1 = MagicMock(spec=Path)
        mock_file1.stat.return_value.st_mtime = 1000
        mock_file2 = MagicMock(spec=Path)
        mock_file2.stat.return_value.st_mtime = 2000
        mock_file3 = MagicMock(spec=Path)
        mock_file3.stat.return_value.st_mtime = 1500

        mock_glob.return_value = [mock_file1, mock_file2, mock_file3]

        backups = manager.list_backups()

        assert len(backups) == 3
        mock_glob.assert_called_once_with("*.graphml*")


class TestGetLatestBackup:
    """Test getting latest backup."""

    def test_get_latest_backup_empty(self):
        """Test getting latest backup when none exist."""
        mock_conn = Mock(spec=Neo4jConnection)
        manager = BackupManager(mock_conn, backup_dir="./empty_test_backups")
        manager.backup_dir.mkdir(exist_ok=True)

        latest = manager.get_latest_backup()

        assert latest is None

    @patch("pathlib.Path.glob")
    def test_get_latest_backup_with_files(self, mock_glob):
        """Test getting latest backup with existing files."""
        mock_conn = Mock(spec=Neo4jConnection)
        manager = BackupManager(mock_conn)

        # Mock backup files with different timestamps
        mock_file1 = MagicMock(spec=Path)
        mock_file1.stat.return_value.st_mtime = 1000
        mock_file2 = MagicMock(spec=Path)
        mock_file2.stat.return_value.st_mtime = 2000  # Latest
        mock_file3 = MagicMock(spec=Path)
        mock_file3.stat.return_value.st_mtime = 1500

        mock_glob.return_value = [mock_file1, mock_file2, mock_file3]

        latest = manager.get_latest_backup()

        assert latest == mock_file2
