#!/usr/bin/env python3
"""Read-only, stdlib reproduction of the isolated-complex gradient audit.

Does not run source scripts or scientific programs. Finite differences below
check the coordinate map and a local linear energy model, not ab initio energy.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys

EV = 27.211386245988
ANG = 0.529177210903
ROOT = Path('/home/sun07ao/grephene')
BASE = ROOT / 'mech_loop/iso_complex_lmct'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[2] / 'var/audit_work/grephene/check_receipt.json')
    args = ap.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    sources = {}

    def read(path, role, patterns=()):
        path = path.resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError('source_out_of_scope')
        pre = path.stat()
        blob = path.read_bytes()
        post = path.stat()
        if (pre.st_size, pre.st_mtime_ns) != (post.st_size, post.st_mtime_ns):
            raise ValueError('source_changed_during_read')
        s = blob.decode('utf-8')
        lines = s.splitlines()
        ranges = [{'start': max(1, i-1), 'end': min(len(lines), i+1)} for i, line in enumerate(lines, 1) if any(re.search(p, line) for p in patterns)]
        if not ranges:
            ranges = [{'start': 1, 'end': len(lines)}]
        # Real independent bytes, never symlink/hardlink to changing original.
        sha = hashlib.sha256(blob).hexdigest()
        snap = args.output.parent / 'snapshots' / sha
        snap.parent.mkdir(parents=True, exist_ok=True)
        if snap.exists() and snap.read_bytes() != blob:
            raise ValueError('snapshot_collision')
        if not snap.exists():
            snap.write_bytes(blob)
        sources[str(path)] = {'path': str(path), 'sha256': sha, 'size': len(blob), 'line_ranges': ranges, 'role': role, 'snapshot': str(snap), 'read_mode': 'full_bytes', 'mtime_ns': post.st_mtime_ns}
        return s

    def engrad(path):
        s = read(path, 'primary_gradient')
        lines = s.splitlines()
        def at(marker):
            return next(i for i, x in enumerate(lines) if marker in x) + 2
        n = int(lines[at('Number of atoms')])
        energy = float(lines[at('current total energy')])
        k = at('current gradient')
        flat = list(map(float, lines[k:k+3*n]))
        grad = [flat[i:i+3] for i in range(0, 3*n, 3)]
        k = at('atomic numbers')
        rows = [x.split() for x in lines[k:k+n]]
        return {'energy': energy, 'grad': grad, 'coords': [list(map(float, x[1:])) for x in rows], 'z': [int(x[0]) for x in rows]}

    runs = {}
    for label in ['gs', 'root1', 'root2', 'root3']:
        d = BASE / 'fc_engrad_rootK' / label
        runs[label] = engrad(d / 'orca.engrad')
        inp = read(d / 'orca.inp', 'primary_input')
        out = read(d / 'orca.out', 'primary_output', [r'Total Energy\s+:', 'FINAL SINGLE POINT ENERGY', 'TERMINATED NORMALLY', r'INPUT FILE', r'IRoot'])
        assert '* xyzfile 0 6' in inp
        assert 'LibXC(WB97X-D4)' in inp and 'def2-TZVP' in inp
        assert '* xyzfile 0 6' in out and 'LibXC(WB97X-D4)' in out and 'def2-TZVP' in out
        assert 'ORCA TERMINATED NORMALLY' in out
        assert runs[label]['z'] == runs['gs']['z']
        assert runs[label]['coords'] == runs['gs']['coords']
        assert abs(float(re.findall(r'FINAL SINGLE POINT ENERGY\s+([-\d.]+)', out)[-1]) - runs[label]['energy']) < 1e-8
        if label != 'gs':
            assert re.search(r'IRoot\s+' + label[-1] + r'\b', inp)
            assert re.search(r'IRoot\s+' + label[-1] + r'\b', out)
    read(BASE / 'project_gradient.py', 'historical_implementation_not_executed', ['def bond_unit_vectors', 'def stretch_projection', 'dEdr =', 'increases bond length'])
    read(BASE / 'RESULTS.md', 'historical_claims', ['−9.133', '−9.189', '−9.206', '垂直间隙', '单调下降', '差梯度订正'])
    read(ROOT / 'research/scientific_evidence_map_20260915/CONTRADICTIONS_AND_ANOMALIES.md', 'imported_assertion_selection_only', [r'3.1', r'3.2'])
    read(BASE / 'compute_pes_fena.py', 'historical_implementation_not_executed')

    def dot(a, b):
        return sum(x*y for x, y in zip(a, b))

    coords = runs['gs']['coords']
    projections = []
    for name, i, j in [('Fe-Na', 0, 15), ('Na-Nb', 15, 16), ('Nb-Ng', 16, 17)]:
        v = [b-a for a, b in zip(coords[i], coords[j])]
        r = math.sqrt(dot(v, v))
        u = [x/r for x in v]
        raw = {key: dot([b-a for a, b in zip(run['grad'][i], run['grad'][j])], u)*EV/ANG for key, run in runs.items()}
        h = 1e-5
        def distance(t):
            return math.sqrt(sum((v[k] + t*u[k])**2 for k in range(3)))
        dr_dt = (distance(h)-distance(-h))/(2*h)
        assert abs(dr_dt-1) < 1e-8
        assert abs((distance(2*h)-distance(-2*h))/(2*h)-2) < 1e-8
        projections.append({'coordinate': name, 'r_angstrom': r*ANG, 'raw_B_dot_g_ev_per_angstrom': raw, 'symmetric_unit_stretch_total_ev_per_angstrom': {k: val/2 for k, val in raw.items()}, 'symmetric_unit_stretch_gap_ev_per_angstrom': {k: (val-raw['gs'])/2 for k, val in raw.items() if k != 'gs'}, 'coordinate_finite_difference_dr_dt': dr_dt})

    # Independent exact energy-reference decomposition at each scan point.
    scan = []
    dat = read(BASE / 'scan_fena/orca.relaxscanact.dat', 'primary_scan_energy')
    read(BASE / 'scan_fena/orca.inp', 'primary_scan_input')
    scan_out = read(BASE / 'scan_fena/orca.out', 'primary_scan_output', ["The Calculated Surface using the 'Actual Energy'", 'TERMINATED NORMALLY'])
    marker_line = next(i for i, x in enumerate(scan_out.splitlines(), 1) if "The Calculated Surface using the 'Actual Energy'" in x)
    sources[str((BASE / 'scan_fena/orca.out').resolve())]['line_ranges'].append({'start': marker_line, 'end': marker_line + 7})
    raw_table = scan_out.split("The Calculated Surface using the 'Actual Energy'")[-1].split('The Calculated Surface using the SCF energy')[0]
    assert [list(map(float, x.split())) for x in raw_table.strip().splitlines()] == [list(map(float, x.split())) for x in dat.splitlines()]
    assert 'ORCA TERMINATED NORMALLY' in scan_out
    for idx, line in enumerate(dat.splitlines(), 1):
        distance, scan_e0 = map(float, line.split())
        d = BASE / 'scan_fena/tda_points' / f'point{idx:03d}'
        inp = read(d / 'orca.inp', 'primary_tda_input')
        out = read(d / 'orca.out', 'primary_tda_output', [r'STATE\s+1:', r'Total Energy\s+:', 'Dispersion correction ', 'FINAL SINGLE POINT ENERGY', 'TERMINATED NORMALLY'])
        assert 'ORCA TERMINATED NORMALLY' in out
        assert re.search(r'xyzfile\s+0\s+6', inp)
        scf = float(re.findall(r'Total Energy\s+:\s+([-\d.]+) Eh', out)[-1])
        disp = float(re.findall(r'Dispersion correction\s+([-\d.]+)', out)[-1])
        final = float(re.findall(r'FINAL SINGLE POINT ENERGY\s+([-\d.]+)', out)[-1])
        state = re.findall(r'STATE\s+1:\s+E=\s+([\d.]+) au\s+([\d.]+) eV', out)[0]
        gap = (final - (scf+disp))*EV
        assert abs(gap-float(state[1])) < 0.001
        scan.append({'point': idx, 'r_angstrom': distance, 'tda_e0_eh': scf+disp, 'tda_e1_eh': final, 'vertical_gap_ev': gap, 'printed_state1_ev': float(state[1]), 'ground_deformation_ev': ((scf+disp)-runs['gs']['energy'])*EV, 'excited_height_above_fc_ground_ev': (final-runs['gs']['energy'])*EV, 'scan_vs_tda_ground_ev': (scan_e0-(scf+disp))*EV})
    increases = [{'from': a['point'], 'to': b['point'], 'increase_ev': b['excited_height_above_fc_ground_ev']-a['excited_height_above_fc_ground_ev']} for a, b in zip(scan, scan[1:]) if b['excited_height_above_fc_ground_ev'] > a['excited_height_above_fc_ground_ev']]
    receipt = {'audit_id': 'grephene-lmct-coordinate-and-energy-001', 'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(), 'exit_status': 0, 'mode': 'real_local_postprocessing_no_new_quantum_calculation', 'python': sys.version, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'constants': {'hartree_to_ev': EV, 'bohr_to_angstrom': ANG}, 'source_files': list(sources.values()), 'composition_atomic_numbers': dict(Counter(runs['gs']['z'])), 'same_coordinates_exact': True, 'projections': projections, 'vertical_fc_gaps_ev': {k: (v['energy']-runs['gs']['energy'])*EV for k, v in runs.items() if k != 'gs'}, 'scan': scan, 'strict_monotonic_descent': not increases, 'upward_scan_steps': increases, 'checks': ['primary_input_charge_multiplicity_method', 'normal_termination_all_read_jobs', 'engrad_vs_output_energy', 'exact_geometry_and_atom_identity', 'unit_stretch_coordinate_finite_difference', 'energy_reference_identity', 'scan_monotonicity'], 'limitations': ['No finite-difference ab initio energy evaluation.', 'Symmetric Cartesian displacement changes other internal coordinates; not a relaxed-path derivative.', 'No state-character/diabatic identity proof and no dynamics or product-yield prediction.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'receipt': str(args.output), 'source_count': len(sources), 'Fe_Na': projections[0], 'endpoint': scan[-1], 'upward_scan_steps': increases}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
