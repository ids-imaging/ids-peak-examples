# Reconnect Example

The Reconnect sample demonstrates how to detect device connection changes and
reliably handle temporary disconnections in a C# application using the IDS peak
API. It shows how to monitor device removal, loss of connection, and subsequent
reconnection, and how to safely resume image acquisition once the device
becomes available again.

## Example Output
```bash
Received Frame ID: 40
Received Frame ID: 41
Received Frame ID: 42
Disconnected-Device-Callback: Key=C:\Program Files\IDS\ids_peak\ids_u3vgentl\64\ids_u3vgentlk.cti|IDS GenICam Producer (U3VK)|IDS USB3 Vision Ifc|1409f497230fU3-328xCP-C-HQ R2-0
Reconnected-Device-Callback:
    Key=C:\Program Files\IDS\ids_peak\ids_u3vgentl\64\ids_u3vgentlk.cti|IDS GenICam Producer (U3VK)|IDS USB3 Vision Ifc|1409f497230fU3-328xCP-C-HQ R2-0
        ReconnectSuccessful: True
        RemoteDeviceAcquisitionRunning: True
        RemoteDeviceConfigurationRestored: False

Received Frame ID: 0
Received Frame ID: 1
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

The IDS peak SDK uses **native (unmanaged) DLLs**, so you **must specify
the `Platform` parameter** when building.

### .NET (modern, SDK-style)

```bash
dotnet build -p:Platform=x64 OpenCamera.csproj
dotnet run   -p:Platform=x64 --project OpenCamera.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 -p:Platform=x64 OpenCamera.csproj
> dotnet run   -r win-x64 -p:Platform=x64 --project OpenCamera.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild OpenCameraFramework.csproj /t:Restore
msbuild OpenCameraFramework.csproj /p:Platform=x64
```
