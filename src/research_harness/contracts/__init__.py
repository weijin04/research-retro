"""Exchange schema and source-specific permissions, independent of semantics."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from research_harness.common import HarnessError


def validate_exchange(value, schema_path=None):
    path = Path(schema_path) if schema_path else Path(__file__).resolve().parents[3] / "contracts/contract.schema.json"
    errors = sorted(Draft202012Validator(json.loads(path.read_text())).iter_errors(value), key=lambda e: str(e.path))
    if errors:
        raise HarnessError("invalid_contract", "; ".join(e.message for e in errors))
    return value


def load_manifest(path):
    data = json.loads(Path(path).read_text())
    for key in ("project_id", "sources", "output_root", "policy_revision"):
        if key not in data:
            raise HarnessError("invalid_contract", f"missing manifest {key}")
    for source in data["sources"]:
        root = Path(source["root"])
        if not root.is_absolute():
            raise HarnessError("invalid_contract", "Source root must be absolute")
        if source.get("egress", "denied") != "denied":
            raise HarnessError("permission_denied", "Scientific manifests currently require denied egress")
    return data
