#!/bin/bash

source ./jobs/skale-ci-s-n-t_pipeline/venv/bin/activate
"$@"
cd ./jobs/skale-ci-s-n-t_pipeline/skale-node-tests

pytest -v -s sktest_snapshot.py
