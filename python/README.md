# Python Examples – IDS peak Generic SDK

This directory contains **Python** example scripts demonstrating the use of the IDS peak generic SDK Python bindings.

## Requirements

- An [IDS peak Setup](https://en.ids-imaging.com/download-peak.html) (Runtime Setup which provides the GenTL is enough)
- Python 3.10 or later

## Setup

1. (Recommended) Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows (PowerShell)
```

2. Install Python packages from the provided `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Running Examples

```bash
python example_name.py
```

or on some linux distributions

```bash
python3 example_name.py
```

## Packages (PyPI)

- https://pypi.org/project/ids-peak/
- https://pypi.org/project/ids-peak-ipl/
- https://pypi.org/project/ids-peak-afl/
- https://pypi.org/project/ids-peak-icv/
- https://pypi.org/project/ids-peak-common/

## Included Examples

### GUI examples

- [Pipeline (Kivy)](gui_kivy_pipeline)
  Shows how the image pipeline can be applied to process camera images. Pipeline settings can be saved and loaded,
  allowing, for example, easy transfer of settings to and from the `IDS peak Cockpit`.
- [Simple Live (QtWidgets)](gui_qtwidgets_simple_live) This example shows how to use QtWidgets to display a live image.

### CLI examples

- [Calibration From File](calibration_from_file) Shows how to perform a camera calibration.
- [Firmware Update](firmware_update) Shows how to programmatically update the firmware of a device.
- [Getting Started With Camera](getting_started_with_camera) This application demonstrates how to open the
  first available camera to acquire images and print their first pixel value.
- [HDR](hdr) Demonstrates how to acquire multiple images with different exposure times using an IDS camera and combine
  them into a single High Dynamic Range (HDR) image.
- [HDR from file](hdr_from_file) Shows how to create an HDR image and apply tone mapping for visual appearance using `IDS peak ICV`.
- [Image Acquisition](image_acquisition) Shows how to acquire images from a camera using the `IDS peak SDK`.
- [Image Region From File](image_region_from_file) Shows what image regions are and how to use them in `IDS peak ICV`.
- [Morphology](morphology) Shows how to use region morphology using `IDS peak ICV`.
- [Nion Point Cloud](nion_point_cloud) Shows how to calculate the depth Map and point cloud using the `IDS Nion` camera
  and `IDS peak ICV`.
- [Node Polling](node_polling) Shows how node polling is used to regularly invalidate GenICam nodes that implement the
  PollingTime feature,
  ensuring that cached values stay up to date.
- [Open Camera](open_camera) Shows how to enumerate devices and access device information.
- [Point Cloud From File](point_cloud_from_file) Shows how to create a point cloud with mapped Mono data using
  `IDS peak ICV`.
- [Reconnect](reconnect) Shows how to use the automatic device reconnect feature of the IDS peak API and how to react to
  connection state changes.
- [Record Video](record_video) Shows how to use the VideoWriter of the IDS peak IPL to create a video sequence.
- [Software Trigger](software_trigger) Shows how to use the software trigger to acquire images.
- [System Timestamp](system_timestamp) Shows how to use the system timestamp feature in order to get a wall-clock time
  corresponding to a arbitrary device timestamp.
- [Threshold From File](threshold_from_file) Shows how to apply a threshold using `IDS peak ICV`.
- [Undistortion From File](undistortion_from_file) Shows how to apply an undistortion using `IDS peak ICV`.
- [Unicast](unicast) This example demonstrates how to use the unicast discovery features of the transport layer (TL) to
  locate cameras that are not in the same subnet as the host system.
- [Workspace Calibration From File](workspace_calibration_from_file) Shows how to calibrate and apply a new workspace
  using `IDS peak ICV`.
