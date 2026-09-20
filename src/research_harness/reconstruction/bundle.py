"""Migrate a researcher reconstruction bundle, retaining every qualification."""
import copy
import json
from pathlib import Path
from research_harness.common import HarnessError, digest, canonical, upsert


def import_bundle(store, ingestor, path):
    bundle = json.loads(Path(path).read_text())
    if not isinstance(bundle.get("records"), list) or not isinstance(bundle.get("source_files"), list):
        raise HarnessError("invalid_contract", "Expected source_files and records")
    artifacts = {}
    line_counts = {}
    for source in bundle["source_files"]:
        artifact = ingestor.capture(source["path"])
        if artifact["data"]["sha256"] != source["sha256"]:
            raise HarnessError("source_changed", source["path"])
        artifacts[source["path"]] = artifact
        line_counts[source["path"]] = len(store.read_blob(artifact["data"]["sha256"]).decode("utf-8", errors="replace").splitlines())
    records = []
    raw_ids = {}
    for path, artifact in artifacts.items():
        eid = "bundle-source:" + digest([ingestor.manifest["project_id"], path])[:24]
        raw_ids[path] = eid
        records.append({"id": eid, "kind": "evidence", "data": {
            "intrinsic_valid": True, "qualification": "source_identity_verified_only",
            "source_locators": [ingestor.locator(artifact)], "blob_refs": artifact["data"]["blob_refs"]}})
    for record in bundle["records"]:
        r = copy.deepcopy(record)
        d = r["data"]
        locators = []
        for loc in d.get("provenance", {}).get("locators", []):
            if loc["path"] not in artifacts:
                raise HarnessError("invalid_locator", "Uncaptured bundle source " + loc["path"])
            artifact = artifacts[loc["path"]]
            if loc["sha256"] != artifact["data"]["sha256"]:
                raise HarnessError("source_changed", loc["path"])
            start, end = loc.get("line_start", 1), loc.get("line_end", line_counts[loc["path"]])
            if not 1 <= start <= end <= line_counts[loc["path"]]:
                raise HarnessError("invalid_locator", "Bundle line range outside verified snapshot")
            converted = {"schema_version": "0.1.0", "project_id": ingestor.manifest["project_id"],
                "id": "locator:" + digest([artifact["id"], artifact["revision"], start, end])[:24],
                "is_example": False, "kind": "source_locator", "artifact_id": artifact["id"],
                "artifact_revision": artifact["revision"], "uri": artifact["data"]["path"],
                "content_identity": {"algorithm": "sha256", "digest": artifact["data"]["sha256"], "scope": "whole_file"},
                "locator": {"type": "lines", "start": start, "end": end, "index_base": 1,
                            "context_note": "historical statement or bounded primary check; qualification retained"},
                "availability": "captured", "extensions": {}}
            locators.append(converted)
        d["source_locators"] = locators
        d["qualification"] = d.get("provenance", {}).get("qualification", "imported_assertion")
        d["bundle_qualification"] = "selective current audits; historical records are not promoted"
        d["blob_refs"] = sorted({loc["content_identity"]["digest"] for loc in locators})
        if d["qualification"].startswith("current_primary"):
            d["support_sets"] = [[raw_ids[loc["uri"]] for loc in locators]]
        records.append(r)
    package_hash = store.put_blob(Path(path).read_bytes())
    records.append({"id": "reconstruction:project-bundle", "kind": "coverage", "data": {
        "bundle_sha256": package_hash, "blob_refs": [package_hash], "coverage": bundle.get("coverage", {}),
        "scope": bundle.get("scope"), "declarations": bundle.get("declarations"),
        "qualification": "historical intake complete for selected indexes; scientific review selective",
        "unreviewed_candidates": sum(r["kind"] == "audit_candidate" for r in bundle["records"])}})
    receipt = upsert(store, records, "migrate historical reconstruction with source identities and explicit current qualifications")
    return {"record_count": len(bundle["records"]), "source_count": len(artifacts), "receipt": receipt}
