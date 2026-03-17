# Software Trigger Example

This example shows how to capture images using a software trigger with
the IDS peak generic API.
The application opens the first available camera, enables software
trigger mode, and provides an interactive console to trigger image
acquisition manually.

Each trigger captures one frame, converts it using the IDS peak image
pipeline, and saves it as a PNG file in the specified output directory
using a timestamp as the filename.


## Requirements

The following IDS peak python packages are required:

* `ids-peak`
* `ids-peak-icv`
* `ids-peak-common`

To install all required dependencies, use the provided `requirements.txt`:

```
pip install -r requirements.txt
```

In addition, a suitable GenTL producer must be installed, for example via the
[IDS peak Setup](https://en.ids-imaging.com/download-peak.html).


## Running the example

After installing all requirements the demo can be run by executing `main.py`
with the Python interpreter:

```
python main.py output_directory
```

Example:

```
python main.py images
```

After startup, the application enters an interactive console.


## Interactive console

The console allows manual triggering of images.

Available commands:

| Command | Description |
|---------|------------|
| `trigger` | Acquire one image using software trigger |
| `t` | Alias for `trigger` |
| `help` | Show available commands |
| `exit` | Exit the application |

Each trigger saves one image to the output directory.


## Optional parameters

The application supports optional camera configuration parameters:

```
python main.py output_directory --exposure 10000 --gain 2
```

| Parameter | Description |
|-----------|-------------|
| `--exposure` | Exposure time in microseconds |
| `--gain` | Master gain factor |

Example:

```
python main.py images --exposure 8000 --gain 1.5
```
