# 实现中的契约版本

原始 `contract.schema.json` 0.1.0 保留为外部交换契约；`rh validate` 验证其结构，不能替代科学检查。通用工作台接受该 AuditCase 契约。

状态内核以 `{id,kind,revision,data}` 存业务记录，开放的 `data` 保留原始扩展。领域开发案例的 `audit-case-local-1`、`project-reconstruction-local-1` 是有明确转换器的领域输入，不静默改称 0.1.0 交换对象。转换在 `reconstruction/audit.py` 与 `bundle.py`，全部原始字节同时保存。

2026-09-20，support-semantics-v2：反驳、无效检验、未知或未核验 Claim 不再成为肯定式下游前提。`support_status` 表达命题的当前可用支持；`adjudication_supported` 表达对该命题的裁决是否仍有依据。原有记录通过一次空科学事务重算并保留旧 revision，不能把 refuted 命题本身当真。

来源身份、运行完成、协议、数值健康、方法适用和推断资格分轴保存。未验证部分的默认值为 unchecked/unknown；无来源不自动推出否定命题。
