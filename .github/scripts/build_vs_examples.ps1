param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ids_peak="C:\Program Files\IDS\ids_peak\"
$env:IDS_PEAK_GENERIC_SDK_PATH="$ids_peak\generic_sdk"
$env:ids_peak_DIR="$IDS_PEAK_GENERIC_SDK_PATH\api\lib\x86_64\cmake\"
$env:ids_peak_icv_DIR="$IDS_PEAK_GENERIC_SDK_PATH\icv\lib\x86_64\cmake\"
$env:ids_peak_afl_DIR="$IDS_PEAK_GENERIC_SDK_PATH\afl\lib\x86_64\cmake\"
$env:ids_peak_ipl_DIR="$IDS_PEAK_GENERIC_SDK_PATH\ipl\lib\x86_64\cmake\"
$env:ids_peak_common_DIR="$ids_peak\common\lib\cmake\"

# Validate that the path exists and is a directory
if (-not (Test-Path $Path -PathType Container)) {
    Write-Host "Error: '$Path' is not a valid directory."
    exit 1
}

# Go through every subdirectory
Get-ChildItem -Path $Path -Directory -Recurse | ForEach-Object {
    $dir = $_.FullName

    # Check if this directory contains a .vcxproj file
    $vcxproj = Get-ChildItem -Path $dir -Filter *.vcxproj -File -ErrorAction SilentlyContinue

    if ($vcxproj) {
        MSBuild $dir /p:ClOptions="/W4 /WX" /p:Configuration=Release /p:Platform=x64 | Out-String
    }
}
