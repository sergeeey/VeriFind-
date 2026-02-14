"""
VEE Sandbox Runner - Docker-based code execution.

Week 2 Day 1: Secure execution environment for LLM-generated code.

Security Features:
1. Network isolation (--network none by default)
2. Filesystem read-only (except /tmp)
3. Timeout enforcement (kills runaway processes)
4. Memory limits (prevents OOM attacks)
5. No privileged operations
6. Code hash tracking for audit
"""

import os
import docker
import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Optional, List

from src.temporal.integrity_checker import TemporalIntegrityChecker


@dataclass
class ExecutionResult:
    """Result of sandbox code execution."""

    status: str  # "success", "error", "timeout"
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    memory_used_mb: float
    executed_at: str  # ISO 8601 timestamp
    code_hash: str  # SHA-256 hash of executed code
    code: str = ""  # Week 5 Day 3: Executed source code for Debate System

    # Week 14: Validation fields for source_verified propagation
    source_verified: bool = False  # True only if execution successful AND output valid
    error_detected: bool = False  # True if Error/Exception in stdout/stderr
    ambiguity_detected: bool = False  # True if pandas Series ambiguity or similar


class SandboxRunner:
    """
    Docker-based sandbox for executing untrusted code.

    Design:
    - Each execution runs in ephemeral container
    - Container removed after execution
    - Resources limited via Docker
    - Network disabled by default
    """

    def __init__(
        self,
        image: str = "ape-vee-sandbox:latest",  # Week 11 Day 5: Custom image with yfinance, fredapi, pandas, numpy
        memory_limit: str = "256m",
        cpu_limit: float = 0.5,
        timeout: int = 30,
        enable_temporal_checks: bool = False,  # NEW: TIM integration
        query_date: Optional[datetime] = None  # NEW: For temporal validation
    ):
        """
        Initialize sandbox runner.

        Args:
            image: Docker image to use
            memory_limit: Memory limit (e.g., "256m", "1g")
            cpu_limit: CPU limit (fraction of CPU, 0.5 = 50%)
            timeout: Default timeout in seconds
            enable_temporal_checks: Enable Temporal Integrity Module (TIM)
            query_date: Query date for temporal validation (required if TIM enabled)
        """
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.timeout = timeout
        self.enable_temporal_checks = enable_temporal_checks
        self.query_date = query_date
        self.disable_docker_sandbox = bool(os.getenv("DISABLE_DOCKER_SANDBOX"))

        # Initialize Temporal Integrity Checker (if enabled)
        if enable_temporal_checks:
            self.tim = TemporalIntegrityChecker(enable_checks=True)
        else:
            self.tim = None

        if self.disable_docker_sandbox:
            self.docker_client = None
            return

        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Docker: {e}")

        # Pull image if not present
        try:
            self.docker_client.images.get(image)
        except docker.errors.ImageNotFound:
            print(f"Pulling image {image}...")
            self.docker_client.images.pull(image)

    def execute(
        self,
        code: str,
        timeout: Optional[int] = None,
        network_mode: str = "none",
        allow_subprocess: bool = False
    ) -> ExecutionResult:
        """
        Execute code in sandboxed environment.

        Args:
            code: Python code to execute
            timeout: Timeout in seconds (overrides default)
            network_mode: Docker network mode ("none", "bridge", "host")
            allow_subprocess: Allow subprocess execution (NOT RECOMMENDED)

        Returns:
            ExecutionResult with execution details
        """
        execution_timeout = timeout if timeout is not None else self.timeout
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        executed_at = datetime.now(UTC).isoformat()
        original_code = code  # Week 5 Day 3: Save for Debate System

        start_time = time.time()

        if self.disable_docker_sandbox or os.getenv("DISABLE_DOCKER_SANDBOX"):
            duration_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                status="success",
                exit_code=0,
                stdout="SANDBOX_DISABLED",
                stderr="",
                duration_ms=duration_ms,
                memory_used_mb=0.0,
                executed_at=executed_at,
                code_hash=code_hash,
                code=original_code
            )

        # NEW: Temporal Integrity Check (if enabled)
        if self.enable_temporal_checks and self.tim:
            if not self.query_date:
                raise ValueError("query_date required when temporal checks enabled")

            tim_result = self.tim.check_code(code, query_date=self.query_date)

            if tim_result.has_violations:
                # Get critical violations
                critical = tim_result.get_critical_violations()

                if critical:
                    # Block execution if critical violations found
                    duration_ms = int((time.time() - start_time) * 1000)
                    return ExecutionResult(
                        status="error",
                        exit_code=-2,  # Special code for temporal violation
                        stdout="",
                        stderr=f"TEMPORAL INTEGRITY VIOLATION:\n{tim_result.report}",
                        duration_ms=duration_ms,
                        memory_used_mb=0.0,
                        executed_at=executed_at,
                        code_hash=code_hash,
                        code=original_code
                    )

        # Prepare restricted code if subprocess disabled
        if not allow_subprocess:
            # Prepend code to block subprocess
            code = """
import sys
import builtins

# Block subprocess imports
original_import = builtins.__import__

def restricted_import(name, *args, **kwargs):
    if name == 'subprocess':
        raise ImportError("subprocess module is disabled in sandbox")
    return original_import(name, *args, **kwargs)

builtins.__import__ = restricted_import

# --- User code below ---
""" + code

        try:
            # Create container with security restrictions
            container = self.docker_client.containers.run(
                image=self.image,
                command=["python", "-u", "-c", code],  # -u = unbuffered output
                detach=True,
                remove=False,  # We'll remove manually after getting stats
                network_mode=network_mode,
                mem_limit=self.memory_limit,
                nano_cpus=int(self.cpu_limit * 1e9),  # Docker expects nanoseconds
                read_only=True,  # CRITICAL: Filesystem read-only
                tmpfs={'/tmp': 'rw,noexec,nosuid,size=100m'},  # Only /tmp writable
                security_opt=['no-new-privileges'],  # Prevent privilege escalation
                cap_drop=['ALL'],  # Drop all capabilities
            )

            # Wait for execution with timeout
            try:
                result = container.wait(timeout=execution_timeout)
                exit_code = result.get('StatusCode', -1)
                status = "success" if exit_code == 0 else "error"

            except Exception as timeout_error:
                # Timeout occurred
                container.kill()
                status = "timeout"
                exit_code = -1

            # Get stdout and stderr separately
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')

            # Get memory stats
            stats = container.stats(stream=False)
            memory_used_mb = stats['memory_stats'].get('usage', 0) / (1024 * 1024)

            # Clean up
            container.remove(force=True)

            duration_ms = int((time.time() - start_time) * 1000)

            # Week 14: Detect execution errors and ambiguity for source_verified
            error_detected = (
                exit_code != 0
                or 'Error' in stdout
                or 'Error' in stderr
                or 'Traceback' in stdout
                or 'Traceback' in stderr
                or 'Exception' in stdout
                or 'Exception' in stderr
            )

            # Detect pandas Series ambiguity and other common issues
            ambiguity_patterns = [
                'truth value.*ambiguous',
                'ambiguous',
                'ValueError',
                'TypeError',
                'KeyError',
                'IndexError',
            ]
            ambiguity_detected = any(
                pattern.lower() in stdout.lower() or pattern.lower() in stderr.lower()
                for pattern in ambiguity_patterns
            )

            # source_verified = True ONLY if: exit_code=0 AND no errors AND no ambiguity
            source_verified = (
                exit_code == 0
                and not error_detected
                and not ambiguity_detected
                and status == "success"
            )

            return ExecutionResult(
                status=status,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                memory_used_mb=memory_used_mb,
                executed_at=executed_at,
                code_hash=code_hash,
                code=original_code,
                source_verified=source_verified,  # NEW
                error_detected=error_detected,  # NEW
                ambiguity_detected=ambiguity_detected,  # NEW
            )

        except Exception as e:
            # Execution failed (Docker error, etc.)
            duration_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                status="error",
                exit_code=-1,
                stdout="",
                stderr=f"Sandbox execution failed: {str(e)}",
                duration_ms=duration_ms,
                memory_used_mb=0.0,
                executed_at=executed_at,
                code_hash=code_hash,
                code=original_code,
                source_verified=False,  # Docker failure = NOT verified
                error_detected=True,  # Exception occurred
                ambiguity_detected=False,  # No code execution, no ambiguity
            )

    def get_active_containers(self) -> List[str]:
        """
        Get list of active container IDs.

        Returns:
            List of container IDs (for cleanup verification)
        """
        if not self.docker_client:
            return []
        containers = self.docker_client.containers.list(
            filters={'ancestor': self.image}
        )
        return [c.id for c in containers]
