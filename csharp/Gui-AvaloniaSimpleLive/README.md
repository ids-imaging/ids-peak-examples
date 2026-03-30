# AvaloniaSimpleLive Example

The **AvaloniaSimpleLive** Example demonstrates how to integrate an IDS camera into a cross-platform desktop application
using **Avalonia 12** and the **MVVM pattern**. It covers device enumeration, opening a camera, starting and stopping
image acquisition, and adjusting camera parameters such as exposure, gain, and framerate.

![Image of the AvaloniaSimpleLive](../../doc/Gui-AvaloniaSimpleLive/image.png)

## Requirements

This example leverages modern .NET features and therefore requires:

* **C# 13 or later**
* **.NET 8 SDK or later**
* A connected IDS camera

> **Note:** The C# bindings include the necessary runtime DLLs to run
> the examples. Installing the IDS peak Runtime Setup is still required
> to provide the drivers and GenTL libraries for device access.

## Build Instructions

The IDS peak SDK relies on native libraries (.dll on Windows, .so on Linux). To ensure the correct native assets are
copied to your output folder, it is recommended to specify your target architecture. For example

Windows x64:

```bash
dotnet run -r win-x64
```

Linux x64:

```bash
dotnet run -r linux-x64
```

# Native AOT Compilation (Optional)
Avalonia 12 is fully optimized for Ahead-Of-Time compilation.
To publish a single, trimmed, high-performance native binary without requiring a .NET runtime on the target machine:

```bash
dotnet publish -c Release -r win-x64 /p:PublishAot=true
```

## Performance & Memory Management

This example is optimized for industrial-grade frame rates. By utilizing **.NET 8** and **Avalonia 12**, the application
achieves:

* **Single-Copy Rendering**: The CameraViewModel uses unsafe pointers to copy the IDS Peak image buffer directly into
  the Avalonia WriteableBitmap back-buffer, avoiding managed heap allocations and intermediate format conversions.
* **Cross-Platform Native Interop:** The same unified C# codebase seamlessly interfaces with native execution
  environments on both Windows and Linux desktop systems.

## Project Structure

```
Gui-AvaloniaSimpleLive/
├── Models/
│   └── CameraService.cs            # Wraps the IDS Peak SDK (acquisition, parameters, reconnect)
├── ViewModels/
│   ├── CameraViewModel.cs          # Main ViewModel — live view, parameter controls
│   ├── CameraSelection.cs          # ViewModel for the camera selection dialog
│   ├── CameraSetting.cs            # Observable parameter types (double, enum, bool, string)
│   └── IFileDialogService.cs       # Abstraction for file dialogs
├── Views/
│   ├── MainWindow.axaml            # Live view and settings panel
│   ├── CameraSelectionWindow.axaml # Camera selection window
│   └── FileDialog.cs               # Avalonia StorageProvider implementation
└── Utils/
    └── InvariantConverter.cs       # IValueConverter for culture-invariant double display
```
