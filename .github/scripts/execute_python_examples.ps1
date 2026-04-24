
$Root = "python"

if (-not (Test-Path $Root -PathType Container)) {
Write-Host "No python examples found"
exit 0
}

Get-ChildItem -Path $Root -Recurse -Directory |
Where-Object { $_.FullName -like "*_from_file" } |
ForEach-Object {
  $exampleDir = $_.FullName
  Write-Host "=============================="
  Write-Host "Running example: $exampleDir"

  $venvPath = Join-Path $exampleDir ".venv"

  python -m venv $venvPath
  & "$venvPath\Scripts\Activate.ps1"

  pip install --upgrade pip --disable-pip-version-check
  pip install -r (Join-Path $exampleDir "requirements.txt")

  $mainPy = Join-Path $exampleDir "main.py"

  if (Test-Path $mainPy) {
    python $mainPy
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
      Write-Error "Error: example at '$mainPy' failed with exit code $exitCode"
      exit $exitCode
    }
  }
  else {
    Write-Error "Error: No main.py in $exampleDir"
    exit 1
  }

  deactivate
}
