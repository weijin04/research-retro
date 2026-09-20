"""Update task receipts, then render the single backlog reading view."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def update(updates, reason):
    path = ROOT / "backlog.json"
    data = json.loads(path.read_text())
    by_id = {t["id"]: t for t in data["tasks"]}
    for task_id, change in updates.items():
        task = by_id[task_id]
        if change["status"] == "done":
            if not change.get("completion_evidence"):
                raise ValueError("done requires receipts: " + task_id)
            for evidence in change["completion_evidence"]:
                if not (ROOT / evidence).exists():
                    raise ValueError("receipt absent: " + evidence)
        task.update(change)
    data["status"] = "in_progress"
    data.setdefault("change_log", []).append({"reason": reason, "task_ids": list(updates),
        "scope_effect": "Product ordering preserved. Historical data and synthetic/live/replay receipts remain distinct."})
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    subprocess.run([sys.executable, str(ROOT / "checks/render_checklist.py")], check=True)


if __name__ == "__main__":
    updates = json.loads(Path(sys.argv[1]).read_text())
    update(updates, sys.argv[2])
