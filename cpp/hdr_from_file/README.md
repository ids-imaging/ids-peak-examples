# HDR algorithm example

This example demonstrates how to generate a **High Dynamic Range (HDR)** image and a **tone‑mapped LDR** output using the `peak::icv` library.
It covers:

- Loading calibration images with multiple exposure times
- Estimating a camera response curve
- Processing captured images into an HDR composite
- Applying tone mapping to produce a viewable LDR result
- Saving HDR and LDR images with timestamped filenames

## Output Images

The HDR output image is a tiff floating point image, which cannot be trivially displayed by most viewers.

The LDR output image is a tone mapped integer image:
![LDR floating point image](data/output/tone_mapped_ldr_image.png)

As you can see there are some black spots throughout the right side of the image. Those are only visible as _black_ in
the tone mapped image. This is an effect due to over exposure in the input images.

## Documentation
For detailed information about HDR processing, response curves, and tone mapping, have a look at this
[Guide](https://en.ids-imaging.com/manuals/ids-peak/ids-peak-icv-documentation/en/guide_hdr.html)
provided in the library documentation.
