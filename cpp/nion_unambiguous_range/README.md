# IDS Nion Unambiguous Range Example

This console example acquires a depth image from an IDS Nion camera and shifts
the depth interval across its 4,096-value wraparound using a 42 mm offset.
It saves one depth map in the current working directory.

## Workflow

1. Opens the first available IDS Nion camera and loads its default user set.
2. Reads `Scan3dCoordinateScale` to convert the 42 mm offset to depth values.
3. Disables intensity and confidence data, then acquires one depth image.
4. Moves the depth image data by a specified offset and saves the result
   as `depth_map_0.tiff`.
5. Stops acquisition and releases the image buffers.

The unambiguous span is 4,096 depth values. Its physical distance is
`4096 × Scan3dCoordinateScale`, so the corresponding metric distance depends
on the scale reported by the camera.

For more information about the unambiguous range of IDS Nion cameras, see the [IDS Nion Getting Started](https://en.ids-imaging.com/techtipp-details/items/nion-getting-started.html).

In order to create a point cloud from the depth map, refer to the [Nion Point Cloud Example](../nion_point_cloud/README.md).

## Requirements

- An IDS Nion camera
- [IDS peak Setup](https://en.ids-imaging.com/download-peak.html) version 26.06.2 or later
- CMake version 3.10 or later
- A C++14-compatible compiler (MSVC, GCC, or Clang)
