# 设计包自检

这些脚本只维护和检查本实施包，不读取本机科研仓库，不调用 Jev，不实现科研 Harness。

在已安装 jsonschema 的 Python 环境中执行：

```bash
python checks/render_checklist.py
python checks/validate_plan.py
```

render_checklist 从 backlog.json 生成清单；validate_plan 检查依赖、版本退出覆盖、五类交换示例、五个无效契约、来源定位和题目结构。结果写入 plan_validation.json。

这些静态/合成契约检查不能证明产品安全、科学推断正确、Jev 准确率或真实项目复盘已完成。
