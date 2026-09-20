"""Format-level inspection only. No scientific engine or project conventions."""
import ast
import csv
import io
import json
from pathlib import Path

VERSION = "formats-1"
TEXT_SUFFIXES = {".csv", ".tsv", ".json", ".jsonl", ".py", ".r", ".jl", ".m", ".c", ".h",
                 ".md", ".txt", ".log", ".out", ".yaml", ".yml", ".toml", ".sh", ".ipynb"}


def parse(content, path):
    result = {"parser_version": VERSION, "coverage": "decoded_text", "scientific_validity": "unchecked",
              "warnings": [], "records": []}
    try:
        text = content.decode("utf-8-sig")
        if "\x00" in text:
            raise UnicodeError("NUL bytes")
    except UnicodeError:
        return {**result, "coverage": "unsupported_format", "warnings": ["binary/non-UTF8; bytes retained"]}
    suffix = Path(path).suffix.lower()
    result["line_count"] = len(text.splitlines())
    try:
        if suffix in (".csv", ".tsv"):
            rows = list(csv.DictReader(io.StringIO(text), delimiter="\t" if suffix == ".tsv" else ","))
            result.update(coverage="parsed_structure", records=rows)
        elif suffix in (".json", ".ipynb"):
            result.update(coverage="parsed_structure", records=[json.loads(text)])
        elif suffix == ".py":
            tree = ast.parse(text)
            result["records"] = [{"type": type(n).__name__, "name": getattr(n, "name", None), "line": n.lineno}
                                 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        else:
            result["records"] = [{"line": i, "text": line} for i, line in enumerate(text.splitlines(), 1) if line.strip()]
    except (ValueError, SyntaxError, csv.Error) as error:
        result.update(coverage="parse_failed", warnings=[f"{type(error).__name__}: {error}"])
    result["warnings"].append("Captured text is untrusted data; decoding and syntax do not establish execution or scientific validity")
    return result
