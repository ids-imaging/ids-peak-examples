# C++ Examples – IDS peak Generic SDK

This directory contains **C++** example programs demonstrating how to use the IDS peak Generic SDK from C++.

## Requirements
- [IDS peak Setup](https://en.ids-imaging.com/download-peak.html) (development headers and libraries) for building examples
- C++14-compatible compiler (GCC, Clang, or MSVC)
- CMake 3.10+
- Qt5 or Qt6 for graphical examples (See `README.md` of the example to verify)

## Build Instructions
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

## General Notes
- These examples are intentionally minimal and focused on API usage (enumeration, opening devices, acquisition, basic parameter setting).
- A `.clang-format` file is provided at the repository root for consistent formatting.
- Use `clang-tidy` for static analysis where appropriate.

## Included Examples

* [Nion Point Cloud](nion_point_cloud) Shows how to calculate the depth Map and point cloud using the `IDS Nion` camera and `IDS peak ICV`.
* [Open Camera](open_camera) This application demonstrates how to use the device manager to open a camera.
