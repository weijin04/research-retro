# 7. 关键系统契约

本文件定义最小边界；`contracts/contract.schema.json` 提供关键交换对象的 JSON Schema 草案。首期不要求一次实现全部领域本体，但以下语义不能在实现中丢失。

## 7.1 通用规则

对象使用稳定 ID，修订使用递增 revision 或不可变版本 ID；两者分开。时间使用带时区的格式，历史时间未知时保留 null 和原文字段。

每条可采信记录保存其来源、提出者、创建活动、当前适用域和修订理由。原始字节与解析表示分开保存，更新解析器会产生新版本，不覆盖旧结果。

不允许 `null` 同时代表“未知”“不适用”“已检查不存在”。使用显式 status 与可空 value。

schema 的合法性仅表示交换格式合约成立。数值单位、对象可比性、协议一致性、推断充分性分别由后续检查负责。

## 7.2 读取与定位契约

`SourceManifest → scan/import → Artifact → SourceLocator → read(locator)`

SourceManifest 声明访问根、排除项、允许格式、外发范围、快照策略和处理预算。扫描器对符号链接解析后的目标继续验证范围，不能借链接越界。

SourceLocator 至少包括 artifact/version/content identity、路径或对象键、定位类型和区间。支持行、字节、表格单元、PDF 页/区域、帧或轨迹区间。对承重数值应能返回原值周围的条件，不能只定位一个脱离语义的数字。

读取必须匹配指定版本。原件变化时返回 `source_changed` 或历史快照，不静默返回新内容。历史副本缺失时返回 `unavailable`，不让模型补齐。

## 7.3 解析适配器契约

`parse(artifact_ref, parser_version, policy) → records + locators + warnings + coverage`

解析输出保存原字段/原值与规范字段/单位；转换规则和常量版本进入 provenance。混合能量类型、载量、温度或参考态不能被统一字段名掩盖。

解析器的覆盖包含已解析和未理解区域。失败不把整个文件登记成“无结果”，部分成功不得登记成“全部解释”。对程序输出优先使用可靠结构化记录；启发式关联需携带不确定标记。

## 7.4 对象、运行和证据契约

ObjectIdentity 保存原对象、别名和状态定义；等价关系必须说明在何种后续操作下可替换。对象合并可撤销。

Run 保存 intent/actual input/actual executable/environment/process/output/postprocess。找不到历史代码时不能使用今天的 HEAD 自动补全。设置一致性检查返回检查了哪些字段、哪些未知、哪些矛盾。

Evidence 记录观测值、目标量、单位、误差、条件、源运行和处理活动。没有单位的数值保留未知，不自动按常见单位理解。模型预测、数值模拟与实验测量分层，不能给预测套实验金标标签。

## 7.5 深审契约

`AuditCase → TaskPacket → analysis/checks → AuditResult → proposed ScientificPatch`

AuditCase 包括：原始主张、真实问题、科学范围、材料、竞争解释或反例、所需推导/检查、授权及预期影响。

AuditResult 包括实际读取的材料、完成的推导或代码检查、真实运行回执、未解决关系、裁决范围和状态影响。方法名称、下一步计划、自评“深刻”均不能填入已完成分析。

独立审查保存 reviewer 的实际输入包及先验暴露；同源审阅不增加独立物理证据数。审计允许 `supported/qualified/refuted/invalid_test/unsupported/unresolved/mixed` 等结果，范围由具体命题限定。

## 7.6 科学提交契约

`propose_patch → validate_structure → verify_read_set → validate_authority → check_support_obligations → commit`

必要字段：patch ID、project ID、base/read-set、原始理由/纠正、操作、依据、审批或核验记录、idempotency key。

支持图由服务器重新计算，不能信任提案者自报的影响集。自动传播负责已有显式依赖；潜在隐含依赖由检索和 Jev 扩展，新的语义边经审查加入。

冲突策略：

| 情况 | 结果 |
|---|---|
| 所读对象未变化 | 可继续检查与提交 |
| 仅无关对象变化 | 不阻塞 |
| 相关对象/权限已变化 | 返回需要重评的对象及差异 |
| 重复 idempotency key 且 payload 相同 | 返回已有事务回执 |
| 重复 key 但 payload 不同 | 冲突，不自动覆盖 |
| 数据库事务失败 | 状态与事件均回滚；隔离未引用 blob |

## 7.7 科学状态变化与治理变化分开

ScientificPatch 没有扩大预算、更改权限或关闭校验器的操作。治理变更走单独 GovernanceDecision，由人类或明确授权的策略主体提交。

人类说“不要继续依赖 A”时可修改 A 的工作使用资格；人类陈述新的观察时登记为带来源的观察；关于解释的判断进入可追溯裁决。身份权威与物理真理分开。

## 7.8 上下文契约

`compile_context(goal, task, state_revision, budget) → ContextPacket`

每个片段有来源版本、角色、mandatory 标记、纳入/排除理由。有效目标、纠正、承重反证和任务依赖不受 Jev 排序单独删除。

ContextPacket 保存实际交付内容的指纹。后续工作登记 read-set 和按需读取记录。预算不足需要拆分读取或任务；不能静默缩减任务要求。

## 7.9 动作、租约与回执契约

`TaskProposal → Admission → Lease → Attempt → ExecutionReceipt → Verification → ScientificPatch`

Admission 检查合法目标、任务身份、相关版本、权限、已有重复任务和资源预算。需要新 candidate type 时允许扩展候选空间，不能通过更换名称绕过旧任务预算。

ExecutionReceipt 保存实际参数、输入指纹、程序/模型版本、开始结束、资源使用、stdout/stderr、输出位置、失败原因及执行边界模式。agent 说“已运行”没有回执时，状态为未核实报告。

工具退出状态、协议遵守、科学检验有效性、任务产物完成分别记录。运行失败结果仍可贡献负知识；解释性断言需要相应依据。

## 7.10 推荐外部命令语义

以下为待实现的 CLI 产品接口草案，不声称当前已有可执行命令：

```text
rh doctor
rh project init
rh sources import / scan / refresh
rh artifact read
rh runs reconstruct
rh audit propose / execute / review
rh state propose / validate / commit / diff
rh context build
rh reconstruct run / resume / report
rh branch show
rh runtime propose / dispatch / reconcile     # F1
rh governance correct                       # 按权限
rh report export
rh backup create / restore-check
```

命令名可调整，但同一操作应在 CLI 和 agent tool adapter 中使用同一业务实现，避免两套语义。CLI 必须提供机器可读输出和稳定错误码。错误至少区分权限拒绝、源变化、版本冲突、解析失败、未知提交状态、外部服务失败与科学检验无效。

## 7.11 schema 演化

只为稳定、重复且影响结果的对象增加强约束字段。临时探索保留 `extensions`，附带表示定义和来源。schema 升级写迁移与兼容说明，回放旧回执仍按原版本解释。

示例 `contracts/contract.schema.json` 覆盖五个关键交换对象；源清单、运行和完整存储表在相应任务中按真实数据完善。不能将该草案自动宣称为完整产品数据库。
