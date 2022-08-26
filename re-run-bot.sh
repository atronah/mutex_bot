#! /usr/bin/env bash

script_path="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

echo "killing all worked instances of mutex_bot"
pkill -f "mutex_bot"

echo "changing working directory to ${script_path}"
pushd "${script_path}"

echo "resetting files to git version and loading new changes from remote repo"
git reset --hard HEAD
git pull

if [ ! -d "venv" ]; then
    echo "creating python virtual environment in ./venv"
    python3 -m venv venv
fi


echo "activating and init python virtual environment"
source ./venv/bin/activate
pip3 install --upgrade pip setuptools wheel

echo "re-installing current project"
pip3 install .

echo "running with nohup"
nohup mutex_bot &

popd
