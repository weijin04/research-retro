# 6. 详细执行清单

共 56 项任务。此文件由 backlog.json 生成；任务变更先更新 JSON，再重新生成。

版本完成要求该版本所有任务及其依赖都有真实产物；单个退出任务不能豁免其他必要工作。

## R0：环境、来源与 Jev 接入

### [x] R0-01 现场预检与独立开发环境

状态：done。
目标：复用本机能力并避免修改活跃科研环境。
依赖：无。负责角色：集成/实现负责人。

具体工作：
1. 检查目标目录、git 根、已有新增文件和可用 Python 环境。
2. 定位既有 cc/codex 调用方式、TypeSafe 插件与隔离能力，只记录路径/版本，不输出凭证。检查 Python 实际链接的 SQLite 版本与已知修复状态。
3. 建立独立项目环境和忽略规则，不改全局配置。

交付：环境能力清单；独立项目入口；权限/能力缺口表。
验收：git 根限定到框架项目。；原科研仓库与既有作业未被修改。；未查明事项明确标记，未把插件版本当模型版本。
Jev：先读取本地 skill，不重装。
完成证据：var/receipts/doctor.json；pyproject.toml；uv.lock；var/receipts/development_tests.log。

### [x] R0-02 目标、来源与权限合同

状态：done。
目标：把产品目标与接入边界变成可检查配置。
依赖：R0-01。负责角色：集成/实现负责人。

具体工作：
1. 建立 R2/F1/E1 的完成范围与优先级。
2. 登记 grephene 首期源、旧索引入口、输出目录和禁止动作。
3. 设置逐来源外发范围、轻量后处理范围、资源上限与审批主体。

交付：ProjectContract；SourceManifest；数据外发/权限策略。
验收：未授权源不进入扫描。；新增科研计算与复盘后处理分开。；策略不存在无限预算或任意工具默认放行。
Jev：按需，不承担最终裁决。
完成证据：research_cases/legacy/config/grephene.json；research_cases/legacy/config/diffusion.json；var/receipts/development_tests.log。

### [x] R0-03 最小契约与项目骨架

状态：done。
目标：提供实现真实链路所需的稳定交换边界。
依赖：R0-02。负责角色：集成/实现负责人。

具体工作：
1. 接收并按现场调整本包五类 JSON 交换草案。
2. 建立 contracts/storage/ingest/reconstruction/decisions/views 模块入口。
3. 确定对象 ID、revision、locator、错误码和迁移约定。

交付：可运行 CLI 骨架；版本化契约；最小配置加载器。
验收：有效/无效样例有确定结果。；未知字段与科学扩展不被静默丢弃。；骨架未被登记成完整产品。
Jev：按需，不承担最终裁决。
完成证据：src/research_harness/cli.py；contracts/MIGRATIONS.md；tests/test_reconstruction.py；var/receipts/development_tests.log。

### [x] R0-04 Jev 适配器与真实 smoke

状态：done。
目标：建设期开始使用 Jev，并保留可追踪调用。
依赖：R0-01, R0-02, R0-03。负责角色：集成/实现负责人。

具体工作：
1. 按当前 skill/SDK 复用配置，完成合成数据真实请求。
2. 记录三种 primitive、实际模型、usage、耗时和错误。
3. 实现有界重试、超时、缓存身份及不外泄日志。
4. 使用少量中文/否定/未完成表述做接入边界检查，完整校准留到 E1。

交付：JevAdapter；真实 smoke 回执；故障/去敏检查。
验收：live 与 synthetic/replay 明确区分。；Noul 不制造独立 confidence。；鉴权或服务故障不会写成语义否定。
Jev：实际调用；仅合成/公开数据。
完成证据：research_cases/legacy/decisions/jev.py；var/receipts/jev/f9fbf3ec9ac1468ca92b904f39ec1e4a.json；tests/test_jev.py；var/receipts/development_tests.log。

### [x] R0-05 复用旧资产并选择首个真实深审关系

状态：done。
目标：从已有可靠入口进入真实问题，避免重做全部调查。
依赖：R0-02。负责角色：科学集成负责人。

具体工作：
1. 读取旧 census 字段定义和 evidence map 入口。
2. 确认一个承重/可疑关系的原始材料可访问。
3. 确定在只读/轻量后处理中可实际解决的 AuditCase，保留其历史主张。

交付：旧资产映射清单；首个 AuditCase 草案；原件定位集。
验收：选择依据涉及科学关系而非易生成报告。；未把旧 reviewer 结论当新审计答案。；未以原件缺失自动启动新科研计算。
Jev：按需，不承担最终裁决。
完成证据：research_cases/grephene/audit_case.json；research_cases/grephene/REPORT.md；var/receipts/development_tests.log。

## R1：真实复盘纵向贯通

### [x] R1-01 状态存储、原件存储与提交事务

状态：done。
目标：让核心记录可恢复且原件不被覆盖。
依赖：R0-03。负责角色：集成/实现负责人。

具体工作：
1. 实现单 writer、对象修订、blob 引用与事件/outbox。
2. 实现原件先落盘、数据库后提交及孤立 blob 对账。
3. 配置本机存储、事务持久化与基础备份。

交付：状态库 v0；blob 服务；事务与故障回执。
验收：事务失败没有半更新状态。；旧 blob/修订仍可读取。；数据库不会指向未完成的已提交输出。；WAL 部署使用包含已知修复的实际库；否则采用明确记录的替代日志模式。
Jev：按需，不承担最终裁决。
完成证据：src/research_harness/storage/store.py；tests/test_storage.py；var/receipts/r2_recovery.json；var/receipts/development_tests.log。

### [x] R1-02 只读接入、快照与精确定位

状态：done。
目标：固定首个案例的真实来源。
依赖：R1-01, R0-05。负责角色：集成/实现负责人。

具体工作：
1. 按 manifest 读取并创建来源身份。
2. 生成稳定副本/片段与内容指纹，保留条件上下文。
3. 实现 locator 读取及源变化检测。

交付：首例来源快照；定位读取 API；覆盖记录。
验收：读取返回对应版本原文。；变化源被识别。；链接不能越出授权根，原件不被写入。
Jev：按需，不承担最终裁决。
完成证据：src/research_harness/ingest/service.py；tests/test_ingest.py；var/receipts/development_tests.log。

### [x] R1-03 旧索引导入和首个解析器

状态：done。
目标：把现有资产变成带来源的结构记录。
依赖：R1-02。负责角色：解析适配器实现者。

具体工作：
1. 导入旧 CSV/TSV/JSON 字段和历史核验状态。
2. 解析首例的输入、输出与后处理。
3. 保留原值/单位、转换规则、未理解区域和告警。

交付：旧索引 importer；首个领域 parser；解析覆盖/告警。
验收：旧 RAW-OK 保留历史身份，未经复核不升级。；每个承重值可回源。；部分解析不冒充完整解释。
Jev：按需，不承担最终裁决。
完成证据：src/research_harness/parsers/basic.py；var/projects/grephene/reconstruction_receipt.json；var/receipts/development_tests.log。

### [x] R1-04 首个实际运行与对象恢复

状态：done。
目标：区分计划、实际输入、代码和输出。
依赖：R1-03。负责角色：科学/代码审计者。

具体工作：
1. 建立实际 Run 及输入/环境/输出链。
2. 记录目标量、对象条件和未知字段。
3. 分别判断进程、协议和科学检验资格。

交付：真实 Run 记录；对象条件表；实际/意图差异。
验收：当前 HEAD 不自动补成历史执行版本。；程序成功不自动变成科学成功。；不确定关联保留候选。
Jev：按需，不承担最终裁决。
完成证据：src/research_harness/reconstruction/runs.py；var/receipts/grephene_runs.json；tests/test_runs.py；var/receipts/development_tests.log。

### [x] R1-05 首个历史命题、支持集合与推断

状态：done。
目标：恢复结果到结论之间的连接。
依赖：R1-04。负责角色：科学集成负责人。

具体工作：
1. 保存历史原文、提出者和时间。
2. 将精确命题、条件、前提集合与推断分开。
3. 登记支持、反对和共享来源。

交付：HistoricalAssertion；Claim/Inference；支持与来源关系。
验收：摘要不是新增独立证据。；条件和量词未丢失。；端点/路径等目标量差别能表达。
Jev：按需，不承担最终裁决。
完成证据：research_cases/grephene/audit_case.json；tests/test_storage.py；var/receipts/development_tests.log。

### [x] R1-06 深审工作台与真实分析

状态：done。
目标：在产品中实际完成一个困难科学关系。
依赖：R1-05。负责角色：高能力科研审计者。

具体工作：
1. 向 agent 提供源材料、问题、工具和授权。
2. 完成必要推导、复算、代码调用核查或候选比较。
3. 形成带残余有效部分和影响范围的 AuditResult。

交付：真实 AuditResult；推导/检查产物；原始调用与读取记录。
验收：包含实际求解，不能只列方法和计划。；竞争解释/反例得到与任务相称处理。；缺口与已完成内容分开。
Jev：可筛查，不能替代承重推导。
完成证据：src/research_harness/reconstruction/workbench.py；research_cases/grephene/audit_check.py；var/receipts/grephene_grouped_audit.json；var/receipts/development_tests.log。

### [x] R1-07 基础科学修订与失效传播

状态：done。
目标：让审计结果改变项目使用状态。
依赖：R1-06, R1-01。负责角色：集成/实现负责人。

具体工作：
1. 实现科学补丁的结构、权限与 read-set 检查。
2. 重算 AND 前提及 OR 替代支持。
3. 同事务写事件和视图失效，保留旧版本。

交付：Patch 接口；支持重算器；修订前后差异。
验收：撤销一组支持不误删独立支持。；无支持不等于相反命题成立。；重复提交不会产生重复变化。
Jev：按需，不承担最终裁决。
完成证据：src/research_harness/governance/patches.py；tests/test_patches.py；var/receipts/r2_recovery.json；var/receipts/development_tests.log。

### [x] R1-08 Jev 建议流接入真实链路

状态：done。
目标：在不赋予科学裁决权的前提下减少阅读与定位成本。
依赖：R0-04, R1-05。负责角色：Jev/控制面实现者。

具体工作：
1. 接入文档角色、候选关系和引用范围题目。
2. 传入获准片段及具体条件。
3. 把建议转成可追溯待审项，保留被遗漏/排后的材料。

交付：题目注册表 v0；真实建议回执；候选审查队列。
验收：Jev 不能直接删除证据或合并对象。；题目含完整语义，不依赖 question ID。；未批准数据不外发。
Jev：核心用途，建议模式。
完成证据：src/research_harness/decisions/workflow.py；var/receipts/jev_main_attachment.json；tests/test_jev_workflow.py；var/receipts/development_tests.log。

### [x] R1-09 首个真实复盘交付与集成

状态：done。
目标：证明纵向链路有科学内容并可重复进入。
依赖：R1-06, R1-07, R1-08。负责角色：集成/实现负责人。

具体工作：
1. 生成与同一状态版本对应的报告和证据入口。
2. 展示实际发生/历史解释/当前判定及修订后果。
3. 运行基础重复、源变化和前提撤销检查。

交付：R1 真实复盘报告；端到端回执；R2 待补能力清单。
验收：读者能回到原件核查。；实际分析与合成测试分开。；不把 R1 当作完善复盘产品发布。
Jev：按需，不承担最终裁决。
完成证据：research_cases/grephene/REPORT.md；var/receipts/grephene_report.json；var/receipts/development_tests.log。

## R2：完善可用的复盘产品

### [x] R2-01 完整覆盖与异构增量接入

状态：done。
目标：对声明范围建立完整资产去向，复用现有解析能力。
依赖：R1-09。负责角色：解析/接入负责人。

具体工作：
1. 导入旧源范围，发现新增/变化/遗漏资产。
2. 按真实需求加入文档、图表、结构与日志读取器。
3. 处理大文件、归档、失败恢复和解析预算。

交付：范围/覆盖账本；增量扫描器；格式适配列表。
验收：每个发现资产有处理状态。；大文件未读部分清晰。；支持不了的格式仍可查询，不被视为无内容。
Jev：按需，不承担最终裁决。
完成证据：src/research_harness/ingest/service.py；var/receipts/grephene_scan.json；tests/test_ingest.py；var/receipts/development_tests.log。

### [x] R2-02 对象身份与数值可比性

状态：done。
目标：保留会改变后续计算或解释的差别。
依赖：R2-01。负责角色：领域与数据模型负责人。

具体工作：
1. 实现对象/运行/比较/命题四类不同关系。
2. 为当前化学项目加入组成、电荷、自旋、方法、参考态等必要检查。
3. 合并采用可撤销版本关系，保留未知和扩展对象。

交付：身份与比较服务；领域条件检查；误并/漏并回归样例。
验收：同名异物不能直接合并。；单位/目标量不可比时无法生成无条件差值解释。；新表示可登记。
Jev：只建议候选关系。
完成证据：src/research_harness/reconstruction/identity.py；src/research_harness/reconstruction/provenance.py；tests/test_provenance.py；var/receipts/development_tests.log。

### [x] R2-03 实际代码、协议与数据血统

状态：done。
目标：追到真正产生结果的实现路径。
依赖：R2-01。负责角色：代码与科学协议审计者。

具体工作：
1. 还原脚本调用、参数覆盖和后处理版本。
2. 查承重结果的 mock/fast 分支、未调用代码与失败后替代实现。
3. 登记输入/训练/调参/验证数据关系与可能污染。

交付：运行血统图；协议差异审计；数据来源与用途表。
验收：代码存在不等于实际执行。；正常退出与目标协议一致性分开。；实现失败不会被自动写成科学反证。
Jev：按需，不承担最终裁决。
完成证据：src/research_harness/reconstruction/runs.py；research_cases/grephene/PROJECT_MAP.md；var/receipts/grephene_runs.json；var/receipts/development_tests.log。

### [x] R2-04 来源去重、共同祖先与独立性

状态：done。
目标：防止同一结果在多份报告中被重复采信。
依赖：R2-02, R2-03。负责角色：集成/实现负责人。

具体工作：
1. 建立字节副本、派生、共祖与候选语义重复。
2. 保留多个实际位置和原始 ID。
3. 支持图中显示共享来源与循环依赖。

交付：来源家族；独立性标签；重复/循环检查。
验收：副本不增加样本量。；不同条件真实运行不被错误去重。；循环引用不能自我生成支持。
Jev：按需，不承担最终裁决。
完成证据：src/research_harness/reconstruction/provenance.py；tests/test_provenance.py；var/receipts/development_tests.log。

### [x] R2-05 五条历史轨迹与纠正记录

状态：done。
目标：恢复做过、相信、报告、记忆和当前判定的差异。
依赖：R2-01, R1-05。负责角色：历史与科学语义审计者。

具体工作：
1. 接入授权历史记录并保留时间/作者/版本。
2. 区分用户指令与模型假设、计划与完成报告。
3. 对照纠正是否传播到代码、状态和后续叙述。

交付：历史断言账本；纠正轨迹；报告/实际差异表。
验收：缺失历史不被今天的解释补写。；后来的纠正优先级与原文可查。；mtime 不冒充事件时间。
Jev：辅助角色/语义关系分类。
完成证据：research_cases/grephene/project_reconstruction.json；src/research_harness/views/report.py；tests/test_views.py；var/receipts/development_tests.log。

### [x] R2-06 分支、负知识与孤立资产

状态：done。
目标：恢复被遗忘及被错误停止的研究资产。
依赖：R2-04, R2-05。负责角色：科学重建者。

具体工作：
1. 按问题身份恢复分支，不按目录套固定路线。
2. 分离证据资格、工作处置和停止原因。
3. 建立孤立结果与消失矛盾队列并完成有价值条目的追查。

交付：分支谱系；负知识账本；孤立资产处理记录。
验收：缺证、无效检验、反证和成本搁置分开。；每项否定带适用范围和重开条件。；难整合结果没有悄悄从产物消失。
Jev：按需，不承担最终裁决。
完成证据：research_cases/grephene/project_reconstruction.json；research_cases/grephene/AUDIT_PRIORITIES.md；var/receipts/development_tests.log。

### [x] R2-07 深审任务编排与承重审计覆盖

状态：done。
目标：使深审成为产品能力，并完成当前报告的必要分析。
依赖：R2-02, R2-03, R2-04, R2-06。负责角色：高能力科学负责人。

具体工作：
1. 按目标依赖、可疑证据和异质来源选择 AuditCase。
2. 支持领域工具、独立判断与需要时的 clean-context 重建。
3. 逐项完成推导/核验/比较，裁决已有材料能支持的范围。

交付：AuditCase 工作台；已完成关键审计集；仍未知与实际阻塞表。
验收：不以预设审计数量替代范围完成。；没有用建议核验填充应完成的分析。；独立审查的输入暴露有记录。
Jev：按需，不承担最终裁决。
完成证据：research_cases/R2_ACCEPTANCE.md；var/receipts/r2_case_snapshot_repair.json；var/receipts/r2_entry_isolation.json；var/receipts/fresh_handoff_r2_extension.json；var/projects/grephene/reconstruction_receipt.json。

### [x] R2-08 项目科学地图与完整综合

状态：done。
目标：形成可理解、可挑战的项目世界模型。
依赖：R2-07。负责角色：科学集成负责人。

具体工作：
1. 围绕目标、对象、必要关系和观测组织科学地图。
2. 并列保留竞争解释、孤立证据和未知。
3. 完成报告全部承重主张的来源/推断链接。

交付：项目科学地图；可信状态基线；完整复盘报告。
验收：综合超越目录/时间线整理。；network/ensemble 等连接仍有推断资格。；条件性结论未升级为无条件事实。
Jev：按需，不承担最终裁决。
完成证据：research_cases/R2_ACCEPTANCE.md；var/receipts/r2_case_snapshot_repair.json；var/receipts/r2_entry_isolation.json；var/receipts/fresh_handoff_r2_extension.json；var/projects/grephene/reconstruction_receipt.json。

### [x] R2-09 增量重建与纠偏事务完善

状态：done。
目标：使来源变化和纠正真正更新后续产物。
依赖：R2-08, R1-07。负责角色：集成/实现负责人。

具体工作：
1. 对象级 read-set、语义影响候选与显式图传播结合。
2. 实现视图失效、报告重建及源项目并发变化对账。
3. 异常恢复与重复任务幂等。

交付：增量重建；完整纠偏事务；冲突与恢复回执。
验收：相关变更触发重评，无关变更不全局阻塞。；旧输出保留当时输入身份。；旧报告不能在渲染失败后冒充最新。
Jev：按需，不承担最终裁决。
完成证据：var/receipts/r2_recovery.json；tests/test_reconstruction.py；tests/test_patches.py；var/receipts/development_tests.log。

### [x] R2-10 上下文编译与可靠交接

状态：done。
目标：让新 agent 能在有限上下文中正确接手。
依赖：R2-08, R2-09。负责角色：集成/实现负责人。

具体工作：
1. 生成目标/纠正/反证/负知识等必带内容。
2. 实现按需原件读取和上下文选择日志。
3. 新会话接手回答关键问题并回源核验。

交付：ContextPacket；handoff 生成器；接手回执。
验收：预算不足不会静默删除关键约束。；未把摘要当原始证据。；新会话保留关键否定范围。
Jev：辅助排序，不能删除必带内容。
完成证据：src/research_harness/context/__init__.py；var/receipts/fresh_handoff.json；research_cases/HANDOFF_REVIEW.md；var/receipts/development_tests.log。

### [x] R2-11 查证查询与人类阅读界面

状态：done。
目标：让复盘产物可查、可纠正和日常使用。
依赖：R2-08。负责角色：集成/实现负责人。

具体工作：
1. 提供主张/来源/运行/分支/未知的检索入口。
2. 生成带版本的报告/表格视图及证据跳转。
3. 加入局部异议/纠正入口和原文安全显示。

交付：查询 CLI/API；只读浏览或 HTML 导出；纠正入口。
验收：链接指向准确来源版本。；视图不另写一份独立真相。；界面建设未拖延深审。
Jev：按需，不承担最终裁决。
完成证据：src/research_harness/views/report.py；tests/test_views.py；research_cases/HANDOFF_REVIEW.md；var/receipts/development_tests.log。

### [x] R2-12 恢复、备份、隐私与边界加固

状态：done。
目标：把复盘从一次性运行提升为可持续工具。
依赖：R2-09。负责角色：集成/实现负责人。

具体工作：
1. 验证中断续跑、数据库/blob 一致备份和恢复。
2. 限制归档展开、路径越界、历史指令和敏感外发。
3. 保留失败隔离、重试上限与可审日志。

交付：恢复工具；备份/恢复回执；安全边界检查。
验收：真实恢复可重建来源引用和状态。；敏感内容未进入外部请求。；错误文件不使全部来源永久失败。
Jev：按需，不承担最终裁决。
完成证据：checks/verify_r2_recovery.py；var/receipts/r2_recovery.json；tests/test_ingest.py；tests/test_jev.py；var/receipts/development_tests.log。

### [x] R2-13 第二领域切片兼容检查

状态：done。
目标：检验核心契约没有写死为单个化学项目。
依赖：R2-07, R2-10。负责角色：独立领域审阅/实现者。

具体工作：
1. 在明确只读范围内选 diffusion 独立切片。
2. 恢复实际运行、目标量和一项承重审计关系。
3. 只扩展确有需要的领域字段，记录对旧数据的迁移。

交付：第二领域复盘切片；兼容性修正；开发数据登记。
验收：不把扩散定义/刚柔/载量差异压进同一字段。；未声称开发切片是盲测。；不因兼容检查无限扩张格式范围。
Jev：按需，不承担最终裁决。
完成证据：research_cases/diffusion/REPORT.md；research_cases/diffusion/audit_case.json；var/projects/diffusion/reconstruction_receipt.json；var/receipts/development_tests.log。

### [x] R2-14 完善复盘产品发布

状态：done。
目标：交付可独立使用的完整复盘模块。
依赖：R2-10, R2-11, R2-12, R2-13。负责角色：集成/实现负责人。

具体工作：
1. 核对当前范围覆盖和所有报告承重主张。
2. 完成一次纠偏后的状态/视图/交接演示。
3. 写使用、恢复、边界说明并冻结 R2 发布。

交付：R2 可运行产品；真实项目交付；发布与操作说明。
验收：具备科学审计、分支/负知识、增量和接手能力。；所有完成声明有实际证据。；未将未解科研问题混同未完成复盘。
Jev：按需，不承担最终裁决。
完成证据：research_cases/R2_ACCEPTANCE.md；var/receipts/r2_case_snapshot_repair.json；var/receipts/r2_entry_isolation.json；var/receipts/fresh_handoff_r2_extension.json；var/projects/grephene/reconstruction_receipt.json。

## SCU：领域通用独立复盘能力单元

### [x] SCU-01 分离核心、开发回归、目标状态与配置

状态：done。
目标：独立发行不依赖开发目录、个人 wrapper 或科研案例。
依赖：R2-14。负责角色：独立能力单元维护者。

具体工作：
1. 迁移案例分派、领域解析及模型实验至非发行回归目录。
2. 打包 Schema 与 Agent 文档；以显式 workspace 统一配置和输出。

交付：独立 wheel；核心与回归物理边界。
验收：源码与安装环境无隐含本机路径依赖。；目标状态不得进入核心仓库。
Jev：不使用；无模型调用。
完成证据：src/research_harness/config.py；pyproject.toml；research_cases/README.md。

### [x] SCU-02 公开生命周期与 Agent 契约

状态：done。
目标：主控 Agent 通过一致接口完成复盘。
依赖：SCU-01。负责角色：独立能力单元维护者。

具体工作：
1. 实现 init、scan/read、reconstruct、audit、correct、export 与 inspect。
2. 保留原件版本、作用域、负知识及 OR/AND 传播。

交付：CLI；九个标准工具定义；Agent 手册。
验收：不需要读取底层 Schema 才能驱动。；错误与版本冲突有稳定契约。
Jev：不使用；无模型调用。
完成证据：AGENT.md；tools.json；src/research_harness/unit.py。

### [x] SCU-03 隔离安装、陌生产物与宿主切换实测

状态：done。
目标：按用户指定顺序验证可移植性、科学状态及交接可读性。
依赖：SCU-02。负责角色：独立能力单元维护者。

具体工作：
1. 离线空环境安装并在只读安装目录中运行。
2. 异构假想项目完成实际计数复算、纠偏、负知识和来源扰动。
3. 核验直接调用与通用 Tool 契约；空白 Agent 只读导出包接手。

交付：真实命令日志；冷启动交接包；空白 Agent 发现与复验。
验收：首次验收不利结果保留，修复有复验。；合成能力验收不称为独立科学盲测。
Jev：不使用；无模型调用。
完成证据：checks/standalone_acceptance.py；releases/standalone-1.0.0/REPORT.md；releases/standalone-1.0.0/blank-agent-review.md。

### [x] SCU-04 冻结 standalone 1.0.0

状态：done。
目标：交付可安装且证据可核查的冻结版本。
依赖：SCU-03。负责角色：独立能力单元维护者。

具体工作：
1. 归档 wheel、源文件哈希、回执与复现说明。
2. 创建 retro-v1.0.0 标签；F1/E1 不扩展。

交付：Freeze Release；安装使用说明。
验收：最终构件与实测构件哈希一致。；范围与未验证宿主明确。
Jev：不使用；无模型调用。
完成证据：releases/standalone-1.0.0/release.json；README.md；CURRENT_STATE.md。

## RETRO2：Research Retro 2.0 确定性恢复与调查产品

### [x] RETRO2-01 统一语义与兼容导入

状态：done。
目标：扩展版本存储、字节定位和五类交换实体，保持 1.0 接口。
依赖：SCU-04。负责角色：产品实现与验收。

具体工作：
1. 扩展版本存储、字节定位和五类交换实体，保持 1.0 接口。

交付：src/research_harness/realization/；src/research_harness/handoff/portable.py。
验收：结构与语义验证；无静默资格提升；迁移 dry-run 与独立目标工作区
Jev：不调用模型。
完成证据：releases/standalone-2.0.0/REPORT.md；releases/standalone-2.0.0/acceptance.json；tests/test_retro2.py。

### [x] RETRO2-02 确定性恢复

状态：done。
目标：冻结来源和 Git DAG，恢复参数链、候选执行与未知边界。
依赖：RETRO2-01。负责角色：产品实现与验收。

具体工作：
1. 冻结来源和 Git DAG，恢复参数链、候选执行与未知边界。

交付：src/research_harness/recovery/。
验收：有效步数与算子恢复；两次历史尝试和未绑定替代；复制、缓存和撤回前提诊断
Jev：不调用模型。
完成证据：releases/standalone-2.0.0/REPORT.md；releases/standalone-2.0.0/acceptance.json；tests/test_retro2.py。

### [x] RETRO2-03 实现契约与判别探针

状态：done。
目标：从调查问题发放可复算探针，区分实际执行与科学判据。
依赖：RETRO2-02。负责角色：产品实现与验收。

具体工作：
1. 从调查问题发放可复算探针，区分实际执行与科学判据。

交付：src/research_harness/investigation.py；src/research_harness/runner/。
验收：四格真实干预；离散公式独立比较；可达性与完整时域分开
Jev：不调用模型。
完成证据：releases/standalone-2.0.0/REPORT.md；releases/standalone-2.0.0/acceptance.json；tests/test_retro2.py。

### [x] RETRO2-04 调查协议与权限

状态：done。
目标：实现证据首读、封存揭示、版本提交、限定收口及依赖影响。
依赖：RETRO2-03。负责角色：产品实现与验收。

具体工作：
1. 实现证据首读、封存揭示、版本提交、限定收口及依赖影响。

交付：src/research_harness/retro2.py；src/research_harness/diagnosis/。
验收：过期相关提交拒绝；无关更新带回执 rebase；contained 和 cooperative 明确区分
Jev：不调用模型。
完成证据：releases/standalone-2.0.0/REPORT.md；releases/standalone-2.0.0/acceptance.json；tests/test_retro2.py。

### [x] RETRO2-05 交接和发布

状态：done。
目标：安装产品、运行公开生命周期、完成冷交接并发布 GitHub。
依赖：RETRO2-04。负责角色：产品实现与验收。

具体工作：
1. 安装产品、运行公开生命周期、完成冷交接并发布 GitHub。

交付：checks/retro2_acceptance.py；releases/standalone-2.0.0/。
验收：离线隔离安装；便携查询与关键重放；空白上下文交接；wheel、回执、文档、标签同步
Jev：不调用模型。
完成证据：releases/standalone-2.0.0/REPORT.md；releases/standalone-2.0.0/acceptance.json；tests/test_retro2.py；releases/standalone-2.0.0/cold-agent-review.md；releases/standalone-2.0.0/cold-agent-recheck.md。

## F1：整体框架 MVP

### [ ] F1-01 研究目标与行动合同

状态：planned。
目标：支持开放科研，同时明确执行产物与权限。
依赖：R2-14。负责角色：集成/实现负责人。

具体工作：
1. 实现探索/推导/构造/实现/检验/修复等行动类型。
2. 绑定项目目标、read-set、资源和预期产物。
3. 保留新表示与未知候选入口。

交付：TaskProposal；Admission 规则；行动类型扩展机制。
验收：探索不被强制填成验证实验。；任务改名不能重置身份或预算。；目标/授权变更另走治理入口。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] F1-02 任务上下文和会话恢复

状态：planned。
目标：新研究行动使用当前有效科学状态。
依赖：F1-01, R2-10。负责角色：集成/实现负责人。

具体工作：
1. 扩展 ContextPacket 到行动 read-set。
2. 记录实际读取和上下文暴露。
3. 恢复会话时重建当前任务与状态，不盲继承旧摘要。

交付：研究上下文编译；会话检查点；过期上下文提示。
验收：关键纠正与反证保留。；相关版本变化可发现。；新候选可按需读取更多原件。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] F1-03 worker 隔离与权限能力

状态：planned。
目标：让执行边界由环境落实。
依赖：F1-01, R2-12。负责角色：运行时/安全实现者。

具体工作：
1. 选择本机可用隔离机制并限制来源/工作区/凭证/网络。
2. 运行 worker 不可写控制配置或数据库。
3. 建立任务级短期 capability 和实际越界测试。

交付：受限 worker；权限配置；越界行为回执。
验收：原件、策略、凭证与未授权远端工具无法访问。；没有把 hooks 模式标为硬控制。；缺失系统能力单独报告而不伪造成功。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] F1-04 执行 broker 与幂等对账

状态：planned。
目标：执行真实工具且避免重复有副作用作业。
依赖：F1-03。负责角色：集成/实现负责人。

具体工作：
1. 实现任务状态机、attempt、幂等键与外部执行 ID。
2. dispatch 前持久化意图与资源预约。
3. 连接中断进入 unknown 后查询对账，禁止盲重发。

交付：broker；执行状态机；对账恢复工具。
验收：同键同请求返回既有结果。；同键异请求报冲突。；未知提交状态不会自动重复运行。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] F1-05 资源租约和父子预算

状态：planned。
目标：控制实际计算与模型调用资源。
依赖：F1-04。负责角色：集成/实现负责人。

具体工作：
1. 绑定 CPU/GPU/内存/磁盘/时间/调用上限。
2. 父子任务共享可追溯预算，记录真实与估计用量。
3. 续期需实际产物与剩余工作，设置有限重试。

交付：Lease 服务；资源观测；续期与预算检查。
验收：拆任务不能逃逸总预算。；不可硬限制的费用明确标记。；超预算处理有安全取消/检查点策略。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] F1-06 真实生成模型与工具适配

状态：planned。
目标：利用现有本机 agent 完成受控研究任务。
依赖：F1-02, F1-04。负责角色：集成/实现负责人。

具体工作：
1. 先打通一个真实模型通道与项目工具接口。
2. 动态代码在隔离工作区执行，记录实际参数与输出。
3. 按需要增加第二通道，避免依赖未核实 CLI 参数。

交付：AgentAdapter；工具调用回执；模型/环境版本记录。
验收：至少一次真实程序/数值工作完成。；模型口头完成不能替代回执。；用户固定模型约束被保留。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] F1-07 结果核验与科学更新闭环

状态：planned。
目标：把真实结果接到正确的科学状态变化。
依赖：F1-05, F1-06。负责角色：集成/实现负责人。

具体工作：
1. 封存输出并分别检查退出、协议、数值和检验资格。
2. 由研究 agent 完成解释/推导并提出补丁。
3. 按来源/read-set/权限/支持义务提交。

交付：VerificationPipeline；真实 Result→Patch；失败与残余知识记录。
验收：更快、运行结束与科学成功分别举证。；失效输入产生的输出按旧身份保存。；正式结论未超出支持范围。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] F1-08 重开表示与事件触发审查

状态：planned。
目标：对结构性失败产生真实行动变化。
依赖：F1-07。负责角色：科学与控制面负责人。

具体工作：
1. 登记核心前提撤销、异质异常、重复无产物等事件。
2. 构造 clean-context 独立证据包。
3. 允许续押、改变任务或扩展表示，并更新资源/路线。

交付：事件监视器；独立重建通道；实际路线/资源变化记录。
验收：不按固定轮数机械换方向。；Jev 漏报不会封死主动重开。；只写反思日志不算处理完成。
Jev：辅助事件识别，不决定唯一研究路线。
完成证据：尚无。

### [ ] F1-09 人类纠正与治理决策入口

状态：planned。
目标：让目标/权限和重大科学判断真实改变系统。
依赖：F1-07。负责角色：集成/实现负责人。

具体工作：
1. 提供证据、分歧、后果和仍可并行的工作。
2. 区分目标/权限变更与事实/解释更新。
3. 提交后更新作用域、任务和上下文。

交付：GovernanceDecision；人类审查包；纠正传播回执。
验收：常规可逆动作无需逐步人工确认。；身份权威不会自动证明经验命题。；一次纠正能改变下一轮行为。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] F1-10 运行恢复、服务故障与可观测性

状态：planned。
目标：让长任务可以中断、恢复和降级。
依赖：F1-08, F1-09。负责角色：集成/实现负责人。

具体工作：
1. 恢复 worker/lease/outbox 状态并与实际进程对账。
2. Jev/API 故障与科学未知分流。
3. 保存调用/成本/错误和状态 diff，控制日志敏感信息。

交付：恢复与降级路径；运行日志；故障注入回执。
验收：安全无关工作继续。；相关过期行动需要重评。；未知外部状态不被写成成功。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] F1-11 真实端到端科研循环

状态：planned。
目标：在现有数据与授权下证明整体工作链运行。
依赖：F1-10。负责角色：科学集成负责人。

具体工作：
1. 从 R2 状态选择可推进的真实关系。
2. 提出、执行有限数值/后处理任务并更新判断。
3. 克隆状态注入有依据纠正，观察新上下文与后续行动。

交付：完整科研会话回执；实际科学更新；纠偏前后行动对照。
验收：包含真实求解和结果使用。；没有自动启动未授权昂贵计算。；不把该演示称为统计证明的自主科研能力。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] F1-12 整体 MVP 发布

状态：planned。
目标：交付声明范围内的受控科研系统。
依赖：F1-11。负责角色：集成/实现负责人。

具体工作：
1. 核对 R2 能力在新运行时下未退化。
2. 验证部署边界、状态恢复、实际资源与纠偏。
3. 冻结模型/题目/策略与能力矩阵，标注未实现远端适配。

交付：F1 发布；操作与部署说明；冻结测评入口。
验收：受控范围可行为验证。；不支持/未验证能力明示。；正式进入 E1 前核心闭环真实可运行。
Jev：按需，不承担最终裁决。
完成证据：尚无。

## E1：集中测评与定向改进

### [ ] E1-01 冻结评测协议与数据边界

状态：planned。
目标：为详细测评建立可解释参考。
依赖：F1-12。负责角色：独立评测负责人。

具体工作：
1. 冻结代码/题目/模型/策略。
2. 登记开发、回归、独立与合成数据来源家族。
3. 确定任务、对照、预算与报告维度。

交付：评测协议；数据 manifest；版本冻结记录。
验收：已开发案例不被称为盲测。；来源关联可检查。；不同对照共享目标和可用原始信息。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] E1-02 原件参考与科学裁决集

状态：planned。
目标：建立超出模型共识的评测依据。
依赖：E1-01。负责角色：独立科学评审。

具体工作：
1. 以原件/复算/适当专家审阅形成参考。
2. 保留对象范围、来源关联和专家分歧。
3. 构造关键未知/反例/错误实现与负知识任务。

交付：参考裁决集；争议记录；任务样例。
验收：不以另一模型输出单独当金标。；参与解释形成的数据不冒充独立。；参考本身可被复核修订。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] E1-03 测评运行与多维指标

状态：planned。
目标：实际测量科研产物与系统行为。
依赖：E1-02。负责角色：集成/实现负责人。

具体工作：
1. 运行资产/对象/推断/分支/纠偏/交接任务。
2. 记录承重误采信、遗漏、误伤和实际成本。
3. 按来源家族和任务类型报告，不压单分数。

交付：测评原始回执；多维指标；误差样例。
验收：全部结果可追溯到运行。；吞吐和报告长度不替代科学质量。；不利结果完整保留。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] E1-04 Harness、Jev 与独立审查消融

状态：planned。
目标：确定增益究竟来自哪部分。
依赖：E1-03。负责角色：独立评测负责人。

具体工作：
1. 比较普通流程、确定性 Harness、加 Jev、加事件审查四组。
2. 在等预算与同等产物资格两种条件下分析。
3. 控制数据/人工输入差异并保留重复运行变化。

交付：消融结果；增益/代价归因；保留/简化建议。
验收：没有把完整系统对照当作 Jev 单独增益。；同源证据不重复统计。；无收益组件可以缩减。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] E1-05 Jev 分任务校准与权限调整

状态：planned。
目标：根据真实后果决定自动化范围。
依赖：E1-03。负责角色：Jev/评测负责人。

具体工作：
1. 检查题目族、候选覆盖和中文边界。
2. 用校准数据决定阈值，在独立数据报告。
3. 调整自动化权限并回归高风险错误。

交付：题目族校准；阈值/策略版本；自动化权限矩阵。
验收：不同 primitive 不共用无依据阈值。；高置信错误也进入分析。；上游漏候选得到修复，不只重排。
Jev：被评测对象，不能自证。
完成证据：尚无。

### [ ] E1-06 系统鲁棒性与故障测评

状态：planned。
目标：测量长周期、并发与权限边界。
依赖：E1-03。负责角色：集成/实现负责人。

具体工作：
1. 在隔离环境进行中断、重复提交、源变化和服务故障。
2. 实际尝试越界与历史指令注入。
3. 检查误阻塞、误放行和恢复后状态一致性。

交付：故障测评回执；边界漏洞清单；恢复结果。
验收：不对真实科研源做破坏测试。；代码审查不冒充行为试验。；未验证范围明确。
Jev：按需，不承担最终裁决。
完成证据：尚无。

### [ ] E1-07 定向修复、复测与下一版地图

状态：planned。
目标：把测评结果变成真实产品改进。
依赖：E1-04, E1-05, E1-06。负责角色：集成/实现负责人。

具体工作：
1. 定位最先失败层和仍有效部分。
2. 修复候选/表示/解析/语义/事务/权限等对应原因。
3. 使用回归与未参与修复的数据复测，更新能力与边界。

交付：修复版本；复测报告；下一版地图。
验收：未用免责声明代替修复。；无证据增益不维持预定路线。；用户可依产物选择部署范围。
Jev：按需，不承担最终裁决。
完成证据：尚无。
