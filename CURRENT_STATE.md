# 当前交付：可安装、可直接接入宿主的 Research Retro

当前产品从 `retro start PROJECT --workspace W` 开始，生成可交给强 Agent 的入口。原项目只读，科学调查、当前认识、修订和交接留在独立 workspace。本轮在这个产品闭环收口，更大 Harness 继续延期。

- 配置 `--worker dsh --jev` 后，Agent 只需 `retro -w W discover`：产品准备下一批材料，运行便宜 worker，做已授权的局部判断，写出 `discovery/latest.md` 科学调查简报。再次运行继续下一批；`--question` 改变调查问题，`--overview` 只看材料概况。dsh 使用宿主配置的 v4.1flash；其它 JSON worker 命令同样可用。
- 强宿主从候选回原件完成科学理解，用 `record` 保存问题、对象、尝试、认识和路线。没有新增科学 ontology、强制 review 或概率门槛；Jev 是过程内的局部判断服务。
- `SPINE.md` 提供短主线，`RESEARCH_MAP.md` 保留详情；版本、来源、核查和历史可追溯。新材料可先产生影响候选，再修订有关认识和行动，保留独立结果。新 Agent 能从导出包继续实际研究。
- 完整链已经实际使用；暴露的局部误判、缺件和宿主遗漏保留在阶段记录中。最后的产品改动是把手工串接压缩成日常发现命令，并直接传入已准备的文本，减少 worker 重复工具读取。没有继续扩充案例或 benchmark。

[安装与使用](releases/standalone-3.6.0/INSTALL.md) · [产品交付说明](releases/standalone-3.6.0/REPORT.md) · [源码入口](README.md) · [冻结产物](releases/standalone-3.6.0/release.json)

已完成关键流程回归和独立离线安装；软件检查不等于科学理解准确率。跨学科、其它强宿主的实测成功率和总体成本优势尚无充分证据。未创建 Git 标签或远程发布；原科研项目和既有作业保持原样。

以下保留阶段历史，不代表当前默认流程或新的完成承诺。

---

# 前一阶段交付：宿主主导的产品闭环（3.6.0）

本轮产品交付完成：单入口独立安装、宿主主持真实重建、独立发现、短科学主线、原件可追溯交接，以及真实后续材料引起的修订。更大 Harness 继续延期。

- `retro start PROJECT --workspace W` 生成随包宿主入口；`record` 一次保存调查，seal/reveal 改为可选。发现与聚焦上下文分离，不再强塞未关联文件。
- `SPINE.md` 读取当前科学节点，`RESEARCH_MAP.md` 保留细节；修订更新行动与主线，历史和独立结果保留。`add-source` 接入新只读材料，核查脚本/结果可携且有明确版本归属。
- Jev 是显式局部 typed judgment 服务，保留原请求/回答/成本；无自动调用、无概率门槛。历史窄授权不扩张。实际一次调用未证明额外科学收益，继续可选。
- 全新 Agent 在独立选定真实材料上完成三臂重建；两个新读者从包完成实际后续核查。B 修订保留 18 个旧节点、更新 1 个、增加 3 个；独立评价者验证历史和重放结果。初次遗漏、失败与揭示后定向修复分别保存。
- 冻结 wheel 通过 135 项回归，以及旧版 4+37、2.0 48、当前产品 4+26 项断网隔离安装/生命周期检查。48 个包内产品文件与当前源码完全一致。
- 结果支持本案例的产品闭环，不证明完整历史覆盖、跨学科/宿主成功率、总体准确率或提速。真实研究状态仍为 draft；原科研项目只读，未提交科学作业。

[安装使用](releases/standalone-3.6.0/INSTALL.md) · [交付报告](releases/standalone-3.6.0/REPORT.md) · [实际产品验收](research_cases/product/REPORT.md) · [独立最终评价](research_cases/product/evaluation/FINAL_ACCEPTANCE_REPORT.md) · [产物与哈希](releases/standalone-3.6.0/release.json)

未创建 Git 标签或远程发布，保留本轮开始前的未提交工作。以下为不可覆盖的历史交付记录，其默认行为和验收口径不代表当前产品。

---

# Research Retro 3.5.0：模块修复完成，验收包含中断续跑

字段语义门禁、真实 Jev 前提/行动检查及回执回写、独立未关联队列已进入公共工作流；CLI、工具定义和随包技能已同步。

- 真实 r655：两处矛盾保持待审；只改理由时下游行动仍被阻断；理由和行动均修平后才解除。完整 87 节点副本在 `/home/sun07ao/retro-workspaces/grephene-retro35-acceptance`。
- Jev 共 44 请求、42 成功、2 次 HTTP 400。旧理由/行动的原始 Choice 都是低于既定 0.8 阈值的 consistent，实际依靠不确定门禁阻断；不宣称模型明确判为 stale。
- 主查询无匹配时独立队列仍推选零引用输出；每个上下文强制加入六个候选。候选曝光不等于重要性或科学覆盖认证。
- 原始状态库与本次 Hessian/条件原件未修改。另有16个历史节点继续待审，项目整体仍为 draft。
- 软件回归与安装兼容性通过。真实验收包含准备、载荷和判别断言问题后的续跑，不冒称单次无中断通过；失败与修正回执均保留。

[详细结果与限制](research_cases/retro35/ACCEPTANCE.md) · [实案入口](research_cases/retro35/accept_r655.py) · [增量 diff](var/retro35/changes.diff) · [验收结果](var/retro35/acceptance/result.json)

历史 3.0 回执继续保留；未发布远程版本或 Git 标签。以下为此前状态记录。

---

# 当前交付：Research Retro 3.0.0

独立产品的软件交付已完成：统一 `retro start PROJECT` 入口、随包宿主工作流、问题驱动的上下文、可修订科学状态、主线与原件导航、便携交接。更大科研 Harness 继续保留，不在本次范围。

- 新入口生成独立 workspace、`START_HERE.md`、宿主方法和初始材料目录；重复运行可续接，既有目标不会静默替换。所有新输出位于原项目之外。
- 强宿主 LLM 主持科学理解；确定性内核维护原件、版本、支持与影响。产品不内置模型服务，1.0/2.0 接口保持兼容。
- 定义/条件先读，旧解释后揭示；全局问题图可修订，未关联材料有独立发现入口。元数据覆盖不等于科学读取。
- 修订更新当前页面并失效旧完成评估；导出发现新材料也会重开覆盖评估。正文、论证和下一步行动的一致性由宿主明确检查，不能仅靠依赖版本。
- 主线不展开大段 JSON；详细结构与原件保留可查询入口。原项目不移动、不写入，不提交科研作业。
- 最终 wheel：117 项回归，旧版 4+37、2.0 48、新版 4+20 项隔离安装/生命周期断言全部通过。
- 真实项目只作开发验证。初次失败、已暴露修复、实际冷接手及三臂比较分别保存；未证明比直接强 LLM 更准确，也未证明任意未见项目上的稳定科学重建。

[安装与使用](README.md) · [产品交付报告](releases/standalone-3.0.0/REPORT.md) · [评价与限制](releases/standalone-3.0.0/EVALUATION.md) · [产物与哈希](releases/standalone-3.0.0/release.json)

本轮未创建 Git 标签或执行远程发布。以下是历史版本记录，其默认路径、验收结果和发布标签不代表当前版本。

---

# 当前交付：Research Retro 2.0.0

依据 `research_retro_architecture/IMPLEMENTATION_CONTRACT.md` 实现的独立产品已完成，发布版本 **2.0.0**，标签 `retro-v2.0.0`。F1/E1 主控框架阶段仍未启动。

- 新入口：snapshot / recover / records / explain / contrast / impact / support / task / probe / close / verify-handoff / migrate；1.0 生命周期继续兼容。
- 核心无模型调用或联网；静态恢复不执行项目代码。历史收据保持 project_asserted，新受控执行单独出具 broker 收据。
- 明确区分捕获、参数条件推导、历史执行关联、模型适用性和科学资格。Python 首版的受支持范围和未知边界见 README。
- 交付对象是带来源、版本、调查义务、探针与限定结论的 ReconstructionPackage。收口状态是 closed-resolved / closed-qualified / open-blocked。
- 干净安装后的 2.0 生命周期已通过 48 个实际断言，包含四格隔离干预、独立离散公式、隐藏原项目后的查询与四次关键重放。记录：`var/retro2/acceptance-04/`。
- 107 项回归、41 项旧版安装与生命周期兼容检查通过。空白 Agent 首轮发现撤回传播缺口，修复后针对性复验通过；原失败与已揭示后的复验均保留。最终产物与证据见 [2.0 发布报告](releases/standalone-2.0.0/REPORT.md)。

以下保留旧版本的历史交付记录，不将其验收数量冒充 2.0 的新增验收。

---

# 当前状态

独立复盘能力单元 **Research Retro 1.0.0** 已完成，冻结标签 `retro-v1.0.0`。这是 R2 内核的产品解耦发布；F1/E1 仍暂停，没有引入主控 Harness、模型路由或跨模型编排。

- 核心仅含通用索引、原件快照、版本状态、Provenance、审计与纠偏、交接导出。案例分派、领域专用解析与 Jev 实验移至 `research_cases/legacy/`，不进入 wheel。
- 状态默认写入目标项目 `.retro/`，也可显式指定独立 workspace；配置、数据库、blob、后处理与报告均留在该 workspace，核心目录禁止写入。
- 入口：`retro init/scan/read/reconstruct/audit/correct/export/inspect/state`；`rh` 同义。Agent 接入见 [AGENT.md](AGENT.md)，通用函数定义见 [tools.json](tools.json)。
- 实际验收：76 项回归检查；最终隔离安装与冷启动共 41 个断言，62 条命令有完整日志。无开发者 home/仓库/网络、安装目录只读；陌生声学假想项目完成实际数值复算、承重纠偏和完整交接。
- 首次空白 Agent 只读交接包重算原件并复原认知，找出三处标签/说明/遗漏问题；修复后针对性复验通过。进一步标签和缺口索引改进也已复核。不能把复验称为新的空白盲测。
- Codex 主控直接 shell 调用与通用 JSON Tool 调用共享 dispatcher；状态、历史、原件读取和错误契约一致。未声称已启动 Claude Code/Pi/OpenCode 实例测试。

下载与复现见 [发布报告](releases/standalone-1.0.0/REPORT.md)、[冻结清单](releases/standalone-1.0.0/release.json) 和 [安装说明](README.md)。最终完整回执在 `var/standalone/acceptance-05/`；压缩副本、独立交接包与 wheel 已纳入版本化发布目录。早期失败与修复前回执保留。

Linux/Python 3.14.4 的隔离安装实测通过；声明的运行接口要求 Python >=3.11/POSIX，未验证原生 Windows 或其它操作系统。显式科研后处理沿用主控宿主的 OS 权限，未冒充 F1 worker 沙箱。真实科研原件、原作业和历史 R2 状态库未修改。

---

# R2 历史发布快照（保留，未重放）

R2 已发布：0.2.0，Git 标签 `r2-0.2.0`（`2ce434e`）。按用户最新要求在此暂时收口。R0/R1 是已完成的中间阶段；F1 未验收草稿已另存 `wip/f1-runtime` 分支，E1 尚未开始。见 [F1 暂存点与剩余工作](F1_CHECKPOINT.md)。

已落地：独立 Git/uv 项目；SQLite DELETE/FULL 状态内核与一致性备份；源范围、不可变字节、精确定位、旧索引迁移、增量覆盖；对象/条件与实际运行恢复；五轨历史、分支、负知识、待审队列；AND/OR 支持及事务纠偏；通用科学工作台、Jev 建议适配、查询、分块上下文与只读阅读器。

当前生产交接：`var/projects/grephene/reports/latest.json` 与 `var/projects/diffusion/reports/latest.json`。grephene 本次发布状态 r2579，恢复179份捕获输出的运行身份，437份原件快照；元数据账本96676项，含97个明确排除的目录根、96138项待读和4项读取失败。覆盖账本不等于科学读取完成。311个原始候选保留并有主题路由。

承重科学结果：

- [局部梯度/能量](research_cases/grephene/REPORT.md)：归一化差梯度约−4.57至−4.60 eV/Å；3.20 Å处垂直隙0.261 eV，与相对FC基态能高1.156 eV分开；两个相邻上升反驳严格单调。
- [T13b](research_cases/grephene/t13b_audit_normalized.json)：短碳接触从C31/C32移至C32/C33；16.049 kcal/mol为受约束采样电子能峰，不能作完全脱附或退火自由能垒。
- [入口EA](research_cases/grephene/entry_audit_REPORT.md)：旧TMS r2SCAN −2.126642 eV成立；几何/方法改变后结果不同。已完成DLPNO垂直EA −0.398233 eV，分离DEA端点 +0.017609 eV，均不确定界面捕获路径或通量。
- [diffusion](research_cases/diffusion/REPORT.md)：20001帧速度独立复算；3 DOF大涨落本身不证明异常，启动段尚未获得平衡/扩散资格。

未采用的强结论：所有有机入口/基面路径关闭、Marcus寿命与机制排名、实验前体与产物身份。保留原话、来源、条件、未知与具体再审入口；缺失原件和新计算需求不被默认为已解决。

实际验收：66项软件检查；真实克隆20项恢复/AND-OR传播与14项扩展依赖隔离；新上下文查证及4项查询缺陷复验通过。见 [验收依据](research_cases/R2_ACCEPTANCE.md)、`var/receipts/development_tests.log`、`r2_recovery.json`、`r2_entry_isolation.json`、`fresh_handoff_r2_extension.json`。

有效纠正：反驳裁决与命题真值分离；逐关系而非整批源依赖；读取与指纹使用同一字节快照（已修导入竞态并重放）；精确ID优先查询；来源变更/删除、相关读集和政策版本传播。此前失败回执保留。

Jev 三次真实合成调用均为 jev-1.13.0，累计1892输入/351输出token；缓存回放另记零新增usage。私密原件没有送入Jev。建设入口有用户授权，运行worker尚待F1环境强制验证。

收口时复核：7份冻结回执哈希一致，两项目的当前版本与发布备份一致且备份完整性通过；回执为 `var/receipts/r2_stop_checkpoint.json`。F1仅保留原型与失败/成功初测记录，没有进入R2发布代码或正式科学状态。

历史复现使用 `r2-0.2.0` 标签及该标签的 README；旧命令不适用于当前 standalone CLI。原件与原作业未修改，未提交新DFT/MD/训练/集群任务，未变更全局配置。
