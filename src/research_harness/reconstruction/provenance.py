"""Explicit provenance and revocable identity relations; never destructive merges."""
from collections import defaultdict
from research_harness.common import HarnessError, stable_id, now
from research_harness.reconstruction.identity import compare

RELATIONS = {'same_object','same_run','numerical_comparison','same_proposition'}


def _references(value):
    if isinstance(value, str): return [value]
    if isinstance(value, dict):
        return [value[k] for k in ('id','artifact_id','source_id') if isinstance(value.get(k),str)]
    if isinstance(value,list): return [r for item in value for r in _references(item)]
    return []


def source_families(store):
    records={r['id']:r for r in store.list()}
    by_hash=defaultdict(list); by_label=defaultdict(list); edges=[]; parents=defaultdict(set)
    for identifier,record in records.items():
        data=record['data']
        if record['kind'].lower()=='artifact' and data.get('sha256'):
            by_hash[data['sha256']].append({'id':identifier,'revision':record['revision'],
                'path':data.get('path'),'identity_scope':data.get('identity_scope'),
                'byte_range':data.get('byte_range')})
        label=data.get('name',data.get('title'))
        if isinstance(label,str) and label.strip(): by_label[label.strip()].append(identifier)
        for field in ('derived_from','source_dependencies','support_sets'):
            for parent in sorted(set(_references(data.get(field)))):
                parents[identifier].add(parent)
                edges.append({'child':identifier,'parent':parent,'type':field,'parent_available':parent in records})
    nodes=set(records)|{p for ps in parents.values() for p in ps}
    children=defaultdict(set)
    for child,ps in parents.items():
        for parent in ps: children[parent].add(child)
    # Iterative Kosaraju avoids recursion limits on long historical derivations.
    visited=set(); order=[]
    for node in sorted(nodes):
        if node in visited: continue
        stack=[(node,False)]
        while stack:
            n,exit=stack.pop()
            if exit: order.append(n); continue
            if n in visited: continue
            visited.add(n); stack.append((n,True))
            stack.extend((p,False) for p in sorted(parents[n],reverse=True) if p not in visited)
    seen=set(); cycles=[]
    for node in reversed(order):
        if node in seen: continue
        component=set(); stack=[node]; seen.add(node)
        while stack:
            n=stack.pop(); component.add(n)
            for child in children[n]:
                if child not in seen: seen.add(child); stack.append(child)
        if len(component)>1 or node in parents[node]:
            external=sorted({p for n in component for p in parents[n] if p not in component})
            cycles.append({'members':sorted(component),'external_dependencies':external,
                'external_supported_records':[p for p in external if p in records and records[p]['data'].get('support_status')=='supported'],
                'support_status_by_member':{n:records.get(n,{}).get('data',{}).get('support_status','unchecked') for n in sorted(component)},
                'independence':'A circular derivation is not an independent support source; external dependencies require their own qualification.'})
    ancestors={}; shared=defaultdict(list)
    for node in sorted(records):
        found=set(); stack=list(parents[node])
        while stack:
            parent=stack.pop()
            if parent in found: continue
            found.add(parent); stack.extend(parents[parent]-found)
        found.discard(node); ancestors[node]=sorted(found)
        for parent in found: shared[parent].append(node)
    families=[{'sha256':sha,'members':members,'byte_identity_count':1,
               'independent_sample_count':None,
               'qualification':'One captured byte identity; copies are not additional independent evidence or runs. Segment hashes establish segment identity only.'}
              for sha,members in sorted(by_hash.items()) if len(members)>1]
    return {'schema_version':'provenance-1','store_revision':store.current_revision(),
            'byte_duplicate_families':families,'derivation_edges':edges,'ancestors':ancestors,
            'common_ancestors':[{'ancestor':p,'descendants':sorted(ds)} for p,ds in sorted(shared.items()) if len(ds)>1],
            'cycles':cycles,
            'semantic_equivalence_candidates':[{'label':label,'ids':sorted(ids),'status':'candidate','merge_performed':False,
                 'reason':'Shared label only; conditions and object identity require explicit comparison.'} for label,ids in sorted(by_label.items()) if len(ids)>1],
            'boundary':'Derived/support edges are explicit provenance, not newly inferred scientific validity. No record or support is changed.'}


def propose_alias(store,left_id,right_id,relation,scope,reason,reviewer):
    if relation not in RELATIONS or not isinstance(scope,dict) or scope.get('domain') not in ('chemistry','diffusion'):
        raise HarnessError('invalid_contract','Explicit supported relation and scope.domain are required')
    if not reason or not reviewer or left_id==right_id:
        raise HarnessError('invalid_contract','Distinct objects, reason and reviewer are required')
    left,right=store.get(left_id),store.get(right_id)
    ldata=left['data'].get('identity',left['data']); rdata=right['data'].get('identity',right['data'])
    check=compare(ldata,rdata,relation,scope['domain'])
    if check['status']=='incompatible':
        raise HarnessError('identity_incompatible','Conflicting scientific identity conditions',check)
    identifier=stable_id('identity_relation',[sorted([left_id,right_id]),relation,scope])
    data={'left_id':left_id,'left_revision':left['revision'],'right_id':right_id,'right_revision':right['revision'],
          'relation':relation,'scope':scope,'reason':reason,'reviewer':reviewer,'comparison':check,
          'status':'reviewed_compatible' if check['status']=='compatible' else 'candidate',
          'merge_performed':False,'revoked':False,'reviewed_at':now(),
          'boundary':'Version-bound identity relation; original objects and scientific support remain separate.'}
    reads={left_id:left['revision'],right_id:right['revision']}
    try: reads[identifier]=store.get(identifier)['revision']
    except KeyError: pass
    receipt=store.commit([{'id':identifier,'kind':'identity_relation','data':data}],reason=reason,read_set=reads,
                         idempotency_key=stable_id('alias-proposal',[data,reads]))
    return {'record':store.get(identifier),'receipt':receipt}


def revoke_alias(store,alias_id,reason,reviewer):
    record=store.get(alias_id)
    if record['kind']!='identity_relation' or not reason or not reviewer:
        raise HarnessError('invalid_contract','Identity relation, reason and reviewer required')
    data={**record['data'],'revoked':True,'status':'revoked','revocation_reason':reason,
          'revoked_by':reviewer,'revoked_at':now()}
    receipt=store.commit([{'id':alias_id,'kind':record['kind'],'data':data}],reason=reason,
                         read_set={alias_id:record['revision']},idempotency_key=stable_id('alias-revoke',[data,record['revision']]))
    return {'record':store.get(alias_id),'receipt':receipt}
