# Research Retro 架构落地材料

本目录是研究设计与参考验收材料，不是 Research Retro 2.0 的发布包。

`IMPLEMENTATION_CONTRACT.md` 给出模块、数据、算法、权限、CLI、完成条件和迁移门。

`contracts.schema.json` 与 `contract_examples.json` 给出五类核心交换记录的草案。示例中收据哈希为占位符，不构成执行证据。结构检验结果在 `schema_validation_results.json`。

`benchmark.py` 在一个全新的输出目录生成合成科研仓库与参考求解结果。要求 Python 3.11+、git 和 POSIX shell。它只运行自身写出的示例代码，不是用于执行任意输入仓库的工具。

```sh
python benchmark.py --output /path/to/a/new/fixture-directory
```

已有执行输出在 `generated/reference_results.json`，其中四种干预均与独立的离散闭式公式比较，并单独报告时间离散误差。14 个参考检查通过。这个结果不代表恢复引擎、LLM 或安全隔离通过验收。

`generated/case/` 是给受测系统的项目，含合成 Git 分支、原始输出、收据、故障和误导叙事。只将该子目录交给受测系统。

`generated/evaluator_only/` 是评测者专用的真值与必需发现；`generated/reference_probes/` 是参考干预结果。盲测时都不能暴露给受测系统。`generated/erased_variant/` 中两个可见目录完全相同，但对应的隐藏历史不同，正确答案应保留不可识别性。

所有设计与测试仅发生在本轮独立工作目录，没有修改原 Research Retro 仓库。当前发行代码以 0c0a6a258eb069aa829c486233993eaf87692264 为检视基线；此次采用源码阅读，没有运行其完整测试套件。
