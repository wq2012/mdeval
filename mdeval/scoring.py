from typing import Dict, List, Any, Tuple, Optional

from .utils import Segment
from .munkres import linear_sum_assignment

def map_speakers(spkr_overlap: Dict[str, Dict[str, float]]) -> Dict[str, str]:
    """
    Find optimal mapping between ref and sys speakers to maximize overlap duration.
    Uses Hungarian algorithm (scipy.optimize.linear_sum_assignment).
    """
    if not spkr_overlap:
        return {}

    ref_spkrs = sorted(list(spkr_overlap.keys()))
    sys_spkrs = set()
    for r in ref_spkrs:
        sys_spkrs.update(spkr_overlap[r].keys())
    sys_spkrs = sorted(list(sys_spkrs))

    if not ref_spkrs or not sys_spkrs:
        return {}

    # Cost matrix: negative overlap (since we want to maximize overlap)
    cost_matrix = [[0.0] * len(sys_spkrs) for _ in range(len(ref_spkrs))]
    for i, r in enumerate(ref_spkrs):
        for j, s in enumerate(sys_spkrs):
            cost_matrix[i][j] = -spkr_overlap[r].get(s, 0.0)

    # Solve bipartite matching
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    mapping = {}
    for r_idx, s_idx in zip(row_ind, col_ind):
        mapping[ref_spkrs[r_idx]] = sys_spkrs[s_idx]

    return mapping

def create_speaker_segs(uem_score, ref_data, sys_data):
    events = []
    # UEM events
    for uem in uem_score:
        if uem.tdur > 1e-8:
            events.append({'TYPE': 'UEM', 'EVENT': 'BEG', 'TIME': uem.tbeg})
            events.append({'TYPE': 'UEM', 'EVENT': 'END', 'TIME': uem.tend})
    
    # Ref events
    for spkr, segs in ref_data.items():
        for seg in segs:
            if seg['TDUR'] > 0:
                events.append({'TYPE': 'REF', 'SPKR': spkr, 'EVENT': 'BEG', 'TIME': seg['TBEG']})
                events.append({'TYPE': 'REF', 'SPKR': spkr, 'EVENT': 'END', 'TIME': seg['TEND']})
                
    # Sys events
    for spkr, segs in sys_data.items():
        for seg in segs:
            if seg['TDUR'] > 0:
                events.append({'TYPE': 'SYS', 'SPKR': spkr, 'EVENT': 'BEG', 'TIME': seg['TBEG']})
                events.append({'TYPE': 'SYS', 'SPKR': spkr, 'EVENT': 'END', 'TIME': seg['TEND']})

    # Sort events
    # Sort order: time ascending. If times equal, END comes before BEG.
    epsilon = 1e-8
    def sort_key(e):
        # Primary: Time
        # Secondary: END < BEG (0 < 1 if we map END=0, BEG=1)
        type_order = 0 if e['EVENT'] == 'END' else 1
        return (e['TIME'], type_order)

    events.sort(key=sort_key)

    segments = []
    current_ref = {}
    current_sys = {}
    
    evaluate = False
    tbeg = 0.0
    
    for event in events:
        time = event['TIME']
        
        # If we were evaluating and time has advanced, emit segment
        if evaluate and time > tbeg + epsilon:
            tend = time
            segments.append({
                'REF': current_ref.copy(),
                'SYS': current_sys.copy(),
                'TBEG': tbeg,
                'TEND': tend,
                'TDUR': tend - tbeg
            })
            tbeg = tend
            
        if event['TYPE'] == 'UEM':
            evaluate = (event['EVENT'] == 'BEG')
            if evaluate:
                tbeg = time
        elif event['TYPE'] == 'REF':
            if event['EVENT'] == 'BEG':
                current_ref[event['SPKR']] = current_ref.get(event['SPKR'], 0) + 1
            else:
                if event['SPKR'] in current_ref:
                    current_ref[event['SPKR']] -= 1
                    if current_ref[event['SPKR']] <= 0:
                        del current_ref[event['SPKR']]
        elif event['TYPE'] == 'SYS':
            if event['EVENT'] == 'BEG':
                current_sys[event['SPKR']] = current_sys.get(event['SPKR'], 0) + 1
            else:
                if event['SPKR'] in current_sys:
                    current_sys[event['SPKR']] -= 1
                    if current_sys[event['SPKR']] <= 0:
                        del current_sys[event['SPKR']]
                        
    return segments

def exclude_overlapping_speech(uem_data: List[Segment], ref_data: Dict[str, List[Dict]]) -> List[Segment]:
    # Gather all speaker segments
    spkr_events = []
    for spkr, segs in ref_data.items():
        for seg in segs:
            if seg['TDUR'] > 0:
                spkr_events.append({'EVENT': 'BEG', 'TIME': seg['TBEG']})
                spkr_events.append({'EVENT': 'END', 'TIME': seg['TEND']})
                
    spkr_events.sort(key=lambda x: (x['TIME'], 1 if x['EVENT'] == 'BEG' else 0))
    # Sort events: Time ascending. If times equal, BEG after END.
    spkr_events.sort(key=lambda x: (x['TIME'], 1 if x['EVENT'] == 'BEG' else 0))
    
    # Find overlap regions (spkr_cnt >= 2)
    overlap_regions = []
    spkr_cnt = 0
    tbeg_overlap = 0.0
    
    for event in spkr_events:
        if event['EVENT'] == 'BEG':
            spkr_cnt += 1
            if spkr_cnt == 2:
                tbeg_overlap = event['TIME']
        else: # END
            spkr_cnt -= 1
            if spkr_cnt == 1:
                # End of overlap
                # End of overlap
                if event['TIME'] > tbeg_overlap:
                    overlap_regions.append({'BEG': tbeg_overlap, 'END': event['TIME']})
                    
    # Now exclude these regions from UEM
    # UEM events: BEG, END
    # Overlap "events": NSZ BEG, NSZ END.
    # We want UEM and NOT NSZ.
    
    events = []
    for uem in uem_data:
        events.append({'TYPE': 'UEM', 'EVENT': 'BEG', 'TIME': uem.tbeg})
        events.append({'TYPE': 'UEM', 'EVENT': 'END', 'TIME': uem.tend})
    
    for ov in overlap_regions:
        events.append({'TYPE': 'NSZ', 'EVENT': 'BEG', 'TIME': ov['BEG']})
        events.append({'TYPE': 'NSZ', 'EVENT': 'END', 'TIME': ov['END']})
        
    # Sort events.
    # Sort events.
    events.sort(key=lambda x: (x['TIME'], 1 if x['EVENT'] == 'BEG' else 0))
    
    new_uem = []
    evl_cnt = 0 # UEM count
    nsz_cnt = 0 # Overlap count
    evaluating = False
    tbeg = 0.0
    epsilon = 1e-8
    
    effective_exclusion = 0.0
    last_t = events[0]['TIME'] if events else 0.0
    
    for event in events:
        cur_t = event['TIME']
        if nsz_cnt > 0 and evl_cnt > 0:
             effective_exclusion += (cur_t - last_t)
        last_t = cur_t
        
        if event['TYPE'] == 'UEM':
            evl_cnt += 1 if event['EVENT'] == 'BEG' else -1
        else: # NSZ
            nsz_cnt += 1 if event['EVENT'] == 'BEG' else -1
            
        # Decision logic
        # Evaluating if evl_cnt > 0 and nsz_cnt == 0
        
        # Check transition
        is_eval_zone = (evl_cnt > 0 and nsz_cnt == 0)
        
        if evaluating:
            if not is_eval_zone:
                if event['TIME'] > tbeg:
                    new_uem.append(Segment(tbeg, event['TIME']))
                evaluating = False
        elif is_eval_zone:
            tbeg = event['TIME']
            evaluating = True
            
    return new_uem

def score_speaker_diarization(file, chnl, ref_data, sys_data, uem_eval, collar=0.0, ignore_overlap=False):
    stats = {
        'EVAL_TIME': 0.0,
        'EVAL_SPEECH': 0.0,
        'SCORED_TIME': 0.0,
        'SCORED_SPEECH': 0.0,
        'MISSED_SPEECH': 0.0,
        'FALARM_SPEECH': 0.0,
        'SCORED_SPEAKER': 0.0,
        'MISSED_SPEAKER': 0.0,
        'FALARM_SPEAKER': 0.0,
        'SPEAKER_ERROR': 0.0,
        'SCORED_WORDS': 0,
        'EVAL_WORDS': 0,
        'MISSED_WORDS': 0,
        'ERROR_WORDS': 0
    }
    
    # Helper to sum up UEM duration
    def sum_uem(uems):
        return sum(s.tdur for s in uems)

    stats['EVAL_TIME'] = sum_uem(uem_eval)
    
    # 1. Map Speakers using full or filtered UEM
    uem_score = uem_eval
    if ignore_overlap:
        uem_score = exclude_overlapping_speech(uem_score, ref_data)
        
    if collar > 0:
        uem_score = apply_collars(uem_score, ref_data, collar)
        
    start_eval_time = sum_uem(uem_eval) # Stats track EVAL_TIME based on original UEM

    # Create segments for mapping AND final scoring
    eval_segs = create_speaker_segs(uem_score, ref_data, sys_data)
    
    spkr_overlap = {} # {ref_spkr: {sys_spkr: overlap_time}}
    
    stats['SCORED_TIME'] = sum_uem(uem_score)
    
    for seg in eval_segs:
        # Accumulate overlap for mapping
        dur = seg['TDUR']
        for r_spkr in seg['REF']:
            if r_spkr not in spkr_overlap:
                spkr_overlap[r_spkr] = {}
            for s_spkr in seg['SYS']:
                spkr_overlap[r_spkr][s_spkr] = spkr_overlap[r_spkr].get(s_spkr, 0.0) + dur

    spkr_map = map_speakers(spkr_overlap)
    
    # Calculate stats
    for seg in eval_segs:
        dur = seg['TDUR']
        n_ref = len(seg['REF'])
        n_sys = len(seg['SYS'])
        
        if n_ref > 0:
            stats['SCORED_SPEECH'] += dur
        
        if n_ref > 0 and n_sys == 0:
            stats['MISSED_SPEECH'] += dur
        if n_sys > 0 and n_ref == 0:
            stats['FALARM_SPEECH'] += dur
            
        stats['SCORED_SPEAKER'] += dur * n_ref
        stats['MISSED_SPEAKER'] += dur * max(n_ref - n_sys, 0)
        stats['FALARM_SPEAKER'] += dur * max(n_sys - n_ref, 0)
        
        # Speaker error
        n_map = 0
        for r_spkr in seg['REF']:
            mapped_sys = spkr_map.get(r_spkr)
            if mapped_sys and mapped_sys in seg['SYS']:
                n_map += 1
        
        stats['SPEAKER_ERROR'] += dur * (min(n_ref, n_sys) - n_map)
        
    # We need to calculate EVAL_SPEECH correctly (on original UEM).
    # Simple way: create segs on uem_eval (without collars/overlap exclusion) just for this stat?
    # Or just iterate ref_data and intersect with uem_eval.
    # Since we need to be exact, let's do create_speaker_segs on uem_eval if different.
    
    if uem_score != uem_eval:
        raw_segs = create_speaker_segs(uem_eval, ref_data, sys_data)
        for seg in raw_segs:
             if len(seg['REF']) > 0:
                 stats['EVAL_SPEECH'] += seg['TDUR']
    else:
        stats['EVAL_SPEECH'] = stats['SCORED_SPEECH']
        pass

    return stats, spkr_map

def apply_collars(uem_eval: List[Segment], ref_data: Dict[str, List[Dict]], collar: float, max_extend: float = 0.0) -> List[Segment]:
    """
    Apply collars to UEM.
    Subtracts regions around reference boundaries from the UEM.
    """
    
    events = []
    
    # 1. UEM Events
    for uem in uem_eval:
        events.append({'EVENT': 'BEG', 'TIME': uem.tbeg})
        events.append({'EVENT': 'END', 'TIME': uem.tend})
        
    # 2. Collar Events (Inverted)
    if collar > 0:
        for spkr, segs in ref_data.items():
            for seg in segs:
                # Start Exclusion (END event)
                events.append({'EVENT': 'END', 'TIME': seg['TBEG'] - collar})
                # End Exclusion (BEG event)
                events.append({'EVENT': 'BEG', 'TIME': seg['TBEG'] + collar})
                
                # Start Exclusion (END event) around TEND
                events.append({'EVENT': 'END', 'TIME': seg['TEND'] - collar})
                # End Exclusion (BEG event) around TEND
                events.append({'EVENT': 'BEG', 'TIME': seg['TEND'] + collar})
                
    # Sort
    # We want BEG < END.
    events.sort(key=lambda x: (x['TIME'], 0 if x['EVENT'] == 'BEG' else 1))
    
    new_uem = []
    evaluate = 0
    tbeg = 0.0
    epsilon = 1e-8
    
    for event in events:
        time = event['TIME']
        if event['EVENT'] == 'BEG':
            evaluate += 1
            if evaluate == 1:
                tbeg = time
        else: # END
            evaluate -= 1
            if evaluate == 0:
                if time > tbeg + epsilon:
                     new_uem.append(Segment(tbeg, time))
                     
    return new_uem
