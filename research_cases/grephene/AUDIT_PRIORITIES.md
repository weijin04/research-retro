# 发布前看“采用了哪些结论”，不要把311项当作311个必做计算

311条 audit_candidate 已全部路由到12个可重叠主题组，并把11条记录中已经解决的共同关系去重为4个审计对象。主题分组只服务调度，不能证明物理等价，也不能把12组称为12个关闭的任务。原始队列未删除、未自动关闭。结构化版本：[audit_queue_triage_v2.json](audit_queue_triage_v2.json)。

当前已由原件解决的范围是：O2/O3/O4模型身份与比较边界、局部梯度及端点能量参考、F5 m2缺少完成驻点认证，以及新增T13b的七帧短接触迁移。更广的电子态字符、生产性路径、机制排序、真实退火通道并未随之解决。

新增T13b核查从11份真实文件完成：实际输出能量表与dat逐项相同，每份缓存几何对应本次扫描输出的最后坐标块，最大坐标尾差小于10⁻⁵ Å。第1点N72近邻为C31/C32，第6点变为C32/C33，距离1.455153/1.455170 Å；1.6、1.8、2.0 Å阈值均得到同样这两个邻居。N72始终没有失去全部短碳接触。第5点相对首个约束采样点的最大电子能为16.048818 kcal/mol，第6点回落到0.255378。由此可纠正“把单根C–N拉长解释为表面完全脱附”“把采样峰当作200 °C退火自由能垒”；不能由此排除另一条退火路径。见[t13b_audit_case.json](t13b_audit_case.json)。

后续只优先三条关系，按当前报告实际采用的结论触发：

| 优先关系 | 何时阻止当前报告发布 | 先查哪些现存材料 |
|---|---|---|
| **LB-ENTRY-COMPETITION：TMS/PFPA EA(Q)与入口淘汰** | 报告采用“端点垂直EA为负，所以DEA/有机入口已排除”，或据此把Fe路线排在TMS之上 | `tms_arm/iso/{TMS,PFPA}/step5_sp`及`raw_live_xj/entry_remaining/tms_arm/iso`；同几何中性/阴离子逐点配对，保留两条几何血统和基组/自旋条件 |
| **LB-ET-TARGET：H_ab/λ实际估计量** | 报告采用跨4数量级门控、Marcus寿命/分支，或把net−1定域态当中性光注入 | `h6a_gate_hab_scan/resting/hab_resting_v2.out`与其余几何输出；然后现有`r4t_lambda_fourpoint`归档六份输出，重建电荷—几何—能量循环 |
| **LB-PATH-NEGATIVES：路径观测与全局关闭** | 报告采用“所有纯净基面基态路径关闭”“顶点低于光子就证明生产性”“固定root就是连续生产性激发路径” | 现有C54 `fe_arm`候选与一条`cage_branch`再复合竞争支；对照最新本地/归档原件、电子态、约束、终点和实际失败环节 |

这些优先项都有可先做的本地原件审计。它们不是直接提交新科研计算的理由，也不是要求最终把机制研究闭合。报告若明确不采用对应物理主张，保留为有限观察/历史判定/未知分支，并撤销相关下游支持，则无需等到该机制问题解决。**不能一边采用强结论，一边仅用“待审”标签满足R2。**

可以立即限域降级保留：旧阴离子数值跨借中性模型；旧−9.2和1.16垂直隙；严格单调说法；T13b退火垒；未由原件再确认的旧全局停止、用户排除空位、方法退休、仅输入和失败作业。最后一类只恢复历史工作处置，不能登记成新的科学反证。源码/几何/数值仍在，可按需要重新审计，不自动重开计算。

实验前体、膜和产物身份属于另一个明确边界：若主报告要采用具体身份或退火化学指认，必须回到授权的样品/谱图原件。原件未提供就保持unknown；计算输入只能证明模型身份。

复现使用版本化脚本，输出必须是尚不存在的框架内路径：

```bash
rtk proxy python3 research_cases/grephene/reconstruct_project.py --output var/audit_work/grephene/reconstruction_next.json
rtk proxy python3 research_cases/grephene/audit_t13b.py --output var/audit_work/grephene/t13b_next.json
rtk proxy python3 research_cases/grephene/triage_audits.py --output var/audit_work/grephene/triage_next.json
```

第一份重建结果已与既有1,014条记录逐条比较；变化只限运行元数据/生成器路径。T13b与triage有实际执行结果，未修改科研来源、执行原脚本、外发或新提交任务。发布阻断集合及采用条件在JSON的`outstanding_load_bearing`；已解部分和可降级部分分别保留，不能将unknown计为科学审计通过。
