#!/bin/bash

set -o errexit
set -o verbose

# build requirements.txt from setup.py
.env/bin/python -m piptools compile setup.py --extra dev 
# Install ckd project dependencies
.env/bin/python -m pip install -r requirements.txt
# compile runtime requirements
# pip-compile -r ./orchestration/runtime/mwaa/requirements.in
# pip-compile -r ./batch/runtime/tablelineage/requirements.in