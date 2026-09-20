# B：从局部几何核查转到既有具名路线的准备度

## 实际循环与结果

先保存A的11节点快照（before-view.json / before-status.json），再将已形成的两个局部问题绑定原件，通过公共triage judge实际提交。随后add-source登记B，仅列路径，在读feasibility-note正文前执行triage impact；7个候选全成功。之后读新原件及其明确引用，没有先按新材料预写结论。固定A包未写入。

followup的R3→R4 CALF谱系得到derived=0.96；校准代理与一般开门排除的scope问题得到insufficient=0.55、incompatible=0.40。它们没有改变A的判断：前者早由精确值/path/hash验证；后者提醒“未证明对应”不等于“证明不对应”。零代理阈值跨越仍不足以排除所有物理开门，但不声称已经证明代理数值错误。

影响候选的7个目标分别核查：question:sign扩展了恢复范围，原科学问题不被推翻；route:next实际改变优先级；route:r4stop、claim:boundednegative、gap:observable三项虽被Jev标affected，科学内容仍成立；claim:void、obs:reuse收到insufficient，也不据此削弱已验证结果。没有概率阈值裁决。最终读Spine发现obs:reuse仍把已完成genealogy列为待办，已仅修订其discovery next_check并重绑CALF条件性待办，科学statement未改；保留首次B导出。

## 新材料如何改变了行动

B是带追加更正的历史可行性笔记，不是新的运行结果或当前执行授权。其过程为：R5聚合版覆盖过小→尝试CoNi温度反转单例→用169与35比较判不可行→撤回跨管线比较→发现此前已有v105、v33和v13 smoke。不能只读早期段落，也不能把最后一段作为不经核查的正确答案。

实际追原件确认：

1. screen.py构造W_winding_c6_kJmol=w6并调用band(w6)，rules.py的35用于此量；scans.py中的barrier_kjmol则是host deformation + window interaction − cavity interaction。lammps_scan.py以0.5*sigma_A为净空目标、以opened_e-reference_e算形变能。故“v13 B=169>35于是不可通过”不是同一估计量的合法比较；本次没有重算169本身，也不把这次更正理解为v13通行势垒已获验证。
2. v33不是抽象的“有限温度层还没建”：已对MIP/Ca-SBMOF既有300K快照做过真正周期净空检测。独立重计path_survival rows得MIP主尾20帧中19成功、0 Kr pass、0 Xe pass，中位1.16260/最大1.28349 Å；失败是index10。即使该失败帧全算Kr通过，也只一事件且只有1/4块出现，不能恢复冻结规则要求的跨块重复支持。结论仅限所测快照净空头；没有证明稀有耦合通过不存在，也没有验证CALF的centroid校准。
3. v13 smoke的result.json确为MIP-203-Suc、Kr/Xe各两seed、298K目标、每条1ps观察，四条通过integration。原件明确finite_temperature_pmf_eligible=false、rate_eligible=false，只overlap_pilot_eligible=true。单瓶颈中心和8Å冻结外壳的稳定性不证明邻窗重叠、平衡、PMF、速率或选择性，更不自动迁移到CALF/CoNi。
4. v105已记录特定既有观测头的单调幅值仲裁反例和协议限制；它可阻止重复包装同样规则，不是任意有限温度理论的普遍no-go。

因此原route:next所提CALF离线校准仍是有效的解释定界任务，但不再是项目级默认第一优先。新增首要后续是盘点既有MIP path-CV Stage1准备度：是否已有邻窗数据、其身份/参数是否一致、若缺数据需要什么最小overlap/autocorrelation/block drift/tube excursion检查，以及边界敏感性与费用。此轮没有提出从零重建有限温度基础设施，也没有启动新窗口或任何模拟。

## 仍然拒绝的新材料宽断言

- B更正后仍称R3/R4/R3b三条“独立”证据，但已核查的CALF R4直接复用R3；该数数方式仍不成立。
- B称描述符“全是0K静态”，与R3动态输入和已存在finite-T smoke的实际对象不一致；需区分冻结静态代理、无偏主体快照、含客体偏置动态与平衡自由能。
- v33的MIP负结果不能替代CALF动态代理验证，不能由此关闭gap:observable。
- PMF Stage1是这里查到的具名候选，不是经穷尽证明的唯一存活路线；smoke的历史可行性也不是今天已通过全部compute-last-gate。后者八项内容本轮未读取，不虚报已过关。

## 版本处置

实际只修订原有question:sign的范围说明、route:next的优先级与动作，加上obs:reuse已完成局部反馈的动作状态，共3项；其余8节点维持原版本，包括R4两次实际结果、独立图见证、校准缺口和局部负结果。obs:reuse的科学statement亦原样保留，只有已完成动作记录更新。新增5项记录：R5错误比较的撤回、v33负知识、MIP smoke资产、Stage1数据缺口、准备度核查路线。变化是证据和机会成本驱动，不因Jev affected而批量改结论。after-view.json与node-diff.json记录实际执行结果。

## 阅读、调用和边界

本轮涉及15个科学文件路径，其中B正文1份、沿B引用新增A原件10份、重用A已读原件4份（followup绑定，无新全文阅读）。模型新增可计正文至少50159 bytes，path_survival首次全文输出截断使精确总量unknown；随后程序完整解析并复算。token unknown。read-trace.json记录每次whole/range、目的及程序/模型区分。导航与工具回执不算科学原件。

局部Jev实际9次，输入63179 tokens、输出406 tokens（工具回执）；followup2次1.283s、impact7次2.932s服务批次elapsed，不当作总墙钟或模型科研能力收益。原件核查和科学结论仍由host承担。

首遇失败/问题保留：followup queue初次未按batch过滤导致截断，之后按9个receipt精确筛选；path_survival整文件输出截断，之后程序处理完整rows。没有隐去失败帧，也没有把已读结果再次封成盲验证。B包仍是局部draft，无全项目完成或独立冷读验收宣称。
