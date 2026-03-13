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

- [Open Camera](open_camera) Shows to how enumerate devices and access device information.
- [Graphical Kivy Demo Using the IDS peak DefaultPipeline](gui_kivy_pipeline)
  Shows how the image pipeline can be applied to process camera images. Pipeline settings can be saved and loaded,
  allowing, for example, easy transfer of settings to and from the `IDS peak Cockpit`.
- [Nion Point Cloud](nion_point_cloud) Shows how to calculate the depth Map and point cloud using the `IDS Nion` camera
  and `IDS peak ICV`.
