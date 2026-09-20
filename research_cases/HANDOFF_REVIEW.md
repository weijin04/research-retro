# 首次接手行为验收

结论：旧交接包可支持有条件的科学接手，但入口摘要与 CLI 输出体量存在实际可用性问题；不代表完整 R2、盲科学评测或物理真值验收。

只从 `var/receipts/grephene_report.json` 指向的 handoff/report/HTML 开始，随后读取 `state.json`、来源快照与实际 `rh query/read/state`；未读取主线程 CURRENT_STATE 或实现源码，未改科学原件、提交计算或外发。所读版本：state 1189、reader-2、1164 记录、56 来源快照。完整命令结果与路径/版本见 [fresh_handoff.json](../var/receipts/fresh_handoff.json)。

1. 目标可由 `query goal` 恢复：解释光相关氮化学及 graphene/Si 对照，不预设前体、中间体和终态成键；重建实际工作及其对象条件、解释与负知识。已完成的是限定 LMCT 后处理及对象可比性/TS 资格检查，历史表仍是 imported_assertion；实验原件、私有历史和完整机制未覆盖。
2. Fe–Nα 对称伸长中，GS 总导数 +0.647191；ES roots1–3 总导数 −3.919086/−3.947411/−3.955604；ES−GS 差导数 −4.566277/−4.594601/−4.602795 eV/Å。若 u 为 Fe→N 单位向量，两端分别移动 ±u dr/2，则 dE/dr=(gN−gFe)·u/2；原始 Wilson B·g 是两倍。总导数与差导数还相差 GS 项，不能把 −9.13 与 −3.92 仅解释成二倍归一化。依据为 gph-c-gradient-normalized r3、fc_gradient r1 和包内执行回执；对象仅是18原子、中性六重态、无 graphene 的孤立片段。
3. p7 同几何垂直隙 0.261261207 eV；相对 FC 基态能高 1.156323072 eV，其中基态形变能 0.895061865 eV。3.20 Å 标签来自扫描表顺序，独立逐点几何匹配仍未完成。
4. 严格单调下降被反驳：p5→6 上升 0.032645827 eV，p6→7 上升 0.002381642 eV。`adjudication_supported=true` 支持反驳，不能读成原命题成立。总体下降和局部伸长方向仍保留；没有机制排除、diabat 连续性或主导通量证明。
5. 能找到 qualified/active 的局部光伸长、unresolved/waiting_input 的均裂通量，以及 invalid_test/parked 的 F5 m2 完整 TS 认证。后者 step_a 位移条件失败而 step_b 有 −615.13 cm⁻¹ 虚频；可保留近似候选，但单虚频不能补足驻点资格。N4 历史 STOP 也保留中性光注入估计量的重开条件，当前仍是待核历史断言。
6. 用 seed=20260920 随机抽取两个原件 locator：GS output L2517–2519（artifact:2f05f6f60c553d4837cd6b5e r1）及 root3 output L4310–4312（artifact:a099ace54056221f8b4c475b r1）。实际源字节与包内快照相同、全文件 SHA256 与 locator 相符、CLI 逐行内容相同；详情和 hash 已保存。
7. SF-04 遗忘 TMS/PFPA EA_vert(Q) 资产可找回，但该条无当前审计；PFPA DLPNO 崩溃更不能默认成为机制反证。T13b 的 --indexes 查询同样只恢复 imported_assertion，不能以 normal termination 或索引能量直接证明物理有效性。
8. 实测当前 `rh state verify` 仍是1189，gradient r3 的记录 diff 为空。旧 state.json/read_set 和按 hash 固定的 sources 可恢复当时解释，`read --revision` 可恢复原件版本；当前没有制造 Store 漂移，完整数据库恢复未实际演示。

实际产品缺陷：报告开头的范围目录先列132个多为哈希的ID，目标需额外搜索；HTML约24.6百万字符、CLI简单 query/diff 因重复 locator 输出数万 token，必须自行 JSON 过滤；`state diff --before 1189` 缺ID却仅给 KeyError None，帮助未说明全局state版本与单条记录revision的区别。以上针对所读旧产物；不以主线程计划中的修复替代实际验收。

## 后续增量恢复实测

保留以上对旧1189/reader-2的原始验收。实际执行 `rh state events --after 1189` 后，观察到1190–1193四个新增事件；`state verify` 为1193、integrity ok。最新 `grephene_report.json` 成功定位1193/reader-3交接包。

逐记录比较结果：旧1164条记录全部存在，记录revision和完整JSON内容均未变；旧read_set完整保留，来源快照集合未变。新增仅两条 synthetic_analogue audit_suggestion 和两条 decision_record，均明确 advisory_candidate_only、不自动改变支持、不评判私有原件。当前CLI查询仍显示严格单调命题 r3 为refuted/unsupported，反驳资格为true。

因此这种无关的附加建议不应阻塞已经限定并审计的科学结论。恢复时先固定旧read_set，再检查1190–1193事件及新增记录，转入最新报告继续阅读即可；这次完成的是附加更新后的接手恢复，并非数据库灾难恢复或新物理真值评测。完整实际输出写入同一JSON回执的 followup。

新报告已实际读到顶部目标、范围和三条命题裁决；新query实测已是简短摘要并给出state get入口。此项改善仅计入本次后续检查，不改写旧入口体验。HTML整体体量与浏览器交互本次未重新测量；query的qualification字段对该claim显示unknown，需与明确的evidence_status分开阅读。

## Entry / T13b 扩展复验（state 2470）

本轮从 `var/projects/grephene/reports/latest.json` 进入 reader-3，短查新增两个案例及未知范围，没有重读全部历史材料或新增科学计算。紧凑回执：[fresh_handoff_r2_extension.json](../var/receipts/fresh_handoff_r2_extension.json)。

报告顶部可直接区分：旧TMS r2SCAN负EA仍是特定孤立分子同几何值；它不支持全局界面DEA排除。新同几何EA随几何、分子及基组变化，分离端点 +0.017609 eV 仅是电子能，不是自由能或势垒。T13b七帧保留短碳接触、p1→p6邻近碳改变；完全脱附被反驳，+16.048818 kcal/mol采样峰不认证退火活化自由能。界面通路、构型可达性、电子连续谱及真实实验恢复仍未知；未发现这些强主张在当前命题区被标作支持。目标、对象条件、待审计候选和未知入口清楚可见。

新增精确读取：T13b扫描输入 `artifact` 的固定revision、L1–46，CLI返回与入口sources快照逐行一致、SHA256一致，路径/ID/hash见回执。

实测缺陷：四个T13b默认query因provenance为字符串、brief按字典取值而崩溃；改用--full能恢复记录。失败输出保留。本轮只能认为固定报告可用于有条件接手，不能宣布R2通过；主线程另报快照读取/后hash同步问题正在修复，该未独立验证的修复不算本轮通过依据。待新版只复验受影响入口。

### 修复后限定复验（state 2579）

四个曾失败的T13b默认query均实测退出码0、精确ID一致，分别恢复完全脱附反驳、接触迁移支持、退火自由能未支持及恢复机制未知。最新固定报告仍保持entry/T13b限定范围与原有未知，并保留目标、待审队列及不宣称完整R2的边界。此次关闭这四项query的已观察可用性故障，旧失败证据保留在紧凑回执；没有重跑全部科学审计或独立验证导入并发快照修复，因此不据此宣布全局科学R2完成。
