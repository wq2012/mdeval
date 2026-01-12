import re
from typing import Dict, List, Any
from .utils import Segment

def load_rttm(file_path: str) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    data = {}
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('#'):
                continue
            parts = re.split(r'\s+', line)
            if len(parts) < 9:
                continue
            
            type_ = parts[0] # SPEAKER, LEXEME etc
            file = parts[1]
            chnl = parts[2]
            tbeg = float(parts[3])
            tdur_str = parts[4]
            tdur = 0.0 if tdur_str == '<NA>' else float(tdur_str)
            
            # parts[5] ortho
            # parts[6] subtype
            # parts[7] speaker name
            
            spkr = parts[7]
            
            if file not in data:
                data[file] = {}
            if chnl not in data[file]:
                data[file][chnl] = {'SPEAKER': [], 'LEXEME': []}
                
            entry = {
                'TYPE': type_,
                'FILE': file,
                'CHNL': chnl,
                'TBEG': tbeg,
                'TDUR': tdur,
                'TEND': tbeg + tdur,
                'SPKR': spkr,
                'SUBT': parts[6] if len(parts) > 6 else '<NA>'
            }
            
            if type_ == 'SPEAKER':
                data[file][chnl]['SPEAKER'].append(entry)
            elif type_ == 'LEXEME':
                 data[file][chnl]['LEXEME'].append(entry)
            # Add other types if needed
            
    return data

def load_uem(file_path: str) -> Dict[str, Dict[str, List[Segment]]]:
    # UEM format: FILE CHNL TBEG TEND
    data = {}
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('#'):
                continue
            parts = re.split(r'\s+', line)
            if len(parts) < 4:
                continue
            
            file = parts[0]
            chnl = parts[1]
            tbeg = float(parts[2])
            tend = float(parts[3])
            
            if file not in data:
                data[file] = {}
            if chnl not in data[file]:
                data[file][chnl] = []
                
            data[file][chnl].append(Segment(tbeg, tend))
    return data
