#!/bin/sh

. ~/miniconda3/etc/profile.d/conda.sh
conda activate aee
cd /mnt/tank/scratch/aartamonov/AutoEvoExtractor

export PYTHONUNBUFFERED=1

python scripts/optimize.py --config config/systems/pilot.yaml