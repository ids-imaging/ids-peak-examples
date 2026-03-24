# Node Polling Example

This example demonstrates how node polling is used to regularly
invalidate GenICam nodes that implement the PollingTime feature,
ensuring that cached values stay up to date.

The application:
- Initializes the IDS peak library
- Detects and opens the first available device
- Prepares and starts image acquisition
- Starts a background thread to periodically poll the nodes
- Enables automatic exposure control (ExposureAuto = Continuous)
- Continuously reads and prints the current exposure time along with
  polling statistics

By polling the node map, nodes with a defined PollingTime are
invalidated automatically once their polling interval elapses.
This guarantees that subsequent reads (e.g., ExposureTime during
auto exposure) return values from the device instead of
cached data.


## Requirements

The following IDS peak Python packages are required:
- `ids-peak`

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
