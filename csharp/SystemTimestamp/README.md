# SystemTimestamp Example

This example demonstrates how to use the **IDS peak `DeviceManager`** to discover,
select, and open a camera that supports system timestamp synchronization.
The device is configured for freerun acquisition, image buffers are acquired,
and buffer system timestamps (nanoseconds since Unix epoch) are retrieved
and converted into structured local and UTC time representations.

In addition, if supported by the device, remote ExposureStart events are
enabled. The example shows how to correlate remote device timestamps with
the host system timestamp domain using the synchronization latch mechanism,
allowing event timestamps to be translated into system time.

### Example Output

```bash
> dotnet run --project SystemTimestamp.csproj
--Buffer--
System timestamp [ns since epoch]: 1770887176180300450
Structured timestamp: [Local] 2026-02-12 10:06:16:180:300:450
Structured timestamp: [UTC] 2026-02-12 09:06:16:180:300:450
--ExposureStartEvent--
Timestamp [ns]: 65749724001800
System timestamp [ns since epoch]: 1770887176165293600
Structured timestamp: [Local] 2026-02-12 10:06:16:165:293:600
Structured timestamp: [UTC] 2026-02-12 09:06:16:165:293:600
--Buffer--
System timestamp [ns since epoch]: 1770887176230300350
Structured timestamp: [Local] 2026-02-12 10:06:16:230:300:350
Structured timestamp: [UTC] 2026-02-12 09:06:16:230:300:350
--ExposureStartEvent--
Timestamp [ns]: 65749774001650
System timestamp [ns since epoch]: 1770887176215293450
Structured timestamp: [Local] 2026-02-12 10:06:16:215:293:450
Structured timestamp: [UTC] 2026-02-12 09:06:16:215:293:450
[...]
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
dotnet build SystemTimestamp.csproj
dotnet run   --project SystemTimestamp.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 SystemTimestamp.csproj
> dotnet run   -r win-x64 --project SystemTimestamp.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild SystemTimestampFramework.csproj /t:Restore
msbuild SystemTimestampFramework.csproj /p:Platform=x64
```

> Note: The IDS peak SDK uses **native (unmanaged) DLLs**, so you **must specify
> the `Platform` parameter** when building.
