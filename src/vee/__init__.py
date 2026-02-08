"""
VEE - Verifiable Execution Environment for APE 2026.

Week 2 Day 1: Docker-based sandbox for executing LLM-generated code.

Security principles:
1. Network isolation (no internet except approved APIs)
2. Filesystem restrictions (read-only except /tmp)
3. Timeout enforcement (max 300s)
4. Resource limits (CPU, memory)
5. No privileged operations
"""

from .sandbox_runner import SandboxRunner, ExecutionResult

__all__ = ["SandboxRunner", "ExecutionResult"]
