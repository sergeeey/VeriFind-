"""Unit tests for WORM Audit Log.

Week 11: SEC/FINRA compliance - immutable audit trail.
"""

import pytest
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.audit.worm_audit_log import (
    WORMAuditLog,
    AuditLogEntry,
    AuditLogLevel
)


class TestWORMAuditLog:
    """Test WORM audit log functionality."""

    @pytest.fixture
    def temp_audit_dir(self):
        """Create temporary directory for audit logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def audit_log(self, temp_audit_dir):
        """Create audit log instance."""
        return WORMAuditLog(storage_path=temp_audit_dir)

    def test_initialization(self, temp_audit_dir):
        """Audit log initializes correctly."""
        log = WORMAuditLog(storage_path=temp_audit_dir)
        assert log.storage_path == Path(temp_audit_dir)
        assert log._sequence == 0
        assert log._previous_hash == "0" * 64

    def test_log_entry_creation(self, audit_log):
        """Log entry is created with correct fields."""
        entry = audit_log.log(
            query_id="query_123",
            user_id="user@example.com",
            action="TEST_ACTION",
            details={"key": "value"}
        )
        
        assert isinstance(entry, AuditLogEntry)
        assert entry.query_id == "query_123"
        assert entry.user_id == "user@example.com"
        assert entry.action == "TEST_ACTION"
        assert entry.details == {"key": "value"}
        assert entry.sequence == 1
        assert len(entry.entry_hash) == 64  # SHA-256 hex
        assert entry.previous_hash == "0" * 64

    def test_sequence_increment(self, audit_log):
        """Sequence number increments for each entry."""
        entry1 = audit_log.log("q1", "user1", "ACTION1")
        entry2 = audit_log.log("q2", "user2", "ACTION2")
        entry3 = audit_log.log("q3", "user3", "ACTION3")
        
        assert entry1.sequence == 1
        assert entry2.sequence == 2
        assert entry3.sequence == 3

    def test_hash_chain(self, audit_log):
        """Hash chain links entries."""
        entry1 = audit_log.log("q1", "user1", "ACTION1")
        entry2 = audit_log.log("q2", "user2", "ACTION2")
        
        # Second entry's previous_hash should be first entry's hash
        assert entry2.previous_hash == entry1.entry_hash

    def test_file_creation(self, audit_log, temp_audit_dir):
        """Log file is created."""
        audit_log.log("q1", "user1", "ACTION1")
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = Path(temp_audit_dir) / f"audit_{today}.log"
        
        assert log_file.exists()
        
        # Check content
        with open(log_file, "r") as f:
            line = f.readline()
            entry = json.loads(line)
            assert entry["query_id"] == "q1"
            assert entry["action"] == "ACTION1"

    def test_verify_integrity_success(self, audit_log):
        """Integrity check passes for valid logs."""
        audit_log.log("q1", "user1", "ACTION1")
        audit_log.log("q2", "user2", "ACTION2")
        audit_log.log("q3", "user3", "ACTION3")
        
        assert audit_log.verify_integrity() is True

    def test_verify_integrity_fail_tampering(self, audit_log, temp_audit_dir):
        """Integrity check fails if log is tampered."""
        audit_log.log("q1", "user1", "ACTION1")
        audit_log.log("q2", "user2", "ACTION2")
        
        # Tamper with the log file
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = Path(temp_audit_dir) / f"audit_{today}.log"
        
        with open(log_file, "r") as f:
            lines = f.readlines()
        
        # Modify first entry
        entry = json.loads(lines[0])
        entry["action"] = "TAMPERED_ACTION"
        lines[0] = json.dumps(entry) + "\n"
        
        with open(log_file, "w") as f:
            f.writelines(lines)
        
        # Create new audit log instance to read tampered file
        audit_log2 = WORMAuditLog(storage_path=temp_audit_dir)
        
        # Integrity check should fail
        assert audit_log2.verify_integrity() is False

    def test_query_entries(self, audit_log):
        """Query entries by filters."""
        audit_log.log("query_1", "user_a", "ACTION", details={"ticker": "AAPL"})
        audit_log.log("query_1", "user_a", "ACTION2", details={"ticker": "MSFT"})
        audit_log.log("query_2", "user_b", "ACTION", details={"ticker": "GOOGL"})
        
        # Query by query_id
        entries = audit_log.get_entries(query_id="query_1")
        assert len(entries) == 2
        
        # Query by user_id
        entries = audit_log.get_entries(user_id="user_b")
        assert len(entries) == 1
        assert entries[0]["query_id"] == "query_2"

    def test_log_query_submitted(self, audit_log):
        """Convenience method for query submission."""
        entry = audit_log.log_query_submitted(
            query_id="q123",
            user_id="user@test.com",
            query_text="Calculate Sharpe ratio for AAPL",
            client_ip="192.168.1.1"
        )
        
        assert entry.action == "QUERY_SUBMITTED"
        assert entry.level == AuditLogLevel.COMPLIANCE.value
        assert entry.details["query_text"] == "Calculate Sharpe ratio for AAPL"
        assert entry.details["client_ip"] == "192.168.1.1"

    def test_log_query_completed(self, audit_log):
        """Convenience method for query completion."""
        entry = audit_log.log_query_completed(
            query_id="q123",
            user_id="user@test.com",
            result_status="success",
            data_source="yfinance",
            execution_time_ms=1250.5
        )
        
        assert entry.action == "QUERY_COMPLETED"
        assert entry.details["result_status"] == "success"
        assert entry.details["data_source"] == "yfinance"
        assert entry.details["execution_time_ms"] == 1250.5

    def test_log_data_access(self, audit_log):
        """Convenience method for data access logging."""
        entry = audit_log.log_data_access(
            query_id="q123",
            user_id="user@test.com",
            ticker="AAPL",
            data_type="ohlcv",
            date_range="2023-01-01 to 2023-12-31"
        )
        
        assert entry.action == "DATA_ACCESSED"
        assert entry.details["ticker"] == "AAPL"
        assert entry.details["data_type"] == "ohlcv"

    def test_entry_immutability(self, audit_log):
        """Audit log entries are immutable."""
        entry = audit_log.log("q1", "user1", "ACTION")
        
        # Attempt to modify should fail
        with pytest.raises(AttributeError):
            entry.action = "MODIFIED"
        
        with pytest.raises(AttributeError):
            entry.query_id = "modified_id"

    def test_persistence_across_instances(self, temp_audit_dir):
        """Log persists across audit log instances."""
        log1 = WORMAuditLog(storage_path=temp_audit_dir)
        log1.log("q1", "user1", "ACTION1")
        
        # Create new instance
        log2 = WORMAuditLog(storage_path=temp_audit_dir)
        log2.log("q2", "user2", "ACTION2")
        
        # Both entries should be in log
        entries = log2.get_entries()
        assert len(entries) == 2
        assert entries[0]["query_id"] == "q1"
        assert entries[1]["query_id"] == "q2"

    def test_hash_uniqueness(self, audit_log):
        """Each entry has unique hash."""
        entry1 = audit_log.log("q1", "user1", "ACTION")
        entry2 = audit_log.log("q2", "user2", "ACTION")
        
        assert entry1.entry_hash != entry2.entry_hash

    def test_level_filtering(self, audit_log):
        """Log level is recorded."""
        entry_info = audit_log.log("q1", "user1", "ACTION", level=AuditLogLevel.INFO)
        entry_compliance = audit_log.log("q2", "user2", "ACTION", level=AuditLogLevel.COMPLIANCE)
        
        assert entry_info.level == "info"
        assert entry_compliance.level == "compliance"
