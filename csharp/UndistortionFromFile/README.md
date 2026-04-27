# Workspace Calibration Example

This example demonstrates how to undistort a distorted image using precomputed camera calibration parameters.

The calibration data from example [CalibrationFromFile](../CalibrationFromFile) is used to correct lens
distortions in the input image, resulting in a geometrically accurate, undistorted output. This showcases how previously
obtained calibration results can be reused to improve image quality and measurement accuracy.

The resulting image is saved next to the executable.

## Input Image

Distorted Image

![Distorted Image](../../data/undistortion_from_file/fisheye.png)

## Undistorted Image

The following image is scaled for visuals.

![Undistorted Image](../../doc/undistortion_from_file/fisheye_undistorted.png)

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
dotnet build UndistortionFromFile.csproj
dotnet run --project UndistortionFromFile.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 UndistortionFromFile.csproj
> dotnet run   -r win-x64 --project UndistortionFromFile.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild UndistortionFromFileFramework.csproj /t:Restore
msbuild UndistortionFromFileFramework.csproj /p:Platform=x64
```
