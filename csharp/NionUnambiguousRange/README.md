# IDS Nion Unambiguous Range Example

This console example acquires a depth image from an IDS Nion camera and moves
the unambiguous range by a specified 450 mm offset. It saves one depth map as
`depth_map_0.tiff` in the current working directory.

## Workflow

1. Opens the first available IDS Nion camera and loads its default user set.
2. Reads `Scan3dCoordinateScale` to convert the 450 mm offset to depth values.
3. Disables intensity and confidence data, then acquires one raw depth image.
4. Moves the unambiguous range data of the raw depth image by the specified
   offset and saves the result as `depth_map_0.tiff`.
5. Stops acquisition and releases the image buffers.

For more information about the unambiguous range of IDS Nion cameras,
see the [IDS Nion Getting Started](https://en.ids-imaging.com/techtipp-details/items/nion-getting-started.html).

In order to create a point cloud from the depth map,
refer to the [Nion Point Cloud Example](../NionPointCloud/README.md).

## Requirements

- An `IDS Nion` camera
- [IDS peak standard Setup](https://en.ids-imaging.com/download-peak.html) version 26.06.2 or later
- **C# 8.0 or later**
- **.NET Framework 4.8** (for classic projects) or **.NET 8** (for modern SDK-style projects)

> **Note:** The C# bindings include the necessary runtime DLLs to run
> the examples. Installing the IDS peak Runtime Setup is still required
> to provide the drivers and GenTL libraries for device access.

## Build Instructions

### .NET (modern, SDK-style)

```bash
dotnet build NionUnambiguousRange.csproj
dotnet run --project NionUnambiguousRange.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 NionUnambiguousRange.csproj
> dotnet run   -r win-x64 --project NionUnambiguousRange.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild NionUnambiguousRangeFramework.csproj /t:Restore
msbuild NionUnambiguousRangeFramework.csproj /p:Platform=x64
```

> Note: The IDS peak SDK uses **native (unmanaged) DLLs**,
> so you **must specify the `Platform` parameter** when building.
