"""Small abstract interpreter. Never imports, compiles or executes project code.

Values outside the registered subset widen to unknown. The environment and Python
library summaries are explicit assumptions, never historical execution evidence.
"""
from __future__ import annotations

import ast
import copy
import json
import operator
import posixpath
import shlex
from dataclasses import dataclass, field

from research_harness.common import digest


@dataclass
class Value:
    value: object = None
    known: bool = True
    deps: set = field(default_factory=set)
    reasons: set = field(default_factory=set)

    def wire(self):
        serializable = not isinstance(self.value, Symbol)
        return {"state": "known" if self.known and serializable else "unknown",
                "value": self.value if self.known and serializable else None, "unit": None,
                "alternatives": [], "unknown_reason": None if self.known and serializable else
                "; ".join(sorted(self.reasons or {"symbolic runtime object"}))}


@dataclass
class Symbol:
    name: str


def unknown(reason, *values):
    return Value(known=False, deps=set().union(*(v.deps for v in values)),
                 reasons={reason}.union(*(v.reasons for v in values)))


def combine(result, *values):
    return Value(result, deps=set().union(*(v.deps for v in values)),
                 reasons=set().union(*(v.reasons for v in values)))


def launcher_environment(content):
    """Literal POSIX assignments only; expansion and command substitution stay unknown."""
    result = {}
    for line in content.decode("utf-8", errors="replace").splitlines():
        try:
            words = shlex.split(line, comments=True)
        except ValueError:
            continue
        if words and words[0] == "export":
            words = words[1:]
        for word in words:
            if "=" not in word:
                break
            key, value = word.split("=", 1)
            if key.isidentifier() and not any(x in value for x in ("$", "`", "\\")):
                result[key] = value
    return result


class Analyzer:
    BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
    COMPARE = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
               ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
               ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}

    def __init__(self, files, path, environment=None, depth=0, scope="module"):
        self.files, self.path = files, path
        self.environment, self.depth = environment or {}, depth
        self.scope = scope
        self.content = files[path]["content"]
        self.lines = self.content.splitlines(keepends=True)
        self.bindings, self.calls, self.gaps, self.imports = [], [], [], []
        self.env, self.functions = {}, {}
        self.assumptions = ["CPython numeric/string/container semantics", "stdlib json/pathlib/os summaries v1",
                            "configuration reads return the supplied frozen bytes",
                            "environment is conditional on literal launcher assignments; no ambient host environment"]
        self.steps = 0

    def havoc(self, reason):
        for name in self.env:
            if not isinstance(self.env[name].value, Symbol):
                self.env[name] = unknown(reason, self.env[name])

    def locator(self, node):
        start = sum(map(len, self.lines[:node.lineno - 1])) + node.col_offset
        end = sum(map(len, self.lines[:node.end_lineno - 1])) + node.end_col_offset
        ref = self.files[self.path]
        return {"artifact_id": ref["id"], "artifact_revision": ref["revision"], "sha256": ref["sha256"],
                "start_byte": start, "end_byte_exclusive": end}

    def expr(self, node):
        self.steps += 1
        if self.steps > 10000:
            return unknown("abstract evaluation budget exhausted")
        try:
            value = self._expr(node)
            if value.known and not isinstance(value.value, Symbol):
                if len(repr(value.value)) > 100000:
                    return unknown("abstract value size limit", value)
            return value
        except (KeyError, IndexError, TypeError, ValueError, ArithmeticError, AttributeError):
            return unknown("unresolved expression: " + ast.unparse(node)[:200])

    def _expr(self, node):
        if isinstance(node, ast.Constant):
            return Value(node.value)
        if isinstance(node, ast.Name):
            return self.env.get(node.id, Value(Symbol(node.id)))
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            vals = [self.expr(n) for n in node.elts]
            return combine([v.value for v in vals], *vals) if all(v.known for v in vals) else unknown("unknown container member", *vals)
        if isinstance(node, ast.Dict):
            keys, vals = [self.expr(k) for k in node.keys], [self.expr(v) for v in node.values]
            return combine(dict(zip([k.value for k in keys], [v.value for v in vals])), *keys, *vals) if all(v.known for v in keys + vals) else unknown("unknown mapping", *keys, *vals)
        if isinstance(node, ast.Attribute):
            base = self.expr(node.value)
            if isinstance(base.value, Symbol):
                return combine(Symbol(base.value.name + "." + node.attr), base)
            return unknown("unknown attribute", base)
        if isinstance(node, ast.Subscript):
            base, key = self.expr(node.value), self.expr(node.slice)
            if isinstance(base.value, Symbol) and base.value.name == "os.environ" and key.known:
                if key.value in self.environment:
                    return Value(self.environment[key.value], deps={"env:" + key.value})
                return unknown("unbound environment: " + str(key.value))
            return combine(base.value[key.value], base, key) if base.known and key.known else unknown("unknown subscript", base, key)
        if isinstance(node, ast.BinOp) and type(node.op) in self.BINARY:
            left, right = self.expr(node.left), self.expr(node.right)
            if not (left.known and right.known):
                return unknown("unknown arithmetic operand", left, right)
            if isinstance(node.op, ast.Mult) and any(isinstance(v.value, int) and abs(v.value) > 1000000 for v in (left, right)) and any(isinstance(v.value, (str, list)) for v in (left, right)):
                return unknown("oversized repetition", left, right)
            return combine(self.BINARY[type(node.op)](left.value, right.value), left, right)
        if isinstance(node, ast.UnaryOp):
            val = self.expr(node.operand)
            if not val.known:
                return val
            op = {ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_}.get(type(node.op))
            return combine(op(val.value), val) if op else unknown("unsupported unary operation", val)
        if isinstance(node, ast.Compare):
            vals = [self.expr(node.left)] + [self.expr(n) for n in node.comparators]
            if all(v.known and not isinstance(v.value, Symbol) for v in vals) and all(type(o) in self.COMPARE for o in node.ops):
                return combine(all(self.COMPARE[type(o)](a.value, b.value) for a, b, o in zip(vals, vals[1:], node.ops)), *vals)
            return unknown("unknown comparison", *vals)
        if isinstance(node, ast.IfExp):
            cond = self.expr(node.test)
            if cond.known and not isinstance(cond.value, Symbol):
                val = self.expr(node.body if cond.value else node.orelse)
                return combine(val.value, cond, val) if val.known else val
            a, b = self.expr(node.body), self.expr(node.orelse)
            if a.known and b.known and a.value == b.value:
                return combine(a.value, cond, a, b)
            return unknown("conditional alternatives: " + ast.unparse(node), cond, a, b)
        if isinstance(node, ast.Call):
            return self.call(node)
        return unknown("unsupported syntax: " + type(node).__name__)

    def call(self, node):
        func = self.expr(node.func)
        name = func.value.name if isinstance(func.value, Symbol) else "unknown"
        args = [self.expr(a) for a in node.args]
        if name == "os.environ.get" and args and args[0].known:
            key = args[0].value
            # An absent key is not proof that a runtime environment used the default.
            if key in self.environment:
                return Value(self.environment[key], deps={"env:" + key})
            return unknown("environment or default unresolved: " + str(key), *args)
        if name in {"Path", "pathlib.Path"} and len(args) == 1 and args[0].known:
            return combine(Symbol("path:" + str(args[0].value)), *args)
        if name.startswith("path:") and name.endswith((".read_text", ".read_bytes")):
            path = name[5:].rsplit(".", 1)[0]
            if path in self.files:
                return Value(self.files[path]["content"].decode("utf-8"), deps={"file:" + path})
            return unknown("missing frozen configuration: " + path)
        if name == "json.loads" and len(args) == 1 and args[0].known:
            return combine(json.loads(args[0].value), *args)
        if name == "json.dumps" and len(args) == 1 and args[0].known:
            return combine(json.dumps(args[0].value), *args)
        if name in {"min", "max", "int", "float", "str", "abs", "len"} and all(a.known and not isinstance(a.value, Symbol) for a in args):
            functions = {"min": min, "max": max, "int": int, "float": float, "str": str, "abs": abs, "len": len}
            return combine(functions[name](*[a.value for a in args]), *args)
        if name == "importlib.import_module" and len(args) == 1 and args[0].known and isinstance(args[0].value, str):
            self.imports.append({"module": args[0].value, "locator": self.locator(node), "conditional": True})
            return combine(Symbol(args[0].value), *args)
        if self.depth < 6 and "." in name:
            module, function = name.rsplit(".", 1)
            path = module.replace(".", "/") + ".py"
            if path in self.files:
                child = Analyzer(self.files, path, self.environment, self.depth + 1, function)
                tree = ast.parse(child.content)
                definition = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function), None)
                if definition and len(definition.args.args) == len(args):
                    child.env = dict(zip([a.arg for a in definition.args.args], args))
                    result = child.statements(definition.body)
                    self.calls.append({"function": name, "path": path, "bindings": child.bindings,
                                       "return": result.wire(), "locator": self.locator(node)})
                    self.gaps.extend(child.gaps)
                    return result
        # These calls are not executed. Reads/mutations through unknown calls may
        # alter every reachable value; statements() performs conservative havoc.
        self.gaps.append({"kind": "unknown_call", "expression": ast.unparse(node)[:200], "locator": self.locator(node)})
        if not (name == "print" or name.startswith("path:") and name.endswith((".write_text", ".write_bytes", ".mkdir"))):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "append" and isinstance(node.func.value, ast.Name) and isinstance(self.env.get(node.func.value.id, Value()).value, list):
                self.env[node.func.value.id] = unknown("mutated list contents")
            else:
                self.havoc("unregistered call may mutate reachable state")
        return unknown("unregistered call: " + name, func, *args)

    def bind(self, target, value, node):
        if isinstance(target, ast.Name):
            requested = None
            expression = getattr(node, "value", None)
            if isinstance(expression, ast.Call) and isinstance(expression.func, ast.Name) and expression.func.id in {"min", "max"} and expression.args:
                requested = self.expr(expression.args[0]).wire()
            self.env[target.id] = value
            binding = {"symbol": target.id, "value": value.wire(), "dependencies": sorted(value.deps),
                       "expression": ast.unparse(node.value) if hasattr(node, "value") else ast.unparse(node),
                       "locator": self.locator(node), "rule": "python-abstract-1", "scope": self.scope,
                       "requested_value": requested}
            self.bindings.append(binding)
            value.deps = value.deps | {"binding:" + self.path + ":" + str(node.lineno) + ":" + target.id}
        else:
            self.gaps.append({"kind": "unsupported_assignment", "locator": self.locator(node)})
            for name in self.env:
                self.env[name] = unknown("alias/mutation may change binding", self.env[name])

    def statements(self, nodes):
        for node in nodes:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.env[alias.asname or alias.name.split(".")[0]] = Value(Symbol(alias.name))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    self.env[alias.asname or alias.name] = Value(Symbol((node.module or "") + "." + alias.name))
            elif isinstance(node, ast.FunctionDef):
                self.functions[node.name] = node
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = self.expr(node.value)
                for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                    self.bind(target, copy.deepcopy(value), node)
            elif isinstance(node, ast.AugAssign):
                expression = ast.copy_location(ast.BinOp(left=node.target, op=node.op, right=node.value), node)
                self.bind(node.target, self.expr(expression), node)
            elif isinstance(node, ast.Return):
                return self.expr(node.value)
            elif isinstance(node, ast.If):
                cond = self.expr(node.test)
                if cond.known and not isinstance(cond.value, Symbol):
                    result = self.statements(node.body if cond.value else node.orelse)
                    if any(isinstance(n, ast.Return) for n in node.body + node.orelse):
                        return result
                else:
                    saved = copy.deepcopy(self.env)
                    self.statements(node.body)
                    branch = self.env
                    self.env = copy.deepcopy(saved)
                    self.statements(node.orelse)
                    for key in set(branch) | set(self.env):
                        a, b = branch.get(key, unknown("unbound branch")), self.env.get(key, unknown("unbound branch"))
                        self.env[key] = a if a.known and b.known and a.value == b.value else unknown("multiple path values", a, b)
                        target = ast.copy_location(ast.Name(id=key, ctx=ast.Store()), node)
                        self.bind(target, self.env[key], node)
            elif isinstance(node, ast.For):
                if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range" and not any(isinstance(n, (ast.Break, ast.Continue, ast.Return)) for n in ast.walk(node)):
                    bounds = [self.expr(a) for a in node.iter.args]
                    if all(v.known and type(v.value) is int for v in bounds):
                        try:
                            sequence = range(*[v.value for v in bounds])
                            bounded = len(sequence) <= 64
                        except (ValueError, OverflowError, TypeError):
                            bounded = False
                        if bounded and isinstance(node.target, ast.Name):
                            for index in sequence:
                                self.env[node.target.id] = Value(index)
                                self.statements(node.body)
                            self.statements(node.orelse)
                            continue
                # Analyze one representative transition; never call it a solved loop.
                self.env[getattr(node.target, "id", "loop_index")] = unknown("loop index interval")
                self.statements(node.body)
                touched = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
                for name in touched:
                    self.env[name] = unknown("loop result not solved", self.env.get(name, Value()))
                    target = ast.copy_location(ast.Name(id=name, ctx=ast.Store()), node)
                    self.bind(target, self.env[name], node)
                self.gaps.append({"kind": "loop_summary", "locator": self.locator(node),
                                  "boundary": "one transition analyzed; final state/iteration count not observed"})
            elif isinstance(node, ast.Expr):
                if isinstance(node.value, ast.Call):
                    expression = ast.unparse(node.value.func)
                    result = self.expr(node.value)
                    # Explicit side-effect summaries: output-only sinks do not
                    # mutate unrelated scalar/config values. Other calls may.
                    if not result.known and not (expression == "print" or expression.endswith((".write_text", ".write_bytes", ".mkdir", ".append"))):
                        for key in self.env:
                            self.env[key] = unknown("unregistered call may mutate binding", self.env[key])
            elif isinstance(node, (ast.Pass, ast.Break, ast.Continue)):
                pass
            else:
                self.gaps.append({"kind": "unsupported_statement", "syntax": type(node).__name__, "locator": self.locator(node)})
                for name in self.env:
                    self.env[name] = unknown("unsupported statement may alter environment", self.env[name])
        return unknown("no statically resolved return")

    def analyze(self):
        try:
            tree = ast.parse(self.content)
            self.statements(tree.body)
            fingerprint = digest(ast.dump(tree, include_attributes=False))
        except (SyntaxError, UnicodeError, RecursionError) as error:
            self.gaps.append({"kind": "parse_failed", "error": type(error).__name__})
            fingerprint = None
        return {"path": self.path, "bindings": self.bindings, "calls": self.calls, "imports": self.imports,
                "gaps": self.gaps, "assumptions": self.assumptions, "ast_fingerprint": fingerprint,
                "qualification": "static_conditional", "observed_read": [],
                "may_read": sorted({d[5:] for b in self.bindings for d in b["dependencies"] if d.startswith("file:")})}
