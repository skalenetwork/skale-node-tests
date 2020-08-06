#!/bin/bash

source ./jobs/venv/bin/activate
"$@"

pytest -v test_transaction.py::test_n_nodes[3]
