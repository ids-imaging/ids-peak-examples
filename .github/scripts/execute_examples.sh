#!/bin/bash
set -e

function runExamplesInFolder()
{
  while IFS= read -r -d '' example; do
    echo "Starting $example"

    set +e
    "$example"
    exit_code=$?
    set -e

    if [ $exit_code -ne 0 ]; then
      echo "Error: example at '$example' failed with exit code $exit_code"
      exit $exit_code
    fi

  done < <(
    find "$1" \( \
      -path "*/*_from_file/*" -o \
      -path "*/morphology/*" \
      \) -type f -executable -print0
    )
}


if [[ ! -d "$1" ]]; then
  echo "Error: '$1' is not a valid directory."
  return 1
fi

echo "Search for executable examples in $1"
runExamplesInFolder "$1"
