#!/bin/bash

source ./jobs/venv/bin/activate
"$@"

pytest -vs sktest_long.py
