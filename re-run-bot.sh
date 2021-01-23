run_file="mutex_bot.py"
venv_dir="../mutex_bot_venv"

pkill -f "python3 ${run_file}"

if [ ! -d "${venv_dir}" ]; then
    echo "create virtual env in ${venv_dir}"
    python3 -m venv ${venv_dir}
    pip install --upgrade pip setuptools wheel
fi

if [ -d ${venv_dir} ]; then
    source "${venv_dir}/bin/activate"
    # pip install .
    python3 ${run_file}
else
    echo "no virtual env"
fi