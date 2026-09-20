"""Stable function definitions and JSON adapter shared by every host and the CLI."""
import json
from importlib.resources import files
from jsonschema import Draft202012Validator
from research_harness.common import HarnessError
from research_harness.storage import ConflictError, AuthorityError
from research_harness.unit import Unit, init, start, inspect_bundle

CONTRACT_VERSION = "1.0"


def definitions():
    return json.loads(files("research_harness.resources").joinpath("tools.json").read_text())


def dispatch(name, arguments):
    definition = next((tool for tool in definitions() if tool["name"] == name), None)
    if definition is None:
        raise HarnessError("unknown_tool", "Unknown tool; use retro tools")
    errors = sorted(Draft202012Validator(definition["parameters"]).iter_errors(arguments), key=lambda error: str(error.path))
    if errors:
        raise HarnessError("invalid_arguments", "; ".join(f"{list(e.path)}: {e.message}" for e in errors))
    args = dict(arguments)
    if name == "retro_init":
        return init(**args)
    if name == "retro_start":
        return start(**args)
    if name == "retro_inspect":
        return inspect_bundle(args["bundle"], full=args.get("full", True))
    if name == "retro_verify_handoff":
        from research_harness.handoff.portable import verify
        return verify(args["bundle"], args["query_set"])
    if name == "retro_migrate":
        from research_harness.handoff.portable import migrate
        return migrate(**args)
    unit = Unit(args.pop("workspace"))
    if name == "retro_triage":
        from research_harness.triage import Triage
        return Triage(unit).run(**args)
    if name == "retro_workflow":
        from research_harness.workflow import Workflow
        return Workflow(unit).run(**args)
    if name in {"retro_record", "retro_spine", "retro_judge"}:
        from research_harness.workflow import Workflow
        return getattr(Workflow(unit), name.removeprefix("retro_"))(**args)
    if name == "retro_discover":
        from research_harness.discovery import run
        return run(unit, **args)
    if name in {"retro_snapshot", "retro_recover", "retro_records", "retro_capabilities", "retro_explain", "retro_impact",
                "retro_contrast", "retro_support", "retro_task", "retro_probe", "retro_close"}:
        from research_harness.retro2 import Service
        return getattr(Service(unit), name.removeprefix("retro_"))(**args)
    if name == "retro_audit":
        return getattr(unit, "audit_" + args.pop("action"))(**args)
    return getattr(unit, name.removeprefix("retro_"))(**args)


def invoke(request):
    """One public request, one result; only authorized workflow checks call Jev."""
    try:
        if not isinstance(request, dict) or set(request) != {"name", "arguments"}:
            raise HarnessError("invalid_arguments", "Expected exactly name and arguments")
        result = dispatch(request["name"], request["arguments"])
        return {"contract_version": CONTRACT_VERSION, "ok": True, "result": result}
    except (HarnessError, ValueError, KeyError, OSError, TypeError) as error:
        code = "version_conflict" if isinstance(error, ConflictError) else "permission_denied" if isinstance(error, AuthorityError) else getattr(error, "code", "invalid_state")
        return {"contract_version": CONTRACT_VERSION, "ok": False,
                "error": {"code": code, "message": str(error), "details": getattr(error, "details", {})}}
