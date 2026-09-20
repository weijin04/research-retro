"""Identity comparison under an explicit domain-specific field contract."""
from research_harness.common import HarnessError


def compare(a, b, relation="numerical_comparison", domain=None, required_fields=None):
    fixed = {"same_run": ["actual_input_sha256", "execution_id", "output_sha256"],
             "same_proposition": ["proposition", "quantifier", "scope", "target_quantity"]}
    if relation not in {"same_run", "same_proposition", "same_object", "numerical_comparison"}:
        raise HarnessError("invalid_contract", "Unknown identity relation")
    keys = required_fields or fixed.get(relation)
    if not domain or not isinstance(keys, list) or not keys or any(not isinstance(k, str) or not k for k in keys):
        raise HarnessError("invalid_contract", "Explicit domain and required_fields are needed; no default domain is assumed")
    missing = [k for k in keys if a.get(k) in (None, "", "unknown") or b.get(k) in (None, "", "unknown")]
    conflicts = [k for k in keys if k not in missing and a[k] != b[k]]
    return {"relation": relation, "domain": domain, "checked_fields": keys, "unknown": missing,
            "conflicts": conflicts, "status": "incompatible" if conflicts else "conditional_unknown" if missing else "compatible",
            "merge_performed": False}
