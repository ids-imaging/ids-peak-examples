# NionPointCloud Example

Demonstrates how to acquire multipart image data from an **IDS Nion** camera
and convert it into a metric 3D point cloud with per-point intensity information (XYZI).

This example shows how to open and configure an IDS Nion camera,
acquire multipart image buffers containing a depth map and an intensity image,
and process this data into usable 3D information.
It illustrates how to convert raw depth values into floating-point metric coordinates,
filter invalid or out-of-range depth measurements,
and apply factory calibration data to undistort both depth and intensity images.

In addition, the example demonstrates how to generate a point cloud from the processed depth data,
associate each 3D point with an intensity value,
and write the resulting depth maps, intensity images, and point cloud data to disk
for further processing or visualization.

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
dotnet build NionPointCloud.csproj
dotnet run --project NionPointCloud.csproj
```

> Optional (smaller output):[NionPointCloudFramework.csproj](NionPointCloudFramework.csproj)
>
> ```bash
> dotnet build -r win-x64 NionPointCloud.csproj
> dotnet run   -r win-x64 --project NionPointCloud.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild NionPointCloudFramework.csproj /t:Restore
msbuild NionPointCloudFramework.csproj /p:Platform=x64
```
