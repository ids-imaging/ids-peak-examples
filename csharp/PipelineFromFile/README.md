# Pipeline Example

This example demonstrates how to configure the image processing
pipeline and how to process images loaded from disk.


## Requirements

This example requires:

* **C# 8.0 or later**
* **.NET Framework 4.8** (for classic projects)
* **.NET 8** (for modern SDK-style projects)

## Build Instructions

### .NET (modern, SDK-style)

```bash
dotnet build PipelineFromFile.csproj
dotnet run --project PipelineFromFile.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 PipelineFromFile.csproj
> dotnet run   -r win-x64 --project PipelineFromFile.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild PipelineFromFileFramework.csproj /t:Restore
msbuild PipelineFromFileFramework.csproj /p:Platform=x64
```
