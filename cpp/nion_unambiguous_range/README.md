# IDS Nion Unambiguous Range Example

This console example acquires a depth image from an IDS Nion camera
and moves the unambiguous range by a specified offset.
It saves one depth map in the current working directory.

## Workflow

1. Opens the first available IDS Nion camera
   and loads its default user set.
2. Reads the value `Scan3dCoordinateScale` used
   to convert the 450mm offset to depth values.
3. Disables intensity and confidence data,
   then acquires one raw depth image.
4. Moves the unambiguous range data of the raw depth image
   by the specified offset
   and saves the result as `depth_map_0.tiff`.
5. Stops acquisition and releases the image buffers.

For more information about the unambiguous range of IDS Nion cameras,
see the [IDS Nion Getting Started](https://en.ids-imaging.com/techtipp-details/items/nion-getting-started.html).

In order to create a point cloud from the depth map,
refer to the [Nion Point Cloud Example](../nion_point_cloud/README.md).

## Requirements

- An IDS Nion camera
- [IDS peak Setup](https://en.ids-imaging.com/download-peak.html)
  version 26.06.2 or later
- CMake version 3.10 or later
- A C++14-compatible compiler (MSVC, GCC, or Clang)
