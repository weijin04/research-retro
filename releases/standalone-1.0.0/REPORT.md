# Standalone 1.0.0 — 实机验收报告

**结果：通过。冻结标签 `retro-v1.0.0`。**最终安装构件与下述执行日志的 wheel 哈希一致，见 [release.json](release.json)。本报告验证独立能力单元的工程行为与明确构造的科研状态，不声称统计性的科研能力、真实声学实验结论或通用 worker 隔离。

| 验收环节 | 实际执行与结果 |
|---|---|
| 1. 单向隔离 | 临时 Linux namespace 中只挂载只读系统运行文件和一次性测试目录；不挂载开发者 home、仓库或原科研项目；清空环境并隔离网络。用公开 pip wheel 离线安装到新 venv，随后把安装目录挂为只读。4 项安装断言通过。 |
| 2. 陌生项目冷启动 | 构造异构声学目录：CSV、深层 TSV、互相矛盾的摘要、未完成 Python、不得执行的原脚本、二进制和超预算长文本。经公开 CLI/Tool 完成扫描、原件读取、证据链重构、实际计数复算、深审、纠偏和完整交接；37 项断言通过。 |
| 空白接手 | 无历史上下文的 Agent 仅凭导出包独立重算计数，恢复当前支持、负知识及撤销历史，指出真实缺陷。修复后作针对性复验；首读和复验分别记录，见 [blank-agent-review.md](blank-agent-review.md)。 |
| 3. 宿主切换 | Codex 主控直接调用标准 CLI；同一操作通过 `retro call` 的标准 Function 请求调用，JSON 结果一致。隔离流程交替使用两种入口，并比较状态、历史、原件读取和边界错误。没有声称已启动 Claude Code、Pi 或 OpenCode 实例。 |
| R2 回归 | 76 项检查通过，包含原有 66 项回归和新增 10 项 standalone 检查。原件竞态、历史快照、负知识、事务/政策屏障、循环与同源证据限制保留；16 种 E1/A/E2/B 条件组合逐一验证逻辑真值。 |

最终验收共 **62 条命令、41 个显式行为断言**；完整 stdout/stderr、Tool 输入及返回码在 [execution.jsonl.gz](execution.jsonl.gz)。运行摘要见 [install-result.json](install-result.json)、[workflow-result.json](workflow-result.json)、[isolation.json](isolation.json)，回归日志见 [unit-tests.log](unit-tests.log)。

承重关系的实际结果：E1 是 A 批次 4/5，E2 是 B 批次 3/4；两者各有一个独立的记录反例，反驳“所有批次 100%”。对于 `H=(E1∧A)∨(E2∧B)`，撤销 A 后 E2∧B 仍支持 H；再撤销 B 后 H 与下游失效。计数观察及其反例没有被条件前提的撤销误伤。协议校准、标签盲法、跨批次独立性和总体表现均未因此获得验证。

另外实际执行：同尺寸并恢复 mtime 的内容改写仍由 SHA256 检出；原件删除撤销相关依据；旧字节仍可按版本读取；失去一个反例不会抹除另一反例，两个反例都失去资格后否定裁决的支持也失效。更换纠偏幂等键不能洗掉旧审计读集；相同键的精确重试保持幂等，不同载荷被拒绝。

交接包先冻结，再对**一次性合成原件**做破坏测试，因此冻结包与破坏测试后的活动 workspace 故意不同。包内保存的是冻结 r61 的知识状态。真实科研项目和历史 R2 数据库从未被本验收修改。隐藏合成原始目录后，独立包仍可检验和读取。

首次隔离安装尝试暴露了测试引导器对本机 Homebrew `uv` 动态加载器的依赖，已改成系统 Python venv + 公开 pip wheel。第一次失败的日志保存在 `var/standalone/acceptance-01/isolation.json`，发布目录的 `prior-attempts.json.gz` 也保留了失败和修复前轮次的记录。安装单元本身不依赖 uv、rtk、bwrap 或个人配置。

空白 Agent 首次指出的标签不一致、第二次撤销说明失真、未结构化的独立性断言均修正；之后补齐审计资格标签与缺口/负知识索引。当前包仍保留所有原始文本与历史修订，没有用摘要覆盖缺陷。

安装与使用：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install ./research_retro-1.0.0-py3-none-any.whl
.venv/bin/retro init /path/to/project
.venv/bin/retro -w /path/to/project/.retro scan
.venv/bin/retro agent
```

wheel 在本目录；无需克隆开发仓库。离线依赖包另存于 `var/standalone/research-retro-1.0.0-linux-cp314-offline.tar.gz`，含本次实际使用的依赖 wheels、清单和安装说明。离线包适用于此次测试的 Linux x86_64 / CPython 3.14；源码声明 Python >=3.11/POSIX，未实测的 OS/解释器组合不作为已验收环境。依赖版本和哈希由发布清单冻结。

开发复现：准备包含发行 wheel、公开依赖和 pip 的 wheelhouse，然后运行 `uv run python checks/standalone_acceptance.py --wheelhouse WHEELHOUSE --output NEW_RECEIPTS`。原始脚本构造完整合成目录并在隔离环境重复上述步骤；它不读取私人项目。`bwrap` 仅用于开发验收。

执行边界：`audit check` 是主控明确调用的本地后处理，执行宿主审阅并授权的 workspace 脚本；它不是 OS 沙箱。科学充分性仍由带来源、范围和实际分析的审查承担。发布没有增加外部模型接口，没有推进 F1/E1，也没有宣称自动完成任意新领域的科学判断。
