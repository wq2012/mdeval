import argparse
import sys
import os
from typing import List
from .io import load_rttm, load_uem
from .scoring import score_speaker_diarization
from .utils import Segment

def main():
    parser = argparse.ArgumentParser(description='Python implementation of NIST md-eval.pl')
    parser.add_argument('-r', '--ref', required=True, help='Reference RTTM file')
    parser.add_argument('-s', '--sys', required=True, help='System RTTM file')
    parser.add_argument('-u', '--uem', help='UEM file (Evaluation Partition)')
    parser.add_argument('-c', '--collar', type=float, default=0.0, help='No-score collar around reference boundaries (seconds)')
    parser.add_argument('-1', '--single-speaker', action='store_true', dest='single_speaker', help='Limit scoring to single-speaker regions')
    # Add other flags as needed
    
    args = parser.parse_args()
    
    # Load Data
    ref_data = load_rttm(args.ref)
    sys_data = load_rttm(args.sys)
    
    uem_data = None
    if args.uem:
        uem_data = load_uem(args.uem)
    
    # Process each file found in REF
    files = sorted(ref_data.keys())
    
    # Accumulate global scores
    total_stats = {
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
        'SCORED_WORDS': 0, # Placeholder
        'EVAL_WORDS': 0
    }
    
    # TODO: Output header matching md-eval.pl
    
    for file in files:
        if file not in sys_data:
            print(f"Warning: File {file} found in REF but not in SYS. Skipping.", file=sys.stderr)
            continue
            
        chnls = sorted(ref_data[file].keys())
        for chnl in chnls:
            if chnl not in sys_data[file]:
                print(f"Warning: Channel {chnl} for file {file} found in REF but not in SYS. Skipping.", file=sys.stderr)
                continue
                
            # Determine UEM
            if uem_data and file in uem_data and chnl in uem_data[file]:
                uem_eval = uem_data[file][chnl]
            else:
                # Infer UEM from REF RTTM (min TBEG, max TEND)
                min_t = 1e30
                max_t = 0
                found_seg = False
                for seg in ref_data[file][chnl]['SPEAKER']:
                    min_t = min(min_t, seg['TBEG'])
                    max_t = max(max_t, seg['TEND'])
                    found_seg = True
                if not found_seg:
                    # Try other types? For now just SPEAKER
                    pass
                if max_t > min_t:
                    uem_eval = [Segment(min_t, max_t)]
                else:
                    uem_eval = []

            # Determine REF/SYS inputs
            # Group by speaker
            # Expected format for scoring: {spkr: [{TBEG, TDUR, TEND, ...}]}
            curr_ref = {}
            for seg in ref_data[file][chnl]['SPEAKER']:
                s = seg['SPKR']
                if s not in curr_ref: curr_ref[s] = []
                curr_ref[s].append(seg)
                
            curr_sys = {}
            if 'SPEAKER' in sys_data[file][chnl]:
                for seg in sys_data[file][chnl]['SPEAKER']:
                    s = seg['SPKR']
                    if s not in curr_sys: curr_sys[s] = []
                    curr_sys[s].append(seg)
            
            file_stats, _ = score_speaker_diarization(file, chnl, curr_ref, curr_sys, uem_eval, args.collar, args.single_speaker)
            
            # Add to totals
            for k in total_stats:
                if k in file_stats:
                    total_stats[k] += file_stats[k]
    
    # Print simplified output
    print_scores("ALL", total_stats)

def print_scores(condition, scores):
    print(f"\n*** Performance analysis for Speaker Diarization for {condition} ***\n")
    
    def p(val): return val
    
    eval_time = scores['EVAL_TIME']
    eval_speech = scores['EVAL_SPEECH']
    scored_time = scores['SCORED_TIME']
    scored_speech = scores['SCORED_SPEECH']
    
    print(f"    EVAL TIME = {eval_time:10.2f} secs")
    print(f"  EVAL SPEECH = {eval_speech:10.2f} secs ({100*eval_speech/eval_time if eval_time else 0:5.1f} percent of evaluated time)")
    print(f"  SCORED TIME = {scored_time:10.2f} secs ({100*scored_time/eval_time if eval_time else 0:5.1f} percent of evaluated time)")
    print(f"SCORED SPEECH = {scored_speech:10.2f} secs ({100*scored_speech/scored_time if scored_time else 0:5.1f} percent of scored time)")
    print(f"   EVAL WORDS = {scores['EVAL_WORDS']:7d}        ")
    print(f" SCORED WORDS = {scores['SCORED_WORDS']:7d}         (100.0 percent of evaluated words)")
    print("---------------------------------------------")
    print(f"MISSED SPEECH = {scores['MISSED_SPEECH']:10.2f} secs ({100*scores['MISSED_SPEECH']/scored_time if scored_time else 0:5.1f} percent of scored time)")
    print(f"FALARM SPEECH = {scores['FALARM_SPEECH']:10.2f} secs ({100*scores['FALARM_SPEECH']/scored_time if scored_time else 0:5.1f} percent of scored time)")
    print(f" MISSED WORDS =       0         (100.0 percent of scored words)")
    print("---------------------------------------------")
    print(f"SCORED SPEAKER TIME = {scores['SCORED_SPEAKER']:10.2f} secs ({100*scores['SCORED_SPEAKER']/scored_speech if scored_speech else 0:5.1f} percent of scored speech)")
    print(f"MISSED SPEAKER TIME = {scores['MISSED_SPEAKER']:10.2f} secs ({100*scores['MISSED_SPEAKER']/scores['SCORED_SPEAKER'] if scores['SCORED_SPEAKER'] else 0:5.1f} percent of scored speaker time)")
    print(f"FALARM SPEAKER TIME = {scores['FALARM_SPEAKER']:10.2f} secs ({100*scores['FALARM_SPEAKER']/scores['SCORED_SPEAKER'] if scores['SCORED_SPEAKER'] else 0:5.1f} percent of scored speaker time)")
    print(f" SPEAKER ERROR TIME = {scores['SPEAKER_ERROR']:10.2f} secs ({100*scores['SPEAKER_ERROR']/scores['SCORED_SPEAKER'] if scores['SCORED_SPEAKER'] else 0:5.1f} percent of scored speaker time)")
    print(f"SPEAKER ERROR WORDS =       0         (100.0 percent of scored speaker words)")
    print("---------------------------------------------")
    der = (scores['MISSED_SPEAKER'] + scores['FALARM_SPEAKER'] + scores['SPEAKER_ERROR']) / scores['SCORED_SPEAKER'] if scores['SCORED_SPEAKER'] else 0
    print(f" OVERALL SPEAKER DIARIZATION ERROR = {100*der:5.2f} percent of scored speaker time  `({condition})")
    print("---------------------------------------------")

if __name__ == '__main__':
    main()
