# Pipeline Example

This example demonstrates how to perform a workspace calibration using a calibration plate to define a new coordinate
system.

An image of the calibration plate is captured and used to estimate the transformation that establishes the
workspace coordinate frame. To illustrate the result, a point cloud (based on the
example [PointCloudFromFile](../PointCloudFromFile)) is loaded, and the computed calibration is applied to
transform the data into the new coordinate system. The transformed point cloud is saved for further processing or
visualization. The resulting files are saved next to the executable.

## Input Image

Workspace Image

![Workspace Image](../../data/workspace_calibration_from_file/workspace.png)

## Requirements

This example requires:

* **C# 8.0 or later**
* **.NET Framework 4.8** (for classic projects)
* **.NET 8** (for modern SDK-style projects)

## Build Instructions

### .NET (modern, SDK-style)

```bash
dotnet build WorkspaceCalibrationFromFile.csproj
dotnet run   --project WorkspaceCalibrationFromFile.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 WorkspaceCalibrationFromFile.csproj
> dotnet run   -r win-x64 --project WorkspaceCalibrationFromFile.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild WorkspaceCalibrationFromFileFramework.csproj /t:Restore
msbuild WorkspaceCalibrationFromFileFramework.csproj /p:Platform=x64
```
