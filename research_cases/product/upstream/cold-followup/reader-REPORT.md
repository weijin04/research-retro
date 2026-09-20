# 独立接手报告

我会继续一个具体任务：恢复具名 `v13_s_only_validation_long/` 的冻结协议、结果与原始时序，先核对材料/结构/path-CV/力场身份，再复核其 Xe 有效样本数和块稳态是否过关。包内阶段盘点已完成；不能直接重新启动一个基础 overlap pilot，也不能宣布 PMF 可做。

## 当前最可信认识

Kr/Xe 方向须按材料状态、温度与测量口径限定。SPINE 所述 R4 失败与 CALF 局部代理负结果不能证明全部开门机制失败，也没有证明有限势垒机制成功。169 与 35 kJ/mol 的跨估计量比较已撤回；不应重做这种阈值打分。v33 对所测热快照硬净空头提供负知识，不能升级为所有含客体动态路径的 no-go。

## 实际核查改变了下一任务的粒度

初始理解已在 `initial_understanding.md` 原样保存：先盘点 MIP Stage1 准备度，检查 smoke 基础。但 SOURCE_INDEX 指向的原件不止 Stage0：

- `v13_finite_t_smoke/result.json` 完整捕获。四条记录的 4000×0.25 fs = 1 ps，与400帧×2.5 fs相符；温度偏差重计1.66–4.22%，存储最大偏移、管壁和主体位移均在 smoke 报告阈内。这里仅重算摘要，不是重新读取轨迹；400帧绝非400个独立样本。
- `v13_s_only_validation/RESULTS.md` 完整原报告写明20条运行已完成、8条邻窗 overlap 全过，Kr最小0.339、Xe最小0.322，高于0.10；但Xe五窗仅一窗ESS≥200，另外四窗少15.5–48个有效样本；4/20块稳态失败。另有一条伞偏离0.544 Å超过旧0.5 Å门。这是严格协议失败，不是没有测试过邻窗。
- 对照该目录 `analyze.py` 前7000/8224字节，确认它确实要求2气体×5窗×2 seed，共20 runs；validated 是 integration、coordinate、overlap、ESS、stationarity、R-hat 的合取。高overlap不能覆盖ESS和稳态失败。报告的43帧尾事件×2.5fs=107.5fs亦一致。未捕获完整分析代码与COLVAR，故未重算overlap/ESS。
- 原报告已冻结一次两新seed、40ps的 `v13_s_only_validation_long/` repair，仍保留ESS、稳态等门，最大偏离改为诊断。SOURCE_INDEX 无该目录的捕获记录；只可说本包不能核验 repair，不可说全项目从未执行。
- `v13_reus_cross_initialization/PLAN.md` 还记录5ps instrumented REUS后的16轨迹因果采样诊断设计。这进一步提醒已有后续路径；它是计划证据，不是16条完成或有效PMF证据。

## 可复用与不该重复

可复用：Stage0工程可行性、各局部负结果的原有限定、s-only 验证失败及其正向坐标/邻窗证据、既有一次修复协议的具名入口。后续 validation 指向10Å path-CV资产，不能把它与8Å smoke视作完全相同模型；恢复原结构哈希和路径/边界契约是合并谱系前的必要输入。

不重复：从零搭 PLUMED 基建、把邻窗overlap视作完全未知而重跑初级pilot、靠R4重调阈值、延长普通无客体快照来挽救已失败的硬净空头、再次用169对35比较、在单个温度反转个案上任意发明温度函数。原 s-only 协议明确限制一次repair，不能未查其结果就追加采样或放宽门槛。

下一步缺少的是具名 long repair 的原始收据/时序、完整分析依赖、身份与边界映射。本次没有访问包外材料、联网或提交模拟。若最终证实repair尚未执行，按2气体×5窗×2新seed×40ps估算生产量800ps；若沿用0.25fs则320万步，另计平衡与边界敏感性。此为条件算术，不是已冻结完整方案，也无运行速度可换算墙钟费用；不据此提交任务。

## 留存

`check.py` 与 `check_result.json` 是摘要算术及索引缺项检查；`sources_used.json` 保存原文件标识、实际包内读取路径、捕获范围和SHA256。`retro inspect` 对本包报告完整性通过，r275、167 files、249 records；它只验证完整性，不提供数字签名或科学结论保证。
