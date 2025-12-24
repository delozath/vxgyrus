"""Use case: load a case (PNG, DICOM single, DICOM series volume).

Put here:
- high-level orchestration:
  - detect input type (file vs directory, DICOM vs PNG)
  - call infrastructure loaders
  - create domain objects (Volume/Mask/Case)
- minimal validation
"""
