#! /usr/bin/env bash

script_path="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

# " <- extra double quote to fix incorect parsing nested double quotes in previous command by some editors


# full path to prevent killing any other bots with `bot.py` main script
run_command="python3 ${script_path}/mutex_bot.py"

pkill -f "${run_command}"

pushd "${script_path}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source ./venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install .

nohup "${run_command}" &

popd
