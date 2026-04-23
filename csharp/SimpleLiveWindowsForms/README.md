# Simple Live Windows Forms Example

This example demonstrates how to acquire images from a camera and display them in a
basic live image viewer using Windows Forms.

The application:

1. Detects available GenTL devices using the DeviceManager
2. Opens the first available and accessible GenTL device
3. Configures the device and starts image acquisition
4. Continuously acquires and displays images in a live viewer

The main window of this example consists of an image viewer area and
an image acquisition statistics bar below it. The image viewer is implemented by a
custom class derived from PictureBox while the statistics bar is a simple set of labels.

## Requirements

This example requires:

* **C# 8.0 or later**
* **.NET Framework 4.6.1** (for classic projects)
* **.NET 8** (for modern SDK-style projects)

> **Note:** The C# bindings include the necessary runtime DLLs to run
> the examples. Installing the IDS peak Runtime Setup is still required
> to provide the drivers and GenTL libraries for device access.

## Build Instructions

### .NET (modern, SDK-style)

```bash
dotnet build SimpleLiveWindowsForms.csproj
dotnet run   --project SimpleLiveWindowsForms.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 SimpleLiveWindowsForms.csproj
> dotnet run   -r win-x64 --project SimpleLiveWindowsForms.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild SimpleLiveWindowsFormsFramework.csproj /t:Restore
msbuild SimpleLiveWindowsFormsFramework.csproj /p:Platform=x64
```

> Note: The IDS peak SDK uses **native (unmanaged) DLLs**, so you **must specify
> the `Platform` parameter** when building.
