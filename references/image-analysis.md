# Binary image-region measurements

## What the tool measures

`binary_components` measures connected foreground regions in a caller-supplied, nonempty two-dimensional binary mask. It reports pixel counts, component bounding boxes and centroids. It does not read an image file, choose a region of interest, segment an image, identify biological or physical classes, or certify that one region represents one real object.

The mask must be rectangular, have at most 512 rows and 512 columns, and contain at most 65,536 pixels. Values must be boolean or finite real numeric zero/one. Connectivity is 4 (shared edge) or 8 (shared edge or corner). The default is 8. A component touches the border when any foreground pixel lies on the outermost row or column.

Coordinates are zero-based `[row, column]` pixel-center indices. The bounding box is `[row_min, column_min, row_max_exclusive, column_max_exclusive]`. The pixel centroid is the mean of the foreground pixel-center indices, not a fitted geometric shape center.

## Filtering and bounded output

Border filtering is applied first when requested. The minimum-pixel filter is applied second to remaining components. The two exclusion counters are therefore mutually exclusive. Raw component/foreground totals, post-filter component/pixel totals and returned component/pixel totals are reported separately. `max_components` limits only returned component geometries; it does not change counts, filtering, or total areas. With zero, the tool still computes all aggregate statistics but returns no component geometries.

## Optional scale

To request physical measurements, supply `pixel_size=[xsize, ysize]` and a nonempty `unit` of at most 32 characters. Each scale must be an explicit positive finite real number; boolean, string and complex values are invalid. The implementation rejects products or reported areas that overflow or underflow outside positive finite floating-point range rather than clipping them.

Physical area is pixel count times `xsize * ysize`. Physical centroid is `[ (column_mean + 0.5) * xsize, (row_mean + 0.5) * ysize ]`, using the top-left pixel corner as origin. `calibration.status` is always `caller_declared_not_verified`: the tool cannot verify how a scale was measured or whether it is appropriate for the image.

## Match validation to the task

For a supplied mask and a geometry/count question, establish the mask definition, ROI boundary, foreground convention, connectivity, border rule and minimum size. Check a small known mask independently (hand arithmetic or a separate flood fill), and preserve the mask and parameters. If no physical scale is supplied, report pixels. If scale is supplied, report that it is caller-declared and unverified. This bounded task does not require inventing an original camera, instrument, specimen population or supervised train/test split.

For a real image-measurement pipeline, preserve raw pixels and acquisition metadata; define the ROI and exclusions; calibrate scale against a traceable reference under the same setup; and record transformations, threshold/preprocessing, border and connectivity rules before comparing outcomes. Validate segmentation against a suitable independent reference or annotated sample, with uncertainty based on the relevant sampling unit.

For supervised image classification, segmentation tuning, or learned enhancement, define annotation rules and disagreement, separate train/validation/test by source family (such as specimen, subject, session or batch) before tuning or augmentation, and keep related crops/augmented images within one split. Report held-out performance and failure modes. A random crop-level split can leak source-specific texture and overstate generalization.

Automated segmentation should use a mature, maintained image-processing library only when the task requires it; choose and document the algorithm, parameter selection and validation independently. This component-measurement function deliberately uses the existing SciPy dependency and adds no heavy image library.

## Backend

SciPy `ndimage.label` assigns labels using the selected centrosymmetric neighborhood structure; `find_objects` returns each label's minimal bounding slices; NumPy counts pixels by label. These operations implement connected components in the supplied mask, not semantic interpretation.

- [SciPy `ndimage.label`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.label.html)
- [SciPy `ndimage.find_objects`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.find_objects.html)
- [SciPy `ndimage.generate_binary_structure`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.generate_binary_structure.html)
