#!/bin/bash

source ./jobs/venv/bin/activate
"$@"

pytest -v test_transaction.py::test_one_node

