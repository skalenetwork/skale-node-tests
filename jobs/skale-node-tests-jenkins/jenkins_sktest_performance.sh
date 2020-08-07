#!/bin/bash

pwd
source ./jobs/venv/bin/activate
"$@"

pytest -vs sktest_performance.py
