#!/bin/bash

pwd
source ./jobs/venv/bin/activate
"$@"

pytest -v sktest_performance.py
