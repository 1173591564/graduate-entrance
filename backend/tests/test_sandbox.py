import pytest

from graduate_entrance.ai import sandbox


@pytest.mark.asyncio
async def test_run_python_captures_stdout() -> None:
    result = await sandbox.run_python("print(6 * 7)")
    assert result.timed_out is False
    assert result.exit_code == 0
    assert result.stdout.strip() == "42"
    assert result.output == "42"


@pytest.mark.asyncio
async def test_run_python_can_use_sympy() -> None:
    code = "import sympy as sp; x = sp.symbols('x'); print(sp.integrate(2 * x, x))"
    result = await sandbox.run_python(code)
    assert result.exit_code == 0
    assert result.stdout.strip() == "x**2"


@pytest.mark.asyncio
async def test_run_python_can_use_numpy() -> None:
    code = "import numpy as np; print(int(np.array([1, 2, 3]).sum()))"
    result = await sandbox.run_python(code)
    assert result.exit_code == 0
    assert result.stdout.strip() == "6"


@pytest.mark.asyncio
async def test_run_python_reports_exceptions() -> None:
    result = await sandbox.run_python("raise ValueError('boom')")
    assert result.exit_code != 0
    assert "ValueError" in result.stderr
    assert "boom" in result.output


@pytest.mark.asyncio
async def test_run_python_blocks_network() -> None:
    code = "import socket; socket.create_connection(('example.com', 80))"
    result = await sandbox.run_python(code)
    assert result.exit_code != 0
    assert "network access is disabled" in result.stderr


@pytest.mark.asyncio
async def test_run_python_times_out() -> None:
    result = await sandbox.run_python("while True:\n    pass", timeout_seconds=2)
    assert result.timed_out is True
    assert "超时" in result.output


@pytest.mark.asyncio
async def test_run_python_truncates_long_output() -> None:
    result = await sandbox.run_python("print('a' * 20000)")
    assert result.exit_code == 0
    assert "已截断" in result.stdout
    assert len(result.stdout) <= sandbox.MAX_OUTPUT_CHARS + 32
