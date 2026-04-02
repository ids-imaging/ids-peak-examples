# QtWidgets Simple Live

![Image of the example window](../../doc/gui_qtwidgets_simple_live/image.png)

This example shows how to display a live camera image using
`pyside6` and QtWidgets.

It demonstrates how to acquire images from a camera, process them
using the `DefaultPipeline` and display them using QtWidgets.

## Requirements

The following IDS peak python packages are required:

* `ids-peak`
* `ids-peak-common`
* `ids-peak-icv`

Aswell as other dependencies:

* `pyside6`

To install all required dependencies, use the provided `requirements.txt`:

```
pip install -r requirements.txt
```

In addition, a suitable GenTL producer must be installed, for example via the
[IDS peak Setup](https://en.ids-imaging.com/download-peak.html).

## Running the example

After installing all requirements the demo can be run by executing `main.py` with the Python interpreter

```
python main.py
```

or, if Python files (*.py) are associated with the Python interpreter, by double-clicking the file.
