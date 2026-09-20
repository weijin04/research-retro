#!/usr/bin/env python3
"""Queue routing only: do not merge evidence or mark whole families audited."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--input',type=Path,default=HERE/'project_reconstruction.json')
ap.add_argument('--output',type=Path,required=True)
args=ap.parse_args()
if args.output.exists():ap.error('choose a fresh output to preserve prior triage')
raw=args.input.read_bytes(); packet=json.loads(raw); indexed={r['id']:r for r in packet['records']}
candidates=[r for r in packet['records'] if r['kind']=='audit_candidate']
groups={
 'identity_reference':{'title':'对象、电荷、组成和比较/参考定义','pattern':r'模型|同名|同一 object|跨对象|MODEL-DEF|O2|O3|O4|composition|charge|参考态|零点|口径|身份'},
 'precursor':{'title':'前体及配位热化学','pattern':r'前体|precursor|MeCN|desorp|置换|κ|二聚|FeCl'},
 'spectroscopy':{'title':'吸收/谱根/实验指纹','pattern':r'TDDFT|TDA|光学|亮|暗态|IR|N1s|光谱|532|根号'},
 'local_excited_gradient':{'title':'局部激发态导数和能量目标量','pattern':r'iso_complex|FC 梯度|差梯度|归一化|垂直隙|1.16|3.92|9.13'},
 'ground_path_and_search':{'title':'路径、采样、驻点与未到达搜索','pattern':r'垒|TS|scan|路径|NEB|IRC|MEP|seam|连通|协同|搜索|回退'},
 'product_recovery':{'title':'产物对象、C-N连接与退火观测','pattern':r'产物|capped|T13|T14|T15|回迁|退火|开环|重键合|重成键|N⁻|N•|NH'},
 'electron_transfer':{'title':'ET目标量、能量循环与耦合','pattern':r'H_ab|CDFT|diabat|diabat|VEA|VIP|EA_vert|Marcus|λ|lambda|CT gap|CT 面|功函数|net −1|电荷转移'},
 'electronic_state_validity':{'title':'自旋、参考解和多参考适用性','pattern':r'自旋|S²|S\*\*2|spin|AFM|octet|Yamaguchi|CASSCF|CAS\(|smear|MR|STAB|MaxIter|Maxiter'},
 'organic_or_alternate_entry':{'title':'有机叠氮与替代入口','pattern':r'TMS|PFPA|DEA|有机|空位|缺陷|Fe\(II\)|cage|捕获|三唑|azidyl'},
 'availability_lineage':{'title':'来源、快照、版本和可恢复性','pattern':r'原件|副本|快照|未完成|无输出|从未|缺|目录|mtime|未收|血统|重排|重复|路径引用'},
 'protocol_and_infrastructure':{'title':'运行协议与解析/基础设施','pattern':r'normal|收敛|Freq|PARTIAL|HESS|约束|constraint|parser|MPI|slurm|node_modules|benchmark|census|计数|误计|字段'},
 'document_metadata':{'title':'文档说明与控制一致性','pattern':r'^规则|^每条标类型|^目的|^分级|^判定方法|^能量差按|^本表|^- 本表|覆盖|控制文档|Control|control-document|reconciliation'}
}
resolved_facets={
 'gph-ledger-line-77-review':('grephene-lmct-coordinate-and-energy-001','Normalized symmetric stretch total/gap distinction; not LMCT state character or full mechanism.'),
 'gph-ledger-line-78-review':('grephene-lmct-coordinate-and-energy-001','Same-geometry endpoint gap vs FC-referenced height.'),
 'gph-anomaly-line-49':('grephene-lmct-coordinate-and-energy-001','Normalization and total-vs-gap derivative mismatch resolved.'),
 'gph-anomaly-line-50':('grephene-lmct-coordinate-and-energy-001','Endpoint energy-reference mismatch resolved.'),
 'gph-directed-audit-t13b':('grephene-t13b-contact-migration-002','All-carbon distance reconstruction and invalid annealing-barrier inference; real annealing channel unknown.'),
 'gph-ledger-line-50-review':('grephene-t13b-contact-migration-002','Seven frames matched to raw scan, 16.048818 sample peak, contact migration.'),
 'gph-forgotten-line-14-review':('grephene-t13b-contact-migration-002','Point6 C32/C33 short contacts and seven-frame availability verified.'),
 'gph-anomaly-line-51':('grephene-t13b-contact-migration-002','Seven actual matched scan frames verified; old review snapshot-history attribution not independently reconstructed.'),
 'gph-anomaly-line-76':('grephene-t13b-contact-migration-002','This one-coordinate sampled electronic profile does not certify an annealing barrier.'),
 'gph-provenance-line-77':('grephene-t13b-contact-migration-002','Local raw cache and archived full output located and matched.'),
 'gph-ledger-line-27-review':('gph-ts-frequency-not-stationarity','Unconverged F5 m2 OptTS plus one imaginary Freq verified; m4 and energy difference not re-audited.')
}
assignments=[]
for r in candidates:
 d=r['data']; parent=indexed.get(d.get('subject_id',''),r)['data']
 text=' '.join([d.get('title',''),parent.get('original_text',''),parent.get('required_work','')])
 matched=[g for g,v in groups.items() if re.search(v['pattern'],text,re.I)]
 if not matched:matched=['document_metadata']
 facets=resolved_facets.get(r['id'])
 assignments.append({'candidate_id':r['id'],'relationship_groups':matched,'action':'retain_unresolved_remainder' if facets else 'retain_for_adoption_check','resolved_facet':{'audit_id':facets[0],'scope':facets[1]} if facets else None,'full_candidate_closed':False,'source_locators':d['provenance']['locators']})
for key,value in groups.items():
 value['member_candidate_ids']=[a['candidate_id'] for a in assignments if key in a['relationship_groups']]
 value['routing_only']=True
 value['status']='unresolved_group_with_possible_resolved_facets'
 value['priority']='P0_if_adopted_in_current_report' if key in {'identity_reference','ground_path_and_search','electron_transfer','organic_or_alternate_entry'} else ('P2_archival_or_metadata' if key in {'protocol_and_infrastructure','document_metadata','availability_lineage'} else 'P1_preserve_branch_qualification')
 value.pop('pattern')

outstanding=[
 {'id':'LB-ENTRY-COMPETITION','relationship':'Matched TMS/PFPA EA(Q) versus historical negative-EA/DEA rejection','blocks_if_report_adopts':['Organic/TMS route is excluded by negative endpoint vertical EA','Fe-associated route is scientifically preferred over TMS from these computed screens'],'required_existing_work':'Pair existing step5_sp neutral/anion on each same geometry, both neutral and anion scan lineages; preserve basis/diffuse functions, spin, zero-point/reference and failed cells. Determine precisely whether geometry-dependent EA overturns a blanket endpoint exclusion.','materials':['mech_loop/entry_competition_20260911/tms_arm/iso/TMS/step5_sp','mech_loop/entry_competition_20260911/tms_arm/iso/PFPA/step5_sp','research/pro_evidence_rebuild_20260915/raw_live_xj/entry_remaining/tms_arm/iso'],'related_candidate_ids':['gph-directed-audit-tmscurve','gph-forgotten-line-27-review','gph-audit-sf-04'],'current_status':'unresolved_existing_assets_first','report_safe_alternative':'Keep route eligibility unresolved and endpoint EA as a narrowly defined historical observation; do not assign overall route rank.','new_compute_required':'not established; existing SP ladder is the first discriminating check'},
 {'id':'LB-ET-TARGET','relationship':'Net-charge/geometry-conditioned H_ab and lambda versus neutral photo-injection/gating','blocks_if_report_adopts':['Four-order coordinate gating is established','Marcus lifetime or branching is current quantitative evidence','Net -1 constrained states quantify neutral photo-injection'],'required_existing_work':'From resting/other-geometry raw CP2K outputs recover actual charge, localization constraints, completed SCF and coupling; then reconstruct r4t four-point cycle with explicit geometry/state pairing. Differentiate missing coupling, failed setup and zero coupling.','materials':['mech_loop/h6a_gate_hab_scan/resting/hab_resting_v2.out','mech_loop/h6a_gate_hab_scan/approach_half','mech_loop/h6a_gate_hab_scan/fena_p040','mech_loop/r4t_lambda_fourpoint','MECHANISM_FIELD_AUDIT_20260907/01_INVENTORY/RAW_CACHE'],'related_candidate_ids':['gph-directed-audit-hab','gph-directed-audit-etcycle','gph-audit-sf-19'],'current_status':'unresolved_existing_assets_first','report_safe_alternative':'Withdraw quantitative kinetic/gating use while retaining raw diabat/coupling observations with the actual target; no claim of no electron transfer.','new_compute_required':'not needed to test whether old target supports the inference; only needed if a new correctly defined cycle is later requested'},
 {'id':'LB-PATH-NEGATIVES','relationship':'Constrained/path-specific observations versus global branch closure and productive connectivity','blocks_if_report_adopts':['All pristine-basal ground-state paths are closed','A low-spin scan apex below photon energy proves productive accessible N2 loss','A fixed root profile proves a continuous productive excited-state route'],'required_existing_work':'Reconstruct the actual C54 Fe-arm candidate conditions and endpoints plus one competing cage/recombination lineage; distinguish stationary/approximate candidate, one-dimensional failed search, change of electronic state and productive connection. Reconcile latest source with the old STOP/closed assertion and attach exact tested domain.','materials':['mech_loop/entry_competition_20260911/fe_arm','mech_loop/entry_competition_20260911/cage_branch','research/pro_evidence_rebuild_20260915/raw_live_xj/entry_remaining/fe_arm','mech_loop/mechanism_decision_20260909/nodes'],'related_candidate_ids':['gph-audit-sf-14','gph-audit-sf-25','gph-audit-sf-11','gph-directed-audit-tslinks'],'current_status':'partly_resolved_F5_certification_bounded; broader_branch_evidence_unresolved','report_safe_alternative':'Record tested route segments and explicit non-results, leave global existence/rank unresolved; preserve failed search as search evidence.','new_compute_required':'existing-output audit first; establishing missing productive connections is a separate research task, not prerequisite for a bounded reconstruction'}
]
result={'schema_version':'audit-queue-triage-1','created_at':datetime.now(timezone.utc).isoformat(),'input':{'path':str(args.input.resolve()),'sha256':hashlib.sha256(raw).hexdigest()},'candidate_count':len(candidates),'relationship_group_count':len(groups),'method':'Human-defined subject grouping and explicit facet adjudication; keyword routing does not infer scientific truth, equivalence or candidate closure.','assignments':assignments,'groups':groups,'outstanding_load_bearing':outstanding,'highest_value_next_relations':[x['id'] for x in outstanding],'resolved_in_scope':[{'audit_id':'grephene-lmct-coordinate-and-energy-001','scope':'explicit local gradient and energy-reference derivation, sampled nonmonotonicity'},{'audit_id':'gph-identity-comparability','scope':'O2/O3/O4 modeled composition and charge comparison'},{'audit_id':'gph-ts-frequency-not-stationarity','scope':'F5 m2 current archived OptTS is not completed converged certification'},{'audit_id':'grephene-t13b-contact-migration-002','scope':'seven-frame contact migration and constrained sample energy; not annealing kinetics'}],'can_demote_without_new_science':[{'scope':'Old anion observations used as neutral-model results','disposition':'Retain model-specific historical observation; remove cross-model support.','qualification':'identity mismatch independently checked; not every old number recalculated'},{'scope':'Old gradient magnitude, endpoint 1.16 vertical gap, strict monotonically descending claim','disposition':'Use accepted scoped corrections; preserve valid original numerical assets.','qualification':'real primary audit complete for these relations'},{'scope':'T13b electronic sample peak as 200 Celsius recovery barrier','disposition':'Remove kinetic support; preserve migration-like geometry and energy profile.','qualification':'real primary audit complete'},{'scope':'Older globally stopped branches, vacancy excluded-by-user, failed gradients, staged inputs and retired method families','disposition':'Retain exact historical work disposition separately from current evidence; mark unverified physical conclusions imported/unknown and do not restart.','qualification':'historical authority/status only, not new physical refutation'}],'release_guard':{'do_not_require':'Mechanism closure, completion of all 311 candidates, new DFT/MD or missing experimental identity to declare a bounded reconstruction complete.','must_require':['Every current load-bearing adopted assertion is tied to a completed scoped audit or explicitly downgraded with dependencies removed.','Report names remaining unknown branches, conditional adoption blockers and missing originals; no universal exclusion or preferred mechanism is silently inherited.','Do not label this full grephene science audit complete merely because all intake items have a queue destination.','Publishing a report that adopts any outstanding_load_bearing claim requires completing its indicated audit first; unknown preserves uncertainty but does not certify the claim.'],'status':'conditional_adoption_blockers_open'},'external_evidence_boundary':{'experiment_identity':'A model input does not establish the experimental precursor/film/product. If the report adopts a specific experimental identity or annealing chemical assignment, obtain the exact authorized sample/spectrum record; absent record remains unknown.','not_new_research':'Missing experimental originals are not a reason to launch additional quantum calculations.'},'queue_mutation':'none; all original candidates and records retained','checks':{'all_candidates_assigned':len(assignments)==len(candidates),'no_duplicate_candidate_id':len({a['candidate_id'] for a in assignments})==len(candidates),'no_whole_candidate_auto_closed':all(not a['full_candidate_closed'] for a in assignments)},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
result['deduplicated_relation_facets']=[
 {'key':'FC-stretch-total-vs-gap','members':['gph-ledger-line-77-review','gph-anomaly-line-49'],'audit':'grephene-lmct-coordinate-and-energy-001'},
 {'key':'endpoint-gap-vs-height','members':['gph-ledger-line-78-review','gph-anomaly-line-50'],'audit':'grephene-lmct-coordinate-and-energy-001'},
 {'key':'T13b-contact-migration-and-sampled-target','members':['gph-directed-audit-t13b','gph-ledger-line-50-review','gph-forgotten-line-14-review','gph-anomaly-line-51','gph-anomaly-line-76','gph-provenance-line-77'],'audit':'grephene-t13b-contact-migration-002'},
 {'key':'F5-m2-stationarity-obligation','members':['gph-ledger-line-27-review'],'audit':'gph-ts-frequency-not-stationarity'}]
result['deduplication_boundary']='These are shared relation facets, not whole-record aliases or independent-evidence votes. Broader claims in the same record stay unresolved. Twelve subject groups overlap and must not be called twelve closed tasks.'
assert all(result['checks'].values())
args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'candidates':len(candidates),'relationship_groups':len(groups),'resolved_facets':len(resolved_facets),'outstanding_ids':[x['id'] for x in outstanding],'group_memberships':{k:len(v['member_candidate_ids']) for k,v in groups.items()}},ensure_ascii=False,indent=2))
