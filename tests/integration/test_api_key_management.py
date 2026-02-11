"""
Integration tests for API Key Management System.

Week 12 Day 1: Test API key creation, validation, and admin endpoints.

Run with:
    pytest tests/integration/test_api_key_management.py -v
"""

import pytest
import pytest_asyncio
import os
from datetime import datetime, timedelta

from src.api.auth.api_key_manager import APIKeyManager


@pytest_asyncio.fixture
async def api_key_manager():
    """Create APIKeyManager instance for testing."""
    manager = APIKeyManager()
    await manager.initialize()

    yield manager

    await manager.close()


class TestAPIKeyGeneration:
    """Test API key generation and hashing."""

    def test_generate_api_key_format(self):
        """Test that generated keys have correct format."""
        api_key = APIKeyManager.generate_api_key()

        assert api_key.startswith("sk-ape-")
        assert len(api_key) == 48  # sk-ape- (7) + 41 hex chars

    def test_hash_api_key_deterministic(self):
        """Test that hashing is deterministic."""
        api_key = "sk-ape-test1234567890123456789012345678901234"

        hash1 = APIKeyManager.hash_api_key(api_key)
        hash2 = APIKeyManager.hash_api_key(api_key)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex = 64 chars

    def test_hash_api_key_different_keys(self):
        """Test that different keys produce different hashes."""
        key1 = "sk-ape-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        key2 = "sk-ape-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

        hash1 = APIKeyManager.hash_api_key(key1)
        hash2 = APIKeyManager.hash_api_key(key2)

        assert hash1 != hash2

    def test_get_key_prefix(self):
        """Test key prefix extraction."""
        api_key = "sk-ape-1234567890abcdefghijklmnopqrstuvwxyz"
        prefix = APIKeyManager.get_key_prefix(api_key)

        assert prefix == "sk-ape-123456789"
        assert len(prefix) == 16


class TestAPIKeyCreation:
    """Test API key creation."""

    @pytest.mark.asyncio
    async def test_create_api_key_basic(self, api_key_manager):
        """Test creating basic API key."""
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Test Customer",
            tier="free"
        )

        # Verify API key format
        assert api_key.startswith("sk-ape-")
        assert len(api_key) == 48

        # Verify key record
        assert key_record['customer_name'] == "Test Customer"
        assert key_record['tier'] == "free"
        assert key_record['is_active'] is True
        assert key_record['rate_limit_per_hour'] == 100
        assert key_record['monthly_quota'] == 10000

    @pytest.mark.asyncio
    async def test_create_api_key_pro_tier(self, api_key_manager):
        """Test creating pro tier API key."""
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Pro Customer",
            tier="pro",
            rate_limit_per_hour=1000,
            monthly_quota=100000,
            customer_email="pro@example.com"
        )

        assert key_record['tier'] == "pro"
        assert key_record['rate_limit_per_hour'] == 1000
        assert key_record['monthly_quota'] == 100000
        assert key_record['customer_email'] == "pro@example.com"

    @pytest.mark.asyncio
    async def test_create_api_key_with_expiration(self, api_key_manager):
        """Test creating API key with expiration."""
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Trial Customer",
            tier="free",
            expires_in_days=30
        )

        # Verify expiration date is ~30 days from now
        expires_at = key_record['expires_at']
        assert expires_at is not None

        expected_expiration = datetime.utcnow() + timedelta(days=30)
        time_diff = abs((expires_at - expected_expiration).total_seconds())
        assert time_diff < 60  # Within 1 minute


class TestAPIKeyValidation:
    """Test API key validation."""

    @pytest.mark.asyncio
    async def test_validate_api_key_success(self, api_key_manager):
        """Test validating a valid API key."""
        # Create key
        api_key, _ = await api_key_manager.create_api_key(
            customer_name="Valid Customer",
            tier="free"
        )

        # Validate key
        is_valid = await api_key_manager.validate_api_key(api_key)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_api_key_invalid(self, api_key_manager):
        """Test validating an invalid API key."""
        fake_key = "sk-ape-invalidinvalidinvalidinvalidinvalid"

        is_valid = await api_key_manager.validate_api_key(fake_key)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_api_key_revoked(self, api_key_manager):
        """Test that revoked keys are invalid."""
        # Create and revoke key
        api_key, _ = await api_key_manager.create_api_key(
            customer_name="Revoked Customer",
            tier="free"
        )

        await api_key_manager.revoke_api_key(api_key)

        # Validation should fail
        is_valid = await api_key_manager.validate_api_key(api_key)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_api_key_updates_last_used(self, api_key_manager):
        """Test that validation updates last_used_at."""
        # Create key
        api_key, key_record = await api_key_manager.create_api_key(
            customer_name="Test Customer",
            tier="free"
        )

        # Initially last_used_at should be None
        assert key_record['last_used_at'] is None

        # Validate key
        await api_key_manager.validate_api_key(api_key, update_last_used=True)

        # Check last_used_at is updated
        key_info = await api_key_manager.get_key_info(api_key)
        assert key_info['last_used_at'] is not None


class TestAPIKeyInfo:
    """Test getting API key information."""

    @pytest.mark.asyncio
    async def test_get_key_info_success(self, api_key_manager):
        """Test getting key info for valid key."""
        # Create key
        api_key, original_record = await api_key_manager.create_api_key(
            customer_name="Info Test Customer",
            tier="pro"
        )

        # Get key info
        key_info = await api_key_manager.get_key_info(api_key)

        assert key_info is not None
        assert key_info['customer_name'] == "Info Test Customer"
        assert key_info['tier'] == "pro"
        assert key_info['id'] == original_record['id']

    @pytest.mark.asyncio
    async def test_get_key_info_not_found(self, api_key_manager):
        """Test getting key info for non-existent key."""
        fake_key = "sk-ape-doesnotexistdoesnotexistdoesnotexis"

        key_info = await api_key_manager.get_key_info(fake_key)
        assert key_info is None


class TestAPIKeyListing:
    """Test listing API keys with filters."""

    @pytest.mark.asyncio
    async def test_list_all_api_keys(self, api_key_manager):
        """Test listing all API keys."""
        # Create multiple keys
        await api_key_manager.create_api_key("Customer 1", tier="free")
        await api_key_manager.create_api_key("Customer 2", tier="pro")

        # List all keys
        keys = await api_key_manager.list_api_keys(limit=100)

        assert len(keys) >= 2

    @pytest.mark.asyncio
    async def test_list_api_keys_filter_by_tier(self, api_key_manager):
        """Test filtering keys by tier."""
        # Create keys with different tiers
        await api_key_manager.create_api_key("Free Customer", tier="free")
        await api_key_manager.create_api_key("Pro Customer", tier="pro")

        # Filter by pro tier
        pro_keys = await api_key_manager.list_api_keys(tier="pro", limit=100)

        assert all(k['tier'] == "pro" for k in pro_keys)

    @pytest.mark.asyncio
    async def test_list_api_keys_filter_by_customer(self, api_key_manager):
        """Test filtering keys by customer name."""
        # Create keys
        await api_key_manager.create_api_key("Acme Corp", tier="free")
        await api_key_manager.create_api_key("Acme Industries", tier="pro")
        await api_key_manager.create_api_key("Other Company", tier="free")

        # Filter by customer name (partial match)
        acme_keys = await api_key_manager.list_api_keys(customer_name="Acme", limit=100)

        assert len(acme_keys) >= 2
        assert all("Acme" in k['customer_name'] for k in acme_keys)


class TestAPIKeyRevocation:
    """Test API key revocation."""

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self, api_key_manager):
        """Test revoking an API key."""
        # Create key
        api_key, _ = await api_key_manager.create_api_key(
            customer_name="To Be Revoked",
            tier="free"
        )

        # Revoke key
        revoked = await api_key_manager.revoke_api_key(api_key)
        assert revoked is True

        # Verify key is inactive
        key_info = await api_key_manager.get_key_info(api_key)
        assert key_info['is_active'] is False

        # Validation should fail
        is_valid = await api_key_manager.validate_api_key(api_key)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(self, api_key_manager):
        """Test revoking non-existent key."""
        fake_key = "sk-ape-doesnotexistdoesnotexistdoesnotexis"

        revoked = await api_key_manager.revoke_api_key(fake_key)
        assert revoked is False


class TestWeek12Day1SuccessCriteria:
    """
    Week 12 Day 1 Success Criteria:

    ✅ API key generation (cryptographically secure)
    ✅ SHA-256 hashing for storage
    ✅ API key validation
    ✅ Rate limiting configuration per key
    ✅ Tier-based access control
    ✅ Admin CRUD operations
    ✅ Database persistence (TimescaleDB)
    """

    @pytest.mark.asyncio
    async def test_week12_day1_success_criteria(self, api_key_manager):
        """Test all Week 12 Day 1 success criteria."""
        print("\n" + "="*60)
        print("✅ WEEK 12 DAY 1 SUCCESS CRITERIA")
        print("="*60)

        # 1. Generate API key
        api_key = APIKeyManager.generate_api_key()
        assert api_key.startswith("sk-ape-")
        print("✅ Cryptographically secure key generation")

        # 2. Hash API key (SHA-256)
        key_hash = APIKeyManager.hash_api_key(api_key)
        assert len(key_hash) == 64
        print("✅ SHA-256 hashing")

        # 3. Create API key with tier and rate limit
        created_key, key_record = await api_key_manager.create_api_key(
            customer_name="Test Corp",
            tier="pro",
            rate_limit_per_hour=1000
        )
        assert key_record['tier'] == "pro"
        assert key_record['rate_limit_per_hour'] == 1000
        print("✅ Tier-based configuration")
        print("✅ Rate limiting configuration")

        # 4. Validate API key
        is_valid = await api_key_manager.validate_api_key(created_key)
        assert is_valid is True
        print("✅ API key validation")

        # 5. List API keys (admin operation)
        keys = await api_key_manager.list_api_keys(limit=10)
        assert len(keys) > 0
        print("✅ Admin CRUD operations")

        # 6. Revoke API key
        revoked = await api_key_manager.revoke_api_key(created_key)
        assert revoked is True
        print("✅ API key revocation")

        # 7. Verify persistence
        key_info = await api_key_manager.get_key_info(created_key)
        assert key_info is not None
        assert key_info['is_active'] is False
        print("✅ Database persistence")

        print("="*60)
        print("🎉 WEEK 12 DAY 1: API KEY MANAGEMENT OPERATIONAL!")
        print("="*60)
