# What a binary mask can and cannot tell you

This fixed teaching case isolates the measurement step after a mask already exists. It contrasts two adjacency conventions, then applies a border rule and a minimum-size rule. The mask is constructed locally from a rectangle, an L-shaped region, a diagonal pair and small controls. It contains no real microscope image, specimen, particle or organism.

![Three retained components and excluded pixels in the synthetic mask](assets/components.png)

*Figure 1. Retained components and excluded pixels.* Outlines mark the retained components; colors distinguish them and grey marks excluded foreground pixels. Coordinates are zero-based columns and rows, with row 0 at the top. A [vector PDF](assets/components.pdf) is also available.

## Results

The **32 by 40** mask contains **72 foreground pixels**. It has **7 regions under 4-connectivity** and **6 under 8-connectivity**. Two pixels that touch only at a corner form separate regions under the first rule and one region under the second. The count changes because the neighborhood definition changes.

Using 8-connectivity, excluding border-touching regions first, and then requiring at least 3 pixels retains **3 regions and 68 pixels**. One border component and two undersized components are excluded. With the caller-declared pixel dimensions `[0.2, 0.3] mm`, the foreground and filtered areas are **4.32 mm²** and **4.08 mm²**. The values demonstrate unit arithmetic only; the tool does not verify calibration.

Pixel centroids use zero-based `[row, column]` pixel-center indices. Bounding boxes are half-open `[row_min, column_min, row_max, column_max]`. Physical centroids add half a pixel and use the top-left pixel corner as origin.

## Independent check

The demo uses a separate queue-based BFS to find 4- and 8-connected groups, then derives area, bounding boxes and centroids directly from the listed pixels. The rectangle has `6×7=42` pixels; the L shape has `10+12=22`. The script also checks conservation of the 72 foreground pixels, filter precedence and total area. It does not use SciPy output as the expected answer. See [results.json](results.json) and [demo.json](demo.json) for the fixed output and verification scope.

These checks support only the implementation and arithmetic on this synthetic mask. They do not validate segmentation quality, real spatial calibration, real-object counts or population claims.

## Reproduce

From the source checkout, choose a new output directory for each run:

```bash
uv run --locked python -m examples.image_analysis_demo --output /path/to/new-mask-run
uv run --locked python demos/image-analysis/build_figure.py --run /path/to/new-mask-run --output /path/to/new-figure
```

The figure uses the shared `scripts.texplot` pgfplots colors and layout helpers. TeX source, PDF, PNG and the plotted data are retained in the figure output. Inspect the rendered image at its delivered size and confirm row orientation; a build receipt is not a visual review.

## A defensible image workflow

For real-image measurement, preserve the original image, acquisition conditions and ROI, and calibrate scale against a traceable reference under the same setup. Choose thresholding, preprocessing, border and connectivity rules for the measurement target, then validate segmentation against an appropriate independent reference or annotated sample. For supervised recognition or data-driven parameter selection, split by source family—specimen, subject, session or batch—before tuning, and augment only the training partition. Related crops stay together. Measuring an already supplied mask does not require inventing these training stages.

`binary_components` accepts only an existing two-dimensional binary mask. It does not read images, select an ROI, threshold or segment pixels, or identify a species, material or object. For segmentation, choose a maintained image-processing library suited to the modality and report parameter selection and independent validation. Component counts alone do not establish real particle counts or biological abundance. See the complete [image-analysis method contract](../../references/image-analysis.md).
