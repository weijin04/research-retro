# 前置关系链：12项局部独立核查

抽样固定：support/scope/genealogy/impact/action各按SHA256(seed NUL id)取2项，再取剩余attention最低2项；seed与队列hash、路径见local-review-sample.json。后两项是低attention/低信息自比较，**不是低confidence样本**。不改变已冻结抽样。

结论：Jev可给出有用的局部范围/依赖提示，但存在独立性误判、作者报告升格直接支持、动作类型错配。不能把队列confidence当真值或自动淘汰动作。12项为分层有意抽样，不给总体准确率。

| ID | 类别 / Jev | 独立核查 |
|---|---|---|
| dsh-c-38 | support / compatible | Only the same script header is supplied as evidence and target. Compatible appropriately avoids certifying actual computation. Full script does load existing inputs, but the local excerpt does not execute or validate C3/A1. next_check jumps to consistency with R4, a different rule/estimand; must match object and conditions before comparing. |
| dsh-c-05 | support / direct | Jev direct elevates one audit report repeating its conclusion into direct support under a prompt that explicitly disallows that. Both excerpts come from the same author text, not independent raw ASE/Zeo outputs. Rigid hard-sphere radii only constrain that observable; full report admits center approximation and missing SI. No global E1 exclusion or proof of real inability to enter. |
| dsh-a-0015 | scope / compatible | Code explicitly names the record override, so record-identity compatibility is supported. Must retain conjunction network_sign==Kr; title R4/v144 merges distinct experiments. Scope relation does not establish that the branch actually fired or validate performance. |
| dsh-a-0030 | scope / compatible | The two snippets repeat the same declared limitations; matching stated conditions is correct. No caller/calibration evidence shows actual diffusivity inputs match conditions. This is agreement with a code contract, not a checked application. |
| dsh-c-16 | genealogy / independent | Summary explicitly describes rerunning scorer and matching identical output hashes. Same pipeline recomputation is not independent provenance for the scientific outcome. Exact target-version binding would still need original run receipt. Full preserved scorer uses min(radii); run1 CSV hash f980812b... matches reported prefix. Independent code review may diagnose a defect but does not make repeated prediction evidence independent. |
| dsh-a-0024 | genealogy / derived | Snippet explicitly loads v13 frontier result.json; full code confirms load and /36 conversion. A source relationship is supported. Target excerpt is analyze.py, not result bytes or manifest binding analyzer version to output. Do not infer full numerical correctness or independent evidence; next_check remains warranted. |
| dsh-c-24 | impact / unaffected | A four-record fixed-bed development comparison does not establish or refute the separate loop contract claim. Unaffected is defensible narrowly; insufficient would express missing bridge. Candidate title not basis-conditioned misreads a deliberately fixed-basis subset. Irreducible error floor is not proved by same material names with differing samples/conditions. Contract text is not supplied. |
| dsh-a-0004 | impact / affected | CoNi doc explicitly imports the same static offset method and its caveat; that can affect interpretation of its window probabilities. Transfer of caveat is real, not new independent measurement. Need raw/calibrated records and operator validity; no conclusion about actual opening follows. |
| dsh-c-34 | action / stale | Target is a historical result statement, not an action. Evidence is the preregistered diagnostic, while later completion appears only inside target source. Stale cannot safely label next_check obsolete. Full basin-diagnosis verdict is INCONCL, not a confirmed artifact explanation. Target context ends with UTF-8 replacement character after byte truncation. Verifying final JSON remains distinct from rerunning MD. |
| dsh-b-16 | action / useful | Question about whether a second independent anchor exists is useful given closure gap. v56 rank-1 object is next_observation_priority, a requested future observation, not acquired data. Title says would fill and next_check asks whether record adds material, risking promotion of a plan to evidence. Cannot establish anchor fulfillment from these snippets. |
| dsh-c-08 | scope / compatible | A 1 ns observation interval and unresolved slower timescale are compatible as declared sampling scope. Cannot literally prove a rare event cannot occur in 1 ns; cannot characterize its rate here. Same report supplies both sides; this does not verify all mechanisms or tell whether other runs exist. |
| dsh-a-0023 | scope / compatible | Code declares three pressure grid points and loops over them; local pressure compatibility is supported. Full function enforces point count/quality gates. Outside this calibration grid having no anchor in this generated set is not no experimental anchor anywhere. Same-source correspondence is low-information, and output eligibility counts remain unread. |

## 关键边界

- dsh-c-16：同一scorer重跑、同一CSV哈希的复述被判independent，错误。作者的缺陷诊断可以新颖，但不能让重复运行的数据成为独立证据。
- dsh-c-05：同一作者审计结论两段互证被判direct，超过提供上下文支持。
- dsh-c-34：以历史结果陈述充当action目标，stale不能直接用于停止next_check；原最终诊断是INCONCL。上下文截断末尾含替换字符�，需保留。
- dsh-b-16：v56 rank-1是待取得的观测计划，不是已经取得的第二个独立锚。提出核查有用，不表示补缺已经成立。
- 范围compatible通常只证明一段代码和它的复述同意同一约定，不证明调用时满足约定。dsh-a-0015还需保留network_sign条件；dsh-a-0023的三压力只限定该校准集。

## 实际读取与缺口

逐项读取真实Jev request.state及criteria，核对24个evidence/target来源上下文。所选捕获字节hash全匹配A；仅c34上下文因UTF8边界不是原文严格子串。针对争议定向读完整对应scorer、v119依赖代码、v35质量门，以及R3b最终basin JSON；run1 CSV hash吻合作者缩写。未执行科学代码，未重算物理结果。

第一次合并显示被工具截断；随后重读缺失的5项原始request，未把截断输出当审阅完成。partial标志表示捕获文件是否部分，不能被解释成Jev读到完整文件。

未审全90项，不能声称召回率/漏判率已测；物理原始几何、调用参数、实验条件同一性、校准输出、真实分支执行等仍未核。未接触运行中的upstream_reasoner或发送科学反馈。后续须按其实际读集/核查成果另评，不得用本报告提示它。

正式阶段只包含本次dsh候选→Jev局部关系→强宿主链；旧三臂与Luna预试均不支持本链收益。不推断提速或Jev额外收益。
