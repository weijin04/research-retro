#!/usr/bin/env python3
"""验证设计包结构；不运行 Jev、不读取本机科研源、不测试未实现产品。"""
from __future__ import annotations
import copy
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def validate() -> dict:
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError('需要现有环境中的 jsonschema 才能校验契约；本脚本不自动安装。') from exc
    plan = load(ROOT/'backlog.json')
    tasks = plan['tasks']
    ids = [task['id'] for task in tasks]
    if len(ids) != len(set(ids)):
        raise AssertionError('任务 ID 重复')
    by_id = {task['id']: task for task in tasks}
    phases = plan['phase_order']
    state = {}
    topo = []
    def visit(task_id):
        if state.get(task_id) == 1:
            raise AssertionError(f'任务依赖成环：{task_id}')
        if state.get(task_id) == 2:
            return
        state[task_id] = 1
        task = by_id[task_id]
        for dep in task['depends_on']:
            if dep not in by_id:
                raise AssertionError(f'{task_id} 缺少依赖 {dep}')
            if phases.index(by_id[dep]['phase']) > phases.index(task['phase']):
                raise AssertionError(f'{task_id} 反向依赖后续版本 {dep}')
            visit(dep)
        state[task_id] = 2
        topo.append(task_id)
    for task_id in ids:
        visit(task_id)
    for task in tasks:
        for field in ['objective','actions','deliverables','acceptance','owner_role']:
            if not task.get(field):
                raise AssertionError(f"{task['id']} 缺字段 {field}")
        if task['status'] == 'done' and not task.get('completion_evidence'):
            raise AssertionError(f"{task['id']} 已完成却没有完成证据")
    def ancestors(i):
        result=set()
        todo=list(by_id[i]['depends_on'])
        while todo:
            d=todo.pop()
            if d not in result:
                result.add(d); todo.extend(by_id[d]['depends_on'])
        return result
    for phase in plan['phases']:
        exits=phase.get('exit_tasks', [phase.get('exit_task')])
        exits=[x for x in exits if x]
        covered=set(exits)
        for i in exits:
            covered.update(ancestors(i))
        expected={t['id'] for t in tasks if t['phase']==phase['id']}
        if not expected.issubset(covered):
            raise AssertionError(f"{phase['id']} 退出任务没有覆盖本版本必要任务：{expected-covered}")
    schema=load(ROOT/'contracts/contract.schema.json')
    jsonschema.Draft202012Validator.check_schema(schema)
    validator=jsonschema.Draft202012Validator(schema)
    examples=['source_locator.json','audit_case.json','scientific_patch.json','task_proposal.json','decision_record.json']
    for name in examples:
        data=load(ROOT/'examples'/name)
        validator.validate(data)
        if data.get('is_example') is not True:
            raise AssertionError(f'{name} 缺少合成示例标记')
    source=load(ROOT/'examples/source_locator.json')
    fixture=ROOT/source['uri']
    if hashlib.sha256(fixture.read_bytes()).hexdigest()!=source['content_identity']['digest']:
        raise AssertionError('示例源指纹不匹配')
    if source['locator']['end']>len(fixture.read_text(encoding='utf-8').splitlines()):
        raise AssertionError('示例行定位越界')
    bad=[]
    b=load(ROOT/'examples/scientific_patch.json'); b['operations'][0]['operation']='increase_permissions'; bad.append(b)
    b=load(ROOT/'examples/decision_record.json'); b['answers']={'bad':{'type':'noul','noul':0.5,'confidence':0.9}}; bad.append(b)
    b=load(ROOT/'examples/source_locator.json'); b['content_identity']['digest']='unknown'; bad.append(b)
    b=load(ROOT/'examples/task_proposal.json'); b['budget_request']['gpu_count_max']=-1; bad.append(b)
    b=load(ROOT/'examples/audit_case.json'); del b['analysis_obligations']; bad.append(b)
    for item in bad:
        if validator.is_valid(item):
            raise AssertionError('预期无效契约意外通过')
    registry=load(ROOT/'examples/jev_questions.json')
    for family in registry['question_families']:
        question=family['question']
        if question['type']!='choice' or not question['instructions']:
            raise AssertionError('题目类型或语义缺失')
        if not {'other','insufficient_context'}.intersection(question['criteria']):
            raise AssertionError(f"{family['family']} 没有不匹配/信息不足入口")
        if len(question['criteria'])>255:
            raise AssertionError('Choice 候选超出当前文档约束')
    smoke=load(ROOT/'examples/jev_preflight_request.json')
    if {q['type'] for q in smoke['questions'].values()}!={'choice','noul','score'}:
        raise AssertionError('smoke 未覆盖三种 primitive')
    required=[f'{i:02d}_' for i in range(11)]
    md_files=list(ROOT.glob('*.md'))
    for prefix in required:
        if not any(p.name.startswith(prefix) for p in md_files):
            raise AssertionError(f'缺少文档 {prefix}')
    known_sources={f'S{i:02d}' for i in range(1,10)}|{f'L{i:02d}' for i in range(1,5)}
    for p in md_files:
        text=p.read_text(encoding='utf-8')
        unknown=set(re.findall(r'\[((?:S|L)\d{2})\]', text))-known_sources
        if unknown:
            raise AssertionError(f'{p.name} 引用未声明来源：{unknown}')
        if '\u2014' in text:
            raise AssertionError(f'{p.name} 包含不需要的破折号')
    return {'status':'passed','verification_scope':'design_package_structure_only',
      'not_verified':['Jev API connectivity or accuracy','real project reconstruction','runtime isolation','resource enforcement','scientific conclusions'],
      'task_count':len(tasks),'tasks_by_phase':dict(Counter(t['phase'] for t in tasks)),
      'task_graph_acyclic':True,'phase_exit_coverage':True,
      'contract_examples_validated':len(examples),'negative_contract_examples_rejected':len(bad),
      'fixture_hash_and_locator_valid':True,'question_families_checked':len(registry['question_families']),
      'main_documents_checked':len(md_files),'implementation_tasks_done':sum(t['status']=='done' for t in tasks),
      'topological_order':topo}

def main() -> None:
    try:
        report=validate()
    except Exception as exc:
        print(f'设计包校验失败：{exc}',file=sys.stderr)
        raise SystemExit(1)
    (ROOT/'checks/plan_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='topological_order'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
