#!/bin/bash

source ./jobs/venv/bin/activate
"$@"

pytest -v -s sktest_sample.py
