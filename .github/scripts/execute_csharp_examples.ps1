param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = "Stop"

function Run-ExamplesInFolder {
    param([string]$Root)

    Get-ChildItem -Path $Root -Recurse -File -Filter *.csproj |
            Where-Object {
                (
                $_.DirectoryName -like "*FromFile*" -or
                        $_.DirectoryName -like "*Morphology*"
                ) -and
                        ($_.Name -notlike "*Framework.csproj")
            }|
            ForEach-Object {
                $csproj = $_.FullName
                Write-Host "Starting dotnet run for $csproj"

                try {
                    dotnet run --project "$csproj"
                    if ($LASTEXITCODE -ne 0) {
                        throw "Error: project '$csproj' failed with exit code $LASTEXITCODE"
                    }
                }
                catch {
                    Write-Host $_
                    exit $LASTEXITCODE
                }
            }
}

# Validate directory
if (-not (Test-Path $Path -PathType Container)) {
    Write-Host "Error: '$Path' is not a valid directory."
    exit 1
}

Write-Host "Search for executable examples in $Path"
Run-ExamplesInFolder -Root $Path
