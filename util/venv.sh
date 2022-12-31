#!/bin/bash
base_dir=$(dirname $(dirname $(realpath "$0")))
python3 -m venv "${base_dir}/.venv"
source "${base_dir}/.venv/bin/activate"
pip install -r "${base_dir}/requirements.txt"
