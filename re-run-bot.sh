#! /usr/bin/env bash

script_path="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

pkill -f "${run_command}"

pushd "${script_path}"

if [ ! -d "venv" ]; then
    if ! command -v python3.7 &> /dev/null
    then
        python3.7 -m venv venv
    else
        python3 -m venv venv
    fi
fi

source ./venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install .


nohup mutex_bot &

popd
