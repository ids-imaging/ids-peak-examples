param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

function Run-ExamplesInFolder {
    param([string]$Root)

    Get-ChildItem -Path $Root -Recurse -File -Filter *.exe |
        Where-Object {
            $_.DirectoryName -like "*_from_file*" -or
            $_.DirectoryName -like "morphology"
        } |
        ForEach-Object {
            Write-Host "Starting $($_.FullName)"
            & $_.FullName
            if ($LASTEXITCODE) {
                throw "Example at '$($_.FullName)' failed with exit code $LASTEXITCODE"
            }
        }
}

# Validate directory
if (-not (Test-Path $Path -PathType Container)) {
    Write-Host "Error: '$Path' is not a valid directory."
    exit 1
}

Run-ExamplesInFolder -Root $Path
