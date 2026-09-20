"""Different equivalence questions deliberately have different constraints."""
from research_harness.common import HarnessError

CHEMISTRY = ["composition", "charge", "multiplicity", "geometry", "environment", "method", "basis", "constraints"]
DIFFUSION = ["material", "guest", "temperature_K", "loading", "framework_flexibility", "ensemble", "time_window", "sampling"]


def compare(a, b, relation="numerical_comparison", domain="chemistry"):
    keys = CHEMISTRY if domain == "chemistry" else DIFFUSION
    if relation == "same_run":
        keys = ["actual_input_sha256", "execution_id", "output_sha256"]
    elif relation == "same_object":
        keys = keys[:5] if domain == "chemistry" else keys[:5]
    elif relation == "same_proposition":
        keys = ["proposition", "quantifier", "scope", "target_quantity"]
    elif relation == "numerical_comparison":
        keys = keys + ["target_quantity", "unit", "reference_state"]
    else:
        raise HarnessError("invalid_contract", "Unknown relation")
    missing = [k for k in keys if a.get(k) in (None, "", "unknown") or b.get(k) in (None, "", "unknown")]
    conflicts = [k for k in keys if k not in missing and a[k] != b[k]]
    return {"relation": relation, "domain": domain, "checked_fields": keys, "unknown": missing,
            "conflicts": conflicts, "status": "incompatible" if conflicts else ("conditional_unknown" if missing else "compatible"),
            "merge_performed": False}


def difference(a, b, value_key="value", domain="chemistry"):
    check = compare(a, b, domain=domain)
    if check["status"] != "compatible":
        raise HarnessError("scientific_test_invalid", "Unconditional difference not licensed", check)
    return {"value": b[value_key] - a[value_key], "unit": a["unit"], "comparability": check}
