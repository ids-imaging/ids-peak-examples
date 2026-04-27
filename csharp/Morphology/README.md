# Image Region Morphology Example

This example demonstrates how to use morphology algorithms on regions.
For a general understanding of regions, have a look at the
[Image Region from file](../ImageRegionFromFile) example.

A region can be dilated and eroded by using a structuring element.
The structuring element is defined as a region itself.
Note, that the structuring element must not be inside the image coordinate system. It has its own coordinate system,
which may even start negative.
In this example a structuring element in form of a rectangle is used:
```
x: -1
y: -1
width: 3
height: 3
```

The following images are scaled for visuals.

## Input Image (created at runtime)

![Input Image](../../doc/morphology/region.png)

## Output

The region is displayed in red.

**Image with dilated region:**

![Output Image with dilated region](../../doc/morphology/region_dilated.png)

**Image with eroded region:**

![Output Image with eroded region](../../doc/morphology/region_eroded.png)

## Requirements

This example requires:

* **C# 8.0 or later**
* **.NET Framework 4.8** (for classic projects)
* **.NET 8** (for modern SDK-style projects)

> **Note:** The C# bindings include the necessary runtime DLLs to run
> the examples. Installing the IDS peak Runtime Setup is still required
> to provide the drivers and GenTL libraries for device access.

## Build Instructions

The IDS peak SDK uses **native (unmanaged) DLLs**, so you **must specify
the `Platform` parameter** when building.

### .NET (modern, SDK-style)

```bash
dotnet build Morphology.csproj
dotnet run --project Morphology.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 Morphology.csproj
> dotnet run   -r win-x64 --project Morphology.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild MorphologyFramework.csproj /t:Restore
msbuild MorphologyFramework.csproj /p:Platform=x64
```
