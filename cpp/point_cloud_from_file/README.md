# Point Cloud Example

This example demonstrates how to generate a 3D point cloud from raw sensor data, consisting of a depth image, an
intensity image and camera calibration parameters.

First, the input images are undistorted using the provided calibration data to correct lens distortions. The corrected
depth image combined with the intensity information is then used to create a point cloud.
Finally, the resulting point cloud is exported and saved as a .ply file for further use or visualization.

## Input Files

Depth Map:

![Screenshot Depth_Map](../../doc/point_cloud_from_file/depth_map.png)

Intensity Image:

![Intensity Image](../../data/point_cloud_from_file/intensity.png)

## Output

PLY:

![Screenshot PLY](../../doc/point_cloud_from_file/point_cloud.png)

## Requirements

This example depends on the following components:

- [IDS peak standard Setup](https://en.ids-imaging.com/download-peak.html) version 2.19 or later
- **CMake** version 3.10 or later
- A supported C++ compiler (MSVC, GCC, or Clang)
