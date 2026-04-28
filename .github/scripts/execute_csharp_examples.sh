#!/bin/bash
set -e

function runExamplesInFolder()
{
  while IFS= read -r -d '' csproj; do
    echo "Starting dotnet run for $csproj"

    set +e
    dotnet run --project "$csproj"
    exit_code=$?
    set -e

    if [ $exit_code -ne 0 ]; then
      echo "Error: project '$csproj' failed with exit code $exit_code"
      exit $exit_code
    fi

  done < <(
    find "$1" \( \
      -path "*/*FromFile/*" -o \
      -path "*/Morphology/*" \
    \) \
    -type f \
    -name "*.csproj" \
    ! -name "*Framework*" \
    -print0
  )
}

if [[ ! -d "$1" ]]; then
  echo "Error: '$1' is not a valid directory."
  return 1
fi

echo "Search for executable examples in $1"
runExamplesInFolder "$1"
