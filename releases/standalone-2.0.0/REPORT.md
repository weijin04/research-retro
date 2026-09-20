# Research Retro 2.0.0 交付报告

2.0 已完成可安装的独立产品：冻结来源 → 确定性恢复 → 调查与判别探针 → 版本审定 → 限定收口 → 可移植交接。保留 1.0 生命周期；F1/E1 主控框架没有启动。核心无模型调用或联网。

## 交付与使用

- `research_retro-2.0.0-py3-none-any.whl`：安装包；[根 README](../../README.md) 给出启动入口。
- GitHub Release 的 `research-retro-2.0.0-linux-cp314-offline.tar.gz`：本次实测 Linux CPython 3.14 的离线 wheelhouse、安装说明及发布回执。
- `handoff.tar.gz`：完整合成科研交接包，包含原始字节、全部版本、调查记录、真实探针和科学支持图。
- [Agent 契约](../../AGENT.md)、[函数定义](../../tools.json)、[2.0 数据契约](../../contracts/retro2.schema.json)。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install research_retro-2.0.0-py3-none-any.whl
.venv/bin/retro init /path/to/project
.venv/bin/retro -w /path/to/project/.retro snapshot
.venv/bin/retro -w /path/to/project/.retro recover --snapshot latest
```

通用运行接口为 Python >=3.11/POSIX。实际安装验收环境为 Linux/Python 3.14.4；其他 Python 版本、原生 Windows 和其他 OS 没有在本次实测。Linux bwrap 仅用于显式请求的 contained 执行。普通读取与恢复不需要 bwrap。

## 实际验收

| 验收 | 结果 | 记录 |
|---|---|---|
| 内核与新增行为回归 | 107 项通过，约 4.2 s | unit-tests.log |
| 旧版安装与完整生命周期兼容 | 4 项安装 + 37 项行为通过 | compatibility-*.json |
| 新版安装后公开生命周期 | 48 项通过，约 20 s | acceptance.json、execution.jsonl.gz |
| 空白上下文首次冷交接 | 复算、原件定位、隔离重放通过；发现撤回传播缺口 | cold-agent-review.md/json |
| 修复后针对性复验 | 原失败门与公开重放通过 | cold-agent-recheck.md/json |

新版验收在没有开发者 home、源码 checkout 或网络的 namespace 中离线安装；运行期安装目录只读。只有 `case/` 提供给受测程序，参考求解器与 evaluator_only 没有提供。该脚本是确定性产品验收，不是 LLM 科学准确率盲测。

四个探针实际执行捕获的程序，与独立离散闭式比较：

| 修复 | 有效步数 | 有效时间 | B 态布居 |
|---|---:|---:|---:|
| 不修复 | 500 | 0.5 s | 0 |
| 仅修复步数上限 | 200000 | 200 s | 0 |
| 仅修复截断算子 | 500 | 0.5 s | 约 0.019753 |
| 两处都修复 | 200000 | 200 s | 0.7999636891353396 |

这区分了两个问题：去掉截断已能恢复非零可达性；完成指定时域还需要足够步数。200 s 连续模型结果为 0.7999636800561899，离散误差约 9.08e-9。结论只针对声明的合成两态模型。

首次空白 Agent 确实发现：H0/C1/C2 只作为历史陈述导出，公开 withdraw 返回空投影，却被标成成功。修复加入 live/portable 共用的 typed 科学支持投影、显式条件前提、审定见证、版本固定的关系以及历史检查点查询；缺图现在报错。

复验实际调用公开接口证实：历史条件前提成立时 H0/C1/C2 有正支持；撤该前提后 H0/C1 变 neither，C2 的独立路径保留。撤独立见证则 C1/C2 均失去支持，H0 保留。当前 H0 的负支持来自单独审定，区别于撤回。首次失败记录保留；复验是已揭示后的针对性复验，不是新的空白盲测。Agent 整体为 cooperative fresh-context，具体查询、复算和重放进程实际 contained。

## 明确边界

历史项目收据仍为 project_asserted；Git 和哈希不证明某提交实际执行。初版 Python 静态分析覆盖文档列出的子集，未知调用、环境和未求解循环留下明确边界。格式解析、捕获范围和 Git 候选上限都保留在包中。

四格复算支持有限模型结论，不能验证真实物理系统。没有声称真实项目盲测、随机化隐藏样本评分或任意科学仓库的自动全真恢复。结构化 review 记录责任和见证，不证明审阅文字的科学正确性。总体验收采用分项门，未给出虚假的通用 100 分证书。

旧工作区保持原位；迁移默认 dry-run，显式 apply 写入新工作区并保留历史陈述。原科研项目、历史作业和系统 Python 均未修改。
