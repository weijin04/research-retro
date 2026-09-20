"""Portable shell interface; direct commands and tool calls share one dispatcher."""
import argparse
import json
import sys
from importlib.resources import files
from pathlib import Path
from research_harness import __version__
from research_harness.agent_tools import invoke, definitions, CONTRACT_VERSION
from research_harness.config import workspace_path
from research_harness.common import HarnessError


def load_input(path):
    return json.loads(sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="retro", description="Standalone evidence-bounded research retrospective. Start: retro init PROJECT")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--workspace", "-w", help="Explicit workspace; then RETRO_WORKSPACE; then CWD/.retro")
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("init", help="Initialize PROJECT/.retro or an explicit independent workspace")
    start.add_argument("project")
    start.add_argument("--workspace", "-w", default=argparse.SUPPRESS)
    start.add_argument("--project-id")
    start.add_argument("--capture-max-bytes", type=int, help="Per-file capture limit (default 1048576)")
    start.add_argument("--scan-max-entries", type=int, help="Census entry limit (default 250000)")
    start.add_argument("--exclude", dest="excludes", action="append", help="Additional excluded path component; repeatable")
    start.add_argument("--metadata-only", dest="capture_text", action="store_false", default=None)
    sub.add_parser("scan", help="Enumerate assets; capture bounded text; retain gaps")
    read = sub.add_parser("read", help="Read a pinned original by artifact ID or project-relative path")
    read.add_argument("reference")
    read.add_argument("--revision", type=int)
    read.add_argument("--start", type=int, default=1)
    read.add_argument("--end", type=int)
    read.add_argument("--live", action="store_true")
    reconstruct = sub.add_parser("reconstruct", help="Add host-authored unchecked statements and conditional dependencies")
    reconstruct.add_argument("--input", required=True, help="JSON document or - for stdin; see retro agent")
    audit = sub.add_parser("audit", help="Open/resume a deep audit, run a check, or submit completed analysis")
    audits = audit.add_subparsers(dest="action", required=True)
    opened = audits.add_parser("open")
    opened.add_argument("--id", required=True)
    opened.add_argument("--targets", nargs="+", required=True)
    opened.add_argument("--question", required=True)
    opened.add_argument("--scope", required=True, help="JSON object with explicit scientific conditions")
    opened.add_argument("--obligation", dest="obligations", action="append", required=True)
    opened.add_argument("--mode", choices=["derive", "check"], default="derive")
    opened.add_argument("--alternative", dest="alternatives", action="append", default=[])
    for action in ("packet", "check", "submit"):
        command = audits.add_parser(action)
        command.add_argument("id")
        if action == "check":
            command.add_argument("--script", required=True, help="Host-authored Python file inside workspace; never an original script")
        if action == "submit":
            command.add_argument("--input", required=True, help="Completed result using packet.result_template")
    correct = sub.add_parser("correct", help="Apply audit-backed corrections and propagate invalidation")
    correct.add_argument("--input", required=True, help="JSON: audit_id, result_revision, operations, reason, idempotency_key")
    export = sub.add_parser("export", help="Rehash originals and write a complete handoff")
    export.add_argument("--destination", help="Empty path inside workspace; default exports/<unique-id>")
    inspect = sub.add_parser("inspect", help="Verify/read a frozen bundle without original project")
    inspect.add_argument("bundle")
    state = sub.add_parser("state", help="Inspect authoritative state and version history")
    state.add_argument("action", choices=["status", "get", "history", "events", "verify", "provenance"], nargs="?", default="status")
    state.add_argument("id", nargs="?")
    call = sub.add_parser("call", help="Function interface: {name,arguments}; same contract as direct CLI")
    call.add_argument("--input", default="-", help="JSON file or - for stdin")
    sub.add_parser("tools", help="Print versioned function definitions; no project required")
    sub.add_parser("agent", help="Print Agent manual; no project required")
    args = parser.parse_args(argv)
    try:
        data = vars(args).copy()
        command, workspace = data.pop("command"), data.pop("workspace")
        if command == "agent":
            print(files("research_harness.resources").joinpath("AGENT.md").read_text())
            return 0
        if command == "tools":
            envelope = {"contract_version": CONTRACT_VERSION, "ok": True, "result": definitions()}
        elif command == "call":
            envelope = invoke(load_input(data["input"]))
        else:
            if command not in ("init", "inspect"):
                data["workspace"] = str(workspace_path(workspace))
            elif command == "init" and workspace:
                data["workspace"] = workspace
            if command == "reconstruct":
                data["document"] = load_input(data.pop("input"))
            elif command == "correct":
                correction = load_input(data.pop("input"))
                if "workspace" in correction:
                    raise ValueError("Correction input must not override --workspace")
                data.update(correction)
            elif command == "audit" and data["action"] == "submit":
                data["result"] = load_input(data.pop("input"))
            elif command == "audit" and data["action"] == "open":
                data["scope"] = json.loads(data["scope"])
            data = {key: value for key, value in data.items() if value is not None}
            envelope = invoke({"name": "retro_" + command, "arguments": data})
    except (HarnessError, ValueError, OSError) as error:
        envelope = {"contract_version": CONTRACT_VERSION, "ok": False, "error": {"code": getattr(error, "code", "invalid_arguments"), "message": str(error), "details": getattr(error, "details", {})}}
    print(json.dumps(envelope, ensure_ascii=False, indent=2, allow_nan=False))
    if envelope["ok"]:
        return 0
    return {"permission_denied": 3, "source_changed": 4, "version_conflict": 5, "scientific_test_invalid": 6}.get(envelope["error"]["code"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
