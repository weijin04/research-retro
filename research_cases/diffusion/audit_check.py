#!/usr/bin/env python3
"""Read-only original-snapshot audit. No repository programs or MD are executed."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics

DEFAULT=Path('/home/sun07ao/diffusion/reports/shuguang-log-audit-20260906/snapshot')

def run(root, output):
    read_at=datetime.now(timezone.utc).isoformat()
    paths={k:root/v for k,v in {
        'input':'in.production_flex_r','script':'flexsg.sh',
        'data':'validation/minimized_with_guest.data',
        'log':'production/FLEX_sg_r9/FLEX_sg_r9.log',
        'early':'production/FLEX_sg_r9/FLEX_sg_r9_early.lammpstrj',
    }.items()}
    texts={k:p.read_text() for k,p in paths.items()}
    lines={k:t.splitlines() for k,t in texts.items()}
    def locate(k,needle):
        return next(i+1 for i,s in enumerate(lines[k]) if needle in s)
    sources=[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
              'start_line':1,'end_line':len(lines[k]),'role':k,'read_at':read_at}
             for k,p in paths.items()]
    masses={}
    start=locate('data','Masses')
    for line in lines['data'][start:]:
        if line.startswith('Atoms'): break
        if line.strip():
            a=line.split(); masses[int(a[0])]=float(a[1])
    atom_start=locate('data','Atoms # full')
    atoms=[]
    for line in lines['data'][atom_start:]:
        if line and line[0].isalpha(): break
        if line.strip(): atoms.append(line.split())
    counts=Counter(int(a[2]) for a in atoms)
    guest=[a for a in atoms if a[2]=='3']
    assert len(guest)==1 and counts=={1:288,2:576,3:1}, counts
    mass=masses[3]
    assert float(guest[0][3]) == 0
    assert 'timestep        1.0' in texts['log']
    assert 'compute_modify  TG extra/dof 0' in texts['log']
    assert 'fix             NVT all nvt temp 300.0 300.0 100.0 tchain 3' in texts['log']
    assert 'run             199980000' in texts['log']
    values=[]
    velocities=[]
    frame_lines=[]
    el=lines['early']
    assert len(el)%10==0, 'incomplete early frame'
    for i in range(0,len(el),10):
        assert el[i]=='ITEM: TIMESTEP' and el[i+3]=='1'
        assert el[i+8]=='ITEM: ATOMS id type x y z vx vy vz'
        a=el[i+9].split()
        assert a[0]==guest[0][0] and a[1]=='3'
        step=int(el[i+1]); v=list(map(float,a[-3:]))
        # v: Angstrom/fs = 1e5 m/s; m: g/mol -> kg per molecule.
        # m*v^2/(3*kB) = mass(g/mol)*1e7*sum(v_i^2)/(3*R).
        temp=mass*1e7*sum(x*x for x in v)/(3*8.31446261815324)
        values.append((step,temp)); velocities.append(v); frame_lines.append(i+10)
    assert [s for s,t in values]==list(range(20001))
    ts=[t for s,t in values]
    block=[{'start_fs':lo,'end_fs_exclusive':lo+5000,'n':5000,
            'mean_K':statistics.mean(t for s,t in values if lo<=s<lo+5000)} for lo in range(0,20000,5000)]
    cuts=[{'discard_fs':cut,'n':sum(s>=cut for s,t in values),
           'mean_K':statistics.mean(t for s,t in values if s>=cut)} for cut in (0,1000,5000,10000,15000)]
    mean=statistics.mean(ts); var=statistics.pvariance(ts)
    autocorr={str(lag):sum((ts[i]-mean)*(ts[i+lag]-mean) for i in range(len(ts)-lag))/((len(ts)-lag)*var) for lag in (1,10,100,1000)}
    thermo={}
    for no,line in enumerate(lines['log'],1):
        a=line.split()
        if len(a)==8:
            try: row=list(map(float,a))
            except ValueError: continue
            thermo[int(row[0])]={'line':no,'row':row}
    endpoint_checks=[]
    for step in (0,20000):
        calculated=values[step][1]; logged=thermo[step]['row'][4]
        assert abs(calculated-logged)<.002
        endpoint_checks.append({'step':step,'recomputed_K':calculated,'log_K':logged,
                                'delta_K':calculated-logged,'trajectory_line':frame_lines[step],
                                'log_line':thermo[step]['line']})
    later=[r['row'][4] for s,r in thermo.items() if s>=200000]
    # A purely mathematical conditional canonical reference, not a fit to these data.
    reference={'assumption':'Three independent Gaussian velocity components at canonical T; no separate guest COM subtraction',
               'T_K':300,'degrees_of_freedom':3,'mean_K':300,
               'sd_K':300*math.sqrt(2/3),'relative_sd':math.sqrt(2/3),
               'derivation':'K=sum(m*v_i^2/2); 2K/(kB*T) ~ chi-square(3). T_inst=2K/(3*kB), E[T_inst]=T, Var[T_inst]=2*T^2/3. For N independent guests relative sd=sqrt(2/(3N)); N=1 is broad, N->infinity tends to zero.'}
    logrows=[r['row'] for s,r in thermo.items() if s in (0,20000)]
    result={
        'id':'diffusion-flex-r9-kinetic-temperature-v1','title':'Single-guest kinetic fluctuations versus equilibrium-sampling claims',
        'historical_assertion':{'source':'Earlier review README is a locator, not primary authority',
            'reconstructed_claim':'Large c_TG fluctuations imply abnormal dynamics or trapping; early 300 K-labelled output can be treated as equilibrium sampling.',
            'provenance_boundary':'The external original critical comment is absent. This formulation reconstructs the disputed claim from the archived review, not a verbatim original assertion.'},
        'research_question':'Do independently reconstructed guest kinetic temperatures establish anomaly, equilibrium, or neither?',
        'development_material':True,'blind_evaluation':False,'read_at':read_at,
        'scientific_scope':{'run':'FLEX_sg_r9','replica_seed':21233,'engine':'LAMMPS 28 Mar 2023',
            'framework':'288 type-1 Si + 576 type-2 O; silica framework. CHA topology is reported historically but not independently identified in this kinetic audit.',
            'guest':'one neutral type-3 united-atom CH4, atom id 865','mass_g_per_mol':mass,
            'atom_counts':dict(counts),'loading':'1 UA CH4 per simulated periodic cell; adsorption-equilibrium loading not established',
            'ensemble':'all-group Nose-Hoover NVT, target 300 K, damping 100 fs, tchain 3; fixed triclinic periodic cell; flexible framework',
            'dt_fs':1.0,'early_window_ps':[0,20],'early_stride_fs':1,'early_complete_frames':len(values),
            'planned_steps':200000000,'planned_duration_ns':200,'observed_last_thermo_step':max(thermo),
            'observed_last_thermo_ns':max(thermo)/1e6,'observational_definition':'c_TG uses guest temp with extra/dof 0: three translational DOF; no guest mean velocity subtraction. UA model has no resolved internal CH4 vibrations or rotations.'},
        'source_files':sources,
        'analyses':{
            'endpoint_reconstruction':endpoint_checks,'temperature_mean_K':mean,'temperature_sd_K':statistics.pstdev(ts),
            'half_open_5ps_blocks':block,'inclusive_discard_sensitivity':cuts,
            'temperature_autocorrelation':autocorr,'autocorrelation_caveat':'Descriptive finite-window correlation only; early transient may be nonstationary. No effective sample count or IID confidence interval inferred.',
            'canonical_reference':reference,
            'early_energy_change_kcal_per_mol':{'potential':thermo[20000]['row'][5]-thermo[0]['row'][5],
                                               'bond':thermo[20000]['row'][6]-thermo[0]['row'][6]},
            'later_sparse_r9':{'start_ps':200,'end_ps':max(thermo)/1000,'n':len(later),'mean_K':statistics.mean(later),
                               'boundary':'Only eight sparsely spaced samples from one replica. Not a stationarity or transport test.'},
            'code_path':{'path':str(paths['script']),'mpirun_line':locate('script','mpirun -np'),
                         'last_command_line':len(lines['script']),
                         'finding':'The next echo expands the preceding mpirun status into text but its own success becomes script exit status. No explicit exit of captured status exists. A failed MD command can therefore have a successful batch shell status.',
                         'scope':'Static shell control-flow audit, no scheduler or MD execution; not evidence this run failed.'}},
        'competing_explanations':[
            {'explanation':'Wrong guest degrees of freedom caused c_TG excursions','status':'disfavored_for_endpoints','test':'3-DOF velocity reconstruction matches both logged endpoints within 0.002 K; explicit extra/dof 0 in input.'},
            {'explanation':'Normal finite-DOF kinetic fluctuations','status':'compatible','test':'Canonical reference predicts 244.949 K standard deviation at 300 K. An isolated low or high TG cannot identify trapping or barrier crossing.'},
            {'explanation':'Initial structural/energy redistribution and correlated short sampling','status':'supported_as_sampling_caution','test':'Input initializes velocities on minimized data and immediately saves early output; block/cutoff means vary, energy components change.'},
            {'explanation':'Thermostat or integration pathology','status':'not_identified_and_not_excluded','test':'These observations do not discriminate it from a transient and correlated sampling. Need already-authorized longer stationary velocity/energy windows and timestep/conservation evidence; no new MD authorized.'},
        ],
        'verdict':'corrected_scope: large instantaneous single-guest kinetic fluctuations alone do not establish dynamic anomaly; early output cannot be accepted as verified equilibrium sampling.',
        'supported_scope':['Independent units/DOF reconstruction of actual archived velocities','Early kinetic sampling sensitivity is established','Failure reporting flaw in shell control flow exists'],
        'failure_boundary':['No equilibrium or diffusion coefficient convergence certificate','No proof of trapping, hopping, thermostat correctness or invalidity','All outputs are archived running prefixes; no final completion receipt'],
        'residual_assets':[{'path':str(root/'production'),'reason':'Other 23 replica logs/low-frequency trajectories remain available; not consumed in this bounded independent slice.'}],
        'unresolved':[
            {'question':'Stationary equilibrium velocity distribution and VACF/kernel eligibility','needed':'Existing equilibrated high-frequency velocity records across replicas plus equilibration and block sensitivity analysis; absent from this slice. If none exist, obtaining them requires new authorization for MD.'},
            {'question':'Long-time diffusion convergence','needed':'Explicit position unwrapping/image evidence, linear MSD regime, fitting-window and replica uncertainty. Temperature alone cannot answer.'},
            {'question':'Historical original criticism identity','needed':'Original comment/source, if provenance precision is required; historical README is only an indirect source.'},
        ],
        'locators':{'mass_line':locate('data','3 16.04246'),'atoms_header_line':atom_start,
                    'guest_atom_line':next(i+1 for i,line in enumerate(lines['data']) if line.split()==guest[0]),'dt_line':locate('log','timestep        1.0'),
                    'dof_line':locate('log','compute_modify  TG extra/dof 0'),
                    'thermostat_line':locate('log','fix             NVT all nvt'),
                    'early_dump_line':locate('input','dump            EARLY'),
                    'position_dump_line':locate('input','dump            TRAJ')}
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/'audit_case.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    report=f'''# Diffusion 第二领域复盘切片：FLEX_sg_r9

独立复算支持范围修订：单客体瞬时动能温度大幅变化本身不是动力学异常证据；这段启动期速度也不能直接标成已平衡 300 K 数据。开发/试用材料，不是盲测。

原件：`{root}`。逐文件 SHA256、读取时间、完整行范围与关键行定位见 `audit_case.json`。原评论缺失，旧 README 只用于定位；没有把旧报告数字作为输入。

## 对象、条件与实际执行

运行是 LAMMPS 28 Mar 2023、seed 21233、1 fs，固定周期三斜晶胞，864 个柔性 Si/O 框架原子和一个质量 {mass} g/mol 的 UA CH4（id 865）。目标 all-group NVT 300 K，阻尼 100 fs，tchain 3。计划 200 ns，但本地日志仅到 {max(thermo)/1e6:g} ns，不能称完成。CHA 拓扑是历史标签，本次未从结构独立鉴定。

原输入直接读最小化 data、创建速度、启动 NVT 并立即保存 early 轨迹；没有单独的预平衡段。early 包含 0–20 ps 的 {len(values)} 个完整 1 fs 速度帧；不是 {len(values)} 个独立样本。

## 原始速度复算与推导

用真实 type-3 质量和三个速度分量计算 `T_inst = mass(g/mol) × 10^7 × (vx²+vy²+vz²) / (3R)`，速度单位 Å/fs。extra/dof 0 保留三个平动自由度。

初末复算为 {ts[0]:.6f} / {ts[-1]:.6f} K；日志为 {thermo[0]['row'][4]} / {thermo[20000]['row'][4]} K，差均小于 0.002 K。小差来自文本速度精度及单位常数约定，排除了这两个端点的主要自由度/单位误读。

全窗口均值 {mean:.6f} K、总体标准差 {statistics.pstdev(ts):.6f} K。四个不重叠半开 5 ps 段均值依次 {', '.join(f"{b['mean_K']:.3f}" for b in block)} K。丢弃前 5 ps（含第 5000 步）后均值 {cuts[2]['mean_K']:.6f} K。分段排除最终第 20000 步以保持每段恰好 5000 帧；全窗口与截断统计包含末帧。

正则条件下三个高斯速度分量使 `2K/(kBT)` 服从 χ²(3)，于是 `E[T_inst]=T`、`Var[T_inst]=2T²/3`。300 K 的标准差为 {reference['sd_K']:.6f} K；N 个独立客体时相对标准差降为 √(2/(3N))，N→∞ 才消失。这个参考分布有条件，不能倒过来证明实际轨迹正则或已平衡。低动能不定位势阱，高动能不证明跨越势垒。

温度序列 lag 1/10/100/1000 fs 的描述性相关分别 {', '.join(f'{v:.6f}' for v in autocorr.values())}。非平稳启动段不能由这些值推有效样本量或 IID 置信区间。势能变化 {result['analyses']['early_energy_change_kcal_per_mol']['potential']:.6f} kcal/mol，键能变化 {result['analyses']['early_energy_change_kcal_per_mol']['bond']:.6f} kcal/mol，与明显启动重整相容，但本身不证明结构崩溃。

## 竞争解释与边界

三个 DOF 的端点复算吻合，削弱温度定义错误解释。有限自由度涨落与启动期相关采样都仍成立；这些材料无法区分正常暂态与潜在 thermostat/积分问题。因此修订的是“这些观测足以判异常/足以判平衡”的推论，而不是宣判整个模型有效或失效。

r9 的 200–{max(thermo)/1000:g} ps 只有 {len(later)} 个稀疏热力学点，均值 {statistics.mean(later):.6f} K。这不足以证明平衡、VACF/记忆核拟合资格或扩散收敛。下一判别材料是已有平衡阶段高频速度及能量、跨副本与窗口敏感性；不存在时需要额外授权采样。本次不运行 MD、不调用原 repo 脚本、不外发数据。

另外，`flexsg.sh` 第 {locate('script','mpirun -np')} 行 mpirun 后只执行 echo；echo 打印旧退出码，但自己的成功码会成为脚本退出码。这是静态可证明的失败报告缺陷，不意味着本次 MD 已失败。完成状态仍需最终步、restart、真实退出码等原始回执。

## 复现

在框架目录运行：

```sh
rtk proxy python3 research_cases/diffusion/audit_check.py
```

结果写入 `research_cases/diffusion/audit_case.json` 和本报告；输入只读。可用 `--output var/audit_work/diffusion/recheck` 隔离重算。标准库轻量后处理，无数值动力学计算。
'''
    (output/'REPORT.md').write_text(report)
    print(json.dumps({'output':str(output),'frames':len(values),'mean_K':mean,'endpoint_checks':endpoint_checks},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--source',type=Path,default=DEFAULT)
    p.add_argument('--output',type=Path,default=Path('research_cases/diffusion'))
    a=p.parse_args(); run(a.source,a.output)
