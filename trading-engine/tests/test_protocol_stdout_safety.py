"""
Tests that the sidecar protocol stream (stdout) is protected from corruption.

Covers:
- builtins.print() redirect to stderr (main.py monkey-patch)
- emitter uses os.write() for atomic writes
- concurrent emitter writes produce valid JSON lines (no interleaving)
"""

import builtins
import io
import json
import os
import sys
import subprocess
import threading

ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

ROOT_DIR = os.path.dirname(ENGINE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def _apply_print_redirect():
    """Apply the same redirect as main.py"""
    _original_print = builtins.print

    def _stderr_print(*args, **kwargs):
        kwargs["file"] = sys.stderr
        _original_print(*args, **kwargs)

    builtins.print = _stderr_print
    return _original_print


def test_print_redirect_does_not_write_to_stdout():
    """print() should go to stderr, not stdout, after redirect."""
    orig = _apply_print_redirect()
    try:
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        print("should not appear on stdout")
        sys.stdout = old_stdout
        assert captured.getvalue() == "", f"print leaked to stdout: {repr(captured.getvalue())}"
    finally:
        builtins.print = orig


def test_emitter_uses_raw_fd():
    """emitter._stdout_fd should be a valid file descriptor."""
    from protocol.emitter import _stdout_fd
    assert isinstance(_stdout_fd, int)
    assert _stdout_fd >= 0


def test_emitter_produces_valid_json_via_subprocess():
    """_send() should write exactly one valid JSON line to stdout when run in a subprocess."""
    venv_python = os.path.join(ENGINE_DIR, ".venv", "bin", "python3")
    if not os.path.isfile(venv_python):
        venv_python = sys.executable

    script = f"""
import sys, os
sys.path.insert(0, {ENGINE_DIR!r})
sys.path.insert(0, {ROOT_DIR!r})
from protocol.emitter import _send
_send({{"event": "test_event", "data": {{"key": "value"}}}})
"""
    result = subprocess.run(
        [venv_python, "-c", script],
        capture_output=True, text=True, timeout=10,
    )
    lines = result.stdout.strip().split("\n")
    assert len(lines) == 1, f"Expected 1 line, got {len(lines)}: {lines}"
    parsed = json.loads(lines[0])
    assert parsed["event"] == "test_event"
    assert parsed["data"]["key"] == "value"


def test_concurrent_writes_produce_valid_json_lines():
    """Multiple threads writing via _send() should produce 100 valid JSON lines."""
    venv_python = os.path.join(ENGINE_DIR, ".venv", "bin", "python3")
    if not os.path.isfile(venv_python):
        venv_python = sys.executable

    script = f"""
import sys, os, threading
sys.path.insert(0, {ENGINE_DIR!r})
sys.path.insert(0, {ROOT_DIR!r})
from protocol.emitter import _send

def writer(tid, count):
    for i in range(count):
        _send({{"event": "thread_test", "data": {{"tid": tid, "i": i}}}})

threads = [threading.Thread(target=writer, args=(t, 20)) for t in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()
"""
    result = subprocess.run(
        [venv_python, "-c", script],
        capture_output=True, text=True, timeout=10,
    )
    lines = result.stdout.strip().split("\n")
    assert len(lines) == 100, f"Expected 100 lines from 5 threads x 20, got {len(lines)}"
    errors = []
    for i, line in enumerate(lines):
        try:
            parsed = json.loads(line)
            assert parsed["event"] == "thread_test"
        except (json.JSONDecodeError, AssertionError) as e:
            errors.append(f"Line {i}: {e} — {repr(line[:100])}")
    assert not errors, "Corrupted lines found:\n" + "\n".join(errors[:5])


def test_print_does_not_corrupt_protocol_in_subprocess():
    """Concurrent print() + _send() should not corrupt JSON lines (main.py redirect active)."""
    venv_python = os.path.join(ENGINE_DIR, ".venv", "bin", "python3")
    if not os.path.isfile(venv_python):
        venv_python = sys.executable

    script = f"""
import sys, os, builtins, threading
sys.path.insert(0, {ENGINE_DIR!r})
sys.path.insert(0, {ROOT_DIR!r})

# Apply the same redirect as main.py
_orig = builtins.print
def _stderr_print(*args, **kwargs):
    kwargs["file"] = sys.stderr
    _orig(*args, **kwargs)
builtins.print = _stderr_print

from protocol.emitter import _send

def protocol_writer(count):
    for i in range(count):
        _send({{"event": "proto", "data": {{"i": i}}}})

def noise_printer(count):
    for i in range(count):
        print(f"PNL Update for Req 1 - Daily: {{i}}, Unrealized: {{i}}, Realized: {{i}}")

t1 = threading.Thread(target=protocol_writer, args=(50,))
t2 = threading.Thread(target=noise_printer, args=(50,))
t1.start()
t2.start()
t1.join()
t2.join()
"""
    result = subprocess.run(
        [venv_python, "-c", script],
        capture_output=True, text=True, timeout=10,
    )
    lines = result.stdout.strip().split("\n")
    assert len(lines) == 50, f"Expected 50 protocol lines on stdout, got {len(lines)}"
    for i, line in enumerate(lines):
        parsed = json.loads(line)
        assert parsed["event"] == "proto", f"Line {i} has wrong event: {parsed}"
    # print() output should be on stderr, not stdout
    assert "PNL Update" in result.stderr, "print() output should appear on stderr"
    assert "PNL Update" not in result.stdout, "print() output should NOT appear on stdout"
