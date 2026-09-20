# Research Retro 产品交付

现在可以独立安装 Research Retro，把它指向已有科研项目，再将生成的 START_HERE.md 交给自己的强 Agent。原项目无需迁移，保持只读；产品管理独立 workspace、科学状态、原件和交接。

## 日常使用

```sh
retro start /path/to/project --workspace /path/to/retro
```

使用已有 dsh v4.1flash 作为便宜 worker 时，只需在启动时配置一次：

```sh
retro start /path/to/project --workspace /path/to/retro --worker dsh --jev
retro -w /path/to/retro discover
```

`discover` 已把材料准备、候选生成、局部判断和简报输出连成一次操作；宿主不必手工串接 packet JSON。重复命令继续下一批，`--question` 发起新的科学调查，`--overview` 只查看概况。`discovery/latest.md` 展示值得调查的问题和关系，原件绑定、历史回执和未读材料仍可下查。未授权 Jev 时保留未判别候选，不妨碍调查。

宿主深入原件、复算和解释矛盾，再通过 `record` 保存实际理解；可以合并或拆分问题、对象和路线。`spine` 选择短阅读顺序，`workflow publish` 生成当前 Scientific Spine 和详细 Research Map，`export` 形成可离线接手的包。新证据经 `add-source` 和可选 `triage impact` 进入修订，当前认识与下一步随节点更新，历史和独立结果保留。

## 产品职责

- 程序维护来源、字节身份、版本、依赖、历史与可复算记录。
- 便宜 worker 提议问题、尝试和局部关系；dsh 只是可选适配器，其模型由宿主配置，产品也接受任意 JSON stdin/stdout worker 命令。
- Jev 在科学建构过程中提供批量局部信号；强 Agent 选择承重调查、形成和修改世界模型。没有概率真值门槛，没有自动科学结论。
- 用户先读短主线，深查时再进入路线、推理、原件与历史；后续 Agent 可以直接继续已形成的研究状态。

完整链已经实际使用，独立读者完成了后续任务，新材料也实际改变了研究入口并保留无关成果。最后一次使用反馈推动了日常发现入口整合，而非再增加验收规则。本轮到此交付，不继续扩展案例或 benchmark。

## 安装、证据与边界

[安装说明](INSTALL.md) 提供在线依赖安装和测试平台的离线 wheelhouse。最终源码与安装包一致，并通过关键回归及无开发者 home、源码 checkout、网络的安装/生命周期检查；详见 acceptance.json。版本沿用本轮 3.6.0，以 release.json 中的 wheel 哈希区分构建。

[阶段使用记录](../../research_cases/product/REPORT.md) 保留成功、首次遗漏、误判、缺件和修复。它们是开发证据，不能证明全部历史恢复、跨学科可靠性或总体成本优势。Jev 仍会误判，强模型仍须核查承重关系；headless worker 的实际成本不能只按模型名称判断。

实测平台为 Linux x86_64 / CPython 3.14.4。产品声明 Python >=3.11/POSIX；Claude Code、Codex、Astra、Pi、OpenCode 等可通过通用 shell/JSON 接口使用，未逐一启动验证所有宿主。无固定宿主 SDK、dsh 或 Jev 强制依赖。

未修改原科研项目、提交科研作业、创建 Git 标签或远程发布。保留本轮开始前已有工作区修改。example-handoff.tar.gz 是合成软件示例；真实研究工作区与历史回执由 receipt-index.json 定位。
