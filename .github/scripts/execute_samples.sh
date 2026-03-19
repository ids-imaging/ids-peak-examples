#!/bin/bash

function runSamplesInFolder()
{
  find "$1" -type f -executable -path "*/*_from_file/*" | while read -r sample; do
    if [[ ! "$sample" =~ \..+$ ]]; then
      echo "Starting $sample"
      "$sample"
    fi
  done
}


if [[ ! -d "$1" ]]; then
  echo "Error: '$1' is not a valid directory."
  return 1
fi

echo "Search for executable samples in $1"
runSamplesInFolder $1
