# Development checks

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
