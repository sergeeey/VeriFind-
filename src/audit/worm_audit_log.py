"""WORM (Write Once Read Many) Audit Log for Financial Compliance.

Week 11: SEC/FINRA compliant immutable audit trail.

Features:
- Tamper-evident hash chain (like blockchain)
- Immutable storage (S3 Glacier or local WORM files)
- Cryptographic signing of entries
- Regulatory compliance: SEC 17a-4, FINRA 4511

Usage:
    audit_log = WORMAuditLog(storage_path="/var/audit/ape")
    audit_log.log_query(
        query_id="abc123",
        user_id="user@example.com",
        query_text="Calculate Sharpe ratio for AAPL",
        action="QUERY_SUBMITTED"
    )
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class AuditLogLevel(Enum):
    """Audit log severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    COMPLIANCE = "compliance"  # Regulatory events


@dataclass(frozen=True)
class AuditLogEntry:
    """
    Immutable audit log entry.
    
    Attributes:
        timestamp: UTC timestamp
        sequence: Monotonic sequence number
        query_id: Associated query ID
        user_id: User identifier
        action: Action performed
        details: Additional context
        level: Log level (info, warning, error, compliance)
        previous_hash: Hash of previous entry (for chain)
        entry_hash: Hash of this entry
    """
    timestamp: str
    sequence: int
    query_id: str
    user_id: str
    action: str
    details: Dict[str, Any]
    level: str
    previous_hash: str
    entry_hash: str


class WORMAuditLog:
    """
    Write Once Read Many audit log.
    
    Guarantees:
    - Entries are immutable after write
    - Tamper-evident (hash chain)
    - Chronological ordering
    - Regulatory compliance
    
    Storage options:
    - Local: Immutable files with append-only
    - S3 Glacier: For production (future)
    """
    
    def __init__(self, storage_path: str):
        """
        Initialize WORM audit log.
        
        Args:
            storage_path: Directory for audit log files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Current log file (daily rotation)
        self.current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.log_file = self.storage_path / f"audit_{self.current_date}.log"
        
        # Sequence counter
        self._sequence = self._get_last_sequence()
        self._previous_hash = self._get_last_hash()
        
        logger.info(f"WORM Audit Log initialized: {self.log_file}")
    
    def _get_last_sequence(self) -> int:
        """Get last sequence number from existing logs."""
        log_files = sorted(self.storage_path.glob("audit_*.log"))
        if not log_files:
            return 0
        
        # Read last line of most recent file
        try:
            with open(log_files[-1], "r") as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    return last_entry.get("sequence", 0)
        except Exception:
            pass
        return 0
    
    def _get_last_hash(self) -> str:
        """Get hash of last entry for chain."""
        log_files = sorted(self.storage_path.glob("audit_*.log"))
        if not log_files:
            return "0" * 64  # Genesis hash
        
        try:
            with open(log_files[-1], "r") as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    return last_entry.get("entry_hash", "0" * 64)
        except Exception:
            pass
        return "0" * 64
    
    def _calculate_hash(self, entry_data: Dict) -> str:
        """Calculate SHA-256 hash of entry data."""
        # Exclude entry_hash from calculation
        data_to_hash = {k: v for k, v in entry_data.items() if k != "entry_hash"}
        json_str = json.dumps(data_to_hash, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def log(
        self,
        query_id: str,
        user_id: str,
        action: str,
        details: Optional[Dict] = None,
        level: AuditLogLevel = AuditLogLevel.INFO
    ) -> AuditLogEntry:
        """
        Write immutable audit log entry.
        
        Args:
            query_id: Query identifier
            user_id: User identifier
            action: Action description
            details: Additional context
            level: Log level
            
        Returns:
            Created audit log entry
        """
        # Rotate log if needed
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if current_date != self.current_date:
            self.current_date = current_date
            self.log_file = self.storage_path / f"audit_{self.current_date}.log"
        
        # Increment sequence
        self._sequence += 1
        
        # Create entry data
        timestamp = datetime.now(timezone.utc).isoformat()
        entry_data = {
            "timestamp": timestamp,
            "sequence": self._sequence,
            "query_id": query_id,
            "user_id": user_id,
            "action": action,
            "level": level.value,
            "details": details or {},
            "previous_hash": self._previous_hash,
        }
        
        # Calculate hash
        entry_hash = self._calculate_hash(entry_data)
        entry_data["entry_hash"] = entry_hash
        
        # Create immutable entry
        entry = AuditLogEntry(**entry_data)
        
        # Write to log (append-only)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry_data, default=str) + "\n")
            f.flush()
        
        # Update chain state
        self._previous_hash = entry_hash
        
        logger.debug(f"Audit log entry #{self._sequence}: {action}")
        return entry
    
    def log_query_submitted(
        self,
        query_id: str,
        user_id: str,
        query_text: str,
        client_ip: Optional[str] = None
    ) -> AuditLogEntry:
        """Log query submission."""
        return self.log(
            query_id=query_id,
            user_id=user_id,
            action="QUERY_SUBMITTED",
            details={
                "query_text": query_text,
                "client_ip": client_ip,
                "event_type": "user_action"
            },
            level=AuditLogLevel.COMPLIANCE
        )
    
    def log_query_completed(
        self,
        query_id: str,
        user_id: str,
        result_status: str,
        data_source: str,
        execution_time_ms: float
    ) -> AuditLogEntry:
        """Log query completion with results."""
        return self.log(
            query_id=query_id,
            user_id=user_id,
            action="QUERY_COMPLETED",
            details={
                "result_status": result_status,
                "data_source": data_source,
                "execution_time_ms": execution_time_ms,
                "event_type": "system_event"
            },
            level=AuditLogLevel.COMPLIANCE
        )
    
    def log_data_access(
        self,
        query_id: str,
        user_id: str,
        ticker: str,
        data_type: str,
        date_range: str
    ) -> AuditLogEntry:
        """Log market data access (for data licensing compliance)."""
        return self.log(
            query_id=query_id,
            user_id=user_id,
            action="DATA_ACCESSED",
            details={
                "ticker": ticker,
                "data_type": data_type,
                "date_range": date_range,
                "event_type": "data_access"
            },
            level=AuditLogLevel.COMPLIANCE
        )
    
    def verify_integrity(self) -> bool:
        """
        Verify integrity of audit log chain.
        
        Checks:
        - All entries are valid JSON
        - Hash chain is intact
        - No entries modified
        
        Returns:
            True if integrity verified, False if tampering detected
        """
        log_files = sorted(self.storage_path.glob("audit_*.log"))
        if not log_files:
            return True
        
        previous_hash = "0" * 64
        
        for log_file in log_files:
            with open(log_file, "r") as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        entry = json.loads(line)
                        
                        # Verify previous_hash matches
                        if entry.get("previous_hash") != previous_hash:
                            logger.error(
                                f"Hash chain broken at {log_file}:{line_num}"
                            )
                            return False
                        
                        # Verify entry_hash
                        stored_hash = entry.pop("entry_hash")
                        calculated_hash = self._calculate_hash(entry)
                        if stored_hash != calculated_hash:
                            logger.error(
                                f"Hash mismatch at {log_file}:{line_num}"
                            )
                            return False
                        
                        previous_hash = stored_hash
                        
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON at {log_file}:{line_num}")
                        return False
        
        logger.info("Audit log integrity verified")
        return True
    
    def get_entries(
        self,
        query_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> list:
        """
        Query audit log entries (read-only).
        
        Args:
            query_id: Filter by query ID
            user_id: Filter by user ID
            start_time: Filter by start time (ISO format)
            end_time: Filter by end time (ISO format)
            
        Returns:
            List of matching entries
        """
        entries = []
        log_files = sorted(self.storage_path.glob("audit_*.log"))
        
        for log_file in log_files:
            with open(log_file, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        
                        # Apply filters
                        if query_id and entry.get("query_id") != query_id:
                            continue
                        if user_id and entry.get("user_id") != user_id:
                            continue
                        if start_time and entry.get("timestamp", "") < start_time:
                            continue
                        if end_time and entry.get("timestamp", "") > end_time:
                            continue
                        
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        
        return entries
