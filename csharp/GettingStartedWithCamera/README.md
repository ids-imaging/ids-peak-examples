# Getting Started With Camera Example

This application demonstrates how to open the first available camera
to acquire images.

## Workflow

The example performs the following steps:

1. Searches for the first available device and opens it.
2. Starts the image acquisition.
3. Acquires five images to print their first pixel values.
4. Stops the image acquisition.
5. Cleanup.

## Requirements

This example requires:

* **C# 8.0 or later**
* **.NET Framework 4.6.1** (for classic projects)
* **.NET 8** (for modern SDK-style projects)
* An **IDS** camera
* [IDS peak runtime Setup](https://en.ids-imaging.com/download-peak.html)

> **Note:** The C# bindings include the necessary runtime DLLs to run
> the examples. Installing the IDS peak Runtime Setup is still required
> to provide the drivers and GenTL libraries for device access.


## Build Instructions

### .NET (modern, SDK-style)

```bash
dotnet build GettingStartedWithCamera.csproj
dotnet run   --project GettingStartedWithCamera.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 GettingStartedWithCamera.csproj
> dotnet run   -r win-x64 --project GettingStartedWithCamera.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild GettingStartedWithCameraFramework.csproj /t:Restore
msbuild GettingStartedWithCameraFramework.csproj /p:Platform=x64
```

> Note: The IDS peak SDK uses **native (unmanaged) DLLs**, so you **must specify
> the `Platform` parameter** when building.
