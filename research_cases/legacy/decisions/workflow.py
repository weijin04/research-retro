"""Synthetic analogue advice queued locally; private evidence never enters requests."""
from pathlib import Path
from research_harness.common import digest, stable_id, upsert
from .jev import JevAdapter

MODEL = 'jev-1.13.0'
POLICY = 'synthetic-analogue-advisory-v1'
QUESTIONS_VERSION = 'evidence-fit-task-route-v1'
LOCAL_CASE_ID = 'grephene-lmct-coordinate-and-energy-001'
# These are fixed fictional descriptions, never interpolated with store content.
ANALOGUES = {
    'strictly_monotonic_with_increase': {
        'provenance':'Wholly fictional integration example; no private scientific data.',
        'observation':'A deterministic checker reports at least one increase in an ordered series.',
        'claim':'The series strictly decreases at every successive point.',
        'proposal':'Inspect the scope of the monotonicity claim using the existing checker output.'},
    'gap_vs_reference_height': {
        'provenance':'Wholly fictional integration example; no private scientific data.',
        'observation':'The observed endpoint height above a starting reference includes a baseline change between configurations.',
        'claim':'This reported endpoint height is the gap between two states at the same configuration.',
        'proposal':'Inspect reference states and target-quantity definitions using existing materials.'},
}
QUESTIONS = {
    'evidence_fit': {'type':'choice',
        'instructions':'Compare the wording of state.claim with the explicit observation in this fictional state. Do not calculate numbers or infer missing science. Which semantic relationship is reported?',
        'criteria':{'consistent':'The observation expresses the same bounded claim.',
                    'scope_or_definition_conflict':'The claim changes or conflicts with an explicitly stated condition or target definition.',
                    'insufficient_context':'The supplied wording cannot distinguish the relationship.'}},
    'task_route': {'type':'choice',
        'instructions':'Which review route is directly warranted by state.proposal and state.observation, based only on the supplied fictional wording? This is an advisory suggestion, not execution permission.',
        'criteria':{'existing_evidence_review':'Review claim wording or target definitions using existing checker output/materials.',
                    'new_computation_request':'The proposal explicitly requires a new scientific calculation.',
                    'insufficient_context':'The proposed work cannot be routed from the supplied wording.'}},
}


def attach_advice(store, record_dir, *, adapter=None):
    """Return candidate receipts. Test adapter injection is explicitly labeled mock.

    The local case ID is attached only after evaluate returns. Neither that ID,
    source manifests, records, paths nor private scientific values are passed to
    Jev. No scientific record, support edge or audit status is changed.
    """
    execution_mode='mock_injected' if adapter is not None else 'live_service_or_recorded_exact_model_cache'
    adapter=adapter or JevAdapter(Path(record_dir))
    spec_hash=digest({'states':ANALOGUES,'questions':QUESTIONS,'model':MODEL,
                      'policy':POLICY,'questions_version':QUESTIONS_VERSION,'execution_mode':execution_mode})
    receipts=[]
    for category,state in ANALOGUES.items():
        decision_id=stable_id('decision_record',[category,spec_hash])
        suggestion_id=stable_id('audit_suggestion',[category,spec_hash])
        try: existing=store.get(decision_id)
        except KeyError: existing=None
        if existing and existing['data'].get('service_status')=='ok':
            receipts.append({'category':category,'decision_id':decision_id,'suggestion_id':suggestion_id,
                             'status':'already_attached','service_called':False,
                             'record_path':existing['data']['decision']['record_path']})
            continue
        decision=adapter.evaluate('synthetic_evidence_fit_and_task_route',state,QUESTIONS,
            QUESTIONS_VERSION,POLICY,requested_model=MODEL,egress_scope='synthetic',
            content_version='fixed-fiction-v1',candidate_version='route-options-v1',source_refs=[])
        boundary={'source_scope':'synthetic_analogue',
                  'qualification':'not_a_judgment_of_private_raw_data',
                  'private_raw_data_evaluated':False,'local_case_id':LOCAL_CASE_ID,
                  'category':category,'execution_mode':execution_mode,'spec_hash':spec_hash,
                  'action':'advisory_candidate_only','automatic_audit_close':False,
                  'automatic_support_change':False,'automatic_identity_merge':False}
        data={**boundary,'service_status':decision['status'],'decision':decision,
              'actual_model':decision.get('actual_model'),'usage':decision.get('usage'),
              'request_hash':decision.get('request_hash')}
        suggestion={**boundary,'title':'Synthetic analogue review suggestion: '+category,
                    'status':'candidate' if decision['status']=='ok' else 'recoverable_service_failure',
                    'decision_record_id':decision_id,'suggested_answers':decision.get('answers'),
                    'error_category':decision.get('error_category'),
                    'next_step':'Researcher may inspect existing private evidence locally; this synthetic suggestion does not validate that evidence.'}
        receipt=upsert(store,[{'id':decision_id,'kind':'decision_record','data':data},
                              {'id':suggestion_id,'kind':'audit_suggestion','data':suggestion}],
                       'queue synthetic analogue advice without judging private evidence')
        receipts.append({'category':category,'decision_id':decision_id,'suggestion_id':suggestion_id,
                         'status':decision['status'],'service_called':not decision.get('cache_hit',False) and bool(decision.get('attempts')),
                         'record_path':decision['record_path'],'actual_model':decision.get('actual_model'),
                         'usage':decision.get('usage'),'store_receipt':receipt})
    return {'status':'attached','source_scope':'synthetic_analogue','spec_hash':spec_hash,
            'execution_mode':execution_mode,'receipts':receipts,
            'boundary':'These decisions concern fictional analogues only; no private raw-data scientific audit was delegated to Jev.'}
