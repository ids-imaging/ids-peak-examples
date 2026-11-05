# IDS Nion Unambiguous Range Example

This console example acquires a depth image from an IDS Nion camera and moves
the unambiguous range by a specified 450 mm offset.
It saves one depth map in the current working directory.

## Workflow

1. Opens the first available IDS Nion camera and loads its default user set.
2. Reads `Scan3dCoordinateScale` to convert the 450 mm offset to depth values.
3. Disables intensity and confidence data, then acquires one raw depth image.
4. Uses NumPy to move the unambiguous range data of the raw depth image by the
   specified offset and saves the result as `depth_map_0.tiff`.
5. Stops acquisition and releases the image buffers.

For more information about the unambiguous range of IDS Nion cameras, see the
[IDS Nion Getting Started](https://en.ids-imaging.com/techtipp-details/items/nion-getting-started.html).

In order to create a point cloud from the depth map, refer to the
[Nion Point Cloud Example](../nion_point_cloud/README.md).

## Requirements

- An IDS Nion camera
- [IDS peak Setup](https://en.ids-imaging.com/download-peak.html) version 26.06.2 or later
- Python 3.10 or later
- Dependencies listed in [requirements](requirements.txt) file

Install the Python dependencies with:

```bash
pip install -r requirements.txt
```

In addition, a suitable GenTL must be installed, for example via the [IDS peak Setup](https://en.ids-imaging.com/download-peak.html).

## Running the example

After installing all requirements the demo can be run by executing `main.py` with the Python interpreter

```bash
python main.py
```

or, if Python files (*.py) are associated with the Python interpreter, by double-clicking the file.
