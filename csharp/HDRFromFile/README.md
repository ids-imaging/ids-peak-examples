# HDR algorithm example

This example demonstrates how to generate a **High Dynamic Range (HDR)** image and a **tone‑mapped LDR** output using the `peak::icv` library.
It covers:

- Loading calibration images with multiple exposure times
- Estimating a camera response curve
- Processing captured images into an HDR composite
- Applying tone mapping to produce a viewable LDR result
- Saving HDR and LDR images with timestamped filenames

## Output Images

The HDR output image is a tiff floating point image, which cannot be trivially displayed by most viewers.

The LDR output image is a tone mapped integer image:
![LDR floating point image](../../doc/hdr_from_file/tone_mapped_ldr_image.png)

As you can see there are some black spots throughout the right side of the image. Those are only visible as _black_ in
the tone mapped image. This is an effect due to over exposure in the input images.

## Documentation

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
dotnet build HDRFromFile.csproj
dotnet run --project HDRFromFile.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 HDRFromFile.csproj
> dotnet run   -r win-x64 --project HDRFromFile.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild HDRFromFileFramework.csproj /t:Restore
msbuild HDRFromFileFramework.csproj /p:Platform=x64
```
