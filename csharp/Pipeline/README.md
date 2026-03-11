# Pipeline Example

This example demonstrates how to configure the image processing
pipeline and how to process images loaded from disk.


## Requirements

This example requires:

* **C# 8.0 or later**
* **.NET Framework 4.6.1** (for classic projects)
* **.NET 8** (for modern SDK-style projects)

## Build Instructions

### .NET (modern, SDK-style)

```bash
dotnet build Pipeline.csproj
dotnet run --project Pipeline.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 Pipeline.csproj
> dotnet run   -r win-x64 --project Pipeline.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild PipelineFramework.csproj /t:Restore
msbuild PipelineFramework.csproj /p:Platform=x64
```
