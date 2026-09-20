"""Thin in-process adapter: same services as CLI, no additional authority."""
from research_harness.context import build_context
from research_harness.views import query
from research_harness.views.report import brief
from research_harness.reconstruction.workbench import AuditWorkbench


class AgentTools:
    def __init__(self, store, ingestor):
        self.store, self.ingestor = store, ingestor
        self.audit = AuditWorkbench(store, ingestor)

    def context(self, task=None, budget_chars=16000):
        return build_context(self.store, task=task, budget_chars=budget_chars)

    def find(self, text, kind=None, limit=20):
        return [brief(r) for r in query(self.store, text, kind=kind, limit=limit)]

    def read(self, locator):
        return self.ingestor.read(locator)

    def audit_packet(self, case_id):
        return self.audit.packet(case_id)
