"""VTK pipelines for image display + mask overlay.

Put here:
- build pipeline:
  - vtkImageReslice / vtkImageSliceMapper
  - window/level mapping
  - mask LUT mapping + alpha
  - vtkImageBlend for overlay
- update methods for:
  - slice index change
  - window/level
  - overlay alpha
  - mask refresh (dirty slice)
"""
