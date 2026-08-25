# Getting Started With Camera Example

This application demonstrates how to open the first available camera
to acquire images and print their first pixel value.

## Workflow

The example performs the following steps:

1. Searches for the first available device and opens it.
2. Starts the image acquisition.
3. Acquires five images to print their first pixel values.
4. Stops the image acquisition.
5. Cleanup.


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
python gettin_started_with_camera.py
```

To run the example using `uv`:

or, if Python files (*.py) are associated with the Python interpreter, by double-clicking the file.

Alternatively when using `uv` the following one-liner also works
``
uv run --with-requirements requirements.txt gettin_started_with_camera.py
```
