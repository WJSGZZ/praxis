"""Derive recurring report quantities from the archived numerical evidence.

No simulation or policy selection takes place here. Formatting remains in the
report builder; mismatched policy/perturbation evidence fails before authoring.
"""
import math


def report_values(results, extended, mesh, structure):
    p = results['parameters']
    schedule = mesh['accepted_schedule']
    flows = schedule['flow_lpm']
    segment_min = schedule['segment_s'] / 60
    if len(flows) != schedule['segments'] or not math.isclose(
            sum(flows) * segment_min, schedule['water_l'], abs_tol=1e-8):
        raise ValueError('Accepted schedule volume does not match its flow record')
    # Legacy run_extended.py computes robust_tolerance for the 0.1 C
    # buffer only; it does not store a general policy-tagged tolerance table.
    buffered = next(row for row in extended['control']['buffer_price']
                    if row['buffer_c'] == .1)
    if buffered['flow_lpm'] != flows:
        raise ValueError('Tap-error evidence belongs to a different buffered policy')
    rows = structure['rows']
    scheduled = {(row['route'], row['body_capacity_j_per_k'] is not None): row
                 for row in rows if row['policy'] == 'scheduled'}
    base = scheduled['surface', False]
    body = scheduled['surface', True]
    deep = scheduled['deep', False]
    return {
        'water_volume_l': 1000 * (p['L'] * p['W'] * p['H'] - p['body_volume']),
        'horizon_min': p['horizon'] / 60,
        'segment_min': segment_min,
        'flow_rates_text': ', '.join('0' if abs(v) < .5e-9 else f'{v:.9f}' for v in flows),
        'rejected_finest_spread_c': mesh['schedule_replayed']['meshes'][-1]['max_span'],
        'tap_error_share': extended['control']['robust_tolerance']['random_error']['0.10']['share_within_limits'],
        'body_capacity_kj_per_k': body['body_capacity_j_per_k'] / 1000,
        'body_minimum_change_c': body['min_temp'] - base['min_temp'],
        'deep_spread_change_c': deep['max_span'] - base['max_span'],
        'final_body_temp_c': body['final_body_temp_c'],
        'all_structures_sampled_passed': all(row['sampled_passed'] for row in rows),
        'structure_max_time_delta_c': max(row['step_check_delta_c'] for row in rows),
        'structure_max_instantaneous_w': max(row['instantaneous_balance_residual_w'] for row in rows),
        'structure_max_integrated_j': max(row['integrated_balance_residual_j'] for row in rows),
    }
