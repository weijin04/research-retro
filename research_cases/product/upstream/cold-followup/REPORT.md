# 冷接手增量：Stage1盘点已完成

fresh reader完成了r275建议的只读盘点。核对其引用的冻结包原文并逐字节匹配注册源：v13_s_only_validation/RESULTS.md完整2061 bytes，SHA256 7933b0eab1b7117838c8e191c2cb8c337856e3c5410680ad67277b1d9d3e94c9；analyze.py仅前7000/8224 bytes，SHA256 8ed41349f39b911df137d1145a704a9beb8c437c3ad6f9e5ace462bd70fcdd48。未读取其余代码、COLVAR或long目录。

原报告记录20条完成、8条邻窗overlap均通过（Kr最小0.339、Xe最小0.322，门0.10），但Xe五窗仅一窗ESS达到200，另外四窗152.0–184.5；4/20块稳态失败，一条最大偏离0.544 Å也违反当时0.5 Å门。分析代码明确validated要求integration/coordinate/overlap/ESS/stationarity/R-hat全部成立。20=2×5×2，8=2×(5−1)，ESS不足15.5–48，43帧×2.5fs=107.5fs；这些摘要算术一致，不是原始时序或ESS重新计算。正向overlap不覆盖其他失败。

报告指名一次两新seed、40ps的v13_s_only_validation_long修复，保留ESS、稳态等门，最大伞偏离改为诊断；修复失败后不允许继续加长或改门。本次没有该具名修复结果的可核证据，不能判它已做或未做。分析入口指向10Å path-CV资产，不能把其模型身份与8Å smoke自动合并。

这完成了旧B“先盘点”的任务，并补充后续证据；不是对旧B方法或窄结论的反证。新增一个原报告观察，更新gap:stage1和route:stage1_readiness：从“是否存在邻窗测试”推进为“已有严格失败及具名repair，下一接手只恢复repair收据/完整时序和身份关系”。本轮不执行该下一任务。其他节点与科学结论保持原版本；r275固定包保持只读；无Jev调用、无模拟。
