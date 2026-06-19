# Image Acquisition Example

This example demonstrates how to acquire images from a camera using the `IDS peak SDK`.
The program performs the following steps:

- Initialize the library
- Setup the datastream by allocating buffers
- Start the datatream
- Grab images from a camera
- Queuing buffers
- Teardown the datastream

## Requirements

The following IDS peak Python packages are required:
- `ids-peak`
- `ids-peak-icv`

To install all required dependencies, use the provided `requirements.txt`:
```
pip install -r requirements.txt
```

In addition, a suitable GenTL must be installed, for example via the [IDS peak Setup](https://en.ids-imaging.com/download-peak.html).

## Running the example

After installing all requirements the demo can be run by executing `main.py` with the Python interpreter

```
python main.py
```

or, if Python files (*.py) are associated with the Python interpreter, by double-clicking the file.
