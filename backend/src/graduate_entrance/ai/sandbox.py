"""Restricted Python sandbox used by ChatLearning to verify calculations.

Executes model-generated code in a fresh, isolated ``python3 -I`` subprocess with
CPU/memory limits, no network access and no writable filesystem. Every call is a new
process with no shared state.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import resource
import signal
import sys
from dataclasses import dataclass

# Prelude injected before user code: block network access inside the sandbox
# process (the backend container itself keeps network for the AI API).
_PRELUDE = """
def _blocked(*_args, **_kwargs):
    raise OSError("network access is disabled in the sandbox")


try:
    import socket as _socket

    _socket.socket = _blocked
    _socket.create_connection = _blocked
    if hasattr(_socket, "create_server"):
        _socket.create_server = _blocked
except Exception:
    pass
"""

MAX_OUTPUT_CHARS = 8192
DEFAULT_TIMEOUT_SECONDS = 15
# RLIMIT_AS caps virtual address space; numpy/sympy reserve large regions on
# import, so this is kept well above the resident memory we actually expect.
DEFAULT_MEMORY_LIMIT_MB = 1024

_semaphore = asyncio.Semaphore(2)


@dataclass(frozen=True)
class SandboxResult:
    stdout: str
    stderr: str
    timed_out: bool
    exit_code: int | None

    @property
    def output(self) -> str:
        parts: list[str] = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr.rstrip())
        if self.timed_out:
            parts.append(f"[执行超时，已终止（>{DEFAULT_TIMEOUT_SECONDS}s）]")
        text = "\n".join(parts).strip()
        if not text:
            return "(无输出)"
        return text


def _limits(memory_limit_mb: int, timeout_seconds: int) -> None:
    cpu_seconds = max(1, timeout_seconds)
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
    memory_bytes = memory_limit_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    os.setsid()


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n…[输出过长已截断]"


async def run_python(
    code: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB,
) -> SandboxResult:
    """Run ``code`` in an isolated subprocess and capture stdout/stderr."""
    program = f"{_PRELUDE}\n{code}"
    async with _semaphore:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-c",
            program,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
            cwd="/tmp",
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            preexec_fn=lambda: _limits(memory_limit_mb, timeout_seconds),
        )
        timed_out = False
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout_seconds
            )
        except TimeoutError:
            timed_out = True
            stdout_bytes, stderr_bytes = b"", b""
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(process.wait(), timeout=5)

    return SandboxResult(
        stdout=_truncate(stdout_bytes.decode("utf-8", "replace")),
        stderr=_truncate(stderr_bytes.decode("utf-8", "replace")),
        timed_out=timed_out,
        exit_code=process.returncode,
    )
