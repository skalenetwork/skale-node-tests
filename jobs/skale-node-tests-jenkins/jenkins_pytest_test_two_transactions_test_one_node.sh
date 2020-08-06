#!/bin/bash

source ./jobs/venv/bin/activate
"$@"

pytest -v test_two_transactions.py::test_one_node
