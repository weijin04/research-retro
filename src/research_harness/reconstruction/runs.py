"""Recover separate observed executions from immutable captured output, never disk inputs."""
import re
from pathlib import Path
from research_harness.common import stable_id,upsert


def reconstruct_captured_runs(store,ingestor):
    artifacts=store.list('artifact');records=[]
    for artifact in artifacts:
        d=artifact['data'];path=Path(d['path'])
        if path.suffix.lower() not in ('.out','.log'): continue
        text=store.read_blob(d['sha256']).decode('utf-8',errors='replace');lines=text.splitlines()
        is_orca='O   R   C   A' in text or 'Program Version' in text or 'FINAL SINGLE POINT ENERGY' in text
        is_lammps=bool(re.search(r'^LAMMPS \(',text,re.M))
        if not is_orca and not is_lammps: continue
        run_id=stable_id('run',[artifact['id']]);object_id=stable_id('scientific_object',[artifact['id']])
        whole=ingestor.locator(artifact,1,max(1,len(lines)))
        echo=[];echo_lines=[]
        if is_orca:
            for i,line in enumerate(lines,1):
                m=re.match(r'\s*\|\s*\d+>\s?(.*)',line)
                if m: echo.append(m.group(1));echo_lines.append(i)
        echo_text='\n'.join(echo)
        tokens=[token for line in echo if line.lstrip().startswith('!') for token in line.lstrip()[1:].split()]
        xyz=re.search(r'^[ \t]*\*[ \t]*(xyzfile|xyz)[ \t]+(-?\d+)[ \t]+(\d+)(?:[ \t]+([^\n]+))?',echo_text,re.M|re.I)
        charge=int(xyz.group(2)) if xyz else 'unknown';mult=int(xyz.group(3)) if xyz else 'unknown'
        elements=[]
        if xyz and xyz.group(1).lower()=='xyz':
            tail=echo_text[xyz.end():].splitlines()
            # Coordinate block extraction requires an explicitly inline geometry header.
            for line in tail:
                if line.strip()=='*': break
                m=re.match(r'^\s*([A-Z][a-z]?)\s+[-+0-9.]',line)
                if m: elements.append(m.group(1))
        if not elements:
            inside=False
            for line in lines:
                if 'CARTESIAN COORDINATES (ANGSTROEM)' in line: inside=True;continue
                if inside:
                    m=re.match(r'^\s*([A-Z][a-z]?)\s+[-+0-9.]+\s+[-+0-9.]+\s+[-+0-9.]+\s*$',line)
                    if m: elements.append(m.group(1))
                    elif elements: break
        composition={element:elements.count(element) for element in sorted(set(elements))} if elements else 'unknown'
        def normalize(s): return '\n'.join(line.strip() for line in s.splitlines() if line.strip())
        candidate_inputs=[]
        for a in artifacts:
            p=Path(a['data']['path'])
            if p.parent==path.parent and p.suffix.lower()=='.inp':
                inp=store.read_blob(a['data']['sha256']).decode('utf-8',errors='replace')
                candidate_inputs.append({'artifact_id':a['id'],'artifact_revision':a['revision'],'sha256':a['data']['sha256'],
                    'qualification':'verified_echo_text_match' if echo and normalize(inp)==normalize(echo_text) else 'candidate_not_historical_input',
                    'source_locator':ingestor.locator(a)})
        version=re.search(r'Program Version\s+([^\n]+)',text) if is_orca else re.search(r'LAMMPS \(([^\n)]+)\)',text)
        scan=bool(re.search(r'relaxed surface scan|surface scan|RELAXED SURFACE',text,re.I))
        axes={'process_completion':'observed_normal_marker' if 'ORCA TERMINATED NORMALLY' in text else 'unknown',
              'optimization_convergence':'observed_marker' if 'THE OPTIMIZATION HAS CONVERGED' in text else 'unknown',
              'scf_convergence':'failure_observed' if re.search(r'SCF NOT CONVERGED|SCF did not converge',text,re.I) else ('observed_marker' if 'SCF CONVERGED' in text else 'unknown'),
              'frequency_values_observed':len(re.findall(r'^\s*\d+:\s+[-+0-9.]+\s+cm',text,re.M)),
              'method_applicability':'unchecked','scientific_test_validity':'unchecked'}
        if is_lammps: axes['process_completion']='observed_prefix_only'
        identity={'composition':composition,'charge':charge,'multiplicity':mult,'geometry':'unknown',
                  'method':tokens if tokens else 'unknown','method_token_semantics':'literal echoed tokens; no inferred method/basis split',
                  'basis':'unknown','environment':'unknown','constraints':'unknown','target_quantity':'unknown','unit':'unknown','reference_state':'unknown',
                  'actual_input_sha256':'unknown','execution_id':'unknown','output_sha256':d['sha256']}
        run={'title':path.name,'output_artifact_id':artifact['id'],'output_revision':artifact['revision'],'output_sha256':d['sha256'],
             'engine':'ORCA' if is_orca else 'LAMMPS','observed_version':version.group(1).strip() if version else 'unknown',
             'actual_binary_sha256':'unknown','actual_execution_identity':'unknown','actual_input_echo':echo_text or None,
             'actual_input_basis':'captured output echo' if echo else 'unknown','input_candidates':candidate_inputs,
             'geometry_reference':xyz.group(4).strip() if xyz and xyz.group(1).lower()=='xyzfile' and xyz.group(4) else 'unknown',
             'geometry_boundary':'No current/latest xyz substituted for executed geometry; scan per-point geometry remains unknown.',
             'execution_structure':'composite_scan_child_candidates_not_independent_unique_executions' if scan else 'one_captured_output_execution_candidate',
             'axes':axes,'identity':identity,'source_locators':[whole],
             'source_dependencies':[artifact['id']],'source_versions':{artifact['id']:artifact['revision']},
             'scientific_object_id':object_id,'qualification':'observed_output_reconstruction_not_physical_validation'}
        if echo_lines: run['echo_locator']=ingestor.locator(artifact,min(echo_lines),max(echo_lines))
        if is_lammps:
            steps=[int(m.group(1)) for m in re.finditer(r'^\s*run\s+(\d+)\s*$',text,re.M)]
            run['planned_run_segments_steps']=steps
            run['planned_steps_boundary']='Echoed run arguments are planned segments, not completion receipts.'
        records.extend([{'id':run_id,'kind':'run','data':run},
                        {'id':object_id,'kind':'scientific_object','data':{'title':path.name+' observed object','identity':identity,
                         'source_locators':[whole],'source_dependencies':[artifact['id']],'output_revision':artifact['revision'],
                         'qualification':'partial_identity_unknown_fields_retained'}}])
    receipt=upsert(store,records,'recover separate executions from immutable captured outputs') if records else {'status':'unchanged','changed_ids':[]}
    return {'status':'reconstructed','run_count':len(records)//2,'receipt':receipt,
            'boundary':'Captured outputs only; no original scripts executed, no external data sent, no scientific validity certified.'}
