"""Trusted builder ScientificPatch endpoint; not an OS authentication boundary."""
import copy
from research_harness.common import HarnessError,canonical,digest,stable_id
from research_harness.contracts import validate_exchange
from research_harness.storage import ConflictError


def kind(record): return record['kind'].replace('_','').lower()


class PatchService:
    def __init__(self,store,ingestor): self.store,self.ingestor=store,ingestor

    def validate(self,patch):
        validate_exchange(patch)
        if patch['kind']!='scientific_patch' or patch['status'] not in ('proposed','validated'):
            raise HarnessError('invalid_contract','Expected proposed or validated ScientificPatch')
        marker_id=stable_id('scientific_patch_receipt',patch['idempotency_key'])
        try: marker=self.store.get(marker_id)
        except KeyError: marker=None
        if marker:
            if marker['data']['patch_digest']!=digest(patch): raise ConflictError('idempotency payload mismatch')
            return copy.deepcopy(marker['data']['verified_plan'])
        reads={r['object_id']:r['revision'] for r in patch['read_set']}
        if len(reads)!=len(patch['read_set']): raise HarnessError('invalid_contract','Duplicate read-set IDs')
        project=self.store.get('project:contract')
        if project['data']['project_id']!=patch['project_id']:
            raise HarnessError('permission_denied','Wrong project')
        if reads.get('project:contract')!=project['revision'] or patch['policy_revision']!=self.store.active_policy_revision():
            raise ConflictError('Project contract or policy changed/missing from original read-set')
        for identifier,revision in reads.items():
            if self.store.get(identifier)['revision']!=revision: raise ConflictError('Stale read: '+identifier)
        def read(identifier):
            r=self.store.get(identifier)
            if reads.get(identifier)!=r['revision']: raise ConflictError('Missing/stale read: '+identifier)
            return r
        verified=[]
        if not patch['verification_refs']: raise HarnessError('scientific_test_invalid','Actual completed verification required')
        for identifier in patch['verification_refs']:
            r=read(identifier);d=r['data']
            if d.get('revoked'): raise HarnessError('scientific_test_invalid','Verification revoked')
            if kind(r)=='auditresult':
                if not all(d.get(k) for k in ('completed_analysis','verdict','scope','blob_refs','reviewer','actual_read_set')):
                    raise HarnessError('scientific_test_invalid','Incomplete audit result')
                for blob in d['blob_refs']: self.store.read_blob(blob)
                for input_id,version in d.get('actual_read_set',{}).items():
                    current=self.store.get(input_id)
                    # Workbench submit advances its case to reviewed, linking this result.
                    if kind(current)=='auditcase' and current['data'].get('result_ref')==identifier and current['revision']==version+1:
                        read(input_id)
                        continue
                    if current['revision']!=version or reads.get(input_id)!=version:
                        raise ConflictError('Audit input changed or absent from patch reads: '+input_id)
                for receipt_id in d.get('verification_receipts',[]):
                    receipt=read(receipt_id)
                    if kind(receipt)!='verificationreceipt' or not receipt['data'].get('blob_refs'):
                        raise HarnessError('scientific_test_invalid','Invalid captured verification receipt')
                    for blob in receipt['data']['blob_refs']: self.store.read_blob(blob)
            elif kind(r)=='auditcase':
                if not str(d.get('status','')).startswith('completed') or d.get('support_status')!='supported' or not d.get('blob_refs'):
                    raise HarnessError('scientific_test_invalid','Audit case is not completed with support')
                for blob in d['blob_refs']: self.store.read_blob(blob)
                for premise_set in d.get('support_sets',[]):
                    for premise in premise_set: read(premise)
            else: raise HarnessError('scientific_test_invalid','Verification must be an actual audit result/case')
            for locator in d.get('source_locators',[]):
                artifact=read(locator['artifact_id'])
                if artifact['revision']!=locator['artifact_revision']:
                    raise ConflictError('Verification locator source changed')
                if locator.get('project_id')!=patch['project_id']:
                    raise HarnessError('permission_denied','Wrong verification locator project')
                self.ingestor.read(locator)
            verified.append(r)
        for ref in patch['reason']['evidence_refs']: read(ref)
        records={}
        reserved={'id','kind','permissions','allowed_actions','budget','budgets','policy_revision','support_status','adjudication_supported','authority','project_id','read_set'}
        def locators(data,required=False):
            ls=data.get('source_locators',[])
            if required and not ls: raise HarnessError('invalid_locator','Evidence requires immutable source locators')
            for locator in ls:
                if locator.get('project_id')!=patch['project_id']: raise HarnessError('permission_denied','Wrong locator project')
                a=read(locator['artifact_id'])
                if a['revision']!=locator['artifact_revision']: raise ConflictError('Locator source version changed')
                self.ingestor.read(locator)
        for operation in patch['operations']:
            op,identifier,payload=operation['operation'],operation['target_id'],copy.deepcopy(operation['payload'])
            if reserved & payload.keys(): raise HarnessError('permission_denied','Payload cannot alter identity/governance/derived support')
            if identifier==marker_id: raise HarnessError('invalid_contract','Target conflicts with patch receipt')
            if identifier in records: raise HarnessError('invalid_contract','Use one explicit operation per target')
            if op in ('add_evidence','add_branch'):
                try: self.store.get(identifier)
                except KeyError: pass
                else: raise ConflictError('Add target already exists')
                record={'id':identifier,'kind':'evidence' if op=='add_evidence' else 'branch','data':{}}
            else:
                record=read(identifier)
            expected={'revoke_assumption':{'assumption','evidence'},'change_claim_scope':{'claim'},
                      'adjudicate_inference':{'inference'},'revise_branch':{'branch'},'record_refutation':{'claim'}}
            if op in expected and kind(record) not in expected[op]:
                raise HarnessError('permission_denied','Operation not permitted on target kind')
            if op!='add_evidence' and 'intrinsic_valid' in payload:
                raise HarnessError('permission_denied','Operation cannot invent intrinsic validity')
            data={**record['data'],**payload}
            locators(data,required=op=='add_evidence')
            if op=='revoke_assumption': data.update(revoked=True,work_qualification='withdrawn')
            elif op=='change_claim_scope':
                if not payload.get('scope'): raise HarnessError('invalid_contract','Explicit corrected scope required')
            elif op=='adjudicate_inference':
                if payload.get('verdict') not in ('supported','qualified','refuted','invalid_test','unsupported','unresolved','mixed'):
                    raise HarnessError('invalid_contract','Explicit scoped inference verdict required')
            elif op=='add_evidence':
                affirmative=payload.get('intrinsic_valid',False)
                if affirmative and not (payload.get('qualification')=='audited_observation' and any(
                    kind(r)=='auditresult' and r['data'].get('verdict') in ('supported','qualified') and r['data'].get('scope')==payload.get('scope') for r in verified)):
                    raise HarnessError('scientific_test_invalid','Raw source presence does not qualify scientific evidence')
                data['intrinsic_valid']=bool(affirmative)
                data['independent_physical_evidence_count']='not increased by duplicate sources or reviews'
                data['source_content_identities']=sorted({l['content_identity']['digest'] for l in data['source_locators']})
            elif op in ('add_branch','revise_branch'):
                if not all(k in data for k in ('evidence_verdict','work_disposition','reopen_conditions')):
                    raise HarnessError('invalid_contract','Branch needs evidence, disposition and reopening conditions')
            elif op=='record_refutation':
                if not payload.get('scope') or 'residual_assets' not in payload:
                    raise HarnessError('invalid_contract','Refutation needs scope and residual_assets')
                data.update(evidence_status='refuted')
                negative_id=stable_id('negative_knowledge',[patch['id'],identifier])
                try: self.store.get(negative_id)
                except KeyError: pass
                else: raise ConflictError('Refutation record already exists')
                records[negative_id]={'id':negative_id,'kind':'negative_knowledge','data':{
                    'target_claim_id':identifier,'original_proposition':record['data'],
                    'scope':payload['scope'],'residual_assets':payload['residual_assets'],
                    'reopen_conditions':payload.get('reopen_conditions',[]),'verdict':'refuted',
                    'verification_refs':patch['verification_refs'],'source_locators':data.get('source_locators',[])}}
            data['scientific_patch_id']=patch['id'];data['verification_refs']=patch['verification_refs']
            records[identifier]={'id':identifier,'kind':record['kind'],'data':data}
        for record in records.values():
            for group in record['data'].get('support_sets',[]):
                for premise in group:
                    if premise not in records: read(premise)
        return {'records':list(records.values()),'read_set':reads,'policy_revision':patch['policy_revision'],
                'idempotency_key':patch['idempotency_key'],'reason':canonical(patch['reason']),
                'marker_id':marker_id,'patch_digest':digest(patch),'patch':copy.deepcopy(patch)}

    def commit(self,patch):
        plan=self.validate(patch)
        marker={'id':plan['marker_id'],'kind':'scientific_patch','data':{
            'patch_digest':plan['patch_digest'],'verified_plan':plan,
            'boundary':'Trusted builder validation; reviewer labels do not confer OS authority.'}}
        return self.store.commit(plan['records']+[marker],reason=plan['reason'],read_set=plan['read_set'],
                                 policy_revision=plan['policy_revision'],idempotency_key=plan['idempotency_key'])
