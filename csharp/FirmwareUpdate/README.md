# Firmware Update Example

This example demonstrates how to programmatically update the firmware of
connected devices using the IDS peak generic API using C#.

The application:
1. Detects available GenTL devices using the DeviceManager
2. Identifies devices compatible with the provided firmware file (GUF)
3. Prompts the user for confirmation before updating
4. Executes the firmware update process
5. Reports update progress via callback functions

Progress callbacks provide information about update start, progress,
individual update steps, successful completion, or failure.

The firmware file must be provided as a command line argument in the
Generic Update Format (GUF).

## Requirements

This example requires:

* **C# 8.0 or later**
* **.NET Framework 4.6.1** (for classic projects)
* **.NET 8** (for modern SDK-style projects)

> **Note:** The C# bindings include the necessary runtime DLLs to run
> the examples. Installing the IDS peak Runtime Setup is still required
> to provide the drivers and GenTL libraries for device access.


Here is a **much more concise, example-specific version** that keeps the same meaning but strips everything down to what users actually need to know and type:

## Build Instructions

The IDS peak SDK uses **native (unmanaged) DLLs**, so you **must specify
the `Platform` parameter** when building.

### .NET (modern, SDK-style)

```bash
dotnet build -p:Platform=x64 FirmwareUpdate.csproj
dotnet run   -p:Platform=x64 --project FirmwareUpdate.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 -p:Platform=x64 FirmwareUpdate.csproj
> dotnet run   -r win-x64 -p:Platform=x64 --project FirmwareUpdate.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild FirmwareUpdateFramework.csproj /t:Restore
msbuild FirmwareUpdateFramework.csproj /p:Platform=x64
```
