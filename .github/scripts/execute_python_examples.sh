#!/usr/bin/env bash

set -euo pipefail

ROOT="python"

if [[ ! -d "$ROOT" ]]; then
echo "No python examples found"
exit 0
fi

find "$ROOT" -type d -path "*_from_file" -o \
 -path "*morphology" | while read -r example_dir; do
echo "=============================="
echo "Running example: $example_dir"

python -m venv "$example_dir/.venv"
source "$example_dir/.venv/bin/activate"

pip install --upgrade pip --disable-pip-version-check --no-input
pip install -r "$example_dir/requirements.txt" --no-input

if [[ -f "$example_dir/main.py" ]]; then
  set +e
  python "$example_dir/main.py"
  exit_code=$?
  set -e

  if [ $exit_code -ne 0 ]; then
    echo "Error: example at '$example_dir/main.py' failed with exit code $exit_code"
    exit $exit_code
  fi
else
  echo "Error: No main.py in $example_dir"
  exit 1
fi

deactivate
done
