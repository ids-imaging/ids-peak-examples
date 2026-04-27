# Image Region Example

This example demonstrates how to handle image regions with the `IDS peak ICV` library.
Regions can be interpreted as a set of points
and can fill a rectangular area of the image, but they don't necessarily have to.
As they are a set of points, their shape can be anything from a single point, over a pixelized circle, to a rectangle.
They are used to enhance image processing performance, while keeping the original image.
Several algorithms in the `IDS peak ICV` library check for an available region in the image and use it when processing.

To illustrate, how regions affect the output of algorithms, the image with its region is processed by a threshold.

## Input Image

![Input Image](../../data/image_region_from_file/beads.png)

## Output

The region is displayed in green.
The result of the threshold is displayed in red.

**Image with full region:**

![Output Image with full region](../../doc/image_region/image_full_region.png)

**Image with reduced region:**

![Output Image with full region](../../doc/image_region/image_reduced_region.png)

One can observe, that the threshold only processed the green `region` area.
Only the bubbles inside the region are colored red.

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
dotnet build ImageRegionFromFile.csproj
dotnet run --project ImageRegionFromFile.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 ImageRegionFromFile.csproj
> dotnet run   -r win-x64 --project ImageRegionFromFile.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild ImageRegionFromFileFramework.csproj /t:Restore
msbuild ImageRegionFromFileFramework.csproj /p:Platform=x64
```
