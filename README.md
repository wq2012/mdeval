# NIST md-eval in Python

[![Python Package](https://github.com/wq2012/mdeval/actions/workflows/python-package.yml/badge.svg)](https://github.com/wq2012/mdeval/actions/workflows/python-package.yml)
[![PyPI Version](https://img.shields.io/pypi/v/mdeval.svg)](https://pypi.python.org/pypi/mdeval)
[![Python Versions](https://img.shields.io/pypi/pyversions/mdeval.svg)](https://pypi.org/project/mdeval)
[![Downloads](https://static.pepy.tech/badge/mdeval)](https://pepy.tech/project/mdeval)

A Python implementation of the NIST `md-eval.pl` script for evaluating rich transcription and speaker diarization accuracy. This tool mimics the core functionality and scoring logic of the standard Perl script used in NIST evaluations (e.g., RT-0x), focusing on Diarization Error Rate (DER).

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
  - [Command Line Interface](#command-line-interface)
  - [Python API](#python-api)
- [Input Formats](#input-formats)
  - [RTTM (Rich Transcription Time Marked)](#rttm-rich-transcription-time-marked)
  - [UEM (Un-partitioned Evaluation Map)](#uem-un-partitioned-evaluation-map)
- [Core Algorithms](#core-algorithms)
  - [Scoring Logic](#scoring-logic)
  - [Optimal Speaker Mapping](#optimal-speaker-mapping)
  - [Collars](#collars)
  - [Overlap Exclusion](#overlap-exclusion)
- [Testing](#testing)
- [Citation](#citation)

## Overview

`mdeval` calculates the Diarization Error Rate (DER) by comparing a system hypothesis (SYS) against a ground truth reference (REF). It supports:
- **Missed Speech**: Speech present in REF but not in SYS.
- **False Alarm**: Speech present in SYS but not in REF.
- **Speaker Error**: Speech assigned to the wrong speaker (after optimal mapping).
- **Collars**: Optional no-score zones around reference segment boundaries.
- **Overlap handling**: Option to exclude regions where multiple reference speakers talk simultaneously.

The goal is to provide a pure Python, dependency-free (or minimal dependency) alternative to the legacy Perl script for modern pipelines.

## Installation

You can install the package via pip:

```bash
pip install mdeval
```

## Usage

### Command Line Interface

The package provides a CLI entry point `mdeval`.

```bash
python3 -m mdeval.cli -r <ref_rttm> -s <sys_rttm> [options]
```

**Arguments:**

- `-r, --ref`: Path to the Reference RTTM file (Required).
- `-s, --sys`: Path to the System/Hypothesis RTTM file (Required).
- `-u, --uem`: Path to the UEM file defining evaluation regions (Optional. If omitted, the valid region is inferred from the Reference RTTM).
- `-c, --collar`: Collar size in seconds (Float, default: 0.0). A "no-score" zone of +/- `collar` seconds is applied around every reference segment boundary.
- `-1, --single-speaker`: Limit scoring to single-speaker regions only (ignore overlaps in REF). This is equivalent to "Overlap Exclusion".

**Example:**

```bash
python3 -m mdeval.cli -r ref.rttm -s hyp.rttm -c 0.25
```

### Python API

You can use the scoring logic programmatically:

```python
from mdeval.io import load_rttm, load_uem
from mdeval.scoring import score_speaker_diarization
from mdeval.utils import Segment

# Load Data
ref_data = load_rttm('ref.rttm')
sys_data = load_rttm('sys.rttm')

# Define Evaluation Map (or infer it)
# uem_eval = [Segment(0.0, 100.0)]
# Or load:
# uem_data = load_uem('test.uem')
# uem_eval = uem_data['file1']['1']

# Parse specific file/channel data
ref_spkrs = {} # ... extract from ref_data['file1']['1']['SPEAKER']
sys_spkrs = {} # ... extract from sys_data['file1']['1']['SPEAKER']

# Score
stats, mapping = score_speaker_diarization(
    'file1', '1', 
    ref_spkrs, sys_spkrs, 
    uem_eval, 
    collar=0.25, 
    ignore_overlap=False
)

print(f"DER: {stats['MISSED_SPEAKER'] + stats['FALARM_SPEAKER'] + stats['SPEAKER_ERROR']}")
```

## Input Formats

### RTTM (Rich Transcription Time Marked)

Format used for both Reference and System inputs.
Space-delimited text file. Lines starting with `;` or `#` are ignored.

**Required Columns (indices 0-8):**

1.  **TYPE**: Segment type (must be `SPEAKER` to be scored).
2.  **FILE**: File name / Recording ID.
3.  **CHNL**: Channel ID (e.g., `1`).
4.  **TBEG**: Start time in seconds (float).
5.  **TDUR**: Duration in seconds (float).
6.  **ORTHO**: Orthography field (ignored/placeholder, e.g., `<NA>`).
7.  **STYPE**: Subtype (ignored/placeholder, e.g., `<NA>`).
8.  **NAME**: Speaker Name/ID.
9.  **CONF**: Confidence score (ignored/placeholder, e.g., `<NA>`).

**Example:**
```
SPEAKER file1 1 0.00 5.00 <NA> <NA> spk1 <NA> <NA>
SPEAKER file1 1 5.00 3.00 <NA> <NA> spk2 <NA> <NA>
```

### UEM (Un-partitioned Evaluation Map)

Defines the time regions that should be evaluated. Regions outside the UEM are ignored.
Space-delimited text file.

**Required Columns:**

1.  **FILE**: File name.
2.  **CHNL**: Channel ID.
3.  **TBEG**: Start time of valid region.
4.  **TEND**: End time of valid region.

**Example:**
```
file1 1 0.00 100.00
file1 1 120.00 300.00
```

## Core Algorithms

### Scoring Logic

The scoring is segment-based (time-weighted).
1.  **Metric**: Diarization Error Rate (DER).
    $$ DER = \frac{\text{Missed Speaker Time} + \text{False Alarm Speaker Time} + \text{Speaker Error Time}}{\text{Total Scored Speaker Time}} $$
2.  **Segmentation**: The timeline is split into contiguous segments where the set of reference and system speakers remains constant.
3.  **Intersection**: For each segment, the number of reference speakers ($N_{ref}$) and system speakers ($N_{sys}$) is compared.

### Optimal Speaker Mapping

Since System speaker labels (e.g., "sys01") do not match Reference labels (e.g., "spk01"), a global 1-to-1 mapping is computed to minimize error.
-   We compute an overlap matrix between every reference speaker and every system speaker over the entire valid UEM duration.
-   The **Hungarian Algorithm** (implemented purely in Python, no `scipy` dependency required) is used to find the optimal assignment that maximizes total overlap time.

### Collars

When `collar > 0`, a "no-score" zone is applied.
-   For every segment boundary in the **Reference** RTTM, a region of $t \pm collar$ is removed from the UEM.
-   This accounts for human annotation uncertainty boundaries.
-   **Note**: The Python implementation follows the logic of `md-eval.pl`'s `add_collars_to_uem` subroutine, using a counter-based approach to subtract the union of all collar regions from the scoring UEM.

### Overlap Exclusion

If enabled (via `-1` / `--single-speaker`), regions where **two or more** Reference speakers are speaking simultaneously are removed from the UEM.
-   This allows evaluation of systems that only output single-speaker segments.
-   **Note**: Overlap exclusion is applied *before* collars in the perl script logic, but effectively they both just subtract time from the valid UEM.

## Testing

The package includes unit tests using Python's `unittest` framework.

Run tests via:
```bash
python3 -m unittest discover tests
```

## Citation

We developed this package as part of the following work:

```
@inproceedings{wang2018speaker,
  title={{Speaker Diarization with LSTM}},
  author={Wang, Quan and Downey, Carlton and Wan, Li and Mansfield, Philip Andrew and Moreno, Ignacio Lopz},
  booktitle={2018 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP)},
  pages={5239--5243},
  year={2018},
  organization={IEEE}
}

@inproceedings{xia2022turn,
  title={{Turn-to-Diarize: Online Speaker Diarization Constrained by Transformer Transducer Speaker Turn Detection}},
  author={Wei Xia and Han Lu and Quan Wang and Anshuman Tripathi and Yiling Huang and Ignacio Lopez Moreno and Hasim Sak},
  booktitle={2022 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP)},
  pages={8077--8081},
  year={2022},
  organization={IEEE}
}

@article{wang2022highly,
  title={Highly Efficient Real-Time Streaming and Fully On-Device Speaker Diarization with Multi-Stage Clustering},
  author={Quan Wang and Yiling Huang and Han Lu and Guanlong Zhao and Ignacio Lopez Moreno},
  journal={arXiv:2210.13690},
  year={2022}
}
```
