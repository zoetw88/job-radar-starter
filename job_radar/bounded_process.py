from __future__ import annotations

import os
import queue
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import BinaryIO, Sequence

from job_radar.windows_job import WindowsJob, resume_suspended_process, unique_job_name


_TASKKILL_TIMEOUT_SECONDS = 1
_PROCESS_WAIT_TIMEOUT_SECONDS = 1
_PIPE_THREAD_JOIN_TIMEOUT_SECONDS = 0.25


@dataclass(frozen=True)
class BoundedProcessResult:
    returncode: int
    stdout: str
    stderr: str


class ProcessOutputLimitError(ValueError):
    def __init__(self, stream: str, maximum_bytes: int):
        self.stream = stream
        self.maximum_bytes = maximum_bytes
        super().__init__(f"{stream} exceeded {maximum_bytes // (1024 * 1024)} MiB")


def kill_process_tree(
    process: subprocess.Popen[bytes],
    windows_job: WindowsJob | None = None,
) -> None:
    if windows_job is not None:
        windows_job.terminate()
        windows_job.wait_empty(_PROCESS_WAIT_TIMEOUT_SECONDS)
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
                text=True,
                timeout=_TASKKILL_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=_PROCESS_WAIT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=_PROCESS_WAIT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            pass


def _read_bounded(
    stream: BinaryIO,
    stream_name: str,
    maximum_bytes: int,
    events: queue.Queue[tuple[str, str | None]],
    output: bytearray,
) -> None:
    overflowed = False
    try:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            if overflowed:
                continue
            if len(output) + len(chunk) > maximum_bytes:
                overflowed = True
                events.put(("overflow", stream_name))
                continue
            output.extend(chunk)
    finally:
        events.put(("reader_done", stream_name))


def _write_input(
    stream: BinaryIO,
    payload: bytes,
    events: queue.Queue[tuple[str, str | None]],
) -> None:
    try:
        stream.write(payload)
        stream.close()
    except (BrokenPipeError, OSError):
        pass
    finally:
        events.put(("writer_done", None))


def run_bounded_process(
    command: Sequence[str],
    *,
    input_text: str,
    timeout_seconds: float,
    max_stdout_bytes: int = 1024 * 1024,
    max_stderr_bytes: int = 1024 * 1024,
) -> BoundedProcessResult:
    if not command or not str(command[0]).strip():
        raise ValueError("command must not be empty")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or timeout_seconds <= 0
    ):
        raise ValueError("timeout_seconds must be a positive number")
    for field, value in (
        ("max_stdout_bytes", max_stdout_bytes),
        ("max_stderr_bytes", max_stderr_bytes),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{field} must be a positive integer")

    launch_command = [str(part) for part in command]
    environment = None
    if os.name == "nt" and (
        os.path.normcase(launch_command[0]) == os.path.normcase(sys.executable)
        and os.path.normcase(sys._base_executable) != os.path.normcase(sys.executable)
    ):
        base_executable = os.path.join(sys.base_prefix, "python.exe")
        launch_command[0] = (
            base_executable if os.path.isfile(base_executable) else sys._base_executable
        )
        environment = os.environ.copy()
        environment.pop("__PYVENV_LAUNCHER__", None)
        inherited_paths = [path for path in sys.path if path]
        existing_pythonpath = environment.get("PYTHONPATH")
        if existing_pythonpath:
            inherited_paths.append(existing_pythonpath)
        environment["PYTHONPATH"] = os.pathsep.join(inherited_paths)
    windows_job = WindowsJob(unique_job_name()) if os.name == "nt" else None
    creationflags = 0x00000004 if windows_job is not None else 0
    try:
        process = subprocess.Popen(
            launch_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            creationflags=creationflags,
            start_new_session=os.name != "nt",
            env=environment,
        )
    except BaseException:
        if windows_job is not None:
            windows_job.close()
        raise
    if windows_job is not None:
        try:
            windows_job.assign_handle(int(process._handle))
            resume_suspended_process(process.pid)
        except BaseException:
            process.kill()
            process.wait(timeout=_PROCESS_WAIT_TIMEOUT_SECONDS)
            windows_job.close()
            raise
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    events: queue.Queue[tuple[str, str | None]] = queue.Queue()
    stdout = bytearray()
    stderr = bytearray()
    threads = [
        threading.Thread(
            target=_read_bounded,
            args=(process.stdout, "stdout", max_stdout_bytes, events, stdout),
            daemon=True,
        ),
        threading.Thread(
            target=_read_bounded,
            args=(process.stderr, "stderr", max_stderr_bytes, events, stderr),
            daemon=True,
        ),
        threading.Thread(
            target=_write_input,
            args=(process.stdin, input_text.encode("utf-8"), events),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()

    deadline = time.monotonic() + timeout_seconds
    readers_done = 0
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                kill_process_tree(process, windows_job)
                raise TimeoutError("process timed out")
            try:
                kind, stream_name = events.get(timeout=min(0.01, remaining))
            except queue.Empty:
                kind, stream_name = "", None
            if kind == "overflow":
                kill_process_tree(process, windows_job)
                maximum = (
                    max_stdout_bytes if stream_name == "stdout" else max_stderr_bytes
                )
                raise ProcessOutputLimitError(str(stream_name), maximum)
            if kind == "reader_done":
                readers_done += 1
            returncode = process.poll()
            if returncode is not None and readers_done == 2:
                break
    finally:
        if process.poll() is None:
            kill_process_tree(process, windows_job)
        thread_deadline = time.monotonic() + _PIPE_THREAD_JOIN_TIMEOUT_SECONDS
        for thread in threads:
            thread.join(timeout=max(0, thread_deadline - time.monotonic()))
        for pipe, thread in zip(
            (process.stdout, process.stderr, process.stdin),
            threads,
            strict=True,
        ):
            if thread.is_alive():
                continue
            try:
                pipe.close()
            except OSError:
                pass
        if windows_job is not None:
            windows_job.close()

    return BoundedProcessResult(
        returncode=process.returncode,
        stdout=stdout.decode("utf-8", errors="strict"),
        stderr=stderr.decode("utf-8", errors="replace"),
    )
