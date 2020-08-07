#!/bin/bash

source ./jobs/venv/bin/activate
"$@"

pytest -v sktest_long.py
