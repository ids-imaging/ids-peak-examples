# OpenCamera Example

The **OpenCamera** example demonstrates how to use the **IDS peak
`DeviceManager`** to discover, select, and open a camera. After opening
the device with control access, it retrieves basic device information
from the remote GenICam node map.

### Example Output

```bash
> dotnet run --project OpenCamera.csproj
IDS peak OpenCamera Example
Devices available:
0: U3-36LxXC-C (IDS U3V Interface; IDS GenICam Producer (U3V) v.1.21.0.0)

Select device to open:
0
Model Name: U3-36LxXC-C
User ID: dev
Sensor Name: onsemi AR1335CSSC32SMD20
Max. resolution (w x h): 4200 x 3120
```

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
dotnet build OpenCamera.csproj
dotnet run   --project OpenCamera.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 OpenCamera.csproj
> dotnet run   -r win-x64 --project OpenCamera.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild OpenCameraFramework.csproj /t:Restore
msbuild OpenCameraFramework.csproj /p:Platform=x64
```

> Note: The IDS peak SDK uses **native (unmanaged) DLLs**, so you **must specify
> the `Platform` parameter** when building.
