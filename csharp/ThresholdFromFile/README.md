# Threshold Example

This example demonstrates how to apply a threshold to an image. The output of the threshold operation is a region, which
is a set of points. The region object may be set to the image, which will then influence further image processing
algorithms in terms of behavior and computing time. The less points a region contains, the faster will following
algorithms be (when they support region processing).

In order to visualize the region, the region is painted into the image. The resulting image is saved next to the
executable.

## Input Image

![Input Image](../../data/threshold_from_file/beads.png)

## Thresholded Image

Thresholded data in red:

![Input Image](../../doc/threshold_from_file/beads_thresholded.png)

## Requirements

This example requires:

* **C# 8.0 or later**
* **.NET Framework 4.8** (for classic projects)
* **.NET 8** (for modern SDK-style projects)

> **Note:** The C# bindings include the necessary runtime DLLs to run
> the examples. Installing the IDS peak Runtime Setup is still required
> to provide the drivers and GenTL libraries for device access.

## Build Instructions

### .NET (modern, SDK-style)

```bash
dotnet build ThresholdFromFile.csproj
dotnet run --project ThresholdFromFile.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 ThresholdFromFile.csproj
> dotnet run   -r win-x64 --project ThresholdFromFile.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild ThresholdFromFileFramework.csproj /t:Restore
msbuild ThresholdFromFileFramework.csproj /p:Platform=x64
```
