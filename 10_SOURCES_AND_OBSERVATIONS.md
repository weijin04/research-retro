# 10. 来源、现场观察与未核实事项

本包日期：2026-09-20。架构、里程碑、任务、接口、预算策略和验收设计均为本轮方案，不是对现成软件能力的陈述。

## A. 当前任务依据

用户明确要求：输出详细项目框架、地图与执行清单，交给本机 agent 实现；Jev 本机已可用，建设过程中可以尝试；优先完善复盘模块，随后整体 MVP，详细测评最后，具体执行路线由本方案设计。

前一轮架构回答是设计上下文，不能当作经过实施验证的系统。此前会话检索恢复的观点仅用于保留目标、纠正与失败经验；涉及当前软件事实以本轮官方资料和现场观察为依据。

## B. 本机只读观察

### L01：项目目录

通过 Remote Desktop Commander 查看 `/home/sun07ao/框架`，工具返回没有条目。只支持当时目录为空的判断，后续实施前需再次检查。没有创建或修改该目录。

### L02：TypeSafe 插件

确认路径：

`/home/sun07ao/.claude/plugins/cache/typesafe-ai/typesafe/0.5.7/README.md`

`/home/sun07ao/.claude/plugins/cache/typesafe-ai/typesafe/0.5.7/skills/typesafe-ai/SKILL.md`

已完整读取这两个文本。README 标示可使用 `/typesafe:typesafe-ai`；skill 说明类型化判断、查阅实时文档、保持代码控制、保留候选覆盖与不确定性。

没有调用 Jev API，没有读取密钥，没有确认 SDK 安装位置、当前模型列表、服务连通性或实际费用。用户提供的“本机可用”作为实施前提，本轮确认的是插件入口。插件版本不等于模型版本。

### L03：grephene evidence map

已列出 `research/scientific_evidence_map_20260915/` 并读取 README。确认存在 SCIENTIFIC_FAMILIES、EVIDENCE_LEDGER、MODEL_PROVENANCE_AUDIT、CONTRADICTIONS_AND_ANOMALIES、FORGOTTEN_ASSETS、REVIEWER_ENTRYPOINTS、JOB_TO_SCIENTIFIC_FAMILY 和 appendix。

README 给出的 job/族/条目数量属于原文报告，本包没有独立重新计数，不用于宣称全项目覆盖或新系统能力。

### L04：grephene raw census

已列出 `research/raw_asset_census_20260915/`。确认存在 ALL_FILES、JOBS、JOBS_DEDUP、JOB_FILES、RAW_RESULTS、GEOMETRIES、PARSE_FAILURES、RESTART_CHAINS、SETTING_MISMATCHES、FIELD_DEFINITIONS、SCAN_SCOPE、scripts 及增量目录。

本轮没有深审其科学正确性，也没有扫描最新计算。它们是可复用的导入入口，不能直接成为新系统金标。

## C. 官方技术资料

所有下列链接于 2026-09-20 查阅。实现时核对实际版本；此处无性能保证和价格承诺。

| ID | 来源 | 支持的具体信息 |
|---|---|---|
| S01 | TypeSafe Introduction，`https://docs.typesafe.ai/introduction` | state 与类型化问题；三种 primitive；同一状态的独立并行问题 |
| S02 | TypeSafe API reference，`https://docs.typesafe.ai/api` | endpoint、请求/响应字段、question ID 语义、模型与 usage 返回 |
| S03 | TypeSafe Python SDK，`https://docs.typesafe.ai/sdk/python` | 同步/异步客户端、现有 SDK 接入和环境变量 |
| S04 | TypeSafe Confidence，`https://docs.typesafe.ai/confidence` | confidence 来自分布，Noul 无独立 confidence，阈值需要按风险验证 |
| S05 | SQLite WAL，`https://www.sqlite.org/wal.html` | WAL 的同机约束、单 writer、checkpoint、持久化设置、WAL-reset 修复及备份边界 |
| S06 | Jev 1.13 jaggedness，`https://docs.typesafe.ai/model-jaggedness/jev-1.13` | 数值、多跳、长无关状态、对抗内容与结构不变量的已知边界 |
| S07 | SQLite Atomic Commit，`https://www.sqlite.org/atomiccommit.html` | 事务原子性机制及其适用条件 |
| S08 | TypeSafe Models，`https://docs.typesafe.ai/models` | 模型/别名、文本输入、语言支持的版本入口；部署时应重新读取 |
| S09 | TypeSafe Quick start，`https://docs.typesafe.ai/introduction/quickstart` | API/SDK/agent skill 的起步示例 |

这些来源支持 Jev 与 SQLite 的接口边界。科研审计 schema、纠偏语义、worker 权限划分、资源租约和评测方案由本包提出，尚待实现及验证。

## D. 仍需实施者现场确定

实际生成模型调用方式；现有 Jev SDK/凭证入口；worker 隔离与资源限制可用性；数据库和源文件的真实规模；远端只读接口；原始文件格式与解析覆盖；每个来源的数据外发范围；实际运行预算。

优先通过只读预检和小规模真实调用查明，不能把这些常规现场问题全转交用户。需要新增权限或用户独有决定时再定位并上报。
