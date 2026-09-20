from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from research_harness.common import HarnessError, digest, now

ISOLATION = ["readonly_inputs", "private_writes", "no_network", "pid_namespace", "no_home",
             "closed_fds", "dropped_capabilities", "resource_limits", "no_source_or_store"]


def base_command():
    binary = shutil.which("bwrap")
    if sys.platform != "linux" or not binary or not Path("/usr/bin/python3").is_file():
        raise HarnessError("capability_blocked", "Contained runner requires Linux, working bwrap and /usr/bin/python3")
    command = [binary, "--unshare-all", "--die-with-parent", "--new-session", "--cap-drop", "ALL", "--clearenv"]
    for path in ("/usr", "/bin", "/lib", "/lib64"):
        if Path(path).exists():
            command += ["--ro-bind", path, path]
    return command + ["--proc", "/proc", "--dev", "/dev", "--dir", "/tmp", "--dir", "/work",
                      "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "LANG", "C.UTF-8",
                      "--setenv", "HOME", "/nonexistent", "--setenv", "PYTHONDONTWRITEBYTECODE", "1"]


def capabilities():
    try:
        result = subprocess.run(base_command() + ["/usr/bin/python3", "-I", "-c", "print('contained')"],
                                capture_output=True, timeout=10, close_fds=True)
        available = result.returncode == 0 and result.stdout.strip() == b"contained"
        reason = None if available else result.stderr.decode(errors="replace")[:400]
    except (HarnessError, OSError, subprocess.SubprocessError) as error:
        available, reason = False, str(error)
    return {"cooperative": True, "contained": available, "isolation": ISOLATION if available else [],
            "reason": reason, "scientific_runtime": "stdlib Python; explicit additional runtimes are not auto-installed"}


def safe_relative(path):
    p = Path(path)
    if not path or p.is_absolute() or ".." in p.parts or "\x00" in path or str(p) != path:
        raise HarnessError("permission_denied", "Projection path must be a normalized relative path")
    if path.startswith("_retro_"):
        raise HarnessError("permission_denied", "Reserved broker filename")
    return p


def run(projected, script, limits, output_directory):
    caps = capabilities()
    if not caps["contained"]:
        raise HarnessError("capability_blocked", caps["reason"])
    for key, ceiling in (("wall_seconds", 60), ("memory_bytes", 1073741824), ("max_output_bytes", 16777216)):
        if type(limits.get(key)) is not int or not 1 <= limits[key] <= ceiling:
            raise HarnessError("permission_denied", "Resource request outside broker limits: " + key)
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=False)
    started = now()
    with tempfile.TemporaryDirectory(prefix="retro-input-") as temporary:
        inputs = Path(temporary)
        for path, content in projected.items():
            target = inputs / safe_relative(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        (inputs / "_retro_probe.py").write_bytes(script)
        # This bootstrap is broker-owned. Mutable project material cannot change
        # limits or the program chosen by the parent. -I blocks PYTHONPATH/site.
        bootstrap = '''import os, resource, runpy, sys
resource.setrlimit(resource.RLIMIT_AS, (MEMORY, MEMORY))
resource.setrlimit(resource.RLIMIT_CPU, (SECONDS, SECONDS))
resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT, OUTPUT))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
sys.path.insert(0, "/input")
runpy.run_path("/input/_retro_probe.py", run_name="__main__")
'''.replace("MEMORY", str(limits["memory_bytes"])).replace("SECONDS", str(limits["wall_seconds"])).replace("OUTPUT", str(limits["max_output_bytes"]))
        (inputs / "_retro_bootstrap.py").write_text(bootstrap)
        command = base_command() + ["--ro-bind", str(inputs), "/input", "--bind", str(output_directory), "/work",
                                    "--chdir", "/work", "/usr/bin/python3", "-I", "/input/_retro_bootstrap.py"]
        termination = "exited"
        # Parent-owned logs are outside the worker's writable projection.
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, close_fds=True, start_new_session=True,
                                       env={"PATH": os.defpath})
            deadline = time.monotonic() + limits["wall_seconds"]
            try:
                while process.poll() is None:
                    size = os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size
                    count = 0
                    for folder, dirs, files in os.walk(output_directory, followlinks=False):
                        dirs[:] = [d for d in dirs if not (Path(folder) / d).is_symlink()]
                        for name in files:
                            p = Path(folder) / name
                            count += 1
                            try:
                                size += p.lstat().st_size
                            except FileNotFoundError:
                                pass
                            if count > 2048 or size > limits["max_output_bytes"]:
                                break
                        if count > 2048 or size > limits["max_output_bytes"]:
                            break
                    if time.monotonic() >= deadline:
                        termination = "timeout"
                    elif count > 2048 or size > limits["max_output_bytes"]:
                        termination = "resource_limit"
                    if termination != "exited":
                        os.killpg(process.pid, signal.SIGKILL)
                        break
                    time.sleep(0.05)
                process.wait(timeout=5)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            stdout.seek(0)
            stderr.seek(0)
            out = stdout.read(limits["max_output_bytes"])
            err = stderr.read(limits["max_output_bytes"])
        captured = {}
        total = len(out) + len(err)
        for p in sorted(output_directory.rglob("*")):
            if p.is_symlink() or not p.is_file() or total + p.stat().st_size > limits["max_output_bytes"]:
                continue
            captured[str(p.relative_to(output_directory))] = p.read_bytes()
            total += len(captured[str(p.relative_to(output_directory))])
    if process.returncode and termination == "exited" and (process.returncode < 0 or b"MemoryError" in err or b"File too large" in err):
        termination = "resource_limit"
    return {"returncode": process.returncode, "termination": termination, "started": started, "finished": now(),
            "stdout": out, "stderr": err, "files": captured, "isolation_observed": ISOLATION,
            "runner_sha256": digest(Path(__file__).read_bytes()), "script_sha256": digest(script)}
