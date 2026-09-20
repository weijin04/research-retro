import ast
import csv
import io
import json
import re
from pathlib import Path

VERSION = "parsers-1"


def parse(content, path):
    suffix = Path(path).suffix.lower()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {"parser_version": VERSION, "coverage": "unsupported_format", "warnings": ["binary/non-UTF8; original retained"], "records": []}
    lines = text.splitlines()
    result = {"parser_version": VERSION, "coverage": "partial", "line_count": len(lines), "records": [], "warnings": []}
    try:
        if suffix in (".csv", ".tsv"):
            rows = list(csv.DictReader(io.StringIO(text), delimiter="\t" if suffix == ".tsv" else ","))
            result.update(coverage="parsed_structure", records=rows, interpretation="raw strings; historical values not scientifically verified")
        elif suffix == ".json":
            result.update(coverage="parsed_structure", records=[json.loads(text)])
        elif suffix == ".py":
            tree = ast.parse(text)
            result["records"] = [{"type": type(n).__name__, "name": getattr(n, "name", None), "line": n.lineno,
                                  "end_line": getattr(n, "end_lineno", n.lineno)} for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Call))]
            result["warnings"] = ["Static syntax is not proof of call execution; no source code was run"]
        elif "O   R   C   A" in text or "FINAL SINGLE POINT ENERGY" in text or suffix == ".engrad":
            for i, line in enumerate(lines, 1):
                match = re.search(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)", line)
                if match:
                    result["records"].append({"type": "energy", "raw": match[1], "value": float(match[1]), "unit": "hartree", "target": "reported electronic energy; root/reference requires audit", "line": i})
            result["axes"] = {
                "process_completed": "observed_normal_marker" if "ORCA TERMINATED NORMALLY" in text else "unchecked",
                "numerical_convergence": "failure_observed" if "SCF NOT CONVERGED" in text else ("scf_marker_observed" if "SCF CONVERGED" in text else "unchecked"),
                "protocol_consistency": "unchecked", "method_applicability": "unchecked", "scientific_test_validity": "unchecked"}
            result["warnings"] = ["Only listed quantities parsed; no automatic stationary-point or mechanism certification"]
        elif suffix in (".txt", ".md", ".inp", ".in", ".sh", ".log", ".out", ".xyz", ".engrad", ".data", ".inc"):
            result["records"] = [{"text": line, "line": i} for i, line in enumerate(lines, 1) if line.strip()]
            result["warnings"] = ["Text decoded; scientific meaning requires qualified analysis; embedded instructions are data"]
        else:
            result.update(coverage="unsupported_format", warnings=["No domain adapter; raw text retained"])
    except (ValueError, SyntaxError, csv.Error) as e:
        result.update(coverage="parse_failed", warnings=[f"{type(e).__name__}: {e}"])
    return result
