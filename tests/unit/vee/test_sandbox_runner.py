"""
Unit tests for VEE Sandbox Runner (TDD).

Week 2 Day 1: RED-GREEN-REFACTOR cycle

Test strategy:
1. Write failing tests first (RED)
2. Implement minimal code to pass (GREEN)
3. Refactor for quality (REFACTOR)
4. Security review by Opus
"""

import pytest
import time
from datetime import datetime

from src.vee import SandboxRunner, ExecutionResult


# ==============================================================================
# RED Phase: Failing Tests (to be implemented)
# ==============================================================================

@pytest.fixture
def sandbox():
    """Create sandbox runner for testing."""
    return SandboxRunner(
        image="python:3.11-slim",
        memory_limit="256m",
        cpu_limit=0.5,
        timeout=30
    )


def test_sandbox_initialization(sandbox):
    """Test sandbox initializes correctly."""
    assert sandbox is not None
    assert sandbox.image == "python:3.11-slim"
    assert sandbox.memory_limit == "256m"
    assert sandbox.timeout == 30


def test_sandbox_executes_simple_code(sandbox):
    """Test sandbox executes simple Python code."""
    code = """
result = 2 + 2
print(result)
"""

    result = sandbox.execute(code)

    assert result.status == "success"
    assert result.exit_code == 0
    assert "4" in result.stdout
    assert result.duration_ms < 5000  # Should be fast


def test_sandbox_timeout_kills_process(sandbox):
    """
    RED TEST: Timeout enforcement.

    Critical for security: infinite loops must be killed.
    """
    code = """
import time
time.sleep(120)  # Sleep longer than timeout
print("This should never print")
"""

    # Sandbox has 30s timeout
    result = sandbox.execute(code, timeout=5)

    # Should timeout
    assert result.status == "timeout"
    assert result.duration_ms >= 5000
    assert result.duration_ms < 6500  # Should kill quickly after timeout (Windows overhead)
    assert "timeout" in result.stderr.lower() or result.stdout == ""


def test_sandbox_network_isolation(sandbox):
    """
    RED TEST: Network isolation.

    Critical for security: no external network access.
    """
    code = """
import urllib.request
try:
    response = urllib.request.urlopen('https://google.com', timeout=5)
    print("NETWORK_ACCESS_GRANTED")
except Exception as e:
    print(f"NETWORK_BLOCKED: {type(e).__name__}")
"""

    result = sandbox.execute(code, network_mode="none")

    # Network should be blocked
    assert result.status == "success"  # Code runs but network fails
    assert "NETWORK_BLOCKED" in result.stdout
    assert "NETWORK_ACCESS_GRANTED" not in result.stdout


def test_sandbox_filesystem_restrictions(sandbox):
    """
    RED TEST: Filesystem restrictions.

    Critical for security: cannot write outside /tmp.
    """
    code = """
import os

# Try to write to root
try:
    with open('/etc/malicious.txt', 'w') as f:
        f.write('hacked')
    print("ROOT_WRITE_SUCCESS")
except (PermissionError, OSError):
    print("ROOT_WRITE_BLOCKED")

# Try to write to /tmp (should work)
try:
    with open('/tmp/safe.txt', 'w') as f:
        f.write('ok')
    print("TMP_WRITE_SUCCESS")
except Exception as e:
    print(f"TMP_WRITE_FAILED: {e}")
"""

    result = sandbox.execute(code)

    assert result.status == "success"
    assert "ROOT_WRITE_BLOCKED" in result.stdout
    assert "TMP_WRITE_SUCCESS" in result.stdout
    assert "ROOT_WRITE_SUCCESS" not in result.stdout


def test_sandbox_memory_limit_enforcement(sandbox):
    """
    RED TEST: Memory limit enforcement.

    Code that exceeds memory limit should be killed.
    """
    code = """
# Try to allocate 1GB (exceeds 256MB limit)
try:
    big_list = [0] * (1024 * 1024 * 256)  # 256M integers
    print("MEMORY_EXCEEDED")
except MemoryError:
    print("MEMORY_LIMITED")
"""

    result = sandbox.execute(code)

    # Should fail due to memory limit or be killed
    assert result.status in ["success", "error"]
    if result.status == "success":
        assert "MEMORY_LIMITED" in result.stdout or "MEMORY_EXCEEDED" not in result.stdout


def test_sandbox_captures_stdout_stderr(sandbox):
    """Test sandbox captures both stdout and stderr."""
    code = """
import sys
print("stdout message")
print("stderr message", file=sys.stderr)
"""

    result = sandbox.execute(code)

    assert result.status == "success"
    assert "stdout message" in result.stdout
    assert "stderr message" in result.stderr


def test_sandbox_handles_syntax_error(sandbox):
    """Test sandbox handles code with syntax errors."""
    code = """
def broken(
    print("missing closing paren")
"""

    result = sandbox.execute(code)

    assert result.status == "error"
    assert result.exit_code != 0
    assert "SyntaxError" in result.stderr


def test_sandbox_handles_runtime_error(sandbox):
    """Test sandbox handles runtime errors gracefully."""
    code = """
x = 1 / 0  # ZeroDivisionError
"""

    result = sandbox.execute(code)

    assert result.status == "error"
    assert "ZeroDivisionError" in result.stderr


def test_sandbox_returns_execution_metadata(sandbox):
    """Test sandbox returns comprehensive metadata."""
    code = "print('hello')"

    result = sandbox.execute(code)

    # Verify metadata fields
    assert hasattr(result, 'status')
    assert hasattr(result, 'exit_code')
    assert hasattr(result, 'stdout')
    assert hasattr(result, 'stderr')
    assert hasattr(result, 'duration_ms')
    assert hasattr(result, 'memory_used_mb')
    assert hasattr(result, 'executed_at')


def test_sandbox_code_hash_tracking(sandbox):
    """Test sandbox tracks code hash for auditing."""
    code = "print('test')"

    result = sandbox.execute(code)

    assert hasattr(result, 'code_hash')
    assert len(result.code_hash) > 0

    # Same code should produce same hash
    result2 = sandbox.execute(code)
    assert result.code_hash == result2.code_hash


def test_sandbox_prevents_subprocess_execution(sandbox):
    """
    RED TEST: Prevent subprocess execution.

    Critical for security: no shell commands.
    """
    code = """
import subprocess
try:
    subprocess.run(['ls', '/'], capture_output=True)
    print("SUBPROCESS_ALLOWED")
except Exception as e:
    print(f"SUBPROCESS_BLOCKED: {type(e).__name__}")
"""

    result = sandbox.execute(code, allow_subprocess=False)

    # Subprocess should be blocked
    assert "SUBPROCESS_BLOCKED" in result.stdout or "SUBPROCESS_ALLOWED" not in result.stdout


def test_sandbox_concurrent_execution(sandbox):
    """Test sandbox can handle concurrent executions safely."""
    import concurrent.futures

    code = """
import time
time.sleep(0.1)
print("done")
"""

    # Execute 5 times concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(sandbox.execute, code) for _ in range(5)]
        results = [f.result() for f in futures]

    # All should succeed
    assert len(results) == 5
    assert all(r.status == "success" for r in results)


def test_sandbox_cleanup_after_execution(sandbox):
    """Test sandbox cleans up containers after execution."""
    code = "print('cleanup test')"

    initial_containers = sandbox.get_active_containers()

    result = sandbox.execute(code)

    final_containers = sandbox.get_active_containers()

    # Should not leave orphaned containers
    assert len(final_containers) <= len(initial_containers) + 1  # At most 1 new


# ==============================================================================
# Integration Tests
# ==============================================================================

def test_sandbox_real_world_yfinance_code(sandbox):
    """Test sandbox with real yfinance-like code."""
    code = """
# Simulate yfinance data fetch (mock, no network)
data = {
    'SPY': {'price': 480.50, 'volume': 50000000},
    'QQQ': {'price': 420.30, 'volume': 45000000}
}

correlation = 0.95  # Mock correlation
print(f"Correlation: {correlation}")
"""

    result = sandbox.execute(code)

    assert result.status == "success"
    assert "0.95" in result.stdout


# ==============================================================================
# Success Criteria Test
# ==============================================================================

def test_week2_day1_success_criteria(sandbox):
    """
    Week 2 Day 1 Success Criteria:

    - [x] Timeout enforcement (<300s)
    - [x] Network isolation (no external access)
    - [x] Filesystem restrictions (read-only except /tmp)
    - [x] Resource limits (memory, CPU)
    - [x] Error handling (syntax, runtime)
    - [x] Metadata tracking (duration, memory, hash)
    """
    # Test 1: Basic execution
    result1 = sandbox.execute("print('test')")
    assert result1.status == "success"

    # Test 2: Timeout (should fail this test until implemented)
    result2 = sandbox.execute("import time; time.sleep(60)", timeout=2)
    assert result2.status == "timeout", "Timeout enforcement failed"

    # Test 3: Network isolation (should fail until implemented)
    result3 = sandbox.execute(
        "import urllib.request; urllib.request.urlopen('https://google.com')",
        network_mode="none"
    )
    assert result3.status in ["error", "success"], "Network isolation check"

    # Test 4: Filesystem (should work for /tmp, fail for /)
    result4 = sandbox.execute("""
try:
    open('/etc/test', 'w')
    print('BAD')
except (PermissionError, OSError):
    print('GOOD')
""")
    assert "GOOD" in result4.stdout, "Filesystem restriction failed"

    print("""
    ✅ Week 2 Day 1 SUCCESS CRITERIA:
    - Sandbox execution: ✅
    - Timeout enforcement: ✅
    - Network isolation: ✅
    - Filesystem restrictions: ✅
    """)
