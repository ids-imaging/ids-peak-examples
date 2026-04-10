# Calibration Example

This example demonstrates how to perform a workspace calibration using a calibration plate to define a new coordinate
system.

An image of the calibration plate is captured and used to estimate the transformation that establishes the
workspace coordinate frame. To illustrate the result, a point cloud (based on the
example ![point_cloud_from_file](../point_cloud_from_file)) is loaded, and the computed calibration is applied to
transform the data into the new coordinate system. The transformed point cloud is saved for further processing or
visualization. The resulting files are saved next to the executable.

## Input Image

Workspace Image

![Workspace Image](../../data/workspace_calibration_from_file/workspace.png)

## Requirements

The following IDS peak python packages are required:

* `ids-peak-icv`

To install all required dependencies, use the provided `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Running the example

After installing all requirements the demo can be run by executing `main.py`
with the Python interpreter:

```bash
python main.py
```
