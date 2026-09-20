# Product acceptance

Research Retro 2.0 adds the installed workflow in `retro2_acceptance.py`:

```sh
uv run python -m unittest discover -s tests -v
uv build --wheel
uv run python checks/standalone_acceptance.py --wheelhouse PATH --output NEW_PATH
uv run python checks/retro2_acceptance.py --wheelhouse PATH --output NEW_PATH
```

The first acceptance preserves the 1.0 lifecycle. The second runs the typed 2.0
recovery/investigation/probe/closure/handoff lifecycle in an offline installed
namespace, including all four actual interventions, an independent discrete formula,
scoped signed support, historical withdrawal and isolated replay without original
paths. The inner process receives only the synthetic case, never evaluator-only
reference files. This deterministic product check is not a blinded LLM evaluation.

Final receipts, the original cold-context review and the separate post-reveal repair
recheck are in `releases/standalone-2.0.0/`. Release reports retain both failed and
successful evidence. New product schemas are packaged in `resources/retro2.schema.json`;
`render_tools.py` regenerates all function definitions.

# Earlier checks

Current standalone acceptance:

```sh
uv run python -m unittest discover -s tests -v
uv build --wheel
uv run python checks/standalone_acceptance.py --wheelhouse WHEELHOUSE --output RECEIPTS
```

The wheelhouse contains the built unit, its public dependencies and a pip wheel for
offline bootstrap. The acceptance script uses Linux `bwrap` with no developer home,
no source checkout and no network, installs into a blank venv, then mounts the
installation read-only. Its foreign synthetic fixture exercises public CLI/tool
calls, real numerical postprocessing, corrections, original changes and handoff.
The ordinary runtime does not depend on `bwrap`, uv or rtk.

`render_tools.py` regenerates the public function definitions. Versioned receipts
and the blank-Agent handoff results are linked from `releases/standalone-1.0.0/REPORT.md`.

## Historical plan validation

以下两个脚本只维护和检查历史实施包，不读取本机科研仓库，不调用 Jev。

在已安装 jsonschema 的 Python 环境中执行：

```bash
python checks/render_checklist.py
python checks/validate_plan.py
```

render_checklist 从 backlog.json 生成清单；validate_plan 检查依赖、版本退出覆盖、五类交换示例、五个无效契约、来源定位和题目结构。结果写入 plan_validation.json。

这些静态/合成契约检查不能证明产品安全、科学推断正确、Jev 准确率或真实项目复盘已完成。
