# C# Examples – IDS peak Generic SDK

This directory contains C# examples demonstrating how to use the IDS
peak Generic SDK via its **.NET** Bindings.

The examples require at least:
- **.NET Framework 4.8** (classic)
- **.NET 8** (modern)

## Requirements

- An [IDS peak Setup](https://en.ids-imaging.com/download-peak.html) (Runtime Setup which provides the GenTL is enough)
- .NET SDK / Visual Studio for building and running examples

> Note: The C# bindings include the necessary runtime DLLs to run the
> examples.
Installing the IDS peak Runtime Setup is still required to provide the necessary GenTL for device access.

## Build Instructions

If **no `RuntimeIdentifier` (`-r`) is specified**, all available native
runtimes from the packages will be copied to your build output.
This would normally maximize compatibility but increase the application size.

You may **optionally specify `-r <rid>`** to reduce the size of the build
output by including only the native libraries for a single runtime.

### .NET (modern, SDK-style)

**Required (correct architecture selection):**

```bash
dotnet build exampleProject.csproj
dotnet run   --project exampleProject.csproj
```

**Optional (smaller output):**

```bash
dotnet build -r win-x64 exampleProject.csproj
dotnet run   -r win-x64 --project exampleProject.csproj
```

### .NET Framework (classic)

The IDS peak SDK relies on **native (unmanaged) DLLs** that are
distributed inside the referenced NuGet packages.

Because native binaries are involved, you **must specify the target
architecture via `-p:Platform=<arch>`** when building. This ensures that
your application is built for an architecture that can correctly load
the required native libraries.

Use Visual Studio **or** build from the command line:

```bash
# Restore packages first
msbuild exampleProjectFramework.csproj /t:Restore

# Build for a specific platform (required for native DLLs)
msbuild exampleProjectFramework.csproj /p:Platform=x64
```

## NuGet

IDS peak .NET packages are available on NuGet and can be added with:
```bash
dotnet add package IDSImaging.Peak.<PackageName>
```

## Included Examples

- [Calibration From File](CalibrationFromFile) Demonstrates how to perform a camera calibration by using images from file.
- [Firmware Update](FirmwareUpdate) Shows how to programatically update the firmware of a device.
- [Getting Started With Camera](GettingStartedWithCamera) Shows how to open the first available camera to acquire images.
- [Gui-AvaloniaSimpleLive](Gui-AvaloniaSimpleLive) Demonstrates how to display a live video feed from an IDS camera in
  a cross-platform desktop application using **Avalonia UI** and the **MVVM** pattern.
- [HDR From File](HDRFromFile) Demonstrates how to generate a **High Dynamic Range (HDR)** image and a **tone‑mapped LDR** output.
- [Image Region From File](ImageRegionFromFile) Command-line example demonstrating how to handle image regions.
- [Morphology](Morphology) Demonstrates how to use morphology algorithms on regions.
- [Nion Point Cloud](NionPointCloud) Command-line example demonstrating Nion Point Cloud acquisition.
- [OpenCamera](OpenCamera) Command-line example demonstrating device enumeration and access.
- [Pipeline From File](PipelineFromFile) This command-line example demonstrates how to use the image processing pipeline.
- [Point Cloud From File](PointCloudFromFile) Shows how to create a point cloud with mapped Mono data using
  `IDS peak ICV`.
- [Reconnect](Reconnect) Command-line example demonstrating robust device reconnect handling.
- [SimpleLiveWindowsForms](SimpleLiveWindowsForms) Windows Forms application demonstrating a basic
  live camera image viewer.
- [System Timestamp](SystemTimestamp) Shows how to use the system timestamp feature in order to get a wall-clock time
  corresponding to an arbitrary device timestamp.
- [Threshold From File](ThresholdFromFile) Demonstrates how to apply a threshold to an image.
- [Undistortion From File](UndistortionFromFile) Demonstrates how to undistort a distorted image using precomputed camera calibration parameters.
- [Unicast](Unicast) This example demonstrates how to use the unicast discovery features of the
  transport layer (TL) to locate cameras that are not in the same subnet as the host system.
- [Workspace Calibration From File](WorkspaceCalibrationFromFile) Shows how to calibrate and apply a new workspace
  using `IDS peak ICV`.
