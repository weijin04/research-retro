"""CLI and agent-callable services use the same implementation."""
from __future__ import annotations
import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from research_harness import __version__
from research_harness.common import HarnessError, atomic_json, now
from research_harness.contracts import load_manifest, validate_exchange
from research_harness.storage import Store
from research_harness.ingest import Ingestor
from research_cases.legacy.audit import CHECKS, case_path, execute_check, integrate_case, revoke
from research_harness.views import export_report, query
from research_harness.context import build_context
from research_harness.reconstruction.bundle import import_bundle
from research_harness.reconstruction.workbench import AuditWorkbench
from research_harness.reconstruction.provenance import source_families
from research_harness.governance.patches import PatchService
from research_harness.views.report import brief
from research_cases.legacy.decisions.workflow import attach_advice
from research_cases.legacy.runs import reconstruct_captured_runs

ROOT = Path(__file__).resolve().parents[2]


def owned_output(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise HarnessError("permission_denied", "Output must remain in the owning framework project")
    return path


def ensure_project(store, manifest):
    try:
        current = store.get("project:contract")
    except KeyError:
        return store.initialize_project(manifest)
    if current["data"] != manifest:
        raise HarnessError("version_conflict", "Manifest differs from initialized project contract; use an explicit governance revision")
    return {"status": "already_initialized", "revision": current["revision"]}


def doctor():
    git = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    result = {"version": __version__, "python": sys.version, "python_executable": sys.executable,
              "sqlite_linked_version": sqlite3.sqlite_version, "sqlite_journal": "DELETE", "synchronous": "FULL",
              "sqlite_reason": "rollback journal avoids dependence on unverified WAL backport status",
              "project_root": str(ROOT), "git_root": git.stdout.strip(), "observed_at": now(),
              "tools": {name: shutil.which(name) for name in ("bwrap", "unshare", "codex", "uv", "rtk")},
              "runtime_boundary": "not_yet_certified", "scientific_source_access": "read_only",
              "external_job_submissions": "forbidden", "credentials_printed": False}
    atomic_json(ROOT / "var/receipts/doctor.json", result)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(prog="rh", description="Evidence-bounded scientific reconstruction")
    p.add_argument("--project", default=str(ROOT / "research_cases/legacy/config/grephene.json"))
    p.add_argument("--store", help="Override store for clone/recovery demonstrations")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor")
    sub.add_parser("init")
    sub.add_parser("jev-advice")
    sub.add_parser("runs")
    source = sub.add_parser("sources")
    source.add_argument("action", choices=["import", "scan", "refresh", "bundle"])
    source.add_argument("--path")
    capture = sub.add_parser("capture")
    capture.add_argument("path")
    read = sub.add_parser("read")
    read.add_argument("id")
    read.add_argument("--revision", type=int)
    read.add_argument("--start", type=int, default=1)
    read.add_argument("--end", type=int)
    read.add_argument("--live", action="store_true")
    audit = sub.add_parser("audit")
    audit.add_argument("action", choices=["run", "show"])
    audit.add_argument("name", choices=list(CHECKS))
    bench = sub.add_parser("workbench")
    bench.add_argument("action", choices=["propose", "packet", "submit", "queue"])
    bench.add_argument("value", nargs="?")
    bench.add_argument("--result")
    sub.add_parser("provenance")
    state = sub.add_parser("state")
    state.add_argument("action", choices=["get", "history", "revoke", "verify", "list", "diff", "events", "validate", "commit"])
    state.add_argument("id", nargs="?")
    state.add_argument("--kind")
    state.add_argument("--before", type=int, default=1, help="单对象的旧 revision，非全局状态版本；diff 必须同时给对象 ID")
    state.add_argument("--after", type=int, default=0, help="events 的起始全局状态版本")
    state.add_argument("--reason")
    find = sub.add_parser("query")
    find.add_argument("text")
    find.add_argument("--kind")
    find.add_argument("--limit", type=int, default=20)
    find.add_argument("--indexes", action="store_true")
    find.add_argument("--full", action="store_true", help="返回完整原字段；默认返回限长摘要和按 ID 查证入口")
    context = sub.add_parser("context")
    context.add_argument("--budget", type=int, default=16000)
    context.add_argument("--part", type=int, help="按 1-based 分块读取，避免一次输出全部必读材料")
    context.add_argument("--full", action="store_true")
    report = sub.add_parser("report")
    report.add_argument("--dest")
    backup = sub.add_parser("backup")
    backup.add_argument("dest")
    reconstruct = sub.add_parser("reconstruct")
    reconstruct.add_argument("action", choices=["run", "resume"])
    reconstruct.add_argument("--skip-scan", action="store_true")
    validate = sub.add_parser("validate")
    validate.add_argument("path")
    args = p.parse_args(argv)
    try:
        if args.cmd == "doctor":
            result = doctor()
        elif args.cmd == "validate":
            validate_exchange(json.loads(Path(args.path).read_text()))
            result = {"valid_structure": True, "scientific_sufficiency": "not_checked"}
        else:
            manifest = load_manifest(args.project)
            root = Path(args.store or manifest["output_root"])
            if not root.is_absolute():
                root = ROOT / root
            if not root.resolve().is_relative_to(ROOT):
                raise HarnessError("permission_denied", "Store must stay inside owning project")
            store, name = Store(root), "diffusion" if manifest["project_id"].startswith("diffusion") else "grephene"
            ingest = Ingestor(store, manifest)
            if args.cmd == "init":
                result = ensure_project(store, manifest)
            elif args.cmd == "jev-advice":
                result = attach_advice(store, ROOT / "var/receipts/jev")
            elif args.cmd == "runs":
                result = reconstruct_captured_runs(store, ingest)
            elif args.cmd == "capture":
                result = ingest.capture(args.path)
            elif args.cmd == "sources":
                if args.action == "bundle":
                    if not args.path: raise HarnessError("invalid_contract", "bundle needs --path")
                    result = import_bundle(store, ingest, args.path)
                elif args.action == "import":
                    paths = [args.path] if args.path else [str(Path(manifest["sources"][0]["root"]) / x) for x in manifest.get("index_imports", [])]
                    result = [ingest.import_table(x) for x in paths]
                elif args.action == "scan":
                    result = [ingest.scan(s["id"]) for s in manifest["sources"]]
                else:
                    result = ingest.refresh()
            elif args.cmd == "read":
                artifact = store.get(args.id, args.revision)
                loc = ingest.locator(artifact, args.start, args.end)
                result = {"locator": loc, "content": ingest.read(loc, live=args.live)}
            elif args.cmd == "audit":
                case = case_path(args.name)
                if args.action == "show":
                    result = json.loads(case.read_text())
                else:
                    for source in json.loads(case.read_text())["source_files"]:
                        ingest.allowed(source["path"])
                    receipt = execute_check(args.name, root / "checks" / args.name)
                    result = integrate_case(store, ingest, case, receipt)
                    atomic_json(root / "audit_integration.json", result)
            elif args.cmd == "workbench":
                workbench = AuditWorkbench(store, ingest)
                if args.action == "queue": result = store.list("audit_candidate")
                elif args.action == "propose": result = workbench.propose(json.loads(Path(args.value).read_text()))
                elif args.action == "packet": result = workbench.packet(args.value)
                elif args.action == "submit":
                    if not args.result: raise HarnessError("invalid_contract", "submit needs --result")
                    result = workbench.submit(args.value, json.loads(Path(args.result).read_text()))
            elif args.cmd == "provenance":
                result = source_families(store)
                atomic_json(root / "provenance.json", result)
            elif args.cmd == "state":
                if args.action in {"get", "history", "diff", "revoke", "validate", "commit"} and not args.id:
                    raise HarnessError("invalid_contract", f"state {args.action} 需要对象 ID（validate/commit 为补丁 JSON 路径）")
                if args.action == "get": result = store.get(args.id)
                elif args.action == "history": result = store.history(args.id)
                elif args.action == "diff": result = store.diff(args.id, args.before)
                elif args.action == "list": result = store.list(args.kind)
                elif args.action == "verify": result = store.verify()
                elif args.action == "events": result = store.events(args.after)
                elif args.action in {"validate", "commit"}:
                    patch = json.loads(Path(args.id).read_text())
                    service = PatchService(store, ingest)
                    result = service.validate(patch) if args.action == "validate" else service.commit(patch)
                elif args.action == "revoke":
                    if not args.reason: raise HarnessError("invalid_contract", "revoke requires original reason")
                    result = revoke(store, args.id, args.reason)
            elif args.cmd == "query":
                result = ingest.query_tables(args.text, args.limit) if args.indexes else query(store, args.text, args.kind, args.limit)
                if not args.indexes and not args.full:
                    result = [brief(r) for r in result]
            elif args.cmd == "context":
                packet = build_context(store, budget_chars=args.budget)
                atomic_json(root / "context.json", packet)
                if args.part is not None:
                    if not 1 <= args.part <= len(packet["chunks"]):
                        raise HarnessError("invalid_contract", "Context part outside declared chunk range")
                    result = {"state_revision": packet["state_revision"], "packet_hash": packet["content_hash"], "part": args.part,
                              "total_parts": len(packet["chunks"]), "chunk": packet["chunks"][args.part - 1]}
                elif args.full:
                    result = packet
                else:
                    result = {k: packet[k] for k in ("state_revision", "content_hash", "budget_chars", "required_chars", "selected_chars", "budget_status")}
                    result.update(packet_path=str(root / "context.json"), total_parts=len(packet["chunks"]),
                                  mandatory_records=sum(i["mandatory"] for i in packet["items"]),
                                  read_instruction="Use --part N for every required chunk or --full. An index is not proof that the material was read.")
            elif args.cmd == "report": result = export_report(store, owned_output(args.dest or root / "reports"))
            elif args.cmd == "backup": result = store.backup(owned_output(args.dest))
            elif args.cmd == "reconstruct":
                ensure_project(store, manifest)
                imported = [ingest.import_table(Path(manifest["sources"][0]["root"]) / x) for x in manifest.get("index_imports", [])]
                audit_results = []
                for audit_name in (["grephene", "grephene-t13b", "grephene-entry"] if name == "grephene" else ["diffusion"]):
                    for source in json.loads(case_path(audit_name).read_text())["source_files"]:
                        ingest.allowed(source["path"])
                    receipt = execute_check(audit_name, root / "checks" / audit_name)
                    audit_results.append(integrate_case(store, ingest, case_path(audit_name), receipt))
                bundle_path = ROOT / "research_cases" / name / "project_reconstruction.json"
                bundle_result = import_bundle(store, ingest, bundle_path) if bundle_path.exists() else None
                run_result = reconstruct_captured_runs(store, ingest)
                coverage = [] if args.skip_scan else [ingest.scan(s["id"]) for s in manifest["sources"]]
                views = export_report(store, root / "reports")
                result = {"imports": imported, "audits": audit_results, "bundle": bundle_result, "runs": run_result, "coverage": coverage, "views": views}
                atomic_json(root / "reconstruction_receipt.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except (HarnessError, ValueError, KeyError, OSError, subprocess.TimeoutExpired) as e:
        print(json.dumps({"error": getattr(e, "code", type(e).__name__), "message": str(e), "details": getattr(e, "details", {})}, ensure_ascii=False, default=str), file=sys.stderr)
        return {"permission_denied": 3, "source_changed": 4, "scientific_test_invalid": 6}.get(getattr(e, "code", ""), 2)


if __name__ == "__main__":
    raise SystemExit(main())
