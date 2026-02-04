![Image of IDS peak](.github/ids_peak.png)
# IDS peak – Example Repository

This repository contains example projects demonstrating how to use `IDS peak` across multiple programming languages.

This collection aims to provide minimal, easy-to-understand examples that show how to interact with IDS cameras using `IDS peak`.

> Note: The full set of example projects is currently available only in the [IDS peak Setup](https://en.ids-imaging.com/download-peak.html).
> Additional samples are being gradually migrated into this repository.


## Available Languages
- [**C++ (C++14)**](cpp)
- [**C# (.NET Standard 2.0, examples may target .NET Framework or .NET 5+)**](csharp)
- [**Python**](python)
- [**C++**](cpp)

## Prerequisites
- [IDS peak Setup](https://en.ids-imaging.com/download-peak.html)
- IDS camera
- Suitable toolchain for each language (described in each subfolder)

## API Overview

### Generic / ComfortC

IDS peak offers two SDK programming interfaces:
- The IDS peak generic SDK
- The IDS peak comfort SDK

> Note: It is not possible to mix the IDS peak comfortSDK and IDS peak genericSDK programming interfaces in the same application.

#### Generic SDK
IDS peak genericSDK allows programming in C++, .NET (incl. C#), C or Python.
The generic SDK offers complete control over the GenICam standard.

#### Comfort SDK
IDS peak comfortC provides access to the complete set of features that is required to operate IDS cameras.
The main objective of IDS peak comfortC is to encapsulate the underlying GenICam standard technology and to free the user from the requirement to have a deeper understanding of the GenICam standard and its abstract paradigms.

Technically IDS peak comfortC encapsulates the IDS peak genericSDK as its Backend.
IDS **only** offers this for the `C` programming language.


### IDS peak API
Application programming interface (API) that provides convenient access to all associated libraries (GenAPI, GenTL, etc.). The core task of the IDS peak API is the communication with the camera, the camera parametrization and the transfer of the image data to the computer.

Click [here](https://de.ids-imaging.com/manuals/ids-peak/ids-peak-api-documentation/en/index.html) for the IDS peak API documentation.

### IDS peak AFL
The auto feature library (AFL) is a library for auto features on the computer (host-based). With the IDS peak AFL, you can e.g. use the autofocus features of the uEye+ LE USB 3.1 AF Rev. 1.2.

Click [here](https://de.ids-imaging.com/manuals/ids-peak/ids-peak-afl-documentation/en/index.html) for the IDS peak AFL documentation.

### IDS peak ICV
The industrial computer vision library (ICV) is a library for image processing. The image pipeline provides a modular processing of raw sensor data through a series of configurable transformation stages. The library supports a wide range of image processing operations, from simple format conversions to advanced enhancement algorithms.

Click [here](https://de.ids-imaging.com/manuals/ids-peak/ids-peak-icv-documentation/en/index.html) for the IDS peak ICV documentation.

### IDS peak IPL
> Note: The IDS peak image processing library (IPL) is still supported for existing projects, while the IDS peak ICV library will be further developed in the future. We recommend using the functions of IDS peak ICV for new developments.

This is a library for high-performance image processing on the computer (Image Processing Library). The IDS peak IPL can be used, for example, to convert camera image that were captured via the IDS peak API from RAW Bayer format into color (debayering).

Click [here](https://de.ids-imaging.com/manuals/ids-peak/ids-peak-ipl-documentation/en/index.html) for the IDS peak IPL documentation.


## Documentation
Official manual describing both camera and programming related topics can be found [here](https://en.ids-imaging.com/manuals/ids-peak/ids-peak-user-manual/en/index.html).

### SDK Documentation:
- [IDS peak API](https://de.ids-imaging.com/manuals/ids-peak/ids-peak-api-documentation/en/index.html)
- [IDS peak AFL](https://de.ids-imaging.com/manuals/ids-peak/ids-peak-afl-documentation/en/index.html)
- [IDS peak ICV](https://de.ids-imaging.com/manuals/ids-peak/ids-peak-icv-documentation/en/index.html)
- [IDS peak IPL](https://de.ids-imaging.com/manuals/ids-peak/ids-peak-ipl-documentation/en/index.html)
- [IDS peak ComfortC](https://de.ids-imaging.com/manuals/ids-peak/ids-peak-comfortsdk-documentation/en/index.html)

## Support & Feedback
For feedback or issues strictly regarding the IDS peak examples, please [open an issue](https://github.com/ids-imaging/ids-peak-examples/issues/new).

For general feedback or support regarding the IDS peak SDK, please contact us here:
- Support: support@ids-imaging.com
- Feedback: peak-feedback@ids-imaging.com

## Contributing
Contributions are always welcome!

See [CONTRIBUTING.md](CONTRIBUTING.md) for ways to get started.
