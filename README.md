# 科研复盘与科研 Harness

从混乱科研资产恢复实际对象、运行、历史说法与当前证据资格。原件只读；科学审计、权限、来源版本与数据事务分开处理。

当前版本和实际回执见 [CURRENT_STATE.md](CURRENT_STATE.md)。R2（0.2.0）的发布依据见 [R2 验收](research_cases/R2_ACCEPTANCE.md)；原始实施包保留在根目录。发布范围是已验证的本机复盘产品及明确范围内的科学重建。

## 本机使用

```sh
rtk proxy uv sync
rtk proxy uv run rh doctor
rtk proxy uv run rh reconstruct resume
rtk proxy uv run rh --project config/diffusion.json reconstruct resume
```

grephene 入口复用旧 census 和 evidence map；外部盘及远端旧路径只保留引用。全目录操作是有范围的元数据增量发现。`pending_read`、不支持格式、缺失与排除项仍在覆盖账本，不等于不存在结果。大型文件默认不全文读取。

输出目录：`var/projects/grephene/`、`var/projects/diffusion/`。打开各自 `reports/latest.json` 指向目录的 `index.html`，即可搜索对象/条件、审计、分支、负知识与待审项。该 HTML 可直接本地打开；完整状态、原件字节和交接包在同一版本目录。

## 查证与纠偏

```sh
rtk proxy uv run rh query 'gradient' --kind claim
rtk proxy uv run rh state get gph-c-gradient-normalized
rtk proxy uv run rh query 'iso_complex_lmct' --indexes --limit 5
rtk proxy uv run rh state events --after 1189
rtk proxy uv run rh state diff gph-c-gradient-normalized --before 1
rtk proxy uv run rh context --budget 16000
rtk proxy uv run rh context --budget 16000 --part 1
```

`query` 默认返回限长目录；`--full` 或 `state get ID` 读取完整字段。全局状态版本是事件序号；对象 `revision` 是该对象自己的版本，二者不同。`rh read ARTIFACT_ID --revision N --start A --end B` 返回指定快照行；`--live` 检查当前原件，变化时保留历史副本并要求重评。

支持集合使用外层 OR、内层 AND。`refuted` 命题不能支持下游肯定推断；`adjudication_supported` 独立表示否定裁决仍有依据。来源变化、相关读集或政策变化均须重评。旧报告、重复字节与多人审阅不会变成多份独立物理证据。

通用科学工作台支持新的问题与表示，不限于内置开发案例：

```sh
rtk proxy uv run rh workbench propose path/to/audit_case.json
rtk proxy uv run rh workbench packet AUDIT_ID
rtk proxy uv run rh workbench submit AUDIT_ID --result path/to/result.json
rtk proxy uv run rh state validate path/to/scientific_patch.json
rtk proxy uv run rh state commit path/to/scientific_patch.json
```

研究者完成实际推导、代码检查或已授权的复算后再提交结果。通用 AuditCase 与 ScientificPatch 的交换结构见 [契约](07_CONTRACTS.md) 和 [schema](contracts/contract.schema.json)，格式检查不代表科学充分性。数值检查需要实际输入、输出和验证回执；纯推导可以提交完整构造，不能只填方法名称。

## 已实际完成的科学审计

- [grephene](research_cases/grephene/REPORT.md)：明确坐标归一化、总/差梯度、垂直能隙和 FC 参考；两个相邻上升点反驳严格单调性。物理推断按不同原件组独立传播。
- [diffusion](research_cases/diffusion/REPORT.md)：逐帧重算 20001 帧速度；三个自由度的涨落推导与启动段分块/相关性检查。未证明平衡或扩散收敛。
- [广域复盘](research_cases/grephene/PROJECT_MAP.md)：保留历史对象、科学族、分支、孤立资产和待审队列；未核验旧判断不升级为当前事实。
- [EA(Q) 与入口](research_cases/grephene/entry_audit_REPORT.md)：369 个原件的同几何配对、几何/基组条件和已完成 DLPNO 端点；保留旧负 EA 数值，撤销跨目标的全局排除资格。
- [T13b](research_cases/grephene/t13b_audit_normalized.json)：七帧实际几何恢复接触迁移，区分采样电子能峰、完全脱附与退火自由能垒。

它们是开发材料，不是盲测。源码、结构化案例和复算脚本在 `research_cases/`；原始来源只读，独立副本与运行回执在忽略的 `var/`。

## Jev 与权限

`rtk proxy uv run rh jev-advice` 使用统一适配器及现有凭证。实际模型、usage、题目、原始返回、错误和缓存均记录。首期只发送合成类比；真实科学原件默认外发拒绝。建议不能自动改变科学支持、对象身份或授权。合成输入的真实 API 调用不代表私密科研引用已被模型审过。

R2 的 CLI/建设 agent 是受用户授权的本机建设入口。它的权限不代表运行 worker 的硬隔离。F1 的隔离与执行回执通过后才单独声明控制能力。原科研作业、原件和全局配置均不在修改范围。

## 恢复与检查

```sh
rtk proxy uv run rh state verify
rtk proxy uv run rh backup var/backups/grephene-001
rtk proxy uv run rh --store var/backups/grephene-001 state verify
rtk proxy uv run python checks/verify_r2_recovery.py
rtk proxy uv run python -m unittest discover -s tests -v
```

备份包括一致 SQLite 副本、全部被引用的历史 blob 和 SHA256 清单。数据库使用实际 Python 链接的 SQLite，当前采用 DELETE journal 与 FULL 同步，不要求升级全机 SQLite。报告渲染失败会保留旧视图过期标记，不能将它当成当前状态。
