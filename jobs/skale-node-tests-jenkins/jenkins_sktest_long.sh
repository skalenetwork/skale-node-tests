#!/bin/bash

source ./jobs/venv/bin/activate
"$@"

pytest -sv sktest_long.py
