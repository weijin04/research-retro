#!/usr/bin/env python3
"""从 backlog.json 重建阅读清单，不改变任务状态。"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    data = json.loads((ROOT / 'backlog.json').read_text(encoding='utf-8'))
    tasks = data['tasks']
    lines = ['# 6. 详细执行清单', '', f'共 {len(tasks)} 项任务。此文件由 backlog.json 生成；任务变更先更新 JSON，再重新生成。', '',
             '版本完成要求该版本所有任务及其依赖都有真实产物；单个退出任务不能豁免其他必要工作。', '']
    for phase in data['phases']:
        lines.extend([f"## {phase['id']}：{phase['name']}", ''])
        for task in (t for t in tasks if t['phase'] == phase['id']):
            mark = 'x' if task['status'] == 'done' else ' '
            lines.extend([f"### [{mark}] {task['id']} {task['title']}", '', f"状态：{task['status']}。",
                f"目标：{task['objective']}",
                f"依赖：{', '.join(task['depends_on']) or '无'}。负责角色：{task['owner_role']}。", '', '具体工作：'])
            lines.extend(f'{i+1}. {action}' for i, action in enumerate(task['actions']))
            lines.extend(['', '交付：'+'；'.join(task['deliverables'])+'。',
                          '验收：'+'；'.join(task['acceptance']), f"Jev：{task['jev_use']}。"])
            evidence = task.get('completion_evidence', [])
            lines.extend(['完成证据：'+('；'.join(map(str,evidence)) if evidence else '尚无')+'。', ''])
    (ROOT / '06_EXECUTION_CHECKLIST.md').write_text('\n'.join(lines).strip()+'\n', encoding='utf-8')

if __name__ == '__main__':
    main()
