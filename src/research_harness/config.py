"""Explicit per-workspace configuration; no home directory or host discovery."""
import json
import os
from pathlib import Path

from research_harness.common import HarnessError, atomic_json

CONFIG = "retro.json"
DEFAULT_EXCLUDES = [".git", ".venv", "__pycache__", ".retro"]


def outside_engine(path):
    path = Path(path).resolve()
    package = Path(__file__).resolve().parent
    roots = [package]
    if package.parent.name == "src":
        roots.append(package.parent.parent)
    if any(path.is_relative_to(root) for root in roots):
        raise HarnessError("permission_denied", "Workspace and outputs must be outside the engine code tree")
    return path


def workspace_path(value=None):
    # Existing 1.x/2.x state remains discoverable; new work stays outside originals.
    legacy = Path.cwd() / ".retro"
    default = legacy if (legacy / CONFIG).is_file() else external_workspace(Path.cwd())
    return outside_engine(value or os.environ.get("RETRO_WORKSPACE") or default)


def external_workspace(project):
    return project.parent / (project.name + ".retro")


def owned(workspace, path):
    workspace = outside_engine(workspace)
    path = Path(path)
    path = outside_engine(path if path.is_absolute() else workspace / path)
    if not path.is_relative_to(workspace):
        raise HarnessError("permission_denied", "Output must be inside the selected workspace")
    return path


def initialize(project, workspace=None, project_id=None, capture_max_bytes=None, scan_max_entries=None, excludes=None, capture_text=None):
    project = Path(project).resolve(strict=True)
    if not project.is_dir():
        raise HarnessError("invalid_config", "Project must be a directory")
    workspace = workspace_path(workspace or external_workspace(project))
    if workspace == project or project.is_relative_to(workspace):
        raise HarnessError("invalid_config", "Workspace cannot contain or equal the source project")
    if (workspace / CONFIG).exists():
        manifest = load(workspace)
        if Path(manifest["sources"][0]["root"]) != project or (project_id and manifest["project_id"] != project_id):
            raise HarnessError("version_conflict", "Workspace is already assigned to another project")
        source = manifest["sources"][0]
        if any(value is not None and value != source[key] for key, value in
               (("snapshot_max_bytes", capture_max_bytes), ("scan_max_entries", scan_max_entries))):
            raise HarnessError("version_conflict", "Initialization options differ from existing workspace")
        if excludes is not None and sorted(set(DEFAULT_EXCLUDES + excludes)) != source["excludes"]:
            raise HarnessError("version_conflict", "Source exclusions differ from existing workspace")
        if capture_text is not None and capture_text != manifest["scan"]["capture_text"]:
            raise HarnessError("version_conflict", "Scan mode differs from existing workspace")
        return workspace, manifest
    if workspace.is_relative_to(project):
        raise HarnessError("invalid_config", "New investigations need a separate workspace outside the source project")
    if workspace.exists() and any(workspace.iterdir()):
        raise HarnessError("invalid_config", "Initialization requires an empty workspace")
    config = {
        "config_version": 1, "project_id": project_id or project.name,
        "policy_revision": 1, "dataset_role": "user_project",
        "sources": [{"id": "project", "root": os.path.relpath(project, workspace),
                     "egress": "denied", "excludes": sorted(set(DEFAULT_EXCLUDES + (excludes or []))),
                     "excluded_paths": [str(workspace)],
                     "snapshot_max_bytes": capture_max_bytes if capture_max_bytes is not None else 1048576,
                     "scan_max_entries": scan_max_entries if scan_max_entries is not None else 250000}],
        "output_root": ".", "allowed_actions": ["read", "derive", "deterministic_postprocess", "propose_revision"],
        "forbidden_actions": ["source_write", "scientific_data_egress", "scientific_job_submission"],
        "scan": {"capture_text": capture_text if capture_text is not None else True},
    }
    atomic_json(workspace / CONFIG, config)
    return workspace, load(workspace)


def load(workspace):
    workspace = workspace_path(workspace)
    path = workspace / CONFIG
    if not path.is_file():
        raise HarnessError("not_initialized", "Run retro init PROJECT [--workspace WORKSPACE] first")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("config_version") != 1 or not isinstance(data.get("project_id"), str) or not data["project_id"].strip():
        raise HarnessError("invalid_config", "Expected config_version=1 and a nonempty project_id")
    if type(data.get("policy_revision")) is not int or data["policy_revision"] < 1 or data.get("output_root") != ".":
        raise HarnessError("invalid_config", "Use a separate workspace; a positive policy_revision and output_root='.' are required")
    if not isinstance(data.get("sources"), list) or not data["sources"]:
        raise HarnessError("invalid_config", "At least one explicit source is required")
    ids = set()
    for source in data["sources"]:
        if not source.get("id") or source["id"] in ids or not source.get("root"):
            raise HarnessError("invalid_config", "Sources require unique IDs and roots")
        ids.add(source["id"])
        source["root"] = str((workspace / source["root"]).resolve())
        if Path(source["root"]).is_relative_to(workspace):
            raise HarnessError("invalid_config", "Source cannot be inside workspace")
        source["excluded_paths"] = [str(workspace)] + [str((workspace / p).resolve()) for p in source.get("excluded_paths", [])]
        source["excluded_paths"] = sorted(set(source["excluded_paths"]))
        if source.get("egress") != "denied":
            raise HarnessError("permission_denied", "Standalone unit has no egress capability")
        for key in ("snapshot_max_bytes", "scan_max_entries"):
            if type(source.get(key)) is not int or source[key] < 1:
                raise HarnessError("invalid_config", f"{key} must be a positive integer")
    data["output_root"] = str(workspace)
    return data
