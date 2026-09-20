# 当前状态

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

复现：`rtk proxy uv run rh reconstruct resume`；第二领域加 `--project config/diffusion.json`；操作、查证与恢复见 [README](README.md)。原件与原作业未修改，未提交新DFT/MD/训练/集群任务，未变更全局配置。
