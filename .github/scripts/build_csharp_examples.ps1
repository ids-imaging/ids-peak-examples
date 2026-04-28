$ErrorActionPreference = "Stop"

try {
    dotnet build csharp/PeakExamples.sln -c Release
    if ($LASTEXITCODE) {
        throw "Building 'PeakExamples.sln failed with exit code $LASTEXITCODE"
    }
    dotnet build csharp/PeakExamplesWindowsOnly.sln -c Release
    if ($LASTEXITCODE) {
        throw "Building 'PeakExamplesWindowsOnly.sln failed with exit code $LASTEXITCODE"
    }

    # NOTE: dotnet build does not always work with Framework projects, we use msbuild for now
    msbuild csharp\PeakExamplesFramework.sln -p:OutDir=BuildFramework -p:Platform=x64 -t:Restore
    if ($LASTEXITCODE) {
        throw "Resotring 'PeakExamplesFramework.sln failed with exit code $LASTEXITCODE"
    }
    msbuild csharp\PeakExamplesFramework.sln -p:OutDir=BuildFramework -p:Platform=x64
    if ($LASTEXITCODE) {
        throw "Building 'PeakExamplesFramework.sln failed with exit code $LASTEXITCODE"
    }
    msbuild csharp\PeakExamplesFrameworkWindowsOnly.sln -p:OutDir=BuildFramework -p:Platform=x64 -t:Restore
    if ($LASTEXITCODE) {
        throw "Restoring 'PeakExamplesFrameworkWindowsOnly.sln failed with exit code $LASTEXITCODE"
    }
    msbuild csharp\PeakExamplesFrameworkWindowsOnly.sln -p:OutDir=BuildFramework -p:Platform=x64
    if ($LASTEXITCODE) {
        throw "Building 'PeakExamplesFrameworkWindowsOnly.sln failed with exit code $LASTEXITCODE"
    }
}
catch {
    Write-Host $_
    exit $LASTEXITCODE
}
