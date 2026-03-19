# C++ Examples – IDS peak Generic SDK

This directory contains **C++** example programs demonstrating how to use the IDS peak Generic SDK from C++.

## Requirements

- [IDS peak Setup](https://en.ids-imaging.com/download-peak.html) (development headers and libraries) for building
  examples
- C++14-compatible compiler (GCC, Clang, or MSVC)
- CMake 3.10+
- Qt5 or Qt6 for graphical examples (See `README.md` of the example to verify)

Some samples offer Visual Studio Projects, though it is recommended to use CMake for building the examples.

## Build Instructions

### CMake

1. Run CMake to configure using the current directory (`.`) as source and `build` as the build directory:

```bash
cmake -B build .
```

2. Build into the `build` directory:

```bash
cmake --build build
```

Or in a single command block:

```
cmake -B build .
cmake --build build
```

### Visual Studio

Open the Visual Studio Project and build it.

## General Notes

- These examples are intentionally minimal and focused on API usage (enumeration, opening devices, acquisition, basic
  parameter setting).
- A `.clang-format` file is provided at the repository root for consistent formatting.
- Use `clang-tidy` for static analysis where appropriate.

## Included Examples

* [Calibration From File](calibration_from_file) Shows how to perform a camera calibration using `IDS peak ICV`.
* [Code Reader From File](code_reader_from_file) Shows how to read a data matrix code from an image using
  `IDS peak ICV`.
* [Get First Pixel](get_first_pixel) This example demonstrates how to acquire an image and print the value of the first
  pixel.
* [Image Region From File](image_region_from_file) Shows what image regions are and how to use them in `IDS peak ICV`.
* [Morphology](morphology) Shows how to use region morphology using `IDS peak ICV`.
* [Nion Point Cloud](nion_point_cloud) Shows how to calculate the depth Map and point cloud using the `IDS Nion` camera
  and `IDS peak ICV`.
* [Open Camera](open_camera) This application demonstrates how to use the device manager to open a camera.
* [Point Cloud From File](point_cloud_from_file) Shows how to create a point cloud with mapped Mono data using
  `IDS peak ICV`.
* [System Timestamp](system_timestamp) Shows how to use the system timestamp feature in order to get a wall-clock time
  corresponding to an arbitrary device timestamp.
* [Threshold From File](threshold_from_file) Shows how to apply a threshold using `IDS peak ICV`.
* [Undistortion From File](undistortion_from_file) Shows how to apply an undistortion using `IDS peak ICV`.
* [Workspace Calibration From File](workspace_calibration_from_file) Shows how to calibrate and apply a new workspace
  using `IDS peak ICV`.
