"""Domain model: Case (what the user opens/edits).

Put here:
- Case dataclass:
  - image: Volume OR 2D image wrapper (for PNG/single DICOM)
  - mask: Mask (optional for 2D; still useful)
  - source paths, study/series identifiers
  - derived artifacts (previews, cached info)
"""
