# Unicast Example

This example demonstrates how to use the unicast discovery
features of the transport layer (TL) to locate cameras that
are not in the same subnet as the host system.

Unlike standard discovery mechanisms that rely on broadcast
traffic, this sample shows how to explicitly target devices
via their IP addresses.

## Usage scenario

In typical GigE Vision setups, device discovery relies on broadcast communication within the same subnet.

This creates a limitation:

- Devices in different subnets cannot be discovered
- Broadcast traffic is often blocked by routers/gateways
- Cameras behind a gateway or routed network remain invisible

## Solution

This example solves this problem by using unicast discovery:

- Sends discovery messages directly to specific IP addresses
- Works across subnets and routed networks
- Avoids reliance on broadcast traffic

## How It Works

1. Select a network interface
2. Provide one or more target IP addresses
3. The program:
   1. Configures the interface for unicast-only discovery
   2. Sends discovery packets directly to the specified IPs
   3. Waits for responses from reachable devices
4. Discovered devices are listed in the console

## Example Use Case

You have a GigE Vision camera with IP `192.168.10.5`, but your PC is on
`192.168.1.x`. A router/gateway connects both networks.

Normally, the camera won’t appear in discovery tools.

When the example is configured with `192.168.10.5`, it sends a unicast
request directly to that address, allowing the camera to respond and
be discovered.

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
dotnet build FirmwareUpdate.csproj
dotnet run   --project FirmwareUpdate.csproj
```

> Optional (smaller output):
>
> ```bash
> dotnet build -r win-x64 FirmwareUpdate.csproj
> dotnet run   -r win-x64 --project FirmwareUpdate.csproj
> ```

### .NET Framework (classic)

Use Visual Studio **or**:

```bash
msbuild FirmwareUpdateFramework.csproj /t:Restore
msbuild FirmwareUpdateFramework.csproj /p:Platform=x64
```

> Note: The IDS peak SDK uses **native (unmanaged) DLLs**, so you **must specify
> the `Platform` parameter** when building.
