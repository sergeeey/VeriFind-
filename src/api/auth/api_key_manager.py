"""
API Key Management System for B2B API.

Week 12 Day 1: Secure API key generation, validation, and management.

Features:
- Cryptographically secure key generation (sk-ape-{32 hex chars})
- SHA-256 hashing for storage
- Rate limiting per key
- Usage tracking integration
- Quota management

Usage:
    from src.api.auth.api_key_manager import APIKeyManager

    manager = APIKeyManager()

    # Create new API key
    api_key, key_record = await manager.create_api_key(
        customer_name="Acme Corp",
        tier="pro",
        rate_limit_per_hour=1000
    )

    # Validate API key
    is_valid = await manager.validate_api_key(api_key)

    # Get key details
    key_info = await manager.get_key_info(api_key)
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import logging

from sqlalchemy import (
    Table, Column, Integer, String, Boolean, DateTime,
    MetaData, select, insert, update, delete
)
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncConnection
import os


logger = logging.getLogger(__name__)


# API Key Schema (TimescaleDB)
metadata = MetaData()

api_keys_table = Table(
    'api_keys',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('key_hash', String(64), unique=True, nullable=False, index=True),  # SHA-256 hash
    Column('key_prefix', String(16), nullable=False),  # First 16 chars for identification
    Column('customer_name', String(255), nullable=False),
    Column('customer_email', String(255), nullable=True),
    Column('tier', String(50), nullable=False),  # free, pro, enterprise
    Column('is_active', Boolean, default=True, nullable=False),
    Column('rate_limit_per_hour', Integer, default=100, nullable=False),
    Column('monthly_quota', Integer, default=10000, nullable=True),  # null = unlimited
    Column('created_at', DateTime, default=datetime.utcnow, nullable=False),
    Column('last_used_at', DateTime, nullable=True),
    Column('expires_at', DateTime, nullable=True),
    Column('metadata', String(1000), nullable=True)  # JSON string for additional data
)


class APIKeyManager:
    """
    API Key Management System.

    Handles creation, validation, and lifecycle of API keys for B2B customers.
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize API Key Manager.

        Args:
            db_url: Database URL (defaults to TIMESCALEDB_URL from env)
        """
        self.db_url = db_url or os.getenv(
            "TIMESCALEDB_ASYNC_URL",
            "postgresql+asyncpg://ape_test:test_password_123@localhost:5433/ape_timeseries"
        )
        self.engine: Optional[AsyncEngine] = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize database connection and create tables if needed."""
        if self.engine is None:
            self.engine = create_async_engine(self.db_url, echo=False)

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(metadata.create_all)

            self.logger.info("API Key Manager initialized")

    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            self.logger.info("API Key Manager closed")

    @staticmethod
    def generate_api_key() -> str:
        """
        Generate cryptographically secure API key.

        Format: sk-ape-{32 hex characters}
        Example: sk-ape-a1b2c3d4e5f6789012345678901234567890abcd

        Returns:
            API key string
        """
        # Generate 32 random bytes (256 bits)
        random_bytes = secrets.token_bytes(32)

        # Convert to hex string (64 chars)
        hex_string = random_bytes.hex()

        # Format: sk-ape-{first 41 chars of hex} = 48 total chars
        api_key = f"sk-ape-{hex_string[:41]}"

        return api_key

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash API key using SHA-256.

        Args:
            api_key: Plain API key

        Returns:
            SHA-256 hash (hex string, 64 chars)
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def get_key_prefix(api_key: str) -> str:
        """
        Get key prefix for identification.

        Args:
            api_key: Plain API key

        Returns:
            First 16 characters (e.g., "sk-ape-a1b2c3d4")
        """
        return api_key[:16]

    async def create_api_key(
        self,
        customer_name: str,
        tier: str = "free",
        rate_limit_per_hour: int = 100,
        monthly_quota: Optional[int] = 10000,
        customer_email: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        metadata: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create new API key.

        Args:
            customer_name: Customer/company name
            tier: Subscription tier (free, pro, enterprise)
            rate_limit_per_hour: Max requests per hour
            monthly_quota: Max requests per month (null = unlimited)
            customer_email: Customer email
            expires_in_days: Days until expiration (null = never)
            metadata: Additional JSON metadata

        Returns:
            Tuple of (plain_api_key, key_record_dict)
        """
        if self.engine is None:
            await self.initialize()

        # Generate API key
        api_key = self.generate_api_key()
        key_hash = self.hash_api_key(api_key)
        key_prefix = self.get_key_prefix(api_key)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Insert into database
        async with self.engine.begin() as conn:
            result = await conn.execute(
                insert(api_keys_table).values(
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    tier=tier,
                    is_active=True,
                    rate_limit_per_hour=rate_limit_per_hour,
                    monthly_quota=monthly_quota,
                    created_at=datetime.utcnow(),
                    expires_at=expires_at,
                    metadata=metadata
                ).returning(api_keys_table)
            )

            key_record = result.fetchone()._asdict()

        self.logger.info(
            f"Created API key for {customer_name} "
            f"(tier={tier}, prefix={key_prefix})"
        )

        return api_key, key_record

    async def validate_api_key(
        self,
        api_key: str,
        update_last_used: bool = True
    ) -> bool:
        """
        Validate API key.

        Args:
            api_key: Plain API key to validate
            update_last_used: Whether to update last_used_at timestamp

        Returns:
            True if valid and active, False otherwise
        """
        if self.engine is None:
            await self.initialize()

        key_hash = self.hash_api_key(api_key)

        async with self.engine.begin() as conn:
            # Get key record
            result = await conn.execute(
                select(api_keys_table).where(
                    api_keys_table.c.key_hash == key_hash
                )
            )

            key_record = result.fetchone()

            if not key_record:
                return False

            key_dict = key_record._asdict()

            # Check if active
            if not key_dict['is_active']:
                self.logger.warning(f"Inactive key used: {key_dict['key_prefix']}")
                return False

            # Check if expired
            if key_dict['expires_at'] and datetime.utcnow() > key_dict['expires_at']:
                self.logger.warning(f"Expired key used: {key_dict['key_prefix']}")
                return False

            # Update last_used_at
            if update_last_used:
                await conn.execute(
                    update(api_keys_table)
                    .where(api_keys_table.c.key_hash == key_hash)
                    .values(last_used_at=datetime.utcnow())
                )

        return True

    async def get_key_info(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Get API key information.

        Args:
            api_key: Plain API key

        Returns:
            Key record dict or None if not found
        """
        if self.engine is None:
            await self.initialize()

        key_hash = self.hash_api_key(api_key)

        async with self.engine.connect() as conn:
            result = await conn.execute(
                select(api_keys_table).where(
                    api_keys_table.c.key_hash == key_hash
                )
            )

            key_record = result.fetchone()

            if not key_record:
                return None

            return key_record._asdict()

    async def list_api_keys(
        self,
        customer_name: Optional[str] = None,
        tier: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100
    ) -> list[Dict[str, Any]]:
        """
        List API keys with optional filters.

        Args:
            customer_name: Filter by customer name (partial match)
            tier: Filter by tier
            is_active: Filter by active status
            limit: Max records to return

        Returns:
            List of key record dicts
        """
        if self.engine is None:
            await self.initialize()

        query = select(api_keys_table)

        # Apply filters
        if customer_name:
            query = query.where(
                api_keys_table.c.customer_name.ilike(f"%{customer_name}%")
            )

        if tier:
            query = query.where(api_keys_table.c.tier == tier)

        if is_active is not None:
            query = query.where(api_keys_table.c.is_active == is_active)

        query = query.order_by(api_keys_table.c.created_at.desc()).limit(limit)

        async with self.engine.connect() as conn:
            result = await conn.execute(query)
            return [row._asdict() for row in result.fetchall()]

    async def revoke_api_key(self, api_key: str) -> bool:
        """
        Revoke (deactivate) API key.

        Args:
            api_key: Plain API key to revoke

        Returns:
            True if revoked successfully, False if not found
        """
        if self.engine is None:
            await self.initialize()

        key_hash = self.hash_api_key(api_key)

        async with self.engine.begin() as conn:
            result = await conn.execute(
                update(api_keys_table)
                .where(api_keys_table.c.key_hash == key_hash)
                .values(is_active=False)
            )

            if result.rowcount == 0:
                return False

            self.logger.info(f"Revoked API key: {self.get_key_prefix(api_key)}")
            return True

    async def revoke_by_id(self, key_id: int) -> bool:
        """
        Revoke (deactivate) API key by ID.

        Useful for admin operations when you only have the key ID,
        not the plain API key.

        Args:
            key_id: API key ID from database

        Returns:
            True if revoked successfully, False if not found
        """
        if self.engine is None:
            await self.initialize()

        async with self.engine.begin() as conn:
            result = await conn.execute(
                update(api_keys_table)
                .where(api_keys_table.c.id == key_id)
                .values(is_active=False)
            )

            if result.rowcount == 0:
                return False

            self.logger.info(f"Revoked API key ID: {key_id}")
            return True

    async def revoke_by_prefix(self, key_prefix: str) -> bool:
        """
        Revoke (deactivate) API key by prefix.

        Finds key by prefix and deactivates it.

        Args:
            key_prefix: Key prefix (e.g., "sk-ape-a1b2c3d4")

        Returns:
            True if revoked successfully, False if not found
        """
        if self.engine is None:
            await self.initialize()

        async with self.engine.begin() as conn:
            result = await conn.execute(
                update(api_keys_table)
                .where(api_keys_table.c.key_prefix == key_prefix)
                .values(is_active=False)
            )

            if result.rowcount == 0:
                return False

            self.logger.info(f"Revoked API key prefix: {key_prefix}")
            return True

    async def delete_api_key(self, api_key: str) -> bool:
        """
        Permanently delete API key.

        WARNING: This is irreversible. Prefer revoke_api_key() instead.

        Args:
            api_key: Plain API key to delete

        Returns:
            True if deleted successfully, False if not found
        """
        if self.engine is None:
            await self.initialize()

        key_hash = self.hash_api_key(api_key)

        async with self.engine.begin() as conn:
            result = await conn.execute(
                delete(api_keys_table).where(
                    api_keys_table.c.key_hash == key_hash
                )
            )

            if result.rowcount == 0:
                return False

            self.logger.warning(f"DELETED API key: {self.get_key_prefix(api_key)}")
            return True


# Global instance
_api_key_manager: Optional[APIKeyManager] = None


async def get_api_key_manager() -> APIKeyManager:
    """Get or create global APIKeyManager instance."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
        await _api_key_manager.initialize()
    return _api_key_manager
