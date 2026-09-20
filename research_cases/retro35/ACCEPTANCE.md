# Research Retro 3.5：修复与真实 r655 验收

三项修改已进入模块公共路径，未硬编码项目、节点 ID 或分支名称：

- `workflow.projection` 检查实际字段判别。正文修订、观察量前提和当前行动触发检查；未检查、过时、不确定或接口失败均保持待审，并阻断支持和必要依赖。版本与哈希只绑定回执。
- `start --jev` / `workflow semantic-review` 保存本工作区的明确授权。后续修订、刷新、发布和续接自动检查发生变化的输入。Jev 只负责前提失效与行动清理；请求、响应、实际模型、usage、耗时和错误写入本地回执及权威状态库，不重试、不伪造结果。
- `retro discover` 与 `workflow discover` 均返回独立 `unlinked_queue`。主查询不筛掉此队列；每个上下文自动带入六个候选和可读原件的有界预览。已出现候选轮换，二进制或读取失败的材料仍显式保留。`start` 返回队列并写入 `DISCOVERY.json`。

CLI、JSON 工具定义、随包技能、Agent 文档和版本均已同步。另修正配置加载仅接受 policy 1 的限制，使已有的追加式治理接口能记录验收副本的新输出目录；原契约与科学历史保留。

## 实案结果

完整 r655 的 87 个科学节点复制到外部工作区：
`/home/sun07ao/retro-workspaces/grephene-retro35-acceptance`。
原始 Retro 状态库和本次使用的 Hessian/条件原件哈希在验收前后相同。

| 状态 | claim:pair-scope needs_review | route:thermal needs_review |
|---|---|---|
| 原 r655 冻结页面 | false | false |
| 3.5 投影，尚无字段回执 | true | true |
| 真实 Jev 判别后 | true | true |
| 仅修平理由并自动检查 | false | true |
| 修平行动、同步显式后继并自动检查 | false | false |

Jev 为 **jev-1.13.0**，本次验收工作共 **44 次请求，42 次成功，2 次 HTTP 400**。
修改后的理由一致性概率为 0.90，行动一致性概率为 0.89。

不能把这次结果表述为 Jev 明确识别了两处“过时”：原理由返回
`consistent=0.79`，原行动返回 `consistent=0.62`。两者低于调用前代码已设定的
0.8 放行阈值，因而仍被标为不确定、维持待审。修订过程中阈值和问题没有按这两个结果调参。
最初要求原始 Choice 必须为 `stale` 的验收断言失败，后改为核对真实字段门禁是否阻断；失败断言与原始回答均保留。这是门禁效果的证据，不能作为 Jev 分类准确率的证明。

无匹配主查询时，独立队列仍返回候选，候选总数为 107816。
上下文实际自动带入此前零引用的 `.engrad` / `.hess`，例如
`research_review_20260915/raw_xj/cage_branch/S_a_singlet/S2_neutral_doublet/orca.engrad`，
随后轮换到其它计算目录。没有预设待找分支；这证明候选主动曝光，不证明候选的科学重要性或完整覆盖。

发布投影与当前状态一致。另有 **16 个历史节点继续待审**，项目保持 draft；本次没有把其它未解决判断改成绿灯。

## 执行纪律与日志

所有三处核心代码先完成，再集中执行检查。但**没有做到一次无中断验收通过**：
准备阶段遇到副本路径契约冲突；真实接入遇到过大的数值/来源定位载荷，随后收窄为字段和观察摘要；原始 Choice 标签断言也失败。均在同一外部副本上继续，未删除失败记录，未重开新的独立案例来掩盖问题。

- 完整回归首次 124 项通过；后续配置/输入收窄/不确定原因标签修改的受影响检查 10 项通过。
- 1.0 隔离安装与兼容生命周期 4+37 项、2.0 48 项通过；最终 3.5 wheel 的宿主工作流隔离安装与生命周期 4+20 项通过。
- 实案最终记录 19 项条件通过；不是冷评估、不是新 Hessian 计算，也不宣称未见项目泛化。

开发回执（保留在本仓库忽略目录）：

- `var/retro35/acceptance/acceptance.jsonl`：追加式全过程，包括失败断言。
- `var/retro35/acceptance/result.json`：最终状态、真实调用数、待审节点和判别边界。
- `var/retro35/acceptance/command-*.json`：公共入口的完整请求与响应。
- `var/retro35/real-r655*.log`：准备、接入、修订与续跑日志。
- `var/retro35/unit-tests.log`、`affected-checks-delivery.log`、`installed-*-final/`、`installed-retro3-delivery/`：软件验证。
- `var/retro35/changes.diff`：相对本次开始时工作区的增量 diff，保留已有 3.0 未提交改动。

真实 API 回执同时保存在外部工作区 `jev/` 和状态库，随状态备份保留；没有记录凭据。
