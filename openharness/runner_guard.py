"""Opt-in command resource guard. No downloads, services, cleanup or authority changes."""
import argparse
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


@contextmanager
def host_lock(path, wait_seconds):
    """All cooperating repos/accounts must use the same operator-owned local file.

    Never unlink it: removing a locked inode would permit a second independent lock.
    ACLs and a shared physical path are operator prerequisites, not auto-installed.
    """
    path = Path(path)
    if not path.is_absolute() or not path.parent.is_dir() or path.is_symlink():
        raise ValueError('lock requires an absolute path in an existing trusted directory')
    with path.open('a+b') as stream:
        deadline = time.monotonic() + wait_seconds
        while True:
            stream.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as error:
                if time.monotonic() >= deadline:
                    raise TimeoutError('host lock unavailable; command was not started') from error
                time.sleep(min(.05, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _windows_run(argv, timeout):
    """Create suspended, contain before resume, kill and drain descendants on exit.

    Kill-on-close also contains abrupt wrapper death. No breakaway is permitted.
    Assignment failure (including incompatible outer Jobs) stops before execution.
    """
    import ctypes as c
    from ctypes import wintypes as w

    class Startup(c.Structure):
        _fields_ = [('cb', w.DWORD), ('reserved', w.LPWSTR), ('desktop', w.LPWSTR),
                    ('title', w.LPWSTR), ('x', w.DWORD), ('y', w.DWORD),
                    ('xsize', w.DWORD), ('ysize', w.DWORD), ('xchars', w.DWORD),
                    ('ychars', w.DWORD), ('fill', w.DWORD), ('flags', w.DWORD),
                    ('show', w.WORD), ('reserved_size', w.WORD), ('reserved_data', c.c_void_p),
                    ('stdin', w.HANDLE), ('stdout', w.HANDLE), ('stderr', w.HANDLE)]

    class Process(c.Structure):
        _fields_ = [('process', w.HANDLE), ('thread', w.HANDLE),
                    ('pid', w.DWORD), ('tid', w.DWORD)]

    class BasicLimits(c.Structure):
        _fields_ = [('process_time', c.c_int64), ('job_time', c.c_int64),
                    ('flags', w.DWORD), ('min_working', c.c_size_t),
                    ('max_working', c.c_size_t), ('active_limit', w.DWORD),
                    ('affinity', c.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]

    class Limits(c.Structure):
        _fields_ = [('basic', BasicLimits), ('io', c.c_uint64 * 6),
                    ('process_memory', c.c_size_t), ('job_memory', c.c_size_t),
                    ('peak_process', c.c_size_t), ('peak_job', c.c_size_t)]

    class Accounting(c.Structure):
        _fields_ = [('times', c.c_int64 * 4), ('faults', w.DWORD),
                    ('total', w.DWORD), ('active', w.DWORD), ('terminated', w.DWORD)]

    kernel = c.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'CreateJobObjectW': ([c.c_void_p, w.LPCWSTR], w.HANDLE),
        'SetInformationJobObject': ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD], w.BOOL),
        'QueryInformationJobObject': ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.c_void_p], w.BOOL),
        'CreateProcessW': ([w.LPCWSTR, w.LPWSTR, c.c_void_p, c.c_void_p, w.BOOL,
                            w.DWORD, c.c_void_p, w.LPCWSTR, c.POINTER(Startup), c.POINTER(Process)], w.BOOL),
        'AssignProcessToJobObject': ([w.HANDLE, w.HANDLE], w.BOOL),
        'TerminateJobObject': ([w.HANDLE, w.UINT], w.BOOL),
        'TerminateProcess': ([w.HANDLE, w.UINT], w.BOOL),
        'ResumeThread': ([w.HANDLE], w.DWORD),
        'WaitForSingleObject': ([w.HANDLE, w.DWORD], w.DWORD),
        'GetExitCodeProcess': ([w.HANDLE, c.POINTER(w.DWORD)], w.BOOL),
        'GetStdHandle': ([w.DWORD], w.HANDLE),
        'CloseHandle': ([w.HANDLE], w.BOOL),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(kernel, name)
        function.argtypes, function.restype = arguments, result

    def require(result):
        if not result:
            raise c.WinError(c.get_last_error())
        return result

    executable = shutil.which(argv[0])
    if not executable or Path(executable).suffix.lower() != '.exe':
        raise ValueError('Windows command must resolve to an .exe; invoke scripts via an explicit interpreter')
    job = require(kernel.CreateJobObjectW(None, None))
    info, attached = Process(), False
    try:
        limits = Limits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        require(kernel.SetInformationJobObject(job, 9, c.byref(limits), c.sizeof(limits)))
        startup = Startup()
        startup.cb, startup.flags = c.sizeof(startup), 0x100  # STARTF_USESTDHANDLES
        startup.stdin = kernel.GetStdHandle(-10 & 0xffffffff)
        startup.stdout = kernel.GetStdHandle(-11 & 0xffffffff)
        startup.stderr = kernel.GetStdHandle(-12 & 0xffffffff)
        command = c.create_unicode_buffer(subprocess.list2cmdline([executable, *argv[1:]]))
        require(kernel.CreateProcessW(executable, command, None, None, True,
                                       0x08000004, None, None, c.byref(startup), c.byref(info)))
        require(kernel.AssignProcessToJobObject(job, info.process))
        attached = True
        if kernel.ResumeThread(info.thread) == 0xffffffff:
            raise c.WinError(c.get_last_error())
        deadline = time.monotonic() + timeout
        while True:
            status = kernel.WaitForSingleObject(info.process, 50)
            if status == 0:
                result = w.DWORD()
                require(kernel.GetExitCodeProcess(info.process, c.byref(result)))
                return result.value
            if status != 258:
                raise c.WinError(c.get_last_error())
            if time.monotonic() >= deadline:
                raise TimeoutError('command timeout')
    finally:
        try:
            if attached:
                require(kernel.TerminateJobObject(job, 124))
                # Retain the host lock until every contained process has exited.
                while True:
                    accounting = Accounting()
                    require(kernel.QueryInformationJobObject(job, 1, c.byref(accounting),
                                                              c.sizeof(accounting), None))
                    if accounting.active == 0:
                        break
                    time.sleep(.01)
            elif info.process:
                require(kernel.TerminateProcess(info.process, 124))
                kernel.WaitForSingleObject(info.process, 0xffffffff)
        finally:
            for handle in (info.thread, info.process, job):
                if handle:
                    kernel.CloseHandle(handle)


def _posix_run(argv, timeout):
    process = subprocess.Popen(argv, start_new_session=True)
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise TimeoutError('command timeout') from error
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def run(argv, *, lock_path, disk_path, min_free_bytes, wait_seconds, timeout_seconds):
    if (not isinstance(argv, list) or not argv or
            any(not isinstance(value, str) or '\0' in value for value in argv) or not argv[0]):
        raise ValueError('command requires a nonempty argv string array')
    if (type(min_free_bytes) is not int or min_free_bytes < 0 or
            any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0
                for v in (wait_seconds, timeout_seconds)) or timeout_seconds == 0):
        raise ValueError('budgets must be finite and nonnegative; timeout must be positive')
    with host_lock(lock_path, wait_seconds):
        free = shutil.disk_usage(disk_path).free
        if free < min_free_bytes:
            raise ValueError(f'disk preflight: {free} bytes available, {min_free_bytes} required')
        return (_windows_run if os.name == 'nt' else _posix_run)(argv, timeout_seconds)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', required=True)
    parser.add_argument('--disk', required=True)
    parser.add_argument('--min-free-bytes', type=int, required=True)
    parser.add_argument('--wait-seconds', type=float, required=True)
    parser.add_argument('--timeout-seconds', type=float, required=True)
    parser.add_argument('--argv-json', default=os.environ.get('OPENHARNESS_COMMAND_JSON'))
    args = parser.parse_args()
    try:
        command = json.loads(args.argv_json or '')
        return run(command, lock_path=args.lock, disk_path=args.disk,
                   min_free_bytes=args.min_free_bytes, wait_seconds=args.wait_seconds,
                   timeout_seconds=args.timeout_seconds)
    except (ValueError, OSError, TimeoutError) as error:
        print(f'Runner guard: {error}', file=sys.stderr)
        return 124 if isinstance(error, TimeoutError) else 2


if __name__ == '__main__':
    raise SystemExit(main())
