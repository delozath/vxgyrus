"""DICOM series (volume) loader using SimpleITK.

Put here:
- find series UIDs in a folder
- select series (first / best / user choice later)
- read image as SimpleITK image, then convert to numpy
- return Volume with spacing/origin/direction preserved
"""
