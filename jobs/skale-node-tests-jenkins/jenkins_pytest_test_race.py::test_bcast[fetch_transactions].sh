#!/bin/bash

source ./jobs/venv/bin/activate
"$@"

pytest -v test_race.py::test_bcast[fetch_transactions]
