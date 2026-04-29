# Calibration Example

This example demonstrates how to perform a camera calibration by using images from file.
The images contain a [calibration plate](https://en.ids-imaging.com/download-details/1012041.html)
in different poses and position, which will improve the calibration result.
In addition, the calibration Algorithm needs a corresponding
[description file](../../data/calibration_from_file/1012041-radon-checkerboard-marker-65mm-6x6.json) matching the calibration plate.
It can be obtained on the IDS [Website](https://en.ids-imaging.com/download-details/1012041.html).
When the calibration algorithm is done processing, the calibration result is saved to a file, containing both,
intrinsic and extrinsic calibration, as well as backprojection errors, indicating the quality of the calibration.

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
dotnet build CalibrationFromFile.csproj
dotnet run --project CalibrationFromFile.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 CalibrationFromFile.csproj
> dotnet run   -r win-x64 --project CalibrationFromFile.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild CalibrationFromFileFramework.csproj /t:Restore
msbuild CalibrationFromFileFramework.csproj /p:Platform=x64
```
